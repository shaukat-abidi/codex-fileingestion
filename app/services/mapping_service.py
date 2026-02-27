from fastapi import HTTPException

from app.services import type_casting


def validate_mappings(schema: dict, csv_columns: list[str], mappings: list[dict]) -> list[dict]:
    schema_cols = {c["name"]: c for c in schema["columns"]}
    csv_set = set(csv_columns)
    errors = []

    mapped_targets = set()
    validated = []

    for item in mappings:
        target_col = item.get("target_col")
        csv_col = item.get("csv_col")
        target_type = item.get("target_type")

        if target_col not in schema_cols:
            errors.append(f"Unknown target column: {target_col}")
            continue

        if not target_type or not type_casting.is_supported_type(target_type):
            errors.append(f"Unsupported target type: {target_type}")
            continue

        if csv_col:
            if csv_col not in csv_set:
                errors.append(f"CSV column not found: {csv_col}")
                continue
            validated.append(
                {
                    "target_col": target_col,
                    "csv_col": csv_col,
                    "target_type": target_type,
                }
            )
            mapped_targets.add(target_col)

    for col in schema["columns"]:
        if not col["nullable"] and col["name"] not in mapped_targets:
            errors.append(f"Non-nullable target column not mapped: {col['name']}")

    if errors:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "Validation failed", "details": errors},
        )

    return validated
