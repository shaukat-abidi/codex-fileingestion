from fastapi import HTTPException

from app.services import type_casting

SAFE_IDENTIFIER_RE = r"^[A-Za-z_][A-Za-z0-9_]*$"


def _normalize_identifier(identifier: str) -> str:
    value = (identifier or "").strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return value


def _is_safe_identifier(identifier: str) -> bool:
    import re

    return bool(re.fullmatch(SAFE_IDENTIFIER_RE, _normalize_identifier(identifier)))


def _is_safe_type(type_name: str) -> bool:
    import re

    value = (type_name or "").strip()
    if not value:
        return False
    if re.search(r"(;|--|/\*|\*/)", value):
        return False
    if re.search(r"\b(DROP|ALTER|CREATE|EXEC|UNION|SELECT|INSERT|DELETE|UPDATE)\b", value, re.IGNORECASE):
        return False
    return type_casting.is_supported_type(value)

def validate_mappings(csv_columns: list[str], mappings: list[dict]) -> list[dict]:
    csv_set = set(csv_columns)
    errors = []
    validated = []
    seen_targets = set()

    for item in mappings:
        target_col = item.get("target_col")
        csv_col = item.get("csv_col")
        target_type = item.get("target_type")

        if not target_col or not _is_safe_identifier(target_col):
            errors.append(f"Invalid target column name: {target_col}")
            continue

        normalized_target_col = _normalize_identifier(target_col)
        if normalized_target_col.lower() in seen_targets:
            errors.append(f"Duplicate target column: {normalized_target_col}")
            continue
        seen_targets.add(normalized_target_col.lower())

        if not _is_safe_type(target_type):
            errors.append(f"Unsupported target type: {target_type}")
            continue

        if not csv_col:
            errors.append(f"CSV column is required for target column: {normalized_target_col}")
            continue
        if csv_col not in csv_set:
            errors.append(f"CSV column not found: {csv_col}")
            continue

        validated.append(
            {
                "target_col": normalized_target_col,
                "csv_col": csv_col,
                "target_type": target_type.strip().upper(),
            }
        )

    if errors:
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "Validation failed", "details": errors},
        )

    return validated
