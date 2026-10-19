"""Hugging Face Hub datasets (optional extra: ``pip install "DataElevate[huggingface]"``).

Uses the user's own token if one is needed (``token=`` or the ``HF_TOKEN`` environment
variable / ``huggingface-cli login``). Public datasets need no token.
"""

import re
from pathlib import Path

from ._deps import require
from .errors import InvalidInput

_URL_RE = re.compile(r"^(?:https?://)?(?:www\.)?huggingface\.co/datasets/([^/?#]+(?:/[^/?#]+)?)",
                     re.IGNORECASE)
_NAME_RE = re.compile(r"[\w.-]+(?:/[\w.-]+)?")


def parse_name(name):
    """Accept 'imdb', 'owner/name' or a huggingface.co/datasets/... URL."""
    if not isinstance(name, str) or not name.strip():
        raise InvalidInput("Hugging Face dataset must be a name like 'owner/name' or a URL.")
    text = name.strip()
    match = _URL_RE.match(text)
    if match:
        return match.group(1)
    if _NAME_RE.fullmatch(text):
        return text
    raise InvalidInput(f"'{name}' is not a valid Hugging Face dataset name or URL.")


def load(name, split="train", config=None, revision=None, token=None, **kwargs):
    """Return a DataFrame for one split, or a dict of DataFrames when split=None."""
    datasets = require("datasets", "datasets", "huggingface")
    repo = parse_name(name)
    try:
        ds = datasets.load_dataset(repo, config, split=split, revision=revision,
                                   token=token, **kwargs)
    except Exception as exc:
        raise InvalidInput(
            f"Hugging Face could not load '{repo}' (config={config!r}, split={split!r}): {exc}\n"
            "Datasets with several configs need config='<name>'. Gated or private datasets "
            "need your own token (token= or HF_TOKEN)."
        ) from exc
    if split is None:
        return {name_: part.to_pandas() for name_, part in ds.items()}
    return ds.to_pandas()


def download(name, destination=None, revision=None, token=None):
    """Download the raw dataset repository files. Returns the local folder."""
    hub = require("huggingface_hub", "huggingface_hub", "huggingface")
    repo = parse_name(name)
    dest = Path(destination) if destination else Path.cwd() / "Data" / repo.split("/")[-1]
    try:
        path = hub.snapshot_download(repo_id=repo, repo_type="dataset", local_dir=str(dest),
                                     revision=revision, token=token)
    except Exception as exc:
        raise InvalidInput(f"Hugging Face could not download '{repo}': {exc}") from exc
    return str(path)
