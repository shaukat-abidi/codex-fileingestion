const state = {
  fileId: null,
  csvColumns: [],
  previewRows: [],
  schema: null,
};

const typeOptions = [
  "INT",
  "BIGINT",
  "FLOAT",
  "REAL",
  "DECIMAL(18,2)",
  "NUMERIC(18,2)",
  "BIT",
  "DATE",
  "DATETIME",
  "DATETIME2",
  "NVARCHAR(100)",
  "VARCHAR(100)",
  "CHAR(10)",
];

const statusBody = document.getElementById("status-body");
const csvMeta = document.getElementById("csv-meta");
const schemaMeta = document.getElementById("schema-meta");
const preview = document.getElementById("preview");
const mappingGrid = document.getElementById("mapping-grid");
const schemaBuilder = document.getElementById("schema-builder");
const tableNameInput = document.getElementById("table-name");
const uploadResult = document.getElementById("upload-result");

function setStatus(text, tone = "neutral") {
  statusBody.textContent = text;
  statusBody.className = `status-body ${tone}`;
}

function renderPreview(columns, rows) {
  if (!rows || rows.length === 0) {
    preview.innerHTML = "<p>No preview rows.</p>";
    return;
  }

  const table = document.createElement("table");
  table.className = "preview-table";

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  columns.forEach((col) => {
    const th = document.createElement("th");
    th.textContent = col;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    columns.forEach((col) => {
      const td = document.createElement("td");
      td.textContent = row[col] ?? "";
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);

  preview.innerHTML = "";
  preview.appendChild(table);
}

function renderSchemaBuilder() {
  schemaBuilder.innerHTML = "";
  if (state.csvColumns.length === 0) {
    schemaBuilder.innerHTML = "<p class='meta'>Upload a CSV to configure schema columns.</p>";
    schemaMeta.textContent = "Waiting for CSV upload.";
    return;
  }

  const table = document.createElement("table");
  table.className = "mapping-table";

  const head = document.createElement("thead");
  head.innerHTML = `
    <tr>
      <th>Use</th>
      <th>CSV Column</th>
      <th>Target Column</th>
      <th>Target Type</th>
      <th>Nullable</th>
    </tr>
  `;
  table.appendChild(head);

  const body = document.createElement("tbody");
  state.csvColumns.forEach((col) => {
    const tr = document.createElement("tr");

    const useCell = document.createElement("td");
    useCell.innerHTML = `<input type="checkbox" class="schema-use" data-csv-col="${col}" checked />`;
    tr.appendChild(useCell);

    const csvCell = document.createElement("td");
    csvCell.textContent = col;
    tr.appendChild(csvCell);

    const targetCell = document.createElement("td");
    targetCell.innerHTML = `<input type="text" class="schema-target-col" data-csv-col="${col}" value="${col}" />`;
    tr.appendChild(targetCell);

    const typeCell = document.createElement("td");
    const typeSelect = document.createElement("select");
    typeSelect.className = "schema-target-type";
    typeSelect.dataset.csvCol = col;
    typeOptions.forEach((t) => {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t;
      if (t === "NVARCHAR(100)") {
        opt.selected = true;
      }
      typeSelect.appendChild(opt);
    });
    typeCell.appendChild(typeSelect);
    tr.appendChild(typeCell);

    const nullableCell = document.createElement("td");
    nullableCell.innerHTML = `<input type="checkbox" class="schema-nullable" data-csv-col="${col}" checked />`;
    tr.appendChild(nullableCell);

    body.appendChild(tr);
  });

  table.appendChild(body);
  schemaBuilder.appendChild(table);
  schemaMeta.textContent = `Ready to configure ${state.csvColumns.length} columns. Set table name then click Refresh.`;
}

function buildSchemaFromUi() {
  if (!tableNameInput) {
    throw new Error("UI is out of date. Hard refresh the page (Ctrl+Shift+R).");
  }
  const tableName = tableNameInput.value.trim();
  if (!tableName) {
    throw new Error("Table name is required");
  }

  const columns = [];
  schemaBuilder.querySelectorAll("tbody tr").forEach((row) => {
    const use = row.querySelector(".schema-use").checked;
    if (!use) {
      return;
    }

    const sourceCsv = row.querySelector(".schema-use").dataset.csvCol;
    const targetCol = row.querySelector(".schema-target-col").value.trim();
    const targetType = row.querySelector(".schema-target-type").value;
    const nullable = row.querySelector(".schema-nullable").checked;

    if (!targetCol) {
      return;
    }

    columns.push({ name: targetCol, type: targetType, nullable, source_csv: sourceCsv });
  });

  if (columns.length === 0) {
    throw new Error("Select at least one schema column");
  }

  state.schema = { table: tableName, columns };
}

function renderMappingGrid() {
  mappingGrid.innerHTML = "";
  if (!state.schema) {
    mappingGrid.innerHTML = "<p class='meta'>Define schema and click Refresh to populate mappings.</p>";
    return;
  }

  const table = document.createElement("table");
  table.className = "mapping-table";

  const head = document.createElement("thead");
  head.innerHTML = `
    <tr>
      <th>Target Column</th>
      <th>Nullable</th>
      <th>CSV Column</th>
      <th>Target Type</th>
    </tr>
  `;
  table.appendChild(head);

  const body = document.createElement("tbody");
  state.schema.columns.forEach((col) => {
    const tr = document.createElement("tr");

    const targetCell = document.createElement("td");
    targetCell.textContent = col.name;
    tr.appendChild(targetCell);

    const nullableCell = document.createElement("td");
    nullableCell.textContent = col.nullable ? "Yes" : "No";
    tr.appendChild(nullableCell);

    const csvCell = document.createElement("td");
    const csvSelect = document.createElement("select");
    csvSelect.className = "mapping-csv-col";
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "-- not mapped --";
    csvSelect.appendChild(empty);

    state.csvColumns.forEach((csvCol) => {
      const opt = document.createElement("option");
      opt.value = csvCol;
      opt.textContent = csvCol;
      if (csvCol === col.source_csv || csvCol.toLowerCase() === col.name.toLowerCase()) {
        opt.selected = true;
      }
      csvSelect.appendChild(opt);
    });
    csvCell.appendChild(csvSelect);
    tr.appendChild(csvCell);

    const typeCell = document.createElement("td");
    const typeSelect = document.createElement("select");
    typeSelect.className = "mapping-target-type";
    typeOptions.forEach((t) => {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t;
      if (t.toUpperCase() === col.type.toUpperCase()) {
        opt.selected = true;
      }
      typeSelect.appendChild(opt);
    });
    typeCell.appendChild(typeSelect);
    tr.appendChild(typeCell);

    body.appendChild(tr);
  });

  table.appendChild(body);
  mappingGrid.appendChild(table);
}

document.getElementById("upload-btn").addEventListener("click", async () => {
  const fileInput = document.getElementById("csv-file");
  if (!fileInput.files.length) {
    setStatus("Select a CSV first.", "warn");
    return;
  }

  setStatus("Uploading CSV...");
  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  const res = await fetch("/api/csv/upload", {
    method: "POST",
    body: formData,
  });

  const data = await res.json();
  if (!res.ok) {
    setStatus("CSV upload failed", "err");
    csvMeta.textContent = data.detail || "Upload failed";
    return;
  }

  state.fileId = data.file_id;
  state.csvColumns = data.columns;
  state.previewRows = data.preview_rows;
  state.schema = null;

  csvMeta.textContent = `File ID: ${data.file_id} | Columns: ${data.columns.length} | Total rows: ${data.total_rows ?? "n/a"}`;
  renderPreview(data.columns, data.preview_rows);
  renderSchemaBuilder();
  renderMappingGrid();
  setStatus("CSV ready", "ok");
});

document.getElementById("refresh-schemas").addEventListener("click", () => {
  try {
    buildSchemaFromUi();
    schemaMeta.textContent = `Table: ${state.schema.table} | Columns: ${state.schema.columns.length}`;
    renderMappingGrid();
    setStatus("Schema configured", "ok");
  } catch (err) {
    setStatus("Schema configuration failed", "err");
    schemaMeta.textContent = err.message;
  }
});

document.getElementById("run-upload").addEventListener("click", async () => {
  if (!state.fileId) {
    setStatus("Upload a CSV first.", "warn");
    return;
  }
  if (!state.schema) {
    setStatus("Define schema and click Refresh first.", "warn");
    return;
  }

  const mappings = [];
  mappingGrid.querySelectorAll("tbody tr").forEach((row) => {
    const targetCol = row.children[0].textContent.trim();
    const csvCol = row.querySelector(".mapping-csv-col").value || null;
    const targetType = row.querySelector(".mapping-target-type").value;
    mappings.push({ target_col: targetCol, csv_col: csvCol, target_type: targetType });
  });

  setStatus("Uploading to SQL Server...");
  const res = await fetch("/api/upload/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      file_id: state.fileId,
      schema: {
        table: state.schema.table,
        columns: state.schema.columns.map((c) => ({
          name: c.name,
          type: c.type,
          nullable: c.nullable,
        })),
      },
      mappings,
    }),
  });

  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail || {};
    uploadResult.textContent = detail.message || "Upload failed";
    if (detail.details) {
      uploadResult.textContent += ` | ${detail.details.join("; ")}`;
    }
    setStatus("Upload failed", "err");
    return;
  }

  uploadResult.textContent = `Inserted ${data.rows_inserted} rows.`;
  setStatus("Upload complete", "ok");
});

renderSchemaBuilder();
renderMappingGrid();
