import json
import os
import stat
import sys
import types
from pathlib import Path

import pytest

from DataElevate import CredentialsError, Download_data, InvalidInput, Load_data
from DataElevate import _gdrive

FILE_ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz012345"


@pytest.mark.parametrize("link", [
    FILE_ID,
    f"https://drive.google.com/file/d/{FILE_ID}/view?usp=sharing",
    f"https://drive.google.com/open?id={FILE_ID}",
    f"https://drive.google.com/uc?export=download&id={FILE_ID}",
    f"https://drive.google.com/drive/folders/{FILE_ID}?usp=sharing",
    f"https://docs.google.com/spreadsheets/d/{FILE_ID}/edit#gid=0",
])
def test_get_file_id(link):
    assert Download_data.GoogleDrive.get_file_id(link) == FILE_ID


@pytest.mark.parametrize("link", ["", "   ", "short", "https://drive.google.com/", None])
def test_get_file_id_rejects(link):
    with pytest.raises(InvalidInput):
        Download_data.GoogleDrive.get_file_id(link)


@pytest.mark.parametrize("name,expected", [
    ("train.csv", "train.csv"), ("../../etc/passwd", ".._.._etc_passwd"),
    ("a/b\\c", "a_b_c"), ("..", "_"), ("", "_"),
])
def test_safe_name(name, expected):
    assert _gdrive.safe_name(name) == expected


@pytest.fixture(autouse=True)
def no_env_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv(_gdrive.ENV_VAR, raising=False)
    monkeypatch.setenv("DATAELEVATE_HOME", str(tmp_path / "home"))


@pytest.fixture
def fake_gdown(monkeypatch):
    calls = []

    def download(url=None, output=None, quiet=False, id=None, fuzzy=False):
        calls.append({"url": url, "id": id, "fuzzy": fuzzy})
        path = Path(output) / "train.csv"
        path.write_text("a,b\n1,2\n")
        return str(path)

    def download_folder(url=None, id=None, output=None, quiet=False):
        calls.append({"url": url, "id": id})
        paths = []
        for name in ("train.csv", "test.csv"):
            p = Path(output) / name
            p.write_text("a\n1\n")
            paths.append(str(p))
        return paths

    monkeypatch.setitem(sys.modules, "gdown", types.SimpleNamespace(
        download=download, download_folder=download_folder))
    return calls


def test_public_file_needs_no_credentials(tmp_path, fake_gdown):
    url = f"https://drive.google.com/file/d/{FILE_ID}/view"
    path = Download_data.GoogleDrive.download_file(url, tmp_path)
    assert Path(path).read_text().startswith("a,b")
    assert fake_gdown[0]["url"] == url and fake_gdown[0]["fuzzy"]


def test_public_file_by_id(tmp_path, fake_gdown):
    Download_data.GoogleDrive.download_file(FILE_ID, tmp_path)
    assert fake_gdown[0]["id"] == FILE_ID


def test_public_folder_and_load(tmp_path, fake_gdown):
    url = f"https://drive.google.com/drive/folders/{FILE_ID}"
    paths = Download_data.GoogleDrive.download_folder(url, tmp_path)
    assert sorted(Path(p).name for p in paths) == ["test.csv", "train.csv"]
    df = Load_data.from_drive(url, file="train.csv", destination=tmp_path / "x")
    assert df["a"].tolist() == [1]


def test_load_from_drive_file(tmp_path, fake_gdown):
    df = Load_data.from_drive(FILE_ID, destination=tmp_path)
    assert df["b"].tolist() == [2]


def test_public_failure_gives_sharing_hint(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "gdown", types.SimpleNamespace(
        download=lambda **kw: None))
    with pytest.raises(InvalidInput, match="Anyone with the link"):
        Download_data.GoogleDrive.download_file(FILE_ID, tmp_path)


def test_missing_credentials_file(tmp_path):
    with pytest.raises(CredentialsError, match="not found"):
        Download_data.GoogleDrive.download_file(FILE_ID, tmp_path,
                                                credentials=tmp_path / "nope.json")


def test_env_var_credentials_used(tmp_path, monkeypatch):
    creds = tmp_path / "creds.json"
    creds.write_text(json.dumps({"something": "else"}))
    monkeypatch.setenv(_gdrive.ENV_VAR, str(creds))
    with pytest.raises(CredentialsError, match="OAuth client"):
        Download_data.GoogleDrive.download_file(FILE_ID, tmp_path)


def test_check_filename_needs_credentials():
    with pytest.raises(CredentialsError):
        Download_data.GoogleDrive.check_filename(FILE_ID)


@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
def test_token_file_is_private(tmp_path):
    token = tmp_path / "tokens" / "t.json"
    _gdrive._write_private(token, "{}")
    assert stat.S_IMODE(token.stat().st_mode) == 0o600


def test_scope_is_read_only():
    assert _gdrive.SCOPES == ["https://www.googleapis.com/auth/drive.readonly"]


class _Req:
    def __init__(self, result):
        self.result = result

    def execute(self):
        return self.result


class FakeService:
    """Minimal Drive service: paged listing of a nested folder."""

    def __init__(self, tree):
        self.tree = tree

    def files(self):
        return self

    def list(self, q, pageToken=None, **kw):
        folder = q.split("'")[1]
        children = self.tree.get(folder, [])
        page = int(pageToken or 0)
        chunk = children[page * 2:(page + 1) * 2]  # 2 items per page to force paging
        nxt = str(page + 1) if (page + 1) * 2 < len(children) else None
        return _Req({"files": chunk, "nextPageToken": nxt})


def test_api_folder_pages_and_recurses(tmp_path, monkeypatch):
    tree = {
        "root": [{"id": f"f{i}", "name": f"file{i}.csv", "mimeType": "text/csv"}
                 for i in range(5)] + [{"id": "sub", "name": "../evil", "mimeType": _gdrive.FOLDER_MIME}],
        "sub": [{"id": "s1", "name": "inner.csv", "mimeType": "text/csv"}],
    }
    monkeypatch.setitem(sys.modules, "googleapiclient.errors",
                        types.SimpleNamespace(HttpError=type("HttpError", (Exception,), {})))
    saved = []

    def fake_download(service, file_id, dest_dir, name=None, mime_type=None):
        saved.append(Path(dest_dir) / name)
        return Path(dest_dir) / name

    monkeypatch.setattr(_gdrive, "api_download_file", fake_download)
    paths = _gdrive.api_download_folder(FakeService(tree), "root", tmp_path / "out", progress=False)
    assert len(paths) == 6  # all 5 files across 3 pages + 1 in the subfolder
    assert (tmp_path / "out" / ".._evil" / "inner.csv") in saved
