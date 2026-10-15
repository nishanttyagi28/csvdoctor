"""Core CSV inspection logic.

Runtime dependencies are limited to the standard library: csv, json, statistics.
"""

from __future__ import annotations

import csv
import io
import math
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

NULL_VALUES = frozenset({"", "na", "n/a", "null", "none"})
TRUE_VALUES = frozenset({"true", "yes"})
FALSE_VALUES = frozenset({"false", "no"})
DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d.%m.%Y",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M",
)
CANDIDATE_DELIMITERS = ",;\t|"
SNIFF_SAMPLE_SIZE = 65536


def _is_null(value: str) -> bool:
    """Return True when *value* represents a missing value."""
    return value.strip().lower() in NULL_VALUES


def _is_int(value: str) -> bool:
    try:
        int(value)
    except (TypeError, ValueError):
        return False
    return True


def _is_float(value: str) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def _is_bool(value: str) -> bool:
    return value.strip().lower() in TRUE_VALUES | FALSE_VALUES


def _is_date(value: str) -> bool:
    text = value.strip()
    try:
        datetime.fromisoformat(text)
        return True
    except ValueError:
        pass
    for fmt in DATE_FORMATS:
        try:
            datetime.strptime(text, fmt)
            return True
        except ValueError:
            continue
    return False


def _infer_type(values: Sequence[str]) -> str:
    """Infer a column type from its non-null values."""
    if not values:
        return "empty"
    if all(_is_int(value) for value in values):
        return "integer"
    if all(_is_float(value) for value in values):
        return "float"
    if all(_is_bool(value) for value in values):
        return "boolean"
    if all(_is_date(value) for value in values):
        return "date"
    return "string"


def _iqr_outlier_count(values: Sequence[float]) -> int:
    """Count values outside the 1.5 * IQR fences."""
    if len(values) < 2:
        return 0
    q1, _q2, q3 = statistics.quantiles(values, n=4, method="inclusive")
    iqr = q3 - q1
    low = q1 - 1.5 * iqr
    high = q3 + 1.5 * iqr
    return sum(1 for value in values if value < low or value > high)


def _numeric_stats(values: Sequence[float]) -> dict[str, Any]:
    """Compute summary statistics for a numeric column."""
    if not values:
        return {}
    return {
        "min": min(values),
        "max": max(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "stdev": statistics.stdev(values) if len(values) >= 2 else None,
        "outlier_count": _iqr_outlier_count(values),
    }


def _profile_column(name: str, raw_values: Sequence[str]) -> dict[str, Any]:
    """Build the profile entry for a single column."""
    null_count = sum(1 for value in raw_values if _is_null(value))
    non_null = [value for value in raw_values if not _is_null(value)]
    column: dict[str, Any] = {
        "name": name,
        "type": _infer_type(non_null),
        "null_count": null_count,
        "unique_count": len(set(non_null)),
    }
    if column["type"] == "integer":
        numbers: list[Any] = [int(value) for value in non_null]
        column.update(_numeric_stats(numbers))
    elif column["type"] == "float":
        numbers = [float(value) for value in non_null]
        column.update(_numeric_stats(numbers))
    return column


def _pad(row: Sequence[str], width: int) -> list[str]:
    """Pad or truncate *row* so that it has exactly *width* fields."""
    padded = list(row[:width])
    if len(padded) < width:
        padded.extend([""] * (width - len(padded)))
    return padded


def _analyze(header: Sequence[str], data: Iterable[Sequence[str]]) -> dict[str, Any]:
    """Profile a parsed table into a JSON-serializable report."""
    width = len(header)
    rows = [_pad(row, width) for row in data if len(row) > 0]
    duplicates = len(rows) - len({tuple(row) for row in rows})
    columns = [
        _profile_column(header[index], [row[index] for row in rows])
        for index in range(width)
    ]
    return {
        "row_count": len(rows),
        "column_count": width,
        "duplicate_row_count": duplicates,
        "columns": columns,
    }


def _sniff_delimiter(sample: str) -> str:
    """Best-effort delimiter detection with a comma fallback."""
    try:
        return csv.Sniffer().sniff(sample, delimiters=CANDIDATE_DELIMITERS).delimiter
    except csv.Error:
        return ","


def _read_table(
    path: Path | str, delimiter: str | None = None
) -> tuple[list[str], list[list[str]], str]:
    """Read *path* into a header, data rows and the delimiter that was used."""
    raw = Path(path).read_bytes()
    text = raw.decode("utf-8-sig", errors="replace")
    if not text.strip():
        return [], [], delimiter or ","
    used_delimiter = delimiter or _sniff_delimiter(text[:SNIFF_SAMPLE_SIZE])
    reader = csv.reader(io.StringIO(text), delimiter=used_delimiter)
    parsed = list(reader)
    if not parsed:
        return [], [], used_delimiter
    header, data = parsed[0], parsed[1:]
    return header, data, used_delimiter


def read_rows(
    path: Path | str, delimiter: str | None = None
) -> list[dict[str, str]]:
    """Read a CSV file into a list of row dictionaries."""
    header, data, _ = _read_table(path, delimiter)
    rows: list[dict[str, str]] = []
    for row in data:
        if len(row) == 0:
            continue
        padded = _pad(row, len(header))
        rows.append({name: padded[index] for index, name in enumerate(header)})
    return rows


def summarize(rows: list[dict[str, str]]) -> dict[str, object]:
    """Summarize rows into a JSON-serializable report."""
    names: list[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    data = [[str(row.get(name, "")) for name in names] for row in rows]
    return _analyze(names, data)


def profile_csv(path: Path | str, delimiter: str | None = None) -> dict[str, Any]:
    """Profile a CSV file.

    The delimiter is sniffed from the file contents unless one is supplied.
    The returned dictionary contains file level counts (``row_count``,
    ``column_count``, ``duplicate_row_count``) and a ``columns`` list with the
    inferred type, null/unique counts and, for numeric columns, summary
    statistics and an IQR-based outlier count.
    """
    header, data, used_delimiter = _read_table(path, delimiter)
    profile = _analyze(header, data)
    profile["path"] = str(path)
    profile["delimiter"] = used_delimiter
    return profile
