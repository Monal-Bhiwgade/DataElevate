"""Kaggle helpers built on ``kagglehub``."""

import logging
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

from ._deps import require
from .errors import InvalidInput

log = logging.getLogger(__name__)

_URL_RE = re.compile(r"^(https?://)?(www\.)?kaggle\.com/", re.IGNORECASE)
_PATH_RE = re.compile(r"^/datasets/([^/]+)/([^/]+)(?:/versions/(\d+))?")
_HANDLE_RE = re.compile(r"([\w.-]+)/([\w.-]+)(?:/versions/(\d+))?/?")


def parse_handle(dataset):
    """Turn a Kaggle dataset URL or ``owner/name`` ID into (kagglehub handle, name)."""
    if not isinstance(dataset, str) or not dataset.strip():
        raise InvalidInput("Kaggle dataset must be a URL or an 'owner/dataset-name' ID.")
    text = dataset.strip()
    if _URL_RE.match(text):
        path = urlparse(text if "://" in text else "https://" + text).path
        match = _PATH_RE.match(path)
        if not match:
            raise InvalidInput(
                f"'{dataset}' is not a Kaggle dataset URL. "
                "Expected https://www.kaggle.com/datasets/<owner>/<dataset-name>.")
    else:
        match = _HANDLE_RE.fullmatch(text)
        if not match:
            raise InvalidInput(
                f"'{dataset}' is not a valid Kaggle dataset ID. Expected '<owner>/<dataset-name>'.")
    owner, name, version = match.groups()
    handle = f"{owner}/{name}" + (f"/versions/{version}" if version else "")
    return handle, name


def _replace(src, target):
    if target.is_dir() and not target.is_symlink():
        shutil.rmtree(target)
    elif target.exists() or target.is_symlink():
        target.unlink()
    if src.is_dir():
        shutil.copytree(src, target)
    else:
        shutil.copy2(src, target)


def remove_cache(cache_path):
    """Delete kagglehub's cached copy of one dataset (all its versions).

    Only removes paths with kagglehub's ``.../datasets/<owner>/<name>/versions/<n>``
    layout, so nothing else on disk can be touched.
    """
    parts = Path(cache_path).parts
    if len(parts) >= 5 and parts[-5] == "datasets" and parts[-2] == "versions":
        dataset_dir = Path(*parts[:-2])
        shutil.rmtree(dataset_dir, ignore_errors=True)
    else:
        log.debug("Not removing unexpected Kaggle cache path %s", cache_path)


def download(dataset, destination=None, keep_cache=False):
    """Download a Kaggle dataset into ``destination``. Returns the copied top-level paths."""
    kagglehub = require("kagglehub", "kagglehub", None)
    handle, name = parse_handle(dataset)
    try:
        cache_path = Path(kagglehub.dataset_download(handle))
    except Exception as exc:
        raise InvalidInput(
            f"Kaggle could not download '{dataset}': {exc}\n"
            "Check the dataset name. Private datasets also need your Kaggle API "
            "credentials (KAGGLE_USERNAME / KAGGLE_KEY or ~/.kaggle/kaggle.json)."
        ) from exc

    destination = Path(destination) if destination else Path.cwd() / "Data" / name
    destination.mkdir(parents=True, exist_ok=True)

    paths = []
    for item in sorted(cache_path.iterdir()):
        target = destination / item.name
        _replace(item, target)
        paths.append(str(target))

    if not keep_cache:
        remove_cache(cache_path)
    return paths
