import http.server
import sqlite3
import sys
import threading
import types
import zipfile
from pathlib import Path

import fsspec
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from DataElevate import Invalid_Directory, InvalidInput, Load_data


# ------------------------------------------------------------------- fixtures

@pytest.fixture
def csvs(tmp_path):
    d = tmp_path / "monthly"
    d.mkdir()
    (d / "jan.csv").write_text("id,amount\n1,10\n2,20\n")
    (d / "feb.csv").write_text("id,amount\n3,30\n")
    return d


@pytest.fixture(scope="module")
def server():
    routes = {"/q3.csv": b"id,amount\n9,90\n"}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = routes.get(self.path)
            self.send_response(200 if body else 404)
            self.send_header("Content-Length", str(len(body or b"")))
            self.end_headers()
            self.wfile.write(body or b"")

        def log_message(self, *a):
            pass

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


@pytest.fixture
def sqlite_db(tmp_path):
    path = tmp_path / "shop.db"
    con = sqlite3.connect(path)
    con.executescript("CREATE TABLE orders (id INTEGER, amount INTEGER);"
                      "INSERT INTO orders VALUES (7, 70), (8, 80);")
    con.commit()
    con.close()
    return path


# ------------------------------------------------------------------- detection

@pytest.mark.parametrize("source,kind", [
    ("https://example.com/x.csv", "url"),
    ("s3://bucket/data/train.parquet", "url"),
    ("s3://bucket/data/*.csv", "url"),
    ("s3://bucket/lake/sales", "lake"),
    ("abfss://c@acct.dfs.core.windows.net/delta/orders", "lake"),
    ("https://drive.google.com/file/d/1AbCdEfGhIjK/view", "drive"),
    ("https://www.kaggle.com/datasets/o/n", "kaggle"),
    ("kaggle:o/n", "kaggle"),
    ("hf:stanfordnlp/imdb", "huggingface"),
    ("https://huggingface.co/datasets/stanfordnlp/imdb", "huggingface"),
    ("postgresql+psycopg2://u:p@h/db", "database"),
    ("sqlite:///x.db", "database"),
    (pd.DataFrame({"a": [1]}), "dataframe"),
])
def test_detect(source, kind):
    assert Load_data.detect_source(source) == kind


def test_detect_local(csvs):
    assert Load_data.detect_source(csvs) == "folder"
    assert Load_data.detect_source(csvs / "jan.csv") == "file"


def test_bare_dataset_name_asks_for_prefix():
    with pytest.raises(InvalidInput, match="kaggle:owner/name|'kaggle:o/n'"):
        Load_data.detect_source("o/n")
    with pytest.raises(Invalid_Directory):
        Load_data.detect_source("no_such_file.csv")


# ------------------------------------------------------------- single sources

def test_folder_of_same_files_is_stacked(csvs):
    df = Load_data.smart_load(csvs)
    assert sorted(df["amount"]) == [10, 20, 30]
    assert set(df["source"]) == {f"{csvs}::feb.csv", f"{csvs}::jan.csv"}


def test_single_file_has_no_source_column(csvs):
    df = Load_data.load(csvs / "jan.csv")
    assert list(df.columns) == ["id", "amount"]


def test_folder_with_different_files_returns_dict(tmp_path):
    (tmp_path / "users.csv").write_text("id,name\n1,a\n")
    (tmp_path / "orders.csv").write_text("id,amount\n1,5\n")
    out = Load_data.smart_load(tmp_path)
    assert set(out) == {f"{tmp_path}::users.csv", f"{tmp_path}::orders.csv"}
    stacked = Load_data.smart_load(tmp_path, combine="concat")
    assert {"name", "amount"} <= set(stacked.columns) and len(stacked) == 2


def test_partitioned_folder_is_read_as_lake(tmp_path):
    pq.write_to_dataset(pa.table({"year": [2024, 2025], "v": [1, 2]}), str(tmp_path / "t"),
                        partition_cols=["year"])
    df = Load_data.smart_load(tmp_path / "t", filters=[("year", "=", 2025)])
    assert df["v"].tolist() == [2]


def test_image_folder_is_indexed(tmp_path):
    for p in ("cat/1.jpg", "dog/2.png"):
        f = tmp_path / "pets" / p
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"x")
    assert sorted(Load_data.smart_load(tmp_path / "pets")["label"]) == ["cat", "dog"]


def test_local_archive_of_csvs(tmp_path):
    archive = tmp_path / "exports.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("a.csv", "x\n1\n")
        zf.writestr("b.csv", "x\n2\n")
    assert sorted(Load_data.smart_load(archive)["x"]) == [1, 2]


def test_pandas_options_reach_the_reader(csvs):
    df = Load_data.smart_load(csvs / "jan.csv", nrows=1)
    assert len(df) == 1


# ------------------------------------------------------------ mixed sources

def test_mixed_sources_stack_with_source_column(csvs, server, sqlite_db, tmp_path):
    memfs = fsspec.filesystem("memory")
    with memfs.open("/bucket/q4.parquet", "wb") as fh:
        pd.DataFrame({"id": [11], "amount": [110]}).to_parquet(fh)
    df = Load_data.smart_load(
        {
            "local": csvs / "jan.csv",
            "web": f"{server}/q3.csv",
            "cloud": "memory://bucket/q4.parquet",
            "db": {"source": f"sqlite:///{sqlite_db.as_posix()}", "table": "orders"},
            "manual": pd.DataFrame({"id": [99], "amount": [999]}),
        },
        destination=tmp_path / "dl",
    )
    assert df.groupby("source")["amount"].sum().to_dict() == {
        "cloud": 110, "db": 150, "local": 30, "manual": 999, "web": 90}
    assert [s["source"] for s in df.attrs["sources"]] == ["local", "web", "cloud", "db", "manual"]
    memfs.store.clear()


def test_list_keeps_input_order_with_parallel_loading(csvs):
    files = [csvs / "feb.csv", csvs / "jan.csv", csvs / "feb.csv"]
    df = Load_data.smart_load(files, max_workers=3)
    assert df["amount"].tolist() == [30, 10, 20, 30]


def test_normalize_columns_lines_up_headers(tmp_path):
    (tmp_path / "a.csv").write_text("Customer ID,Total Amount\n1,5\n")
    (tmp_path / "b.csv").write_text("customer_id,total_amount\n2,6\n")
    raw = Load_data.smart_load([tmp_path / "a.csv", tmp_path / "b.csv"])
    assert isinstance(raw, dict)  # different headers: not stacked by default
    df = Load_data.smart_load([tmp_path / "a.csv", tmp_path / "b.csv"], normalize_columns=True)
    assert list(df.columns) == ["source", "customer_id", "total_amount"] and len(df) == 2


def test_per_source_options_and_names(tmp_path):
    pq.write_to_dataset(pa.table({"year": [2024, 2025], "v": [1, 2]}), str(tmp_path / "lake"),
                        partition_cols=["year"])
    (tmp_path / "extra.csv").write_text("v,year\n3,2025\n")
    df = Load_data.smart_load([
        {"source": str(tmp_path / "lake"), "filters": [("year", "=", 2025)], "name": "lake"},
        {"source": str(tmp_path / "extra.csv"), "name": "extra"},
    ], combine="concat")
    assert sorted(df["v"]) == [2, 3] and set(df["source"]) == {"lake", "extra"}


def test_errors_skip(csvs, tmp_path):
    df = Load_data.smart_load([csvs / "jan.csv", tmp_path / "missing.csv"], errors="skip")
    assert len(df) == 2 and df.attrs["skipped"][0]["source"].endswith("missing.csv")
    with pytest.raises(Invalid_Directory):
        Load_data.smart_load([csvs / "jan.csv", tmp_path / "missing.csv"])


def test_combine_dict(csvs):
    out = Load_data.smart_load({"a": csvs / "jan.csv", "b": csvs / "feb.csv"}, combine="dict")
    assert set(out) == {"a", "b"} and out["b"]["amount"].tolist() == [30]


def test_source_column_clash_and_disable(tmp_path):
    (tmp_path / "a.csv").write_text("source,v\nx,1\n")
    (tmp_path / "b.csv").write_text("source,v\ny,2\n")
    with pytest.raises(InvalidInput, match="already exists"):
        Load_data.smart_load([tmp_path / "a.csv", tmp_path / "b.csv"])
    df = Load_data.smart_load([tmp_path / "a.csv", tmp_path / "b.csv"], source_column=None)
    assert df["source"].tolist() == ["x", "y"]


def test_database_password_never_in_output(sqlite_db, monkeypatch):
    seen = {}

    def fake_from_url(url, table, **kw):
        seen["url"] = url
        return pd.DataFrame({"id": [1]})
    monkeypatch.setattr(Load_data.Database, "from_url", staticmethod(fake_from_url))
    df = Load_data.smart_load([
        {"source": "postgresql://analyst:S3cret!@db.example.com/shop", "table": "orders"},
        pd.DataFrame({"id": [2]}),
    ])
    assert "S3cret" not in " ".join(df["source"]) and "***" in df["source"][0]
    assert "S3cret" in seen["url"]  # the real URL is still used to connect


def test_database_needs_table_or_query():
    with pytest.raises(InvalidInput, match="table"):
        Load_data.smart_load("postgresql://u:pw@h/db")


def test_kaggle_and_hf_prefixes(tmp_path, monkeypatch):
    def dataset_download(handle):
        d = tmp_path / "cache" / "datasets" / "o" / "n" / "versions" / "1"
        d.mkdir(parents=True, exist_ok=True)
        (d / "train.csv").write_text("text,label\nhi,1\n")
        return str(d)
    monkeypatch.setitem(sys.modules, "kagglehub",
                        types.SimpleNamespace(dataset_download=dataset_download))

    class Split:
        def to_pandas(self):
            return pd.DataFrame({"text": ["yo"], "label": [0]})
    monkeypatch.setitem(sys.modules, "datasets", types.SimpleNamespace(
        load_dataset=lambda *a, **k: Split()))
    df = Load_data.smart_load(["kaggle:o/n", "hf:o/n"], destination=tmp_path / "dl")
    assert df["label"].tolist() == [1, 0]
    assert df["source"].tolist() == ["kaggle:o/n", "hf:o/n"]


def test_bad_arguments(csvs):
    with pytest.raises(InvalidInput):
        Load_data.smart_load(csvs, combine="merge")
    with pytest.raises(InvalidInput):
        Load_data.smart_load(csvs, errors="ignore")
    with pytest.raises(InvalidInput):
        Load_data.smart_load([])
    with pytest.raises(InvalidInput):
        Load_data.smart_load([{"name": "x"}])
