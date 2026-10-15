import json

from csvdoctor.core import profile_csv
from csvdoctor.report import to_json, to_markdown


def _profile(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("a,b\n1,x\n2,y\n", encoding="utf-8")
    return profile_csv(path)


def test_to_json_round_trips(tmp_path) -> None:
    profile = _profile(tmp_path)
    output = to_json(profile)

    assert json.loads(output) == profile


def test_to_markdown_contains_summary_and_columns(tmp_path) -> None:
    profile = _profile(tmp_path)
    output = to_markdown(profile)

    assert "# CSV profile" in output
    assert "| Column | Type |" in output
    assert "| a | integer |" in output
    assert "| b | string |" in output


def test_to_markdown_formats_numeric_and_empty_cells(tmp_path) -> None:
    path = tmp_path / "numbers.csv"
    path.write_text("v,label\n1,one\n2,two\n3,three\n4,four\n", encoding="utf-8")
    output = to_markdown(profile_csv(path))

    assert "- Rows: 4" in output
    assert "- Columns: 2" in output
    assert "- Delimiter: `,`" in output
    assert "| v | integer | 0 | 4 | 1 | 4 | 2.5 | 2.5 | 1.29099 | 0 |" in output
    assert "| label | string | 0 | 4 |  |  |  |  |  |  |" in output


def test_to_json_and_markdown_for_empty_profile(tmp_path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")
    profile = profile_csv(path)

    assert json.loads(to_json(profile)) == profile
    assert profile["row_count"] == 0
    assert profile["columns"] == []
    assert "_No columns to report._" in to_markdown(profile)
