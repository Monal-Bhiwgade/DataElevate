"""Download from any link: direct URLs, cloud storage and other fsspec filesystems.

* ``http(s)://``  plain download with progress, resume-safe temp file, and caching.
  GitHub "blob" links and Dropbox share links are rewritten to their direct form;
  Google Drive and Kaggle links are routed to those downloaders.
* ``s3://``, ``gs://``, ``az://``/``abfs://``, ``sftp://``, ``ftp://``, ``github://``,
  ``hf://``, ``memory://`` ... go through fsspec, the same layer pandas uses. Each cloud
  needs only a small pure-Python extra, so it works the same on Windows, macOS and Linux.

Credentials are always the user's own: environment variables, the cloud's standard
config files, or ``storage_options=``. DataElevate never stores them.
"""

import os
import re
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qsl, unquote, urlencode, urlparse, urlunparse

from ._deps import require
from ._gdrive import safe_name
from .errors import DataElevateError, InvalidInput, MissingDependencyError

DEFAULT_DIR = "Data"
HTTP = {"http", "https"}
# protocol -> (package to install, DataElevate extra)
PROTOCOL_EXTRAS = {
    "s3": ("s3fs", "s3"), "s3a": ("s3fs", "s3"),
    "gs": ("gcsfs", "gcs"), "gcs": ("gcsfs", "gcs"),
    "az": ("adlfs", "azure"), "abfs": ("adlfs", "azure"), "abfss": ("adlfs", "azure"),
    "adl": ("adlfs", "azure"),
    "sftp": ("paramiko", "sftp"), "ssh": ("paramiko", "sftp"),
    "hf": ("huggingface_hub", "huggingface"),
}
_PROTO_RE = re.compile(r"^([a-zA-Z][\w+.-]*)://")
_GLOB_CHARS = set("*?[")


def protocol(url):
    """Return the lower-case URL scheme, or None for a plain path."""
    match = _PROTO_RE.match(url.strip()) if isinstance(url, str) else None
    return match.group(1).lower() if match else None


# --------------------------------------------------------------------------- http

def normalize_http_url(url):
    """Rewrite share links that would otherwise download an HTML page."""
    parts = urlparse(url.strip())
    host = parts.netloc.lower()

    # github.com/<owner>/<repo>/blob/<ref>/<path> -> raw.githubusercontent.com/...
    if host in ("github.com", "www.github.com"):
        segs = parts.path.strip("/").split("/")
        if len(segs) > 4 and segs[2] in ("blob", "raw"):
            path = "/".join(segs[:2] + segs[3:])
            return f"https://raw.githubusercontent.com/{path}"

    # Dropbox share links: dl=0 shows a preview page, dl=1 downloads the file
    if host.endswith("dropbox.com"):
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "dl"]
        query.append(("dl", "1"))
        return urlunparse(parts._replace(query=urlencode(query)))
    return url.strip()


def _name_from_url(url):
    name = unquote(PurePosixPath(urlparse(url).path).name)
    return safe_name(name) if name else None


def _name_from_disposition(header):
    if not header:
        return None
    match = re.search(r"filename\*\s*=\s*[^']*''([^;]+)", header, re.IGNORECASE)
    if match:
        return safe_name(unquote(match.group(1).strip().strip('"')))
    match = re.search(r'filename\s*=\s*"?([^";]+)"?', header, re.IGNORECASE)
    return safe_name(match.group(1).strip()) if match else None


def http_download(url, dest_dir, overwrite=False, progress=True, timeout=60):
    """Stream a URL to ``dest_dir``. Reuses an existing file unless overwrite=True."""
    requests = require("requests", "requests", None)
    from tqdm.auto import tqdm

    url = normalize_http_url(url)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    url_name = _name_from_url(url)
    if url_name and Path(url_name).suffix and not overwrite and (dest_dir / url_name).is_file():
        return dest_dir / url_name

    try:
        with requests.get(url, stream=True, timeout=timeout, allow_redirects=True) as resp:
            if resp.status_code >= 400:
                raise InvalidInput(f"Download failed: HTTP {resp.status_code} for {url}")
            name = (_name_from_disposition(resp.headers.get("content-disposition"))
                    or url_name or "download")
            target = dest_dir / name
            if target.is_file() and not overwrite:
                return target
            tmp = target.with_name(target.name + ".part")
            total = int(resp.headers.get("content-length") or 0) or None
            with open(tmp, "wb") as fh, tqdm(total=total, unit="B", unit_scale=True,
                                            desc=name, disable=not progress) as bar:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    if chunk:
                        fh.write(chunk)
                        bar.update(len(chunk))
            os.replace(tmp, target)
            return target
    except requests.RequestException as exc:
        raise InvalidInput(f"Could not download {url}: {exc}") from exc


# ------------------------------------------------------------------------- fsspec

def _filesystem(url, storage_options):
    fsspec = require("fsspec", "fsspec", None)
    proto = protocol(url)
    try:
        return fsspec.core.url_to_fs(url, **(storage_options or {}))
    except ImportError as exc:
        package, extra = PROTOCOL_EXTRAS.get(proto, (f"an fsspec backend for {proto}://", None))
        raise MissingDependencyError(package, extra) from exc
    except ValueError as exc:
        raise InvalidInput(f"Unsupported URL scheme '{proto}://' in {url}: {exc}") from exc


def _local_target(root, rel):
    parts = [safe_name(p) for p in rel.split("/") if p]
    target = root.joinpath(*parts) if parts else root
    resolved, base = target.resolve(), root.resolve()
    if resolved != base and base not in resolved.parents:
        raise InvalidInput(f"Blocked unsafe remote path '{rel}'.")
    return target


def fs_download(url, dest_dir, storage_options=None, overwrite=False, progress=True):
    """Download a file, folder or glob from an fsspec URL. Returns local paths."""
    from tqdm.auto import tqdm

    fs, path = _filesystem(url, storage_options)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    def fetch(remote, local):
        if local.is_file() and not overwrite:
            return local
        local.parent.mkdir(parents=True, exist_ok=True)
        tmp = local.with_name(local.name + ".part")
        fs.get_file(remote, str(tmp))
        os.replace(tmp, local)
        return local

    try:
        if _GLOB_CHARS & set(path):
            matches = [m for m in fs.glob(path) if fs.isfile(m)]
            if not matches:
                raise InvalidInput(f"No files match {url}")
            it = tqdm(matches, unit="file", disable=not progress)
            return [fetch(m, _local_target(dest_dir, PurePosixPath(m).name)) for m in it]

        if fs.isdir(path):
            base = path.rstrip("/")
            folder = _local_target(dest_dir, PurePosixPath(base).name or "data")
            files = fs.find(base)
            for remote in tqdm(files, unit="file", disable=not progress):
                rel = remote[len(base):].lstrip("/") if remote.startswith(base) \
                    else PurePosixPath(remote).name
                fetch(remote, _local_target(folder, rel))
            folder.mkdir(parents=True, exist_ok=True)
            return [folder]

        if not fs.exists(path):
            raise InvalidInput(f"Not found: {url}")
        return [fetch(path, _local_target(dest_dir, PurePosixPath(path).name))]
    except DataElevateError:
        raise
    except Exception as exc:
        raise InvalidInput(
            f"Could not read {url}: {type(exc).__name__}: {exc}\n"
            "Check the path and your credentials. Public buckets usually need "
            "storage_options={'anon': True}."
        ) from exc


# ------------------------------------------------------------------------ routing

def _is_unpack_target(path):
    """True for archives to unpack (images.zip), False for compressed data (train.csv.gz)."""
    from ._loaders import check_data_type
    from .extractor import _archive_kind
    kind, _ = _archive_kind(path)
    return path.is_file() and kind in ("tar", "zip") and check_data_type(path) is None


def _unpack(path, overwrite):
    from .extractor import Extractor, _archive_kind
    _, ext = _archive_kind(path)
    folder = path.with_name(path.name[: -len(ext)] or "extracted")
    if folder.is_dir() and any(folder.iterdir()) and not overwrite:
        return folder
    return Path(Extractor.extract_archive(path, folder))


def download(url, destination=None, extract=True, storage_options=None, overwrite=False,
             progress=True, credentials=None):
    """Download any supported link. Returns a list of local paths (files or folders)."""
    proto = protocol(url)
    if proto is None:
        raise InvalidInput(f"'{url}' is not a URL. For files on disk use Load_data.from_local().")
    dest = Path(destination) if destination else Path.cwd() / DEFAULT_DIR

    if proto in HTTP:
        host = urlparse(url).netloc.lower()
        if host.endswith(("drive.google.com", "docs.google.com")):
            from .download import Download_data
            gd = Download_data.GoogleDrive
            if "/folders/" in url:
                paths = gd.download_folder(url, dest, credentials=credentials, progress=progress)
            else:
                paths = [gd.download_file(url, dest, credentials=credentials, progress=progress)]
        elif host.endswith("kaggle.com"):
            from . import _kaggle
            paths = _kaggle.download(url, destination)
        else:
            paths = [http_download(url, dest, overwrite, progress)]
    else:
        paths = fs_download(url, dest, storage_options, overwrite, progress)

    paths = [Path(p) for p in paths]
    if extract:
        paths = [_unpack(p, overwrite) if _is_unpack_target(p) else p for p in paths]
    return [str(p) for p in paths]
