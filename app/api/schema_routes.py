from fastapi import APIRouter

from app.models.dto import SchemaListResponse, SchemaResponse
from app.services import schema_service

router = APIRouter()


@router.get("/schema/list", response_model=SchemaListResponse)
def list_schemas():
    schemas = schema_service.list_schemas()
    return SchemaListResponse(schemas=schemas)


@router.get("/schema/{schema_name}", response_model=SchemaResponse)
def get_schema(schema_name: str):
    schema = schema_service.get_schema(schema_name)
    return SchemaResponse(**schema)
