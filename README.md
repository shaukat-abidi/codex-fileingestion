# CSV to SQL Server Uploader (v1)

Simple FastAPI app to upload a CSV, preview top 5 rows, define table/mapping in UI, and insert into SQL Server using chunked, transactional, parameterized queries.

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

## Run
```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

## Notes
- Upload size limit is controlled by `MAX_UPLOAD_MB`.
- Chunk size is controlled by `CHUNK_SIZE`.
- Uploaded CSVs are stored under `tmp_uploads/` and removed after successful insert.

## Manual test flow
1) Upload a CSV and confirm preview shows 5 rows.
2) In Load Schema, enter `schema.table` and click `Generate Schema`; mapping grid should populate from CSV columns without DB calls.
3) Upload to a table that does not exist; app should create table from mappings and insert rows.
4) Upload the same CSV again to the same table; app should append rows.
5) Enter an invalid table name (for example `dbo.Customer;DROP`) and confirm request is rejected.
