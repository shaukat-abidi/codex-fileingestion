import logging
import os
import re

import pandas as pd
import pyodbc

from app.services import type_casting

logger = logging.getLogger(__name__)

BRACKETED_TABLE_RE = re.compile(r"^\[([A-Za-z_][A-Za-z0-9_]*)\]\.\[([A-Za-z_][A-Za-z0-9_]*)\]$")
PLAIN_TABLE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)$")
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
UNSAFE_SQL_RE = re.compile(r"(;|--|/\*|\*/)")
UNSAFE_KEYWORDS_RE = re.compile(r"\b(DROP|ALTER|CREATE|EXEC|UNION|SELECT|INSERT|DELETE|UPDATE)\b", re.IGNORECASE)


class ConversionError(Exception):
    def __init__(self, details: list[str]):
        super().__init__("Conversion failed")
        self.details = details


class ValidationError(Exception):
    pass


def _connection_string() -> str:
    driver = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 17 for SQL Server")
    host = os.getenv("SQLSERVER_HOST", "")
    database = os.getenv("SQLSERVER_DATABASE", "")
    username = os.getenv("SQLSERVER_USERNAME", "")
    password = os.getenv("SQLSERVER_PASSWORD", "")

    if not host or not database:
        raise ValueError("SQLSERVER_HOST and SQLSERVER_DATABASE are required")

    if username and password:
        return (
            f"DRIVER={{{driver}}};"
            f"SERVER={host};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            "TrustServerCertificate=yes;"
        )

    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={host};"
        f"DATABASE={database};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )


def _normalize_identifier(identifier: str) -> str:
    value = (identifier or "").strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return value


def validate_table_name(table: str) -> str:
    value = (table or "").strip()
    match = BRACKETED_TABLE_RE.fullmatch(value) or PLAIN_TABLE_RE.fullmatch(value)
    if not match:
        raise ValidationError("Invalid table name. Use schema.table or [schema].[table]")
    schema_name, table_name = match.group(1), match.group(2)
    return f"[{schema_name}].[{table_name}]"


def validate_column_name(column: str) -> str:
    value = _normalize_identifier(column)
    if not IDENTIFIER_RE.fullmatch(value):
        raise ValidationError(f"Invalid target column name: {column}")
    return value


def validate_target_type(target_type: str) -> str:
    value = (target_type or "").strip().upper()
    if not value:
        raise ValidationError("Target type is required")
    if UNSAFE_SQL_RE.search(value) or UNSAFE_KEYWORDS_RE.search(value):
        raise ValidationError(f"Suspicious target type: {target_type}")
    if not type_casting.is_supported_type(value):
        raise ValidationError(f"Unsupported target type: {target_type}")
    return value


def _table_exists(cursor: pyodbc.Cursor, table: str) -> bool:
    safe_table = validate_table_name(table)
    schema_name, table_name = [part.strip("[]") for part in safe_table.split(".")]
    cursor.execute(
        """
        SELECT 1
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
        """,
        schema_name,
        table_name,
    )
    return cursor.fetchone() is not None


def _create_table_from_mappings(cursor: pyodbc.Cursor, table: str, mappings: list[dict]) -> None:
    safe_table = validate_table_name(table)
    column_defs = []
    seen = set()
    for mapping in mappings:
        column_name = validate_column_name(mapping["target_col"])
        if column_name.lower() in seen:
            raise ValidationError(f"Duplicate target column: {column_name}")
        seen.add(column_name.lower())
        sql_type = validate_target_type(mapping["target_type"])
        column_defs.append(f"[{column_name}] {sql_type} NULL")

    if not column_defs:
        raise ValidationError("No target columns provided")

    create_sql = f"CREATE TABLE {safe_table} ({', '.join(column_defs)})"
    cursor.execute(create_sql)


def table_exists(table: str) -> bool:
    conn = pyodbc.connect(_connection_string())
    try:
        cursor = conn.cursor()
        return _table_exists(cursor, table)
    finally:
        conn.close()


def create_table_from_mappings(table: str, mappings: list[dict]) -> None:
    conn = pyodbc.connect(_connection_string())
    conn.autocommit = False
    try:
        cursor = conn.cursor()
        _create_table_from_mappings(cursor, table, mappings)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def insert_csv(file_path: str, table: str, mappings: list[dict], chunk_size: int | None = None) -> int:
    if not mappings:
        raise ValueError("No mappings provided")

    safe_table = validate_table_name(table)
    if chunk_size is None:
        chunk_size = int(os.getenv("CHUNK_SIZE", "2000"))

    target_cols = [validate_column_name(m["target_col"]) for m in mappings]
    csv_cols = [m["csv_col"] for m in mappings]
    target_types = [validate_target_type(m["target_type"]) for m in mappings]

    placeholders = ", ".join(["?"] * len(target_cols))
    col_sql = ", ".join(f"[{c}]" for c in target_cols)
    insert_sql = f"INSERT INTO {safe_table} ({col_sql}) VALUES ({placeholders})"

    total_inserted = 0
    conn = pyodbc.connect(_connection_string())
    conn.autocommit = False

    try:
        cursor = conn.cursor()
        cursor.fast_executemany = True

        if not _table_exists(cursor, safe_table):
            _create_table_from_mappings(cursor, safe_table, mappings)

        reader = pd.read_csv(
            file_path,
            dtype=str,
            keep_default_na=False,
            na_filter=False,
            chunksize=chunk_size,
        )

        processed = 0
        for chunk in reader:
            rows = []
            errors = []

            for idx, row in enumerate(chunk[csv_cols].itertuples(index=False, name=None)):
                values = []
                row_num = processed + idx + 2
                for val, target_type in zip(row, target_types):
                    try:
                        converted = type_casting.cast_value(val, target_type, nullable=True)
                        values.append(converted)
                    except Exception as exc:  # pragma: no cover
                        errors.append(f"Row {row_num}: {exc}")
                        if len(errors) >= 10:
                            break
                if errors:
                    break
                rows.append(tuple(values))

            if errors:
                raise ConversionError(errors)

            if rows:
                cursor.executemany(insert_sql, rows)
                total_inserted += len(rows)

            processed += len(chunk)

        conn.commit()
        logger.info("Inserted %d rows into %s", total_inserted, safe_table)
        return total_inserted
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
