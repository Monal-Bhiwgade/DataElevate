import http.server
import io
import sys
import threading
import types
import zipfile
from pathlib import Path

import fsspec
import pandas as pd
import pytest

from DataElevate import Download_data, InvalidInput, Load_data, MissingDependencyError
from DataElevate._remote import _name_from_disposition, normalize_http_url, protocol


# --------------------------------------------------------------- local http server

def _zip_bytes():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("images/cat/1.jpg", b"jpg")
        zf.writestr("images/dog/2.jpg", b"jpg")
    return buf.getvalue()


ROUTES = {
    "/data/train.csv": (b"a,b\n1,2\n3,4\n", {}),
    "/download?id=7": (b"x\n9\n", {"Content-Disposition": 'attachment; filename="report.csv"'}),
    "/pets.zip": (_zip_bytes(), {}),
    "/table.parquet": (None, {}),
}


class Handler(http.server.BaseHTTPRequestHandler):
    hits = []

    def do_GET(self):
        Handler.hits.append(self.path)
        if self.path not in ROUTES:
            self.send_response(404)
            self.end_headers()
            return
        body, headers = ROUTES[self.path]
        self.send_response(200)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def server():
    buf = io.BytesIO()
    pd.DataFrame({"v": [1, 2, 3]}).to_parquet(buf)
    ROUTES["/table.parquet"] = (buf.getvalue(), {})
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def test_from_url_csv(server, tmp_path):
    df = Load_data.from_url(f"{server}/data/train.csv", destination=tmp_path)
    assert df["b"].tolist() == [2, 4]


def test_from_url_parquet(server, tmp_path):
    assert Load_data.from_url(f"{server}/table.parquet", destination=tmp_path)["v"].sum() == 6


def test_filename_from_content_disposition(server, tmp_path):
    paths = Download_data.from_url(f"{server}/download?id=7", tmp_path, progress=False)
    assert Path(paths[0]).name == "report.csv"


def test_cache_reuses_file(server, tmp_path):
    Handler.hits.clear()
    Download_data.from_url(f"{server}/data/train.csv", tmp_path, progress=False)
    Download_data.from_url(f"{server}/data/train.csv", tmp_path, progress=False)
    assert Handler.hits.count("/data/train.csv") == 1
    Download_data.from_url(f"{server}/data/train.csv", tmp_path, progress=False, overwrite=True)
    assert Handler.hits.count("/data/train.csv") == 2


def test_archive_is_extracted(server, tmp_path):
    paths = Download_data.from_url(f"{server}/pets.zip", tmp_path, progress=False)
    folder = Path(paths[0])
    assert folder.is_dir() and (folder / "images" / "dog" / "2.jpg").exists()
    raw = Download_data.from_url(f"{server}/pets.zip", tmp_path / "raw", extract=False,
                                 progress=False)
    assert raw[0].endswith("pets.zip")


def test_http_error(server, tmp_path):
    with pytest.raises(InvalidInput, match="404"):
        Download_data.from_url(f"{server}/missing.csv", tmp_path, progress=False)


def test_images_from_url(server, tmp_path):
    df = Load_data.from_images(f"{server}/pets.zip", destination=tmp_path)
    assert sorted(df["label"]) == ["cat", "dog"]


def test_not_a_url(tmp_path):
    with pytest.raises(InvalidInput, match="from_local"):
        Download_data.from_url(str(tmp_path / "x.csv"))


# --------------------------------------------------------------- link rewriting

@pytest.mark.parametrize("url,expected", [
    ("https://github.com/o/r/blob/main/data/x.csv",
     "https://raw.githubusercontent.com/o/r/main/data/x.csv"),
    ("https://www.dropbox.com/s/abc/x.csv?dl=0", "https://www.dropbox.com/s/abc/x.csv?dl=1"),
    ("https://www.dropbox.com/scl/fi/abc/x.csv?rlkey=k",
     "https://www.dropbox.com/scl/fi/abc/x.csv?rlkey=k&dl=1"),
    ("https://example.com/x.csv", "https://example.com/x.csv"),
])
def test_normalize_http_url(url, expected):
    assert normalize_http_url(url) == expected


@pytest.mark.parametrize("header,name", [
    ('attachment; filename="a b.csv"', "a b.csv"),
    ("attachment; filename*=UTF-8''r%C3%A9sum%C3%A9.csv", "résumé.csv"),
    ('attachment; filename="../../evil.csv"', ".._.._evil.csv"),
    (None, None),
])
def test_content_disposition(header, name):
    assert _name_from_disposition(header) == name


def test_protocol():
    assert protocol("S3://b/k") == "s3" and protocol("C:\\data\\x.csv") is None


def test_drive_and_kaggle_links_are_routed(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(Download_data.GoogleDrive, "download_file",
                        staticmethod(lambda url, dest, **kw: calls.append("drive") or str(tmp_path / "f.csv")))
    import DataElevate._kaggle as k
    monkeypatch.setattr(k, "download", lambda url, dest: calls.append("kaggle") or [])
    Download_data.from_url("https://drive.google.com/file/d/1AbCdEfGhIjK/view", tmp_path)
    Download_data.from_url("https://www.kaggle.com/datasets/o/n", tmp_path)
    assert calls == ["drive", "kaggle"]


# ------------------------------------------------------------- fsspec / cloud paths

@pytest.fixture
def memfs():
    fs = fsspec.filesystem("memory")
    fs.store.clear()
    fs.pseudo_dirs.clear()
    fs.pseudo_dirs.append("")
    yield fs
    fs.store.clear()


def test_memory_file(memfs, tmp_path):
    with memfs.open("/bucket/train.csv", "w") as fh:
        fh.write("a\n1\n2\n")
    assert Load_data.from_cloud("memory://bucket/train.csv", destination=tmp_path)["a"].sum() == 3


def test_memory_folder_keeps_structure(memfs, tmp_path):
    for p in ("/lake/raw/a.csv", "/lake/raw/sub/b.csv"):
        with memfs.open(p, "w") as fh:
            fh.write("x\n1\n")
    paths = Download_data.from_url("memory://lake/raw", tmp_path, progress=False)
    folder = Path(paths[0])
    assert (folder / "a.csv").exists() and (folder / "sub" / "b.csv").exists()
    df = Load_data.from_url("memory://lake/raw", file="b.csv", destination=tmp_path / "2")
    assert df["x"].tolist() == [1]


def test_memory_glob(memfs, tmp_path):
    for p in ("/b/p1.parquet", "/b/p2.parquet", "/b/notes.txt"):
        with memfs.open(p, "wb") as fh:
            pd.DataFrame({"v": [1]}).to_parquet(fh) if p.endswith(".parquet") else fh.write(b"x")
    paths = Download_data.from_url("memory://b/*.parquet", tmp_path, progress=False)
    assert sorted(Path(p).name for p in paths) == ["p1.parquet", "p2.parquet"]


def test_missing_remote_file(memfs, tmp_path):
    with pytest.raises(InvalidInput, match="Not found"):
        Download_data.from_url("memory://nope/x.csv", tmp_path, progress=False)


def test_missing_cloud_extra_names_the_install(tmp_path, monkeypatch):
    import DataElevate._remote as r

    def no_backend(url, **kw):
        raise ImportError("Install s3fs to access S3")
    monkeypatch.setattr(fsspec.core, "url_to_fs", no_backend)
    with pytest.raises(MissingDependencyError, match=r"DataElevate\[s3\]"):
        Download_data.from_url("s3://bucket/x.csv", tmp_path)
    assert r.PROTOCOL_EXTRAS["abfss"][1] == "azure"


def test_storage_options_are_passed_through(tmp_path, monkeypatch):
    seen = {}
    real = fsspec.core.url_to_fs

    def spy(url, **kw):
        seen.update(kw)
        return real("memory://x", )
    monkeypatch.setattr(fsspec.core, "url_to_fs", spy)
    with pytest.raises(InvalidInput):
        Download_data.from_url("s3://bucket/x.csv", tmp_path, storage_options={"anon": True})
    assert seen == {"anon": True}
