"""Safely extract archives (.zip, .tar, .tar.gz/.tgz, .tar.bz2, .tar.xz, .gz, .bz2, .xz)."""

import bz2
import gzip
import lzma
import shutil
import tarfile
import zipfile
from pathlib import Path

from .errors import Invalid_Directory, Invalid_File_Support, InvalidInput

_TAR_MODES = {
    ".tar": "r:",
    ".tar.gz": "r:gz", ".tgz": "r:gz",
    ".tar.bz2": "r:bz2", ".tbz2": "r:bz2", ".tbz": "r:bz2",
    ".tar.xz": "r:xz", ".txz": "r:xz",
}
_SINGLE = {".gz": gzip.open, ".bz2": bz2.open, ".xz": lzma.open}


def _archive_kind(path):
    name = path.name.lower()
    for ext in sorted(_TAR_MODES, key=len, reverse=True):
        if name.endswith(ext):
            return "tar", ext
    if name.endswith(".zip"):
        return "zip", ".zip"
    for ext in _SINGLE:
        if name.endswith(ext):
            return "single", ext
    return None, None


def _ensure_inside(root, target, member):
    target = target.resolve()
    if target != root and root not in target.parents:
        raise InvalidInput(f"Blocked unsafe path in archive: '{member}' would extract "
                           f"outside {root}.")


def _extract_tar(path, mode, root):
    with tarfile.open(path, mode) as tar:
        for member in tar.getmembers():
            dest = root / member.name
            _ensure_inside(root, dest, member.name)
            if member.issym():
                _ensure_inside(root, dest.parent / member.linkname, member.name)
            elif member.islnk():
                _ensure_inside(root, root / member.linkname, member.name)
            elif member.isdev():
                raise InvalidInput(f"Blocked device file in archive: '{member.name}'.")
        if hasattr(tarfile, "data_filter"):
            tar.extractall(root, filter="data")
        else:  # Python without extraction filters: members were checked above
            tar.extractall(root)


def _extract_zip(path, root):
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            _ensure_inside(root, root / name, name)
        zf.extractall(root)


class Extractor:

    @staticmethod
    def extract_archive(from_path, destination=None, remove_finished=False, *, to_path=None):
        """Extract an archive and return where the contents went.

        Args:
            from_path: Path to the archive.
            destination: Folder to extract into. Defaults to the archive's folder.
            remove_finished: Delete the archive after a successful extraction.

        Returns:
            The extraction folder, or the output file for single-file
            compressions (.gz, .bz2, .xz), as a string.
        """
        path = Path(from_path)
        if not path.is_file():
            raise Invalid_Directory(f"Archive not found: {path}")
        kind, ext = _archive_kind(path)
        if kind is None:
            raise Invalid_File_Support(f"Extraction of '{path.name}' is not supported.")

        root = Path(destination or to_path or path.parent).resolve()
        root.mkdir(parents=True, exist_ok=True)

        if kind == "tar":
            _extract_tar(path, _TAR_MODES[ext], root)
            result = root
        elif kind == "zip":
            _extract_zip(path, root)
            result = root
        else:
            result = root / path.name[: -len(ext)]
            with _SINGLE[ext](path, "rb") as src, open(result, "wb") as dst:
                shutil.copyfileobj(src, dst)

        if remove_finished:
            path.unlink()
        return str(result)
