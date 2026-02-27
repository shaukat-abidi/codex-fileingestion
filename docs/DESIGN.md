# CSV → SQL Server Uploader

## Design Document (v1)

------------------------------------------------------------------------

## 1. Purpose

This document defines the architecture, design decisions, API contracts,
validation rules, and implementation plan for a simple web application
that:

1.  Uploads a CSV file\
2.  Displays the top 10 rows\
3.  Loads a target SQL Server table schema from a `.txt` file\
4.  Allows user-driven column mapping and type selection\
5.  Inserts CSV data into a SQL Server table

This document serves as the **single source of truth** for Codex to
implement the system.

------------------------------------------------------------------------

## 2. Scope

### Included (v1)

-   Single-page web application
-   CSV upload
-   Preview top 10 rows
-   Load schema from local `.txt` file
-   Manual column mapping UI
-   Target type override UI
-   Insert into SQL Server
-   Basic validation
-   Transactional insert
-   Chunked inserts for performance

### Excluded (Out of Scope)

-   Authentication / login
-   Role-based access
-   Upserts / merge logic
-   Data deduplication
-   Background jobs
-   Very large file streaming optimizations
-   Advanced data cleansing
-   Complex transformation rules
-   Production hardening

------------------------------------------------------------------------

## 3. Technology Stack

### Backend

-   Python 3.11+
-   FastAPI
-   pyodbc
-   pandas (for preview and CSV parsing)
-   python-dotenv
-   Uvicorn

### Frontend

-   Static HTML
-   Vanilla JavaScript
-   Optional: Bootstrap CSS

### Database

-   Microsoft SQL Server
-   ODBC Driver 17 or 18

------------------------------------------------------------------------

## 4. System Architecture

Browser (Frontend) - Upload CSV - Load schema - Configure mapping -
Submit upload request

FastAPI Backend - Stores uploaded CSV temporarily - Reads schema from
`schemas/` - Validates mapping and types - Performs type casting -
Inserts rows into SQL Server (chunked) - Returns structured response

SQL Server - Receives parameterized inserts - Transaction committed or
rolled back

------------------------------------------------------------------------

## 5. User Flow

### Step 1 -- Upload CSV

User selects CSV file and clicks "Load CSV". Backend returns: -
file_id - CSV headers - top 10 rows - optional total row count

### Step 2 -- Load Schema

User selects a schema file. Backend loads schema definition and
returns: - table name - target columns - default types - nullable flags

### Step 3 -- Map Columns

For each target column: - Select CSV column (dropdown) - Select target
type (dropdown) - Nullable indicator shown

Validation rules: - Non-nullable target columns must be mapped - CSV
column must exist - Types must be valid

### Step 4 -- Upload

User clicks "Upload to SQL Server". Backend: - Validates mapping - Reads
CSV - Converts values - Inserts in chunks - Returns success or
structured error

------------------------------------------------------------------------

## 6. Schema File Format

Schemas are stored in `schemas/` folder as `.txt` files.

Each file contains JSON.

Example:

``` json
{
  "table": "dbo.Customer",
  "columns": [
    {"name": "CustomerId", "type": "INT", "nullable": false},
    {"name": "FirstName", "type": "NVARCHAR(100)", "nullable": true},
    {"name": "LastName", "type": "NVARCHAR(100)", "nullable": true},
    {"name": "DOB", "type": "DATE", "nullable": true},
    {"name": "IsActive", "type": "BIT", "nullable": false}
  ]
}
```

Rules: - table is required - columns must be a list - name, type,
nullable are required - type must be valid SQL Server type string

Table name must come from schema file only.

User cannot override table name.

------------------------------------------------------------------------

## 7. Data Type Conversion Rules

Empty strings → NULL.

Supported types:

INT, BIGINT → Python int\
FLOAT, REAL → Python float\
DECIMAL(p,s), NUMERIC(p,s) → Decimal\
BIT → Accept: 0,1,true,false,yes,no\
DATE → Expect ISO format YYYY-MM-DD\
DATETIME, DATETIME2 → Expect ISO datetime\
NVARCHAR(n), VARCHAR(n), CHAR(n) → string

If conversion fails: - Upload fails - Return first N (e.g., 10) errors -
Transaction rolled back

------------------------------------------------------------------------

## 8. Insert Strategy

-   Use pyodbc
-   fast_executemany = True
-   Parameterized query
-   Insert in chunks (default 2000 rows)
-   Wrap entire operation in transaction

Example SQL:

INSERT INTO dbo.Customer (\[CustomerId\], \[FirstName\], \[DOB\]) VALUES
(?, ?, ?)

Only mapped columns are inserted.

------------------------------------------------------------------------

## 9. API Design

### 1. POST /api/csv/upload

Request: multipart/form-data\
file field: "file"

Response: { "file_id": "uuid", "columns": \["col1", "col2"\],
"preview_rows": \[ {"col1": "1", "col2": "Ali"} \], "total_rows": 1000 }

------------------------------------------------------------------------

### 2. GET /api/schema/list

Response: { "schemas": \["customer_table.txt"\] }

------------------------------------------------------------------------

### 3. GET /api/schema/{schema_name}

Response: { "table": "dbo.Customer", "columns": \[...\] }

------------------------------------------------------------------------

### 4. POST /api/upload/run

Request: { "file_id": "uuid", "schema_name": "customer_table.txt",
"mappings": \[ { "target_col": "CustomerId", "csv_col": "CustomerId",
"target_type": "INT" } \] }

Response (success): { "status": "success", "rows_inserted": 12034 }

Response (error): { "status": "error", "message": "Validation failed",
"details": \["Error description"\] }

------------------------------------------------------------------------

## 10. Project Structure

    csv_sql_uploader/
      app/
        main.py
        api/
          csv_routes.py
          schema_routes.py
          upload_routes.py
        services/
          csv_service.py
          schema_service.py
          mapping_service.py
          sql_service.py
          type_casting.py
        models/
          dto.py
        static/
          index.html
          app.js
          styles.css
      schemas/
        customer_table.txt
      tmp_uploads/
      docs/
        DESIGN.md
      .env.example
      requirements.txt
      README.md

------------------------------------------------------------------------

## 11. Configuration

Use `.env` file.

Variables:

SQLSERVER_HOST\
SQLSERVER_DATABASE\
SQLSERVER_USERNAME\
SQLSERVER_PASSWORD\
SQLSERVER_DRIVER\
UPLOAD_DIR\
SCHEMA_DIR

Connection string constructed in backend.

------------------------------------------------------------------------

## 12. Validation Rules

Before upload:

1.  Schema must exist.
2.  file_id must exist.
3.  Non-nullable target columns must be mapped.
4.  Mapped CSV columns must exist in CSV.
5.  target_type must be valid SQL type string.
6.  Table name must match schema file.

------------------------------------------------------------------------

## 13. Security Controls (Basic)

-   Only load schema files from SCHEMA_DIR.
-   Restrict upload to .csv extension.
-   Enforce max file size.
-   Use parameterized SQL.
-   No dynamic SQL table names.
-   Store uploads in temp folder.
-   Delete file after successful upload.

------------------------------------------------------------------------

## 14. Error Handling Strategy

-   Fail-fast on validation errors.
-   Fail entire transaction on conversion error.
-   Return structured JSON errors.
-   Log internal errors to console.

------------------------------------------------------------------------

## 15. Acceptance Criteria

System is considered complete when:

-   CSV uploads successfully.
-   Top 10 rows display correctly.
-   Schema loads correctly.
-   Mapping UI functions correctly.
-   Data inserts correctly.
-   Errors are reported clearly.
-   Transaction rolls back on failure.

------------------------------------------------------------------------

## 16. Implementation Phases

Phase 1 -- Scaffold FastAPI app\
Phase 2 -- Implement schema endpoints\
Phase 3 -- Implement CSV upload + preview\
Phase 4 -- Build frontend mapping grid\
Phase 5 -- Implement validation + casting\
Phase 6 -- Implement chunked insert\
Phase 7 -- Add cleanup + error handling

------------------------------------------------------------------------

## 17. Future Enhancements (Not v1)

-   Authentication
-   Async background job
-   Progress bar
-   Row-level error report CSV
-   Upsert mode
-   Direct schema read from SQL Server
-   Auto type inference
-   Data quality rules

------------------------------------------------------------------------

End of document.
