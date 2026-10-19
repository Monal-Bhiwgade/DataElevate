"""Index image-classification folders into a DataFrame of (path, label, split).

Understands the two common layouts:

    images/cat/001.jpg                  -> label from the class folder
    images/train/cat/001.jpg            -> split from train/val/test, then label
"""

from pathlib import Path

import pandas as pd

from .errors import InvalidInput

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
SPLIT_NAMES = {
    "train": "train", "training": "train",
    "val": "val", "valid": "val", "validation": "val", "dev": "val",
    "test": "test", "testing": "test",
}


def _hidden(rel_parts):
    return any(p.startswith(".") or p == "__MACOSX" for p in rel_parts)


def _unwrap(root):
    """Step into lone wrapper folders (common in zips: ``PetImages/Cat/1.jpg``).

    A single folder is only a wrapper if it contains subfolders; a single folder of
    images (``cats/1.jpg``) is a class and is kept as the label.
    """
    while True:
        children = [c for c in root.iterdir() if not c.name.startswith(".") and c.name != "__MACOSX"]
        if len(children) == 1 and children[0].is_dir():
            inner = children[0]
            if inner.name.lower() not in SPLIT_NAMES and any(
                    c.is_dir() and not c.name.startswith(".") for c in inner.iterdir()):
                root = inner
                continue
        return root


def index_images(root, extensions=None):
    """Return a DataFrame with columns path, label (if folders) and split (if present)."""
    root = Path(root)
    if not root.is_dir():
        raise InvalidInput(f"Image folder not found: {root}")
    exts = {e.lower() if e.startswith(".") else "." + e.lower() for e in (extensions or IMAGE_EXT)}
    root = _unwrap(root)

    rows = []
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in exts:
            continue
        rel = f.relative_to(root).parts
        if _hidden(rel):
            continue
        folders = list(rel[:-1])
        split = None
        if folders and folders[0].lower() in SPLIT_NAMES:
            split = SPLIT_NAMES[folders[0].lower()]
            folders = folders[1:]
        rows.append({"path": str(f), "label": folders[0] if folders else None, "split": split})

    if not rows:
        raise InvalidInput(f"No images ({', '.join(sorted(exts))}) found under {root}.")
    df = pd.DataFrame(rows, columns=["path", "label", "split"])
    for col in ("split", "label"):
        if df[col].isna().all():
            df = df.drop(columns=col)
    return df
