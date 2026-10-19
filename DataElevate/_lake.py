"""Read tables straight out of a data lake without downloading the whole thing.

Supports folders of Parquet/CSV/JSON files (including Hive-style partitions such as
``year=2025/month=10/``) on any storage fsspec can reach, and Delta Lake tables
(``deltalake`` package: no Spark, no Java). Column selection, filters and row limits
are pushed down, so only the files and columns you need are read.
"""

from ._deps import require
from .errors import DataElevateError, InvalidInput

FORMATS = ("auto", "parquet", "delta", "csv", "json")


def _filter_expression(filters):
    if not filters:
        return None
    pq = require("pyarrow.parquet", "pyarrow", None)
    try:
        return pq.filters_to_expression(filters)
    except Exception as exc:
        raise InvalidInput(
            f"Invalid filters {filters!r}: {exc}\n"
            "Use a list of (column, op, value) tuples, e.g. [('year', '=', 2025), "
            "('country', 'in', ['IN', 'US'])]. Ops: = != < <= > >= in 'not in'."
        ) from exc


def _filesystem(url, storage_options):
    from . import _remote
    if _remote.protocol(url) is None:
        return None, url
    return _remote._filesystem(url, storage_options)


def _is_delta(url, storage_options):
    fs, path = _filesystem(url, storage_options)
    log = path.rstrip("/") + "/_delta_log"
    if fs is None:
        from pathlib import Path
        return Path(log).is_dir()
    try:
        return fs.isdir(log)
    except Exception:
        return False


def open_dataset(url, format="auto", storage_options=None, version=None):
    """Return (pyarrow Dataset, resolved format) for a lake path."""
    if format not in FORMATS:
        raise InvalidInput(f"format must be one of {', '.join(FORMATS)}.")
    if format == "auto":
        format = "delta" if _is_delta(url, storage_options) else "parquet"

    if format == "delta":
        deltalake = require("deltalake", "deltalake", "delta")
        try:
            table = deltalake.DeltaTable(
                url, version=version if isinstance(version, int) else None,
                storage_options=storage_options)
            if isinstance(version, str):
                table.load_as_version(version)
            return table.to_pyarrow_dataset(), format
        except Exception as exc:
            raise InvalidInput(f"Could not open Delta table {url}: {exc}") from exc

    if version is not None:
        raise InvalidInput("version= only applies to Delta tables.")
    ds = require("pyarrow.dataset", "pyarrow", None)
    fs, path = _filesystem(url, storage_options)
    try:
        return ds.dataset(path, filesystem=fs, format=format, partitioning="hive"), format
    except DataElevateError:
        raise
    except Exception as exc:
        raise InvalidInput(
            f"Could not open {url} as a {format} dataset: {exc}\n"
            "Check the path and credentials (storage_options=, or your cloud's "
            "environment variables / config files).") from exc


def load(url, format="auto", columns=None, filters=None, limit=None, storage_options=None,
         version=None):
    """Read (part of) a lake table into a DataFrame."""
    dataset, _ = open_dataset(url, format, storage_options, version)
    expr = _filter_expression(filters)
    try:
        if limit is not None:
            table = dataset.head(int(limit), columns=columns, filter=expr)
        else:
            table = dataset.to_table(columns=columns, filter=expr)
    except Exception as exc:
        raise InvalidInput(f"Could not read {url}: {exc}") from exc
    return table.to_pandas()


def describe(url, format="auto", storage_options=None, version=None):
    """Summarise a lake table without reading its data."""
    dataset, fmt = open_dataset(url, format, storage_options, version)
    partitioning = getattr(dataset, "partitioning", None)
    part_cols = list(partitioning.schema.names) if partitioning is not None and \
        getattr(partitioning, "schema", None) is not None else []
    files = getattr(dataset, "files", None)
    return {
        "format": fmt,
        "columns": {f.name: str(f.type) for f in dataset.schema},
        "partition_columns": part_cols,
        "files": len(files) if files is not None else None,
    }
