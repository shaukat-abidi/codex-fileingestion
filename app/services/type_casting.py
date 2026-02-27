import re
from datetime import date, datetime, time
from decimal import Decimal

TYPE_DECIMAL_RE = re.compile(r"^(DECIMAL|NUMERIC)\((\d+),\s*(\d+)\)$")
TYPE_TEXT_RE = re.compile(r"^(NVARCHAR|VARCHAR|CHAR)\((\d+)\)$")


def parse_sql_type(sql_type: str) -> tuple[str, tuple[int, ...] | None]:
    t = sql_type.strip().upper()

    if t in {"INT", "BIGINT", "FLOAT", "REAL", "BIT", "DATE", "DATETIME", "DATETIME2"}:
        return t, None

    m = TYPE_DECIMAL_RE.match(t)
    if m:
        return m.group(1), (int(m.group(2)), int(m.group(3)))

    m = TYPE_TEXT_RE.match(t)
    if m:
        return m.group(1), (int(m.group(2)),)

    return "", None


def is_supported_type(sql_type: str) -> bool:
    base, _ = parse_sql_type(sql_type)
    return bool(base)


def _empty_to_none(value):
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def cast_value(value, target_type: str, nullable: bool = True):
    value = _empty_to_none(value)
    if value is None:
        if nullable:
            return None
        raise ValueError("Non-nullable column has empty value")

    base, _ = parse_sql_type(target_type)
    if not base:
        raise ValueError(f"Unsupported type: {target_type}")

    if base in {"INT", "BIGINT"}:
        return int(value)

    if base in {"FLOAT", "REAL"}:
        return float(value)

    if base in {"DECIMAL", "NUMERIC"}:
        return Decimal(str(value))

    if base == "BIT":
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return bool(value)
        if isinstance(value, str):
            v = value.strip().lower()
            if v in {"1", "true", "yes"}:
                return True
            if v in {"0", "false", "no"}:
                return False
        raise ValueError(f"Invalid BIT value: {value}")

    if base == "DATE":
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        return date.fromisoformat(str(value))

    if base in {"DATETIME", "DATETIME2"}:
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            d = date.fromisoformat(str(value))
            return datetime.combine(d, time())

    if base in {"NVARCHAR", "VARCHAR", "CHAR"}:
        return str(value)

    raise ValueError(f"Unsupported type: {target_type}")
