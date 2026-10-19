"""Smart loader: give it any source, or many, and get one DataFrame back.

Each source is detected automatically (local file or folder, https link, cloud path,
data lake, Kaggle, Google Drive, Hugging Face, database URL, image folder, or an
existing DataFrame), loaded with the right loader, and the results are combined.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from . import _images, _loaders, _remote
from .errors import DataElevateError, Invalid_Directory, InvalidInput

log = logging.getLogger(__name__)

COMBINE_MODES = ("auto", "concat", "dict")
DB_SCHEMES = {"postgresql", "postgres", "mysql", "mariadb", "mssql", "sqlite", "oracle",
              "redshift", "snowflake", "bigquery", "databricks", "duckdb", "trino", "presto"}
_HANDLE_RE = re.compile(r"[\w.-]+/[\w.-]+")

# Options each loader understands; anything else in a spec goes to the pandas reader.
LOADER_KEYS = {"file", "destination", "storage_options", "credentials", "auth", "columns",
               "filters", "limit", "format", "version", "split", "config", "revision",
               "token", "table", "query", "params", "schema", "extensions", "overwrite",
               "combine"}


# ---------------------------------------------------------------------- detection

def detect(source):
    """Return what kind of source this is, without loading it."""
    if isinstance(source, pd.DataFrame):
        return "dataframe"
    if not isinstance(source, (str, Path)):
        raise InvalidInput(f"Can't load a source of type {type(source).__name__}.")
    text = str(source).strip()
    low = text.lower()

    if low.startswith("kaggle:"):
        return "kaggle"
    if low.startswith(("hf:", "huggingface:")) and not low.startswith("hf://"):
        return "huggingface"

    proto = _remote.protocol(text)
    if proto:
        if proto.split("+")[0] in DB_SCHEMES:
            return "database"
        if proto in _remote.HTTP:
            host = urlparse(text).netloc.lower()
            if host.endswith("huggingface.co") and "/datasets/" in text:
                return "huggingface"
            if host.endswith(("drive.google.com", "docs.google.com")):
                return "drive"
            if host.endswith("kaggle.com"):
                return "kaggle"
            return "url"
        path = urlparse(text).path
        name = Path(path.rstrip("/")).name
        if _remote._GLOB_CHARS & set(path) or _loaders.check_data_type(name) or \
                any(name.lower().endswith(e) for e in (".zip", ".tar", ".tgz", ".tar.gz")):
            return "url"
        return "lake"

    path = Path(text).expanduser()
    if path.is_file():
        return "file"
    if path.is_dir():
        return "folder"
    if _HANDLE_RE.fullmatch(text):
        raise InvalidInput(
            f"'{text}' isn't a local path. If it's a dataset name, say where it lives: "
            f"'kaggle:{text}' or 'hf:{text}'.")
    raise Invalid_Directory(f"Not found: {text}")


def _strip_prefix(text):
    return text.split(":", 1)[1] if ":" in text and not _remote.protocol(text) else text


def _label(source, kind):
    """A readable label for the source column; database passwords are never shown."""
    if kind == "dataframe":
        return "dataframe"
    text = str(source)
    if kind == "database":
        try:
            from sqlalchemy.engine import make_url
            return make_url(text).render_as_string(hide_password=True)
        except Exception:
            return re.sub(r"//([^:/@]+):[^@]*@", r"//\1:***@", text)
    return text


# ------------------------------------------------------------------------ loading

def _split_opts(opts):
    loader = {k: v for k, v in opts.items() if k in LOADER_KEYS}
    pandas_kwargs = {k: v for k, v in opts.items() if k not in LOADER_KEYS}
    return loader, pandas_kwargs


def _load_files(files, root, pandas_kwargs, combine):
    """Load several data files from one source; returns DataFrame or {relpath: df}."""
    frames = {}
    for f in files:
        try:
            rel = f.relative_to(root).as_posix() if root else f.name
        except ValueError:
            rel = f.name
        frames[rel] = _loaders.load(f, **pandas_kwargs)
    if len(frames) == 1:
        return next(iter(frames.values()))
    return frames


def _load_paths(paths, opts, pandas_kwargs, combine):
    """Load whatever came down from a download: one file, many files, or images."""
    paths = [Path(p) for p in paths]
    paths = [_remote._unpack(p, False) if _remote._is_unpack_target(p) else p for p in paths]
    if opts.get("file"):
        from .load_data import _pick_file
        return _loaders.load(_pick_file("source", paths, opts["file"]), **pandas_kwargs)

    if len(paths) == 1 and paths[0].is_dir():
        return _load_folder(paths[0], opts, pandas_kwargs, combine)

    files = _loaders.find_loadable(paths)
    root = Path(_common_dir(paths))
    if files:
        return _load_files(files, root, pandas_kwargs, combine)
    return _images.index_images(root, opts.get("extensions"))


def _common_dir(paths):
    import os
    dirs = [str(p if p.is_dir() else p.parent) for p in paths]
    return os.path.commonpath(dirs) if dirs else "."


def _is_lake_folder(root):
    if (root / "_delta_log").is_dir():
        return True
    return any(c.is_dir() and "=" in c.name for c in root.iterdir())


def _load_folder(root, opts, pandas_kwargs, combine):
    from .load_data import Load_data
    if opts.get("file"):
        from .load_data import _pick_file
        return _loaders.load(_pick_file(str(root), [root], opts["file"]), **pandas_kwargs)
    if _is_lake_folder(root):
        return Load_data.from_lake(str(root), **_lake_opts(opts))
    files = _loaders.find_loadable([root])
    if files:
        return _load_files(files, root, pandas_kwargs, combine)
    return _images.index_images(root, opts.get("extensions"))


def _lake_opts(opts):
    keys = ("columns", "filters", "limit", "format", "storage_options", "version")
    return {k: opts[k] for k in keys if k in opts}


def load_one(source, kind, opts):
    """Load a single source. Returns a DataFrame or a dict of DataFrames."""
    from .load_data import Load_data
    from . import _hf, _kaggle

    opts, pandas_kwargs = _split_opts(opts)
    combine = opts.get("combine", "auto")
    text = str(source).strip() if kind != "dataframe" else None

    if kind == "dataframe":
        return source.copy()
    if kind == "file":
        path = Path(text).expanduser()
        if _remote._is_unpack_target(path):
            return _load_folder(_remote._unpack(path, False), opts, pandas_kwargs, combine)
        return _loaders.load(path, **pandas_kwargs)
    if kind == "folder":
        return _load_folder(Path(text).expanduser(), opts, pandas_kwargs, combine)
    if kind == "lake":
        try:
            return Load_data.from_lake(text, **_lake_opts(opts))
        except InvalidInput as exc:  # not a Parquet/Delta table: download the files instead
            log.info("Not a lake table (%s); downloading %s instead.", exc, text)
            kind = "url"
    if kind == "url":
        paths = _remote.download(text, opts.get("destination"), True,
                                 opts.get("storage_options"), opts.get("overwrite", False),
                                 credentials=opts.get("credentials"))
        return _load_paths(paths, opts, pandas_kwargs, combine)
    if kind == "kaggle":
        paths = _kaggle.download(_strip_prefix(text), opts.get("destination"))
        return _load_paths(paths, opts, pandas_kwargs, combine)
    if kind == "drive":
        from .download import Download_data
        gd = Download_data.GoogleDrive
        auth, creds, dest = opts.get("auth", "auto"), opts.get("credentials"), opts.get("destination")
        if "/folders/" in text:
            paths = gd.download_folder(text, dest, credentials=creds, auth=auth)
        else:
            paths = [gd.download_file(text, dest, credentials=creds, auth=auth)]
        return _load_paths(paths, opts, pandas_kwargs, combine)
    if kind == "huggingface":
        return _hf.load(_strip_prefix(text), opts.get("split", "train"), opts.get("config"),
                        opts.get("revision"), opts.get("token"))
    if kind == "database":
        if "table" not in opts and "query" not in opts:
            raise InvalidInput(
                f"Database source {_label(text, kind)} needs a 'table' or 'query'. Pass it as "
                "{'source': '<url>', 'table': 'orders'}.")
        return Load_data.Database.from_url(text, opts.get("table"), query=opts.get("query"),
                                           params=opts.get("params"), schema=opts.get("schema"))
    raise InvalidInput(f"Unknown source kind '{kind}'.")


# ---------------------------------------------------------------------- combining

def _normalize(name):
    return re.sub(r"\W+", "_", str(name).strip().lower()).strip("_") or str(name)


def _parse_sources(sources, options):
    """Turn the user's input into a list of (name, source, kind, opts)."""
    if isinstance(sources, dict) and "source" in sources:
        items = [(None, sources)]
    elif isinstance(sources, dict):
        items = list(sources.items())
    elif isinstance(sources, (list, tuple)):
        items = [(None, s) for s in sources]
    else:
        items = [(None, sources)]
    if not items:
        raise InvalidInput("No sources given.")

    parsed = []
    for name, item in items:
        if isinstance(item, dict):
            if "source" not in item:
                raise InvalidInput(f"Source spec {item!r} needs a 'source' key.")
            spec = dict(item)
            src = spec.pop("source")
            name = spec.pop("name", name)
            kind = spec.pop("type", None)
            opts = {**options, **spec}
        else:
            src, kind, opts = item, None, dict(options)
        if kind is None:
            try:
                kind = detect(src)
            except DataElevateError as exc:  # reported per source, so errors="skip" covers it
                kind = exc
        label = name or _label(src, kind if isinstance(kind, str) else "unknown")
        parsed.append((label, src, kind, opts))
    return parsed


def _flatten(name, result):
    """Yield (label, DataFrame) pairs from a single source's result."""
    if isinstance(result, dict):
        for sub, df in result.items():
            yield f"{name}::{sub}", df
    else:
        yield name, result


def smart_load(sources, combine="auto", source_column="source", normalize_columns=False,
               errors="raise", max_workers=4, **options):
    """See Load_data.smart_load."""
    if combine not in COMBINE_MODES:
        raise InvalidInput(f"combine must be one of {', '.join(COMBINE_MODES)}.")
    if errors not in ("raise", "skip"):
        raise InvalidInput("errors must be 'raise' or 'skip'.")
    parsed = _parse_sources(sources, options)

    def run(entry):
        name, src, kind, opts = entry
        try:
            if isinstance(kind, Exception):
                raise kind
            return name, kind, load_one(src, kind, {**opts, "combine": combine}), None
        except DataElevateError as exc:
            if errors == "raise":
                raise
            return name, kind, None, exc
        except Exception as exc:
            if errors == "raise":
                raise InvalidInput(f"Could not load {name}: {type(exc).__name__}: {exc}") from exc
            return name, kind, None, exc

    workers = max(1, min(int(max_workers or 1), len(parsed)))
    if workers == 1:
        results = [run(e) for e in parsed]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(run, parsed))  # keeps the input order

    frames, report, skipped = [], [], []
    for name, kind, result, err in results:
        if err is not None:
            log.warning("Skipped %s: %s", name, err)
            skipped.append({"source": name, "kind": kind if isinstance(kind, str) else None,
                            "error": str(err)})
            continue
        for label, df in _flatten(name, result):
            if normalize_columns:
                df = df.rename(columns=_normalize)
            frames.append((label, df))
            report.append({"source": label, "kind": kind, "rows": len(df)})
    if not frames:
        raise InvalidInput(f"Nothing could be loaded. Errors: {skipped}")

    same_columns = len({tuple(df.columns) for _, df in frames}) == 1
    if combine == "dict" or (combine == "auto" and not same_columns and len(frames) > 1):
        out = {label: df for label, df in frames}
        if combine == "auto":
            log.info("Sources have different columns; returning a dict. "
                     "Use combine='concat' to stack them anyway.")
        return out

    if len(frames) == 1:
        out = frames[0][1].copy()
        if source_column and len(parsed) > 1:
            out.insert(0, source_column, frames[0][0])
    else:
        parts = []
        for label, df in frames:
            df = df.copy()
            if source_column:
                if source_column in df.columns:
                    raise InvalidInput(f"Column '{source_column}' already exists; pass "
                                       "source_column='<other name>' or None.")
                df.insert(0, source_column, label)
            parts.append(df)
        out = pd.concat(parts, ignore_index=True, sort=False)
    out.attrs["sources"] = report
    if skipped:
        out.attrs["skipped"] = skipped
    return out
