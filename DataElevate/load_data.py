"""Load data into pandas DataFrames from files, URLs, cloud storage, Kaggle, Google Drive,
Hugging Face, image folders and databases."""

import os
from pathlib import Path

import pandas as pd

from . import _hf, _images, _kaggle, _lake, _loaders, _remote
from ._deps import require
from .download import Download_data
from .errors import InvalidInput, MultipleFilesError


def _pick_file(source, paths, file):
    """Choose one loadable file from downloaded paths."""
    candidates = _loaders.find_loadable(paths)
    if file is not None:
        wanted = [p for p in candidates if p.name == file or p.as_posix().endswith("/" + file)]
        if not wanted:
            names = ", ".join(p.name for p in candidates) or "none"
            raise InvalidInput(f"'{file}' not found in '{source}'. Loadable files: {names}")
        return wanted[0]
    if not candidates:
        raise InvalidInput(
            f"'{source}' has no loadable data files (csv, tsv, txt, Excel, Parquet, JSON, "
            "JSONL, Feather). For image datasets use Load_data.from_images().")
    if len(candidates) > 1:
        raise MultipleFilesError(source, [p.name for p in candidates])
    return candidates[0]


class Load_data:
    """Load datasets straight into a pandas DataFrame."""

    @staticmethod
    def from_local(path, **kwargs):
        """Load a CSV, TSV/TXT (delimiter auto-detected), Excel, Parquet, JSON, JSONL or
        Feather file. Compressed text formats such as ``train.csv.gz`` also work.

        Extra keyword arguments are passed to the pandas reader.
        """
        return _loaders.load(path, **kwargs)

    @staticmethod
    def from_kaggle(url, file=None, destination=None, **kwargs):
        """Download a Kaggle dataset and load it.

        If the dataset has several data files, pass ``file='name.csv'`` to pick one.
        """
        paths = _kaggle.download(url, destination)
        return _loaders.load(_pick_file(url, paths, file), **kwargs)

    @staticmethod
    def from_drive(url, file=None, destination=None, credentials=None, auth="auto", **kwargs):
        """Download a Google Drive file (or folder) and load it.

        Public links need nothing. Private ones open a browser once to sign in with
        Google (read-only), or use your own ``credentials=`` file. ``auth`` is "auto"
        (default), "public" or "oauth"; see ``Download_data.GoogleDrive``.
        """
        gd = Download_data.GoogleDrive
        if "/folders/" in str(url):
            paths = gd.download_folder(url, destination, credentials=credentials, auth=auth)
        else:
            paths = [gd.download_file(url, destination, credentials=credentials, auth=auth)]
        return _loaders.load(_pick_file(url, paths, file), **kwargs)

    @staticmethod
    def from_url(url, file=None, destination=None, storage_options=None, credentials=None,
                 overwrite=False, **kwargs):
        """Download from any link and load it.

        Works with ``https://`` links (including GitHub and Dropbox share links),
        Google Drive and Kaggle links, and cloud/remote storage: ``s3://``, ``gs://``,
        ``az://``, ``sftp://``, ``ftp://``, ``github://``, ``hf://``. Archives are
        extracted automatically. Files are cached in ``./Data`` and reused next time
        (``overwrite=True`` to re-download).

        ``storage_options`` passes your own cloud settings/credentials, e.g.
        ``{"anon": True}`` for a public S3 bucket.
        """
        paths = _remote.download(url, destination, True, storage_options, overwrite,
                                 credentials=credentials)
        return _loaders.load(_pick_file(url, paths, file), **kwargs)

    from_cloud = from_url

    @staticmethod
    def from_huggingface(name, split="train", config=None, revision=None, token=None,
                         **kwargs):
        """Load a Hugging Face Hub dataset split into a DataFrame.

        ``name`` is ``"owner/dataset"`` or a huggingface.co/datasets URL. Use slices such
        as ``split="train[:1000]"`` for a quick sample, and ``split=None`` to get a dict of
        all splits. Needs ``pip install "DataElevate[huggingface]"``.
        """
        return _hf.load(name, split, config, revision, token, **kwargs)

    @staticmethod
    def from_images(source, extensions=None, destination=None, storage_options=None,
                    credentials=None):
        """Index an image-classification dataset into a DataFrame of path, label, split.

        ``source`` can be a local folder, a local archive, or any link ``from_url``
        accepts (Kaggle, Google Drive, https, s3:// ...). Labels come from class folder
        names (``cat/001.jpg``), and splits from ``train/``, ``val/``, ``test/`` folders.
        """
        source_path = Path(str(source))
        if _remote.protocol(str(source)) is None:
            if source_path.is_dir():
                root = source_path
            elif source_path.is_file() and _remote._is_unpack_target(source_path):
                root = _remote._unpack(source_path, overwrite=False)
            else:
                raise InvalidInput(f"'{source}' is not a folder, an archive, or a URL.")
        else:
            paths = [Path(p) for p in _remote.download(
                source, destination, True, storage_options, credentials=credentials)]
            paths = [_remote._unpack(p, False) if _remote._is_unpack_target(p) else p
                     for p in paths]
            if len(paths) == 1 and paths[0].is_dir():
                root = paths[0]
            else:
                root = Path(os.path.commonpath([str(p if p.is_dir() else p.parent)
                                                for p in paths]))
        return _images.index_images(root, extensions)

    @staticmethod
    def from_lake(url, columns=None, filters=None, limit=None, format="auto",
                  storage_options=None, version=None):
        """Read a table from a data lake, fetching only what you ask for.

        ``url`` is a folder of Parquet/CSV/JSON files (Hive partitions like
        ``year=2025/`` become columns) or a Delta Lake table, on ``s3://``, ``gs://``,
        ``az://``/``abfs://``, other fsspec storage, or a local path. Delta is detected
        automatically.

        Args:
            columns: Only these columns are read, e.g. ``["user_id", "amount"]``.
            filters: Rows to keep, pushed down to skip whole files/partitions, e.g.
                ``[("year", "=", 2025), ("country", "in", ["IN", "US"])]``.
            limit: Stop after this many rows (quick samples of huge tables).
            format: "auto" (default), "parquet", "delta", "csv" or "json".
            storage_options: Your own storage credentials/settings.
            version: Delta only: a version number or timestamp (time travel).
        """
        return _lake.load(url, format, columns, filters, limit, storage_options, version)

    @staticmethod
    def describe_lake(url, format="auto", storage_options=None, version=None):
        """Show a lake table's format, columns, partition columns and file count
        without reading any data. Use it to decide columns= and filters=."""
        return _lake.describe(url, format, storage_options, version)

    class Database:
        """Load a table (or the result of your own SQL query) from a database.

        Table names are looked up through SQLAlchemy and quoted safely, so a table
        name can never inject SQL. Passwords with special characters are escaped.
        Install drivers with ``pip install "DataElevate[db]"``
        (SQL Server / Azure SQL: ``"DataElevate[mssql]"``, no ODBC install needed).
        """

        @staticmethod
        def _engine(drivername, module, package, extra, db_name, username, password,
                    host, port, query=None):
            sa = require("sqlalchemy", "SQLAlchemy", extra)
            require(module, package, extra)
            url = sa.engine.URL.create(
                drivername, username=username, password=password, host=host,
                port=int(port) if port else None, database=db_name, query=query or {})
            return sa.create_engine(url)

        @staticmethod
        def _read(engine, table_name=None, query=None, params=None, schema=None):
            sa = require("sqlalchemy", "SQLAlchemy", "db")
            if (table_name is None) == (query is None):
                raise InvalidInput("Pass exactly one of table_name or query.")
            try:
                with engine.connect() as conn:
                    if query is not None:
                        return pd.read_sql(sa.text(query), conn, params=params)
                    if schema is None and "." in table_name:
                        schema, table_name = table_name.split(".", 1)
                    table = sa.Table(table_name, sa.MetaData(), autoload_with=conn,
                                     schema=schema)
                    return pd.read_sql(sa.select(table), conn)
            except sa.exc.NoSuchTableError as exc:
                raise InvalidInput(f"Table '{table_name}' does not exist.") from exc
            finally:
                engine.dispose()

        @staticmethod
        def from_url(connection_url, table_name=None, *, query=None, params=None, schema=None):
            """Load from any SQLAlchemy connection URL, e.g. ``postgresql+psycopg2://...``."""
            sa = require("sqlalchemy", "SQLAlchemy", "db")
            return Load_data.Database._read(
                sa.create_engine(connection_url), table_name, query, params, schema)

        @staticmethod
        def from_postgresql(db_name, table_name=None, username=None, password=None,
                            host="localhost", port=5432, *, query=None, params=None,
                            schema=None, user=None):
            engine = Load_data.Database._engine(
                "postgresql+psycopg2", "psycopg2", "psycopg2-binary", "db",
                db_name, username or user, password, host, port)
            return Load_data.Database._read(engine, table_name, query, params, schema)

        @staticmethod
        def from_mysql(db_name, table_name=None, username=None, password=None,
                       host="localhost", port=3306, *, query=None, params=None, user=None):
            engine = Load_data.Database._engine(
                "mysql+pymysql", "pymysql", "PyMySQL", "db",
                db_name, username or user, password, host, port)
            return Load_data.Database._read(engine, table_name, query, params)

        @staticmethod
        def from_mariadb(db_name, table_name=None, username=None, password=None,
                         host="localhost", port=3306, *, query=None, params=None, user=None):
            return Load_data.Database.from_mysql(
                db_name, table_name, username or user, password, host, port,
                query=query, params=params)

        @staticmethod
        def from_mssql(db_name, table_name=None, username=None, password=None,
                       host="localhost", port=1433, *, query=None, params=None,
                       schema=None, user=None, driver=None):
            """SQL Server. Uses the pymssql driver by default (wheels bundle everything), so no ODBC
            install is needed. Pass ``driver="ODBC Driver 18 for SQL Server"`` to use
            pyodbc with an installed ODBC driver instead."""
            if driver:
                engine = Load_data.Database._engine(
                    "mssql+pyodbc", "pyodbc", "pyodbc", "mssql-odbc",
                    db_name, username or user, password, host, port, query={"driver": driver})
            else:
                engine = Load_data.Database._engine(
                    "mssql+pymssql", "pymssql", "pymssql", "mssql",
                    db_name, username or user, password, host, port)
            return Load_data.Database._read(engine, table_name, query, params, schema)

        @staticmethod
        def from_azure_sql(db_name, table_name=None, username=None, password=None,
                           host="localhost", port=1433, *, query=None, params=None,
                           schema=None, user=None, driver=None):
            """Azure SQL Database (same options as from_mssql)."""
            return Load_data.Database.from_mssql(
                db_name, table_name, username or user, password, host, port,
                query=query, params=params, schema=schema, driver=driver)

        @staticmethod
        def from_oracle(db_name, table_name=None, username=None, password=None,
                        host="localhost", port=1521, *, query=None, params=None,
                        schema=None, user=None):
            engine = Load_data.Database._engine(
                "oracle+oracledb", "oracledb", "oracledb", "db",
                db_name, username or user, password, host, port)
            return Load_data.Database._read(engine, table_name, query, params, schema)

        @staticmethod
        def from_amazon_rds(db_name, table_name=None, username=None, password=None,
                            host=None, port=None, *, engine="mysql", query=None,
                            params=None, user=None):
            """Amazon RDS: set ``engine='mysql'`` (default) or ``engine='postgresql'``."""
            if engine == "postgresql":
                return Load_data.Database.from_postgresql(
                    db_name, table_name, username or user, password, host, port or 5432,
                    query=query, params=params)
            if engine == "mysql":
                return Load_data.Database.from_mysql(
                    db_name, table_name, username or user, password, host, port or 3306,
                    query=query, params=params)
            raise InvalidInput("engine must be 'mysql' or 'postgresql'.")

        @staticmethod
        def from_sqlite(db_name, table_name=None, *, query=None, params=None):
            """Load from an SQLite file (it must already exist)."""
            path = Path(db_name)
            if not path.is_file():
                raise InvalidInput(f"SQLite database file not found: {path}")
            sa = require("sqlalchemy", "SQLAlchemy", "db")
            engine = sa.create_engine(sa.engine.URL.create("sqlite", database=str(path)))
            return Load_data.Database._read(engine, table_name, query, params)

        sqlite = from_sqlite
