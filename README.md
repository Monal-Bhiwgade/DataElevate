# DataElevate

**Get training data into pandas in a few lines of code.**

DataElevate downloads datasets from Kaggle and Google Drive, extracts archives, and loads
CSV, TSV/TXT and Excel files (or database tables) straight into a DataFrame, so you can
go from a dataset link to training a model without writing the plumbing every time.

```python
from DataElevate import Load_data

df = Load_data.from_kaggle("uciml/iris", file="Iris.csv")
```

---

## Installation

```bash
pip install DataElevate
```

The core install covers local files, Kaggle and public Google Drive links. Add extras
only for what you need:

| Extra | Install | Adds |
|---|---|---|
| `gdrive` | `pip install "DataElevate[gdrive]"` | Private Google Drive files (your own credentials) |
| `db` | `pip install "DataElevate[db]"` | PostgreSQL, MySQL/MariaDB, Oracle, SQLite |
| `mssql` | `pip install "DataElevate[mssql]"` | SQL Server / Azure SQL (also needs the Microsoft ODBC driver) |
| `all` | `pip install "DataElevate[all]"` | Everything above |

Requires Python 3.9+.

---

## Quickstart

```python
from DataElevate import Download_data, Load_data, Extractor
```

### Load data straight into a DataFrame

```python
# Local file: .csv, .tsv, .txt (delimiter auto-detected), .xlsx, .xls
df = Load_data.from_local("data/train.csv")

# Kaggle: URL or "owner/dataset-name"
df = Load_data.from_kaggle("https://www.kaggle.com/datasets/uciml/iris")

# The dataset has several files? Pick one:
df = Load_data.from_kaggle("owner/dataset-name", file="train.csv")

# Google Drive: a public share link works with no setup
df = Load_data.from_drive("https://drive.google.com/file/d/<FILE_ID>/view?usp=sharing")
```

Extra keyword arguments go to pandas, e.g. `Load_data.from_local("big.csv", nrows=1000)`.

### Download data

```python
# Kaggle: saved to ./Data/<dataset-name> unless you pass a destination
paths = Download_data.Kaggle.from_kaggle("owner/dataset-name", destination="data/")

# Google Drive: files and folders (subfolders included)
path  = Download_data.GoogleDrive.download_file("<link or ID>", destination="data/")
paths = Download_data.GoogleDrive.download_folder("<folder link or ID>", destination="data/")

# Google Docs/Sheets/Slides are exported to .docx / .xlsx / .pptx
```

### Extract archives

```python
Extractor.extract_archive("data/images.zip", destination="data/images")
```

Supports `.zip`, `.tar`, `.tar.gz`/`.tgz`, `.tar.bz2`, `.tar.xz`, and single-file `.gz`,
`.bz2`, `.xz`. Archives that try to write outside the destination folder are blocked.

### Load from a database

```python
import os

df = Load_data.Database.from_postgresql(
    db_name="shop", table_name="orders",
    username="analyst", password=os.environ["DB_PASSWORD"],
    host="localhost", port=5432,
)

# Or your own SQL, with parameters
df = Load_data.Database.from_mysql(
    "shop", query="SELECT * FROM orders WHERE year = :y", params={"y": 2025},
    username="analyst", password=os.environ["DB_PASSWORD"],
)

# Any SQLAlchemy URL
df = Load_data.Database.from_url("sqlite:///local.db", "orders")
```

Available: `from_postgresql`, `from_mysql`, `from_mariadb`, `from_mssql`, `from_azure_sql`,
`from_oracle`, `from_amazon_rds` (`engine="mysql"` or `"postgresql"`), `from_sqlite`,
`from_url`. Table names are looked up and quoted safely, so they can't inject SQL.

---

## Credentials

**DataElevate never ships or stores anyone else's credentials.** Everything uses your own.

### Kaggle

Public datasets work without login. For private datasets, set `KAGGLE_USERNAME` and
`KAGGLE_KEY`, or put your `kaggle.json` in `~/.kaggle/`
([how to get it](https://www.kaggle.com/docs/api)).

### Private Google Drive files

Public links ("Anyone with the link") need nothing. For private files:

1. `pip install "DataElevate[gdrive]"`
2. In [Google Cloud Console](https://console.cloud.google.com/), enable the **Google Drive API**
   and create an **OAuth client ID** of type **Desktop app**. Download the JSON.
   (A **service account** key JSON also works; share the files with the service account.)
3. Point DataElevate at it, either per call or once via an environment variable:

```python
path = Download_data.GoogleDrive.download_file(link, credentials="~/secrets/gdrive.json")
```

```bash
export DATAELEVATE_GDRIVE_CREDENTIALS=~/secrets/gdrive.json
```

The first call opens a browser to sign in. Access is **read-only**. The sign-in token is
cached in `~/.dataelevate/tokens/` (readable only by you); set `DATAELEVATE_HOME` to move it.

Keep credential files outside your project folder and never commit them.

---

## Errors

All errors inherit from `DataElevateError`:

| Error | When |
|---|---|
| `InvalidInput` | Bad URL/ID, inaccessible dataset, unsafe archive, missing table |
| `Invalid_Directory` | File or archive not found |
| `Invalid_File_Support` | Unsupported file type |
| `MultipleFilesError` | Dataset has several data files; pass `file=` (lists them) |
| `MissingDependencyError` | An optional extra isn't installed (tells you which) |
| `CredentialsError` | Google credentials missing or invalid |

---

## Contributing

Issues and pull requests are welcome. To run the tests:

```bash
pip install -e ".[dev]"
pytest
```

See [SECURITY.md](SECURITY.md) to report a security issue and [CHANGELOG.md](CHANGELOG.md)
for release notes.

## License

MIT. See [LICENSE](LICENSE).

## Author

**Monal Bhiwgade**
