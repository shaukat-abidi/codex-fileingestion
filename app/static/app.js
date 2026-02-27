const state = {
  fileId: null,
  csvColumns: [],
  previewRows: [],
  table: null,
  mappings: [],
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
  "NVARCHAR(255)",
  "NVARCHAR(100)",
  "VARCHAR(100)",
  "CHAR(10)",
];

const statusBody = document.getElementById("status-body");
const csvMeta = document.getElementById("csv-meta");
const schemaMeta = document.getElementById("schema-meta");
const preview = document.getElementById("preview");
const mappingGrid = document.getElementById("mapping-grid");
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

function initializeMappings() {
  state.mappings = state.csvColumns.map((col) => ({
    target_col: col,
    csv_col: col,
    target_type: "NVARCHAR(255)",
  }));
}

function renderMappingGrid() {
  mappingGrid.innerHTML = "";
  if (!state.table || state.mappings.length === 0) {
    mappingGrid.innerHTML = "<p class='meta'>Enter table name and click Generate Schema.</p>";
    return;
  }

  const table = document.createElement("table");
  table.className = "mapping-table";

  const head = document.createElement("thead");
  head.innerHTML = `
    <tr>
      <th>Target Column</th>
      <th>CSV Column</th>
      <th>Target Type</th>
    </tr>
  `;
  table.appendChild(head);

  const body = document.createElement("tbody");
  state.mappings.forEach((map) => {
    const tr = document.createElement("tr");

    const targetCell = document.createElement("td");
    const targetInput = document.createElement("input");
    targetInput.type = "text";
    targetInput.className = "mapping-target-col";
    targetInput.value = map.target_col;
    targetCell.appendChild(targetInput);
    tr.appendChild(targetCell);

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
      if (csvCol === map.csv_col) {
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
      if (t.toUpperCase() === map.target_type.toUpperCase()) {
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

function collectMappingsFromGrid() {
  const mappings = [];
  mappingGrid.querySelectorAll("tbody tr").forEach((row) => {
    const targetCol = row.querySelector(".mapping-target-col").value.trim();
    const csvCol = row.querySelector(".mapping-csv-col").value || null;
    const targetType = row.querySelector(".mapping-target-type").value;
    mappings.push({ target_col: targetCol, csv_col: csvCol, target_type: targetType });
  });
  return mappings;
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
  state.table = null;
  state.mappings = [];

  csvMeta.textContent = `File ID: ${data.file_id} | Columns: ${data.columns.length} | Preview rows: ${data.preview_rows.length}`;
  renderPreview(data.columns, data.preview_rows);
  renderMappingGrid();
  schemaMeta.textContent = "Enter target table name, then click Generate Schema.";
  setStatus("CSV ready", "ok");
});

document.getElementById("refresh-schemas").addEventListener("click", () => {
  const table = tableNameInput.value.trim();
  if (!state.fileId) {
    setStatus("Upload a CSV first.", "warn");
    return;
  }
  if (!table) {
    setStatus("Table name required", "warn");
    schemaMeta.textContent = "Enter target table name";
    return;
  }

  state.table = table;
  initializeMappings();
  renderMappingGrid();
  schemaMeta.textContent = `Target table: ${state.table}`;
  setStatus("Schema generated", "ok");
});

document.getElementById("run-upload").addEventListener("click", async () => {
  if (!state.fileId) {
    setStatus("Upload a CSV first.", "warn");
    return;
  }
  if (!state.table) {
    setStatus("Generate schema first.", "warn");
    return;
  }

  const mappings = collectMappingsFromGrid();

  setStatus("Uploading to SQL Server...");
  const res = await fetch("/api/upload/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      file_id: state.fileId,
      table: state.table,
      mappings,
    }),
  });

  const data = await res.json();
  if (!res.ok) {
    const detail = data.detail || {};
    uploadResult.textContent = detail.message || data.detail || "Upload failed";
    if (detail.details) {
      uploadResult.textContent += ` | ${detail.details.join("; ")}`;
    }
    setStatus("Upload failed", "err");
    return;
  }

  uploadResult.textContent = `Inserted ${data.rows_inserted} rows.`;
  setStatus("Upload complete", "ok");
});

renderMappingGrid();
schemaMeta.textContent = "Upload CSV first.";
