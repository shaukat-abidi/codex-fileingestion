import os

from fastapi import APIRouter, HTTPException

from app.models.dto import UploadRunRequest, UploadRunResponse
from app.services import csv_service, mapping_service, schema_service, sql_service

router = APIRouter()


@router.post("/upload/run", response_model=UploadRunResponse)
def run_upload(request: UploadRunRequest):
    upload_dir = csv_service.get_upload_dir()
    file_path = os.path.join(upload_dir, f"{request.file_id}.csv")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="file_id not found")

    schema = schema_service.get_schema(request.schema_name)
    csv_columns = csv_service.get_csv_columns(file_path)

    mappings = mapping_service.validate_mappings(
        schema=schema,
        csv_columns=csv_columns,
        mappings=[m.model_dump() for m in request.mappings],
    )

    try:
        rows_inserted = sql_service.insert_csv(
            file_path=file_path,
            schema=schema,
            mappings=mappings,
        )
    except sql_service.ConversionError as exc:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "Conversion failed", "details": exc.details},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"status": "error", "message": "Insert failed", "details": [str(exc)]},
        )

    try:
        os.remove(file_path)
    except OSError:
        pass

    return UploadRunResponse(status="success", rows_inserted=rows_inserted)
