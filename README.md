# CSV to SQL Server Uploader (v1)

Simple FastAPI app to upload a CSV, preview top 10 rows, map to a schema file, and insert into SQL Server using chunked, transactional, parameterized queries.

## Prereqs
- Python 3.11+
- ODBC Driver 17 or 18 for SQL Server
- SQL Server reachable from your machine

## Setup
1) Create a virtualenv and install deps:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Create `.env` from `.env.example` and fill in SQL Server values.

3) Put schema files in `schemas/` as `.txt` JSON files.

## Run
```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

## Notes
- Upload size limit is controlled by `MAX_UPLOAD_MB`.
- Chunk size is controlled by `CHUNK_SIZE`.
- Uploaded CSVs are stored under `tmp_uploads/` and removed after successful insert.
