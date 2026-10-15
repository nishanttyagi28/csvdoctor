import json

import pytest

from csvdoctor.core import profile_csv, read_rows, summarize


def _write(tmp_path, text: str, name: str = "data.csv"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_profile_basic_types_and_counts(tmp_path) -> None:
    path = _write(
        tmp_path,
        "id,name,score,active,joined\n"
        "1,Alice,1.5,true,2020-01-01\n"
        "2,Bob,,false,2020-02-01\n"
        "3,Alice,3.5,yes,2020-03-01\n",
    )
    profile = profile_csv(path)

    assert profile["row_count"] == 3
    assert profile["column_count"] == 5
    assert profile["duplicate_row_count"] == 0
    assert profile["delimiter"] == ","

    columns = {column["name"]: column for column in profile["columns"]}
    assert columns["id"]["type"] == "integer"
    assert columns["name"]["type"] == "string"
    assert columns["name"]["null_count"] == 0
    assert columns["name"]["unique_count"] == 2
    assert columns["score"]["type"] == "float"
    assert columns["score"]["null_count"] == 1
    assert columns["active"]["type"] == "boolean"
    assert columns["joined"]["type"] == "date"


def test_numeric_stats_and_outliers(tmp_path) -> None:
    path = _write(tmp_path, "value\n1\n2\n3\n4\n100\n")
    profile = profile_csv(path)
    column = profile["columns"][0]

    assert column["type"] == "integer"
    assert column["min"] == 1
    assert column["max"] == 100
    assert column["mean"] == 22
    assert column["median"] == 3
    assert column["outlier_count"] == 1


def test_sniffed_delimiter_override(tmp_path) -> None:
    path = _write(tmp_path, "a;b\n1;2\n3;4\n")
    auto = profile_csv(path)
    assert auto["delimiter"] == ";"
    assert auto["column_count"] == 2

    forced = profile_csv(path, delimiter=";")
    assert forced["column_count"] == 2


def test_empty_file(tmp_path) -> None:
    path = _write(tmp_path, "")
    profile = profile_csv(path)

    assert profile["row_count"] == 0
    assert profile["column_count"] == 0
    assert profile["columns"] == []


def test_header_only_file(tmp_path) -> None:
    path = _write(tmp_path, "a,b,c\n")
    profile = profile_csv(path)

    assert profile["row_count"] == 0
    assert profile["column_count"] == 3
    assert [column["name"] for column in profile["columns"]] == ["a", "b", "c"]
    assert all(column["type"] == "empty" for column in profile["columns"])


def test_ragged_rows(tmp_path) -> None:
    path = _write(tmp_path, "a,b,c\n1,2\n1,2,3,4\n")
    profile = profile_csv(path)

    assert profile["column_count"] == 3
    assert profile["row_count"] == 2
    assert {column["name"]: column["null_count"] for column in profile["columns"]}[
        "c"
    ] == 1


def test_duplicate_rows(tmp_path) -> None:
    path = _write(tmp_path, "a,b\n1,x\n1,x\n2,y\n1,x\n")
    profile = profile_csv(path)

    assert profile["row_count"] == 4
    assert profile["duplicate_row_count"] == 2


def test_null_tokens_are_case_insensitive(tmp_path) -> None:
    path = _write(tmp_path, 'a\nNA\nn/a\nNone\nnull\n""\n')
    profile = profile_csv(path)
    column = profile["columns"][0]

    assert column["type"] == "empty"
    assert column["null_count"] == 5


def test_read_rows_and_summarize(tmp_path) -> None:
    path = _write(tmp_path, "a,b\n1,2\n3,4\n")
    rows = read_rows(path)
    assert rows == [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]

    summary = summarize(rows)
    assert summary["row_count"] == 2
    assert summary["column_count"] == 2
    assert summary["columns"][0]["type"] == "integer"


def test_profile_is_json_serializable(tmp_path) -> None:
    path = _write(tmp_path, "a\n1\n2\n")
    json.dumps(profile_csv(path))


def test_infer_float_type_and_stats(tmp_path) -> None:
    path = _write(tmp_path, "value\n1.5\n2.5\n3.5\n4.5\n")
    column = profile_csv(path)["columns"][0]

    assert column["type"] == "float"
    assert column["null_count"] == 0
    assert column["unique_count"] == 4
    assert column["min"] == 1.5
    assert column["max"] == 4.5
    assert column["mean"] == pytest.approx(3.0)
    assert column["median"] == pytest.approx(3.0)
    assert column["stdev"] == pytest.approx(1.2909944487358056)
    assert column["outlier_count"] == 0


def test_infer_boolean_type_with_null(tmp_path) -> None:
    path = _write(tmp_path, "flag\ntrue\nFALSE\nYes\nno\nN/A\n")
    profile = profile_csv(path)
    column = profile["columns"][0]

    assert profile["row_count"] == 5
    assert column["type"] == "boolean"
    assert column["null_count"] == 1
    assert column["unique_count"] == 4
    assert "mean" not in column


def test_infer_date_type_multiple_formats(tmp_path) -> None:
    path = _write(
        tmp_path,
        "when\n"
        "2020-01-01\n"
        "2020/01/02\n"
        "2020.01.03\n"
        "2020-01-01T12:30:00\n"
        "2020-01-01 12:30:00\n",
    )
    column = profile_csv(path)["columns"][0]

    assert column["type"] == "date"
    assert column["null_count"] == 0
    assert column["unique_count"] == 5


def test_all_null_column_is_empty_type(tmp_path) -> None:
    path = _write(tmp_path, "value\nNA\nnull\nN/A\nNone\n")
    column = profile_csv(path)["columns"][0]

    assert column["type"] == "empty"
    assert column["null_count"] == 4
    assert column["unique_count"] == 0
    assert "min" not in column
    assert "stdev" not in column


def test_stdev_none_for_single_value(tmp_path) -> None:
    path = _write(tmp_path, "value\n42\n")
    column = profile_csv(path)["columns"][0]

    assert column["type"] == "integer"
    assert column["min"] == 42
    assert column["max"] == 42
    assert column["mean"] == pytest.approx(42.0)
    assert column["median"] == 42
    assert column["stdev"] is None
    assert column["outlier_count"] == 0


def test_outlier_count_for_float_column(tmp_path) -> None:
    path = _write(tmp_path, "value\n1.0\n2.0\n3.0\n4.0\n100.0\n")
    column = profile_csv(path)["columns"][0]

    assert column["type"] == "float"
    assert column["min"] == 1.0
    assert column["max"] == 100.0
    assert column["mean"] == pytest.approx(22.0)
    assert column["outlier_count"] == 1


def test_semicolon_header_only_sniffing(tmp_path) -> None:
    path = _write(tmp_path, "a;b;c\n")
    profile = profile_csv(path)

    assert profile["delimiter"] == ";"
    assert profile["row_count"] == 0
    assert profile["column_count"] == 3
    assert [column["name"] for column in profile["columns"]] == ["a", "b", "c"]
    assert all(column["type"] == "empty" for column in profile["columns"])


def test_bom_and_crlf_line_endings(tmp_path) -> None:
    path = tmp_path / "bom.csv"
    path.write_bytes(b"\xef\xbb\xbfa,b\r\n1,2\r\n")
    profile = profile_csv(path)

    assert [column["name"] for column in profile["columns"]] == ["a", "b"]
    assert profile["row_count"] == 1
    assert profile["delimiter"] == ","
    assert profile["columns"][0]["type"] == "integer"


def test_whitespace_only_file(tmp_path) -> None:
    path = _write(tmp_path, "   \n\t\n")
    profile = profile_csv(path)

    assert profile["row_count"] == 0
    assert profile["column_count"] == 0
    assert profile["columns"] == []
