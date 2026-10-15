"""Format csvdoctor profiles as Markdown or JSON."""

from __future__ import annotations

import json
from typing import Any

_NUMERIC_FIELDS = ("min", "max", "mean", "median", "stdev", "outlier_count")


def _format_number(value: Any) -> str:
    """Format a numeric value for a Markdown table."""
    if value is None:
        return ""
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.6g}"
    return str(value)


def to_json(profile: dict[str, Any]) -> str:
    """Format *profile* as a pretty-printed JSON document."""
    return json.dumps(profile, indent=2, ensure_ascii=False)


def to_markdown(profile: dict[str, Any]) -> str:
    """Format *profile* as a Markdown report."""
    lines: list[str] = []
    path = profile.get("path")
    lines.append(f"# CSV profile: {path}" if path else "# CSV profile")
    lines.append("")
    lines.append(f"- Rows: {profile.get('row_count', 0)}")
    lines.append(f"- Columns: {profile.get('column_count', 0)}")
    lines.append(f"- Duplicate rows: {profile.get('duplicate_row_count', 0)}")
    if profile.get("delimiter"):
        lines.append(f"- Delimiter: `{profile['delimiter']}`")
    lines.append("")

    columns = profile.get("columns") or []
    if not columns:
        lines.append("_No columns to report._")
        return "\n".join(lines) + "\n"

    lines.append(
        "| Column | Type | Nulls | Unique | Min | Max | Mean | Median | Stdev | Outliers |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for column in columns:
        cells = [
            str(column.get("name", "")),
            str(column.get("type", "")),
            str(column.get("null_count", 0)),
            str(column.get("unique_count", 0)),
        ]
        cells.extend(_format_number(column.get(field)) for field in _NUMERIC_FIELDS)
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"
