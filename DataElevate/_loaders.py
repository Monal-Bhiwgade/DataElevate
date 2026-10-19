"""Read local files into pandas DataFrames."""

import csv
from pathlib import Path

import pandas as pd

from .errors import Invalid_Directory, Invalid_File_Support

CSV_EXT = {".csv"}
TEXT_EXT = {".txt", ".tsv"}
EXCEL_EXT = {".xlsx", ".xlsm", ".xls"}
SUPPORTED_EXT = CSV_EXT | TEXT_EXT | EXCEL_EXT


def check_data_type(path):
    """Return 'csv', 'text', 'excel', or None for an unsupported extension."""
    ext = Path(path).suffix.lower()
    if ext in CSV_EXT:
        return "csv"
    if ext in TEXT_EXT:
        return "text"
    if ext in EXCEL_EXT:
        return "excel"
    return None


def from_csv(path, **kwargs):
    return pd.read_csv(path, **kwargs)


def from_excel(path, **kwargs):
    return pd.read_excel(path, **kwargs)


def from_text(path, **kwargs):
    """Read a delimited text file, detecting tab/comma/semicolon/pipe delimiters."""
    if "sep" not in kwargs and "delimiter" not in kwargs:
        with open(path, "r", newline="", encoding=kwargs.get("encoding") or "utf-8",
                  errors="replace") as fh:
            sample = fh.read(64 * 1024)
        try:
            kwargs["sep"] = csv.Sniffer().sniff(sample, delimiters="\t,;|").delimiter
        except csv.Error:
            first_line = sample.splitlines()[0] if sample else ""
            kwargs["sep"] = "\t" if "\t" in first_line else ","
    return pd.read_csv(path, **kwargs)


def load(path, **kwargs):
    """Load a supported file into a DataFrame. Extra kwargs go to pandas."""
    path = Path(path)
    if not path.is_file():
        raise Invalid_Directory(f"File not found: {path}")
    kind = check_data_type(path)
    if kind == "csv":
        return from_csv(path, **kwargs)
    if kind == "text":
        return from_text(path, **kwargs)
    if kind == "excel":
        return from_excel(path, **kwargs)
    raise Invalid_File_Support(
        f"'{path.name}' is not a supported file type. Supported: "
        f"{', '.join(sorted(SUPPORTED_EXT))}")


def find_loadable(paths):
    """Return every supported data file under the given files/folders, sorted."""
    found = []
    for p in map(Path, paths):
        if p.is_dir():
            found += [f for f in p.rglob("*") if f.is_file() and check_data_type(f)]
        elif p.is_file() and check_data_type(p):
            found.append(p)
    return sorted(set(found))
