import sys
import types
import zipfile

import pandas as pd
import pytest

from DataElevate import Download_data, InvalidInput, Load_data, MissingDependencyError
from DataElevate._hf import parse_name


# ------------------------------------------------------------------- Hugging Face

@pytest.mark.parametrize("value,name", [
    ("imdb", "imdb"), ("stanfordnlp/imdb", "stanfordnlp/imdb"),
    ("https://huggingface.co/datasets/stanfordnlp/imdb", "stanfordnlp/imdb"),
    ("https://huggingface.co/datasets/stanfordnlp/imdb/viewer/plain_text/train", "stanfordnlp/imdb"),
])
def test_parse_name(value, name):
    assert parse_name(value) == name


@pytest.mark.parametrize("value", ["", "a b", "https://example.com/x", None])
def test_parse_name_rejects(value):
    with pytest.raises(InvalidInput):
        parse_name(value)


class FakeSplit:
    def __init__(self, rows):
        self.rows = rows

    def to_pandas(self):
        return pd.DataFrame(self.rows)


@pytest.fixture
def fake_datasets(monkeypatch):
    calls = []

    def load_dataset(repo, config, split=None, revision=None, token=None, **kw):
        calls.append({"repo": repo, "config": config, "split": split, "token": token})
        if repo == "missing/x":
            raise FileNotFoundError("Dataset not found")
        if split is None:
            return {"train": FakeSplit([{"t": "a"}]), "test": FakeSplit([{"t": "b"}])}
        return FakeSplit([{"text": "good", "label": 1}, {"text": "bad", "label": 0}])

    monkeypatch.setitem(sys.modules, "datasets", types.SimpleNamespace(load_dataset=load_dataset))
    return calls


def test_hf_load_split(fake_datasets):
    df = Load_data.from_huggingface("https://huggingface.co/datasets/stanfordnlp/imdb",
                                    split="train[:2]")
    assert df["label"].tolist() == [1, 0]
    assert fake_datasets[0] == {"repo": "stanfordnlp/imdb", "config": None,
                                "split": "train[:2]", "token": None}


def test_hf_all_splits(fake_datasets):
    parts = Load_data.from_huggingface("o/n", split=None)
    assert set(parts) == {"train", "test"} and parts["test"]["t"].tolist() == ["b"]


def test_hf_error_hint(fake_datasets):
    with pytest.raises(InvalidInput, match="config="):
        Load_data.from_huggingface("missing/x")


def test_hf_missing_extra(monkeypatch):
    monkeypatch.setitem(sys.modules, "datasets", None)
    with pytest.raises(MissingDependencyError, match=r"DataElevate\[huggingface\]"):
        Load_data.from_huggingface("o/n")


def test_hf_download(monkeypatch, tmp_path):
    seen = {}

    def snapshot_download(**kw):
        seen.update(kw)
        return kw["local_dir"]
    monkeypatch.setitem(sys.modules, "huggingface_hub",
                        types.SimpleNamespace(snapshot_download=snapshot_download))
    out = Download_data.HuggingFace.download("o/n", tmp_path / "hf")
    assert out == str(tmp_path / "hf") and seen["repo_type"] == "dataset"


# --------------------------------------------------------------------- image folders

def _img(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG")


def test_class_folders(tmp_path):
    for p in ("cat/1.jpg", "cat/2.PNG", "dog/3.jpeg", "dog/notes.txt", ".hidden/4.jpg"):
        _img(tmp_path / "pets" / p)
    df = Load_data.from_images(tmp_path / "pets")
    assert list(df.columns) == ["path", "label"]
    assert sorted(df["label"]) == ["cat", "cat", "dog"]


def test_split_folders_inside_wrapper_zip(tmp_path):
    archive = tmp_path / "flowers.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for p in ("flowers/train/rose/1.jpg", "flowers/train/tulip/2.jpg",
                  "flowers/validation/rose/3.jpg", "flowers/test/tulip/4.jpg",
                  "__MACOSX/flowers/._1.jpg"):
            zf.writestr(p, b"img")
    df = Load_data.from_images(archive)
    assert sorted(df["split"].unique()) == ["test", "train", "val"]
    assert df.groupby("split").size().to_dict() == {"test": 1, "train": 2, "val": 1}
    assert set(df["label"]) == {"rose", "tulip"}


def test_flat_folder_has_no_label(tmp_path):
    for i in range(3):
        _img(tmp_path / "imgs" / f"{i}.png")
    df = Load_data.from_images(tmp_path / "imgs")
    assert list(df.columns) == ["path"] and len(df) == 3


def test_custom_extensions(tmp_path):
    _img(tmp_path / "scans" / "a" / "1.dcm")
    assert len(Load_data.from_images(tmp_path / "scans", extensions=["dcm"])) == 1


def test_no_images(tmp_path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(InvalidInput, match="No images"):
        Load_data.from_images(tmp_path / "empty")
    with pytest.raises(InvalidInput):
        Load_data.from_images(tmp_path / "nothing-here")


def test_single_class_folder_is_label_not_wrapper(tmp_path):
    _img(tmp_path / "data" / "cats" / "1.jpg")
    _img(tmp_path / "data" / "cats" / "2.jpg")
    assert set(Load_data.from_images(tmp_path / "data")["label"]) == {"cats"}


def test_nested_wrappers(tmp_path):
    for p in ("export/PetImages/Cat/1.jpg", "export/PetImages/Dog/2.jpg"):
        _img(tmp_path / p)
    assert sorted(Load_data.from_images(tmp_path / "export")["label"]) == ["Cat", "Dog"]
