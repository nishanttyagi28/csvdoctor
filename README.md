# csvdoctor

Quick health check for CSV files. Points it at a file and it tells you row and
column counts, duplicate rows, the inferred type of each column, how many
values are missing, and basic stats (min/max/mean/median/stdev, IQR outliers)
for numeric columns. No dependencies outside the standard library.

## Install

Needs Python 3.10+.

```console
git clone https://github.com/nishanttyagi28/csvdoctor.git
cd csvdoctor
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

Given `people.csv`:

```
name,age,city
Alice,34,Pune
Bob,,Delhi
Alice,34,Pune
Cara,29,Mumbai
```

```console
$ csvdoctor people.csv
# CSV profile: people.csv

- Rows: 4
- Columns: 3
- Duplicate rows: 1
- Delimiter: `,`

| Column | Type | Nulls | Unique | Min | Max | Mean | Median | Stdev | Outliers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| name | string | 0 | 3 |  |  |  |  |  |  |
| age | integer | 1 | 2 | 29 | 34 | 32.3333 | 34 | 2.88675 | 0 |
| city | string | 0 | 3 |  |  |  |  |  |  |
```

Options:

- `-f json` prints the profile as JSON instead of Markdown
- `-o report.md` writes the report to a file
- `-d ';'` sets the delimiter (otherwise it's sniffed from the file)

You can also run it as `python -m csvdoctor`, or use it from Python:

```python
from csvdoctor.core import profile_csv

profile = profile_csv("people.csv")
print(profile["duplicate_row_count"])  # 1
```

Values like `""`, `NA`, `n/a`, `null` and `none` (any case) count as missing.

## Tests

```console
pytest
```

## License

MIT
