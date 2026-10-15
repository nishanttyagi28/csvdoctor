import json

from csvdoctor.cli import build_parser, main


def test_parser_accepts_path() -> None:
    args = build_parser().parse_args(["data.csv"])
    assert args.path == "data.csv"
    assert args.format == "markdown"
    assert args.output is None
    assert args.delimiter is None


def test_missing_file_returns_nonzero(tmp_path, capsys) -> None:
    missing = tmp_path / "missing.csv"
    assert main([str(missing)]) == 1
    captured = capsys.readouterr()
    assert "no such file" in captured.err
    assert str(missing) in captured.err


def test_markdown_to_stdout_by_default(tmp_path, capsys) -> None:
    path = tmp_path / "data.csv"
    path.write_text("a,b\n1,x\n", encoding="utf-8")

    assert main([str(path)]) == 0
    captured = capsys.readouterr()
    assert "# CSV profile" in captured.out


def test_json_format(tmp_path, capsys) -> None:
    path = tmp_path / "data.csv"
    path.write_text("a,b\n1,x\n", encoding="utf-8")

    assert main([str(path), "--format", "json"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["row_count"] == 1


def test_output_file(tmp_path, capsys) -> None:
    path = tmp_path / "data.csv"
    path.write_text("a,b\n1,x\n", encoding="utf-8")
    out = tmp_path / "report.md"

    assert main([str(path), "--output", str(out)]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "# CSV profile" in out.read_text(encoding="utf-8")


def test_json_output_file(tmp_path, capsys) -> None:
    path = tmp_path / "data.csv"
    path.write_text("a,b\n1,x\n2,y\n", encoding="utf-8")
    out = tmp_path / "report.json"

    assert main([str(path), "--format", "json", "--output", str(out)]) == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["row_count"] == 2
    assert report["column_count"] == 2
    assert report["columns"][0]["type"] == "integer"


def test_delimiter_override(tmp_path, capsys) -> None:
    path = tmp_path / "data.csv"
    path.write_text("a|b\n1|2\n", encoding="utf-8")

    assert main([str(path), "--delimiter", "|", "--format", "json"]) == 0
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["delimiter"] == "|"
    assert report["column_count"] == 2
