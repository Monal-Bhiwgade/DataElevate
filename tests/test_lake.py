import fsspec
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from DataElevate import InvalidInput, Load_data, MissingDependencyError

ROWS = pd.DataFrame({
    "year": [2024, 2024, 2025, 2025, 2025, 2025],
    "country": ["IN", "US", "IN", "US", "IN", "DE"],
    "amount": [10, 20, 30, 40, 50, 60],
    "user_id": [1, 2, 3, 4, 5, 6],
})


def _write_partitioned(root, filesystem=None):
    pq.write_to_dataset(pa.Table.from_pandas(ROWS, preserve_index=False), root,
                        partition_cols=["year", "country"], filesystem=filesystem)


@pytest.fixture
def lake(tmp_path):
    root = tmp_path / "sales"
    _write_partitioned(str(root))
    return root


def test_reads_partitioned_dataset(lake):
    df = Load_data.from_lake(str(lake))
    assert len(df) == 6 and {"year", "country", "amount"} <= set(df.columns)


def test_columns_filters_limit(lake):
    df = Load_data.from_lake(str(lake), columns=["user_id", "amount"],
                             filters=[("year", "=", 2025), ("country", "in", ["IN", "US"])])
    assert list(df.columns) == ["user_id", "amount"]
    assert sorted(df["amount"]) == [30, 40, 50]
    assert len(Load_data.from_lake(str(lake), limit=2)) == 2


def test_or_filters(lake):
    df = Load_data.from_lake(str(lake), filters=[[("country", "=", "DE")],
                                                  [("amount", "<", 15)]])
    assert sorted(df["amount"]) == [10, 60]


def test_describe(lake):
    info = Load_data.describe_lake(str(lake))
    assert info["format"] == "parquet"
    assert {"year", "country", "amount"} <= set(info["columns"])
    assert info["partition_columns"] == ["year", "country"]
    assert info["files"] == 5  # one file per (year, country) partition


def test_remote_lake_over_fsspec():
    fs = fsspec.filesystem("memory")
    fs.store.clear()
    _write_partitioned("/warehouse/sales", filesystem=fs)
    df = Load_data.from_lake("memory://warehouse/sales", filters=[("country", "=", "DE")])
    assert df["amount"].tolist() == [60]
    fs.store.clear()


def test_csv_lake(tmp_path):
    for year in (2024, 2025):
        d = tmp_path / "logs" / f"year={year}"
        d.mkdir(parents=True)
        (d / "part.csv").write_text(f"event,n\nclick,{year - 2020}\n")
    df = Load_data.from_lake(str(tmp_path / "logs"), format="csv", filters=[("year", ">", 2024)])
    assert df["n"].tolist() == [5]


def test_bad_filters_message(lake):
    with pytest.raises(InvalidInput, match="column, op, value"):
        Load_data.from_lake(str(lake), filters=[("year", "~", 1)])


def test_bad_format(lake):
    with pytest.raises(InvalidInput):
        Load_data.from_lake(str(lake), format="orc2")


def test_version_only_for_delta(lake):
    with pytest.raises(InvalidInput, match="Delta"):
        Load_data.from_lake(str(lake), format="parquet", version=1)


# ----------------------------------------------------------------------- Delta Lake

deltalake = pytest.importorskip("deltalake")


@pytest.fixture
def delta_table(tmp_path):
    path = str(tmp_path / "events")
    deltalake.write_deltalake(path, ROWS.iloc[:2], partition_by=["year"])
    deltalake.write_deltalake(path, ROWS.iloc[2:], mode="append", partition_by=["year"])
    return path


def test_delta_auto_detected_with_pushdown(delta_table):
    assert Load_data.describe_lake(delta_table)["format"] == "delta"
    df = Load_data.from_lake(delta_table, columns=["amount"], filters=[("year", "=", 2025)])
    assert sorted(df["amount"]) == [30, 40, 50, 60]


def test_delta_time_travel(delta_table):
    assert len(Load_data.from_lake(delta_table, version=0)) == 2
    assert len(Load_data.from_lake(delta_table)) == 6


def test_delta_missing_extra(monkeypatch, lake):
    import DataElevate._lake as lk

    def missing(module, package, extra):
        raise MissingDependencyError(package, extra)
    monkeypatch.setattr(lk, "require", missing)
    with pytest.raises(MissingDependencyError, match=r"DataElevate\[delta\]"):
        Load_data.from_lake(str(lake), format="delta")
