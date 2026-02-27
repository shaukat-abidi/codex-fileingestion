import os

from fastapi import APIRouter, HTTPException

from app.models.dto import UploadRunRequest, UploadRunResponse
from app.services import csv_service, mapping_service, schema_service, sql_service, type_casting

router = APIRouter()


@router.post("/upload/run", response_model=UploadRunResponse)
def run_upload(request: UploadRunRequest):
    upload_dir = csv_service.get_upload_dir()
    file_path = os.path.join(upload_dir, f"{request.file_id}.csv")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="file_id not found")

    if request.upload_schema is not None:
        schema = request.upload_schema.model_dump()
        if not schema.get("table"):
            raise HTTPException(status_code=400, detail="Schema table is required")
        for col in schema.get("columns", []):
            if not col.get("name"):
                raise HTTPException(status_code=400, detail="Schema column name is required")
            if not type_casting.is_supported_type(col.get("type", "")):
                raise HTTPException(status_code=400, detail=f"Unsupported type: {col.get('type')}")
            if not isinstance(col.get("nullable"), bool):
                raise HTTPException(status_code=400, detail="Schema column nullable must be boolean")
    elif request.schema_name:
        schema = schema_service.get_schema(request.schema_name)
    else:
        raise HTTPException(status_code=400, detail="Provide schema or schema_name")
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
