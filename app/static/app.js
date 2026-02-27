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
const schemaSelect = document.getElementById("schema-select");
const uploadResult = document.getElementById("upload-result");

function setStatus(text, tone = "neutral") {
  statusBody.textContent = text;
  statusBody.className = `status-body ${tone}`;
}

async function fetchSchemas() {
  setStatus("Loading schemas...");
  const res = await fetch("/api/schema/list");
  const data = await res.json();
  if (!res.ok) {
    setStatus("Failed to load schemas", "err");
    schemaMeta.textContent = data.detail || "Could not load schema list";
    schemaSelect.innerHTML = "";
    return;
  }

  schemaSelect.innerHTML = "";
  data.schemas.forEach((name) => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    schemaSelect.appendChild(opt);
  });

  if (data.schemas.length === 0) {
    state.schema = null;
    schemaMeta.textContent = "No schema files found in schemas/ directory.";
    renderMappingGrid();
    setStatus("No schemas found", "warn");
    return;
  }

  await loadSchema(schemaSelect.value);
  setStatus("Schemas loaded", "ok");
}

async function loadSchema(name) {
  if (!name) {
    return;
  }
  setStatus("Loading schema...");
  const res = await fetch(`/api/schema/${encodeURIComponent(name)}`);
  const data = await res.json();
  if (!res.ok) {
    state.schema = null;
    setStatus("Schema load failed", "err");
    schemaMeta.textContent = data.detail || "Schema load failed";
    renderMappingGrid();
    return;
  }
  state.schema = data;
  schemaMeta.textContent = `Table: ${data.table} | Columns: ${data.columns.length}`;
  renderMappingGrid();
  setStatus("Schema ready", "ok");
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

function renderMappingGrid() {
  mappingGrid.innerHTML = "";
  if (!state.schema) {
    mappingGrid.innerHTML = "<p class='meta'>Load a schema to map columns.</p>";
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
    csvSelect.dataset.targetCol = col.name;
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "-- not mapped --";
    csvSelect.appendChild(empty);
    state.csvColumns.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      if (c.toLowerCase() === col.name.toLowerCase()) {
        opt.selected = true;
      }
      csvSelect.appendChild(opt);
    });
    csvCell.appendChild(csvSelect);
    tr.appendChild(csvCell);

    const typeCell = document.createElement("td");
    const typeSelect = document.createElement("select");
    typeSelect.dataset.targetCol = col.name;
    const defaultOpt = document.createElement("option");
    defaultOpt.value = col.type;
    defaultOpt.textContent = `${col.type} (schema)`;
    defaultOpt.selected = true;
    typeSelect.appendChild(defaultOpt);

    typeOptions.forEach((t) => {
      if (t.toUpperCase() === col.type.toUpperCase()) {
        return;
      }
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t;
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

  csvMeta.textContent = `File ID: ${data.file_id} | Columns: ${data.columns.length} | Total rows: ${data.total_rows ?? "n/a"}`;
  renderPreview(data.columns, data.preview_rows);
  renderMappingGrid();
  setStatus("CSV ready", "ok");
});

document.getElementById("refresh-schemas").addEventListener("click", fetchSchemas);

schemaSelect.addEventListener("change", async () => {
  await loadSchema(schemaSelect.value);
});

document.getElementById("run-upload").addEventListener("click", async () => {
  if (!state.fileId) {
    setStatus("Upload a CSV first.", "warn");
    return;
  }
  if (!state.schema) {
    setStatus("Load a schema first.", "warn");
    return;
  }

  const mappings = [];
  mappingGrid.querySelectorAll("tbody tr").forEach((row) => {
    const targetCol = row.children[0].textContent.trim();
    const csvCol = row.querySelector("select[data-target-col]").value || null;
    const targetType = row.querySelectorAll("select[data-target-col]")[1].value;
    mappings.push({ target_col: targetCol, csv_col: csvCol, target_type: targetType });
  });

  setStatus("Uploading to SQL Server...");
  const res = await fetch("/api/upload/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      file_id: state.fileId,
      schema_name: schemaSelect.value,
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

fetchSchemas();
