import gzip
import json
import zipfile

import pandas as pd
import pytest

from DataElevate import Load_data
from DataElevate._loaders import check_data_type

DF = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})


def test_parquet(tmp_path):
    p = tmp_path / "d.parquet"
    DF.to_parquet(p)
    assert Load_data.from_local(p).equals(DF)


def test_feather(tmp_path):
    p = tmp_path / "d.feather"
    DF.to_feather(p)
    assert Load_data.from_local(p).equals(DF)


def test_json_records(tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]))
    assert Load_data.from_local(p)["a"].tolist() == [1, 2]


def test_json_nested_is_flattened(tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"data": [{"id": 1, "user": {"name": "a"}},
                                      {"id": 2, "user": {"name": "b"}}], "meta": {"n": 2}}))
    df = Load_data.from_local(p)
    assert df["user.name"].tolist() == ["a", "b"]


def test_jsonl(tmp_path):
    p = tmp_path / "d.jsonl"
    p.write_text('{"a": 1}\n{"a": 2}\n')
    assert Load_data.from_local(p)["a"].tolist() == [1, 2]


def test_compressed_csv_gz(tmp_path):
    p = tmp_path / "train.csv.gz"
    with gzip.open(p, "wt") as fh:
        fh.write("a,b\n1,2\n")
    assert Load_data.from_local(p)["b"].tolist() == [2]


def test_compressed_csv_zip(tmp_path):
    p = tmp_path / "train.csv.zip"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("train.csv", "a,b\n1,2\n")
    assert Load_data.from_local(p)["a"].tolist() == [1]


def test_compressed_tsv_sniffs_delimiter(tmp_path):
    p = tmp_path / "train.tsv.gz"
    with gzip.open(p, "wt") as fh:
        fh.write("a\tb\n1\t2\n")
    assert list(Load_data.from_local(p).columns) == ["a", "b"]


@pytest.mark.parametrize("name,kind", [
    ("x.csv", "csv"), ("x.CSV.GZ", "csv"), ("x.parquet", "parquet"), ("x.pq", "parquet"),
    ("x.jsonl.gz", "jsonl"), ("x.ndjson", "jsonl"), ("x.arrow", "feather"),
    ("images.zip", None), ("data.tar.gz", None), ("x.parquet.gz", None), ("README", None),
])
def test_check_data_type(name, kind):
    assert check_data_type(name) == kind
