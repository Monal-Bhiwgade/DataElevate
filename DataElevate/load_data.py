"""Load data into pandas DataFrames from local files, Kaggle, Google Drive and databases."""

from pathlib import Path

import pandas as pd

from . import _kaggle, _loaders
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
        raise InvalidInput(f"'{source}' has no loadable files (csv, txt, tsv, Excel).")
    if len(candidates) > 1:
        raise MultipleFilesError(source, [p.name for p in candidates])
    return candidates[0]


class Load_data:
    """Load datasets straight into a pandas DataFrame."""

    @staticmethod
    def from_local(path, **kwargs):
        """Load a CSV, TSV/TXT (delimiter auto-detected) or Excel file.

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
    def from_drive(url, file=None, destination=None, credentials=None, **kwargs):
        """Download a Google Drive file (or folder) and load it.

        Public links need no setup; for private files pass ``credentials=``
        (see ``Download_data.GoogleDrive``).
        """
        if "/folders/" in str(url):
            paths = Download_data.GoogleDrive.download_folder(
                url, destination, credentials=credentials)
        else:
            paths = [Download_data.GoogleDrive.download_file(
                url, destination, credentials=credentials)]
        return _loaders.load(_pick_file(url, paths, file), **kwargs)

    class Database:
        """Load a table (or the result of your own SQL query) from a database.

        Table names are looked up through SQLAlchemy and quoted safely, so a table
        name can never inject SQL. Passwords with special characters are escaped.
        Install drivers with ``pip install "DataElevate[db]"``
        (SQL Server / Azure SQL: ``"DataElevate[mssql]"``).
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
                       schema=None, user=None, driver="ODBC Driver 18 for SQL Server"):
            engine = Load_data.Database._engine(
                "mssql+pyodbc", "pyodbc", "pyodbc", "mssql",
                db_name, username or user, password, host, port, query={"driver": driver})
            return Load_data.Database._read(engine, table_name, query, params, schema)

        @staticmethod
        def from_azure_sql(db_name, table_name=None, username=None, password=None,
                           host="localhost", port=1433, *, query=None, params=None,
                           schema=None, user=None, driver="ODBC Driver 18 for SQL Server"):
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
