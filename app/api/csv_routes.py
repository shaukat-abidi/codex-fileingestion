from fastapi import APIRouter, File, UploadFile

from app.models.dto import CsvUploadResponse
from app.services import csv_service

router = APIRouter()


@router.post("/csv/upload", response_model=CsvUploadResponse)
async def upload_csv(file: UploadFile = File(...)):
    result = await csv_service.save_upload(file)
    return CsvUploadResponse(**result)
