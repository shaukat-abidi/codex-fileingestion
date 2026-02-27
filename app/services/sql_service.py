import logging
import os
import re

import pandas as pd
import pyodbc

from app.services import type_casting

logger = logging.getLogger(__name__)

SAFE_TABLE_RE = re.compile(r"^[A-Za-z0-9_\.\[\]]+$")


class ConversionError(Exception):
    def __init__(self, details: list[str]):
        super().__init__("Conversion failed")
        self.details = details


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


def _safe_table(table: str) -> str:
    if not SAFE_TABLE_RE.match(table):
        raise ValueError("Invalid table name")
    return table


def insert_csv(file_path: str, schema: dict, mappings: list[dict], chunk_size: int | None = None) -> int:
    if not mappings:
        raise ValueError("No mappings provided")

    table = _safe_table(schema["table"])
    schema_cols = {c["name"]: c for c in schema["columns"]}

    if chunk_size is None:
        chunk_size = int(os.getenv("CHUNK_SIZE", "2000"))

    target_cols = [m["target_col"] for m in mappings]
    csv_cols = [m["csv_col"] for m in mappings]
    target_types = [m["target_type"] for m in mappings]
    nullables = [schema_cols[m["target_col"]]["nullable"] for m in mappings]

    placeholders = ", ".join(["?"] * len(target_cols))
    col_sql = ", ".join(f"[{c}]" for c in target_cols)
    insert_sql = f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})"

    total_inserted = 0
    conn = pyodbc.connect(_connection_string())
    conn.autocommit = False

    try:
        cursor = conn.cursor()
        cursor.fast_executemany = True

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
                for val, target_type, nullable in zip(row, target_types, nullables):
                    try:
                        converted = type_casting.cast_value(val, target_type, nullable=nullable)
                        values.append(converted)
                    except Exception as exc:
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
        logger.info("Inserted %d rows into %s", total_inserted, table)
        return total_inserted
    except ConversionError:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
