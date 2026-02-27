from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CsvUploadResponse(BaseModel):
    file_id: str
    columns: list[str]
    preview_rows: list[dict[str, Any]]
    total_rows: int | None = None


class SchemaColumn(BaseModel):
    name: str
    type: str
    nullable: bool


class SchemaResponse(BaseModel):
    table: str
    columns: list[SchemaColumn]


class SchemaListResponse(BaseModel):
    schemas: list[str]


class MappingItem(BaseModel):
    target_col: str = Field(..., min_length=1)
    csv_col: str | None = None
    target_type: str = Field(..., min_length=1)


class UploadRunRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    file_id: str
    schema_name: str | None = None
    upload_schema: SchemaResponse | None = Field(default=None, alias="schema")
    mappings: list[MappingItem]


class UploadRunResponse(BaseModel):
    status: str
    rows_inserted: int | None = None
    message: str | None = None
    details: list[str] | None = None
