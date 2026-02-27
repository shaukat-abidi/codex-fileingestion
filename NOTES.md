# Session Notes

Logout timestamp: 2026-02-26 17:07:39 AEDT

Summary
- Implemented FastAPI backend with CSV upload/preview, schema loading, mapping validation, and SQL Server chunked inserts.
- Added static frontend (HTML/JS/CSS) with mapping UI and API wiring.
- Added config files (.env.example, requirements.txt, .gitignore) and README.
- Added sample schema and sample CSV for testing.

Key files
- app/main.py
- app/api/csv_routes.py
- app/api/schema_routes.py
- app/api/upload_routes.py
- app/services/csv_service.py
- app/services/schema_service.py
- app/services/mapping_service.py
- app/services/sql_service.py
- app/services/type_casting.py
- app/models/dto.py
- app/static/index.html
- app/static/app.js
- app/static/styles.css
- schemas/customer_table.txt
- sample_data/customer.csv

Run
- Create .env from .env.example
- uvicorn app.main:app --reload
