import json
import os
import re

from fastapi import HTTPException

from app.services import type_casting

SAFE_SCHEMA_RE = re.compile(r"^[A-Za-z0-9_.-]+\.txt$")


def get_schema_dir() -> str:
    schema_dir = os.getenv("SCHEMA_DIR", "schemas")
    os.makedirs(schema_dir, exist_ok=True)
    return schema_dir


def _sanitize_schema_name(schema_name: str) -> str:
    if not SAFE_SCHEMA_RE.match(schema_name):
        raise HTTPException(status_code=400, detail="Invalid schema name")
    if os.path.basename(schema_name) != schema_name:
        raise HTTPException(status_code=400, detail="Invalid schema name")
    return schema_name


def list_schemas() -> list[str]:
    schema_dir = get_schema_dir()
    files = []
    for name in os.listdir(schema_dir):
        if name.lower().endswith(".txt"):
            files.append(name)
    return sorted(files)


def get_schema(schema_name: str) -> dict:
    schema_dir = get_schema_dir()
    schema_name = _sanitize_schema_name(schema_name)
    schema_path = os.path.realpath(os.path.join(schema_dir, schema_name))

    if not schema_path.startswith(os.path.realpath(schema_dir) + os.sep):
        raise HTTPException(status_code=400, detail="Invalid schema path")

    if not os.path.exists(schema_path):
        raise HTTPException(status_code=404, detail="Schema not found")

    with open(schema_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Schema must be an object")

    table = data.get("table")
    columns = data.get("columns")

    if not table or not isinstance(table, str):
        raise HTTPException(status_code=400, detail="Schema table is required")

    if not isinstance(columns, list):
        raise HTTPException(status_code=400, detail="Schema columns must be a list")

    validated_cols = []
    for col in columns:
        if not isinstance(col, dict):
            raise HTTPException(status_code=400, detail="Invalid column definition")
        name = col.get("name")
        col_type = col.get("type")
        nullable = col.get("nullable")
        if not name or not isinstance(name, str):
            raise HTTPException(status_code=400, detail="Column name is required")
        if not col_type or not isinstance(col_type, str):
            raise HTTPException(status_code=400, detail="Column type is required")
        if not isinstance(nullable, bool):
            raise HTTPException(status_code=400, detail="Column nullable is required")
        if not type_casting.is_supported_type(col_type):
            raise HTTPException(status_code=400, detail=f"Unsupported type: {col_type}")

        validated_cols.append({"name": name, "type": col_type, "nullable": nullable})

    return {"table": table, "columns": validated_cols}
