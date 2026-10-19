import sys
import types
from pathlib import Path

import pytest

from DataElevate import Download_data, InvalidInput, Load_data, MultipleFilesError
from DataElevate._kaggle import parse_handle


@pytest.mark.parametrize("value,handle", [
    ("owner/name", "owner/name"),
    ("owner/name/versions/3", "owner/name/versions/3"),
    ("https://www.kaggle.com/datasets/owner/name", "owner/name"),
    ("https://www.kaggle.com/datasets/owner/name/data", "owner/name"),
    ("kaggle.com/datasets/owner/name?select=train.csv", "owner/name"),
    ("https://www.kaggle.com/datasets/owner/name/versions/2", "owner/name/versions/2"),
])
def test_parse_handle(value, handle):
    assert parse_handle(value)[0] == handle


@pytest.mark.parametrize("value", ["", "justaname", "https://www.kaggle.com/competitions/titanic",
                                   "https://example.com/datasets/a/b", None])
def test_parse_handle_rejects(value):
    with pytest.raises(InvalidInput):
        parse_handle(value)


@pytest.fixture
def fake_kagglehub(tmp_path, monkeypatch):
    """Stand-in for kagglehub that writes files into a kagglehub-shaped cache."""
    cache_root = tmp_path / "cache"
    state = {"files": {"train.csv": "a,b\n1,2\n"}}

    def dataset_download(handle):
        owner, name = handle.split("/")[:2]
        version_dir = cache_root / "datasets" / owner / name / "versions" / "1"
        version_dir.mkdir(parents=True, exist_ok=True)
        for rel, text in state["files"].items():
            f = version_dir / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text)
        return str(version_dir)

    monkeypatch.setitem(sys.modules, "kagglehub", types.SimpleNamespace(
        dataset_download=dataset_download))
    state["cache_root"] = cache_root
    return state


def test_download_copies_and_clears_only_that_cache(tmp_path, fake_kagglehub):
    other = fake_kagglehub["cache_root"] / "datasets" / "owner" / "other-dataset"
    other.mkdir(parents=True)
    paths = Download_data.Kaggle.from_kaggle("owner/name", tmp_path / "dest")
    assert [Path(p).name for p in paths] == ["train.csv"]
    assert (tmp_path / "dest" / "train.csv").exists()
    assert not (fake_kagglehub["cache_root"] / "datasets" / "owner" / "name").exists()
    assert other.exists()  # other datasets from the same owner are untouched


def test_download_keep_cache(tmp_path, fake_kagglehub):
    Download_data.Kaggle.from_kaggle("owner/name", tmp_path / "dest", keep_cache=True)
    assert (fake_kagglehub["cache_root"] / "datasets" / "owner" / "name").exists()


def test_default_destination(tmp_path, fake_kagglehub, monkeypatch):
    monkeypatch.chdir(tmp_path)
    paths = Download_data.Kaggle.from_kaggle("https://www.kaggle.com/datasets/owner/name")
    assert Path(paths[0]) == tmp_path / "Data" / "name" / "train.csv"


def test_load_single_file(tmp_path, fake_kagglehub):
    df = Load_data.from_kaggle("owner/name", destination=tmp_path / "d")
    assert df["b"].tolist() == [2]


def test_load_multiple_files(tmp_path, fake_kagglehub):
    fake_kagglehub["files"] = {"train.csv": "a\n1\n", "sub/test.csv": "a\n2\n", "README.md": "x"}
    with pytest.raises(MultipleFilesError) as err:
        Load_data.from_kaggle("owner/name", destination=tmp_path / "d")
    assert set(err.value.files) == {"train.csv", "test.csv"}
    df = Load_data.from_kaggle("owner/name", file="test.csv", destination=tmp_path / "d")
    assert df["a"].tolist() == [2]


def test_kagglehub_error_is_wrapped(tmp_path, monkeypatch):
    def boom(handle):
        raise RuntimeError("404 not found")
    monkeypatch.setitem(sys.modules, "kagglehub", types.SimpleNamespace(dataset_download=boom))
    with pytest.raises(InvalidInput, match="404"):
        Download_data.Kaggle.from_kaggle("owner/missing", tmp_path)
