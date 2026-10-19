"""Read local files into pandas DataFrames."""

import bz2
import csv
import gzip
import json
import lzma
import zipfile
from pathlib import Path

import pandas as pd

from .errors import Invalid_Directory, Invalid_File_Support

# extension -> kind
FORMATS = {
    ".csv": "csv",
    ".txt": "text", ".tsv": "text",
    ".xlsx": "excel", ".xlsm": "excel", ".xls": "excel",
    ".parquet": "parquet", ".pq": "parquet",
    ".json": "json",
    ".jsonl": "jsonl", ".ndjson": "jsonl",
    ".feather": "feather", ".arrow": "feather",
}
# Kinds pandas can read through a compression layer, e.g. train.csv.gz or train.csv.zip
COMPRESSIBLE = {"csv", "text", "json", "jsonl"}
COMPRESSION_EXT = {".gz": "gzip", ".bz2": "bz2", ".xz": "xz", ".zip": "zip"}

SUPPORTED_EXT = sorted(FORMATS) + [
    f"{e}{c}" for e in (".csv", ".tsv", ".txt", ".json", ".jsonl") for c in (".gz", ".zip")]


def _split(path):
    """Return (kind, compression) for a file name, or (None, None)."""
    suffixes = [s.lower() for s in Path(path).suffixes]
    if not suffixes:
        return None, None
    last = suffixes[-1]
    if last in FORMATS:
        return FORMATS[last], None
    if last in COMPRESSION_EXT and len(suffixes) >= 2:
        kind = FORMATS.get(suffixes[-2])
        if kind in COMPRESSIBLE:
            return kind, COMPRESSION_EXT[last]
    return None, None


def check_data_type(path):
    """Return the data kind ('csv', 'text', 'excel', 'parquet', 'json', 'jsonl',
    'feather') for a file name, or None if it isn't a supported data file."""
    return _split(path)[0]


def _sample_text(path, compression, encoding, size=64 * 1024):
    if compression == "zip":
        with zipfile.ZipFile(path) as zf:
            names = [n for n in zf.namelist() if not n.endswith("/")]
            raw = zf.open(names[0]).read(size) if names else b""
        return raw.decode(encoding, errors="replace")
    opener = {"gzip": gzip.open, "bz2": bz2.open, "xz": lzma.open}.get(compression, open)
    with opener(path, "rb") as fh:
        return fh.read(size).decode(encoding, errors="replace")


def from_text(path, compression=None, **kwargs):
    """Read a delimited text file, detecting tab/comma/semicolon/pipe delimiters."""
    if "sep" not in kwargs and "delimiter" not in kwargs:
        sample = _sample_text(path, compression, kwargs.get("encoding") or "utf-8")
        try:
            kwargs["sep"] = csv.Sniffer().sniff(sample, delimiters="\t,;|").delimiter
        except csv.Error:
            first_line = sample.splitlines()[0] if sample else ""
            kwargs["sep"] = "\t" if "\t" in first_line else ","
    return pd.read_csv(path, compression=compression or "infer", **kwargs)


def from_json(path, compression=None, **kwargs):
    """Read JSON: a list of records, a column dict, or nested objects (flattened)."""
    try:
        return pd.read_json(path, compression=compression or "infer", **kwargs)
    except ValueError:
        if kwargs:
            raise
        text = _sample_text(path, compression, "utf-8", size=-1) if compression \
            else Path(path).read_text(encoding="utf-8")
        data = json.loads(text)
        if isinstance(data, dict):
            # {"data": [...]} style wrappers: use the first list of records found
            lists = [v for v in data.values() if isinstance(v, list)]
            data = lists[0] if len(lists) == 1 else [data]
        return pd.json_normalize(data)


def load(path, **kwargs):
    """Load a supported file into a DataFrame. Extra kwargs go to pandas."""
    path = Path(path)
    if not path.is_file():
        raise Invalid_Directory(f"File not found: {path}")
    kind, compression = _split(path)
    if kind == "csv":
        return pd.read_csv(path, compression=compression or "infer", **kwargs)
    if kind == "text":
        return from_text(path, compression, **kwargs)
    if kind == "excel":
        return pd.read_excel(path, **kwargs)
    if kind == "parquet":
        return pd.read_parquet(path, **kwargs)
    if kind == "json":
        return from_json(path, compression, **kwargs)
    if kind == "jsonl":
        return pd.read_json(path, lines=True, compression=compression or "infer", **kwargs)
    if kind == "feather":
        return pd.read_feather(path, **kwargs)
    raise Invalid_File_Support(
        f"'{path.name}' is not a supported file type. Supported: {', '.join(SUPPORTED_EXT)}")


def find_loadable(paths):
    """Return every supported data file under the given files/folders, sorted."""
    found = []
    for p in map(Path, paths):
        if p.is_dir():
            found += [f for f in p.rglob("*") if f.is_file() and check_data_type(f)]
        elif p.is_file() and check_data_type(p):
            found.append(p)
    return sorted(set(found))


# Kept for anyone who imported these helpers in 1.1
def from_csv(path, **kwargs):
    return pd.read_csv(path, **kwargs)


def from_excel(path, **kwargs):
    return pd.read_excel(path, **kwargs)

