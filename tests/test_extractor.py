import gzip
import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from DataElevate import Extractor, Invalid_Directory, Invalid_File_Support, InvalidInput


def test_zip(tmp_path):
    archive = tmp_path / "d.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("folder/train.csv", "a\n1\n")
    out = Extractor.extract_archive(archive, tmp_path / "out")
    assert (Path(out) / "folder" / "train.csv").read_text() == "a\n1\n"


@pytest.mark.parametrize("ext,mode", [(".tar", "w"), (".tar.gz", "w:gz"), (".tgz", "w:gz"),
                                      (".tar.bz2", "w:bz2"), (".tar.xz", "w:xz")])
def test_tar_variants(tmp_path, ext, mode):
    src = tmp_path / "train.csv"
    src.write_text("a\n1\n")
    archive = tmp_path / f"d{ext}"
    with tarfile.open(archive, mode) as tf:
        tf.add(src, arcname="train.csv")
    out = Extractor.extract_archive(archive, destination=tmp_path / "out")
    assert (Path(out) / "train.csv").exists()


def test_gz_single_file_and_remove(tmp_path):
    archive = tmp_path / "train.csv.gz"
    with gzip.open(archive, "wb") as fh:
        fh.write(b"a\n1\n")
    out = Extractor.extract_archive(archive, remove_finished=True)
    assert Path(out).name == "train.csv" and Path(out).read_text() == "a\n1\n"
    assert not archive.exists()


def test_legacy_to_path_keyword(tmp_path):
    archive = tmp_path / "d.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("x.txt", "hi")
    out = Extractor.extract_archive(archive, to_path=tmp_path / "legacy")
    assert (Path(out) / "x.txt").exists()


def test_zip_slip_blocked(tmp_path):
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../escaped.txt", "pwned")
    with pytest.raises(InvalidInput):
        Extractor.extract_archive(archive, tmp_path / "out")
    assert not (tmp_path / "escaped.txt").exists()


def test_tar_traversal_blocked(tmp_path):
    archive = tmp_path / "evil.tar"
    with tarfile.open(archive, "w") as tf:
        info = tarfile.TarInfo("../escaped.txt")
        data = b"pwned"
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    with pytest.raises(InvalidInput):
        Extractor.extract_archive(archive, tmp_path / "out")
    assert not (tmp_path / "escaped.txt").exists()


def test_tar_symlink_escape_blocked(tmp_path):
    archive = tmp_path / "evil.tar"
    with tarfile.open(archive, "w") as tf:
        info = tarfile.TarInfo("link")
        info.type = tarfile.SYMTYPE
        info.linkname = "../../etc"
        tf.addfile(info)
    with pytest.raises(InvalidInput):
        Extractor.extract_archive(archive, tmp_path / "out")


def test_unsupported_and_missing(tmp_path):
    bad = tmp_path / "file.rar"
    bad.write_bytes(b"x")
    with pytest.raises(Invalid_File_Support):
        Extractor.extract_archive(bad)
    with pytest.raises(ValueError):  # still a ValueError, as in 1.0.x
        Extractor.extract_archive(bad)
    with pytest.raises(Invalid_Directory):
        Extractor.extract_archive(tmp_path / "missing.zip")
