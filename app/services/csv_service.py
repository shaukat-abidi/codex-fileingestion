import logging
import os
import uuid

import pandas as pd
from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)


def _get_env_int(name: str, default_value: int) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default_value
    try:
        return int(value)
    except ValueError:
        return default_value


def get_upload_dir() -> str:
    upload_dir = os.getenv("UPLOAD_DIR", "tmp_uploads")
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


async def save_upload(upload_file: UploadFile) -> dict:
    if not upload_file.filename or not upload_file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are allowed")

    max_mb = _get_env_int("MAX_UPLOAD_MB", 20)
    max_bytes = max_mb * 1024 * 1024

    upload_dir = get_upload_dir()
    file_id = str(uuid.uuid4())
    file_path = os.path.join(upload_dir, f"{file_id}.csv")

    total_bytes = 0
    try:
        with open(file_path, "wb") as f:
            while True:
                chunk = await upload_file.read(1024 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large; max {max_mb} MB",
                    )
                f.write(chunk)
    finally:
        await upload_file.close()

    df = pd.read_csv(file_path, nrows=10, dtype=str, keep_default_na=False, na_filter=False)
    preview_rows = df.to_dict(orient="records")
    columns = list(df.columns)

    total_rows = None
    count_rows = os.getenv("COUNT_TOTAL_ROWS", "true").lower() == "true"
    if count_rows:
        with open(file_path, "rb") as f:
            total_rows = max(sum(1 for _ in f) - 1, 0)

    logger.info("Uploaded CSV %s (%d bytes)", file_id, total_bytes)

    return {
        "file_id": file_id,
        "columns": columns,
        "preview_rows": preview_rows,
        "total_rows": total_rows,
    }


def get_csv_columns(file_path: str) -> list[str]:
    df = pd.read_csv(file_path, nrows=0, dtype=str)
    return list(df.columns)
