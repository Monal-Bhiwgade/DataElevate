# DataElevate: load ML training data into pandas in one line

[![PyPI version](https://img.shields.io/pypi/v/DataElevate.svg)](https://pypi.org/project/DataElevate/)
[![Python versions](https://img.shields.io/pypi/pyversions/DataElevate.svg)](https://pypi.org/project/DataElevate/)
[![Tests](https://github.com/Monal-Bhiwgade/DataElevate/actions/workflows/tests.yml/badge.svg)](https://github.com/Monal-Bhiwgade/DataElevate/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/Monal-Bhiwgade/DataElevate/blob/main/LICENSE)

**DataElevate is a Python dataset loader for machine learning and data science.** It downloads
and loads data from **Kaggle, Hugging Face, Google Drive, Amazon S3, Google Cloud Storage,
Azure, data lakes (Parquet and Delta Lake), web links and SQL databases** straight into a
**pandas DataFrame**, with one function call.

It handles the downloading, unzipping, partition files, sign-in and format detection, so you
can go from a dataset link to `model.fit()` without writing the plumbing every time. It works
the same on Windows, macOS and Linux, with nothing to install outside `pip`.

```python
from DataElevate import Load_data

# One call, any mix of sources: detected, loaded and stacked for you
df = Load_data.load(["data/jan.csv", "s3://lake/feb.parquet", "kaggle:owner/march-sales"])

df = Load_data.from_kaggle("uciml/iris", file="Iris.csv")              # Kaggle dataset
df = Load_data.from_huggingface("stanfordnlp/imdb", split="train")     # Hugging Face
df = Load_data.from_drive("https://drive.google.com/file/d/<ID>/view") # Google Drive
df = Load_data.from_lake("s3://company-lake/sales", columns=["user_id", "amount"],
                         filters=[("year", "=", 2025)])                # Data lake on S3
```

### Why DataElevate?

- **One API for every source:** local files, URLs, cloud storage, data lakes, Kaggle,
  Hugging Face, Google Drive and databases all return a pandas DataFrame.
- **Smart loader:** pass a list of mixed sources and get one combined table, with a column
  showing where each row came from.
- **Big data friendly:** read only the columns and partitions you need from Parquet and
  Delta Lake tables on S3, GCS or Azure, without Spark or Java.
- **Deep learning ready:** turn image folders (`train/cat/1.jpg`) into a path, label and
  split table for PyTorch or TensorFlow.
- **Cross-platform, pip-only:** every dependency ships wheels for Windows, macOS and Linux.
- **Secure by default:** no bundled credentials, read-only Google access, SQL-injection-safe
  table loading and safe archive extraction.

---

## Installation

```bash
pip install DataElevate
```

The core install covers local files, any `https://` link, local data-lake folders, Kaggle
and Google Drive (public links and Google sign-in). Add extras only for what you need:

| Extra | Adds |
|---|---|
| `s3`, `gcs`, `azure`, `sftp` | Amazon S3, Google Cloud Storage, Azure Blob/ADLS, SFTP |
| `cloud` | All four storage backends |
| `delta` | Delta Lake tables (no Spark or Java needed) |
| `lake` | `cloud` + `delta` |
| `huggingface` | Hugging Face Hub datasets |
| `db` | PostgreSQL, MySQL/MariaDB, Oracle, SQLite |
| `mssql` | SQL Server / Azure SQL (no ODBC install needed) |
| `all` | Everything above |

```bash
pip install "DataElevate[lake,huggingface]"
```

Requires Python 3.9+. Every dependency ships ready-made wheels for Windows, macOS and Linux.

---

## Load data

```python
from DataElevate import Load_data
```

### Smart loader: any source, or many at once

Give `Load_data.load()` (also called `smart_load()`) one source or a list, and it works out
what each one is, loads it with the right loader, and combines the results.

```python
# A folder of monthly exports -> one DataFrame
df = Load_data.load("exports/")

# Different sources with the same columns -> stacked, with a "source" column
df = Load_data.load({
    "2023": "data/sales_2023.csv",
    "2024": "https://example.com/sales_2024.parquet",
    "2025": "s3://company-lake/sales_2025/",
    "crm":  {"source": "postgresql://analyst@db/shop", "table": "sales"},
    "manual": existing_dataframe,
})

# Per-source options, plus options for every source
df = Load_data.load([
    {"source": "s3://lake/events", "filters": [("year", "=", 2025)], "name": "events"},
    {"source": "hf:stanfordnlp/imdb", "split": "train[:1000]", "name": "imdb"},
], storage_options={"anon": True})
```

It recognises:

| Source | Example | Loaded as |
|---|---|---|
| Local file or archive | `"data/train.csv"`, `"exports.zip"` | File(s) |
| Local folder | `"exports/"` | All data files combined; a partitioned/Delta folder is read as a lake; an image folder is indexed |
| Web link | `"https://.../train.csv"` | Downloaded (GitHub/Dropbox links fixed) |
| Cloud file, folder or glob | `"s3://b/train.parquet"`, `"gs://b/*.csv"` | Downloaded |
| Cloud table folder | `"s3://lake/sales"` | Data-lake table (Parquet/Delta), with filters |
| Kaggle | `"kaggle:owner/name"` or a kaggle.com link | Kaggle dataset |
| Google Drive | a drive.google.com link | Drive file/folder (sign-in if private) |
| Hugging Face | `"hf:owner/name"` or a huggingface.co link | Dataset split |
| Database | `{"source": "postgresql://...", "table": "orders"}` | Table or `query` |
| DataFrame | `df` | As is |

Check what it will do without loading: `Load_data.detect_source("s3://lake/sales")` → `"lake"`.

Options:

- `combine="auto"` (default) stacks when every part has the same columns, otherwise returns
  a dict of DataFrames. `"concat"` always stacks (missing columns become empty);
  `"dict"` always returns `{name: DataFrame}`.
- `normalize_columns=True` turns `"Customer ID"` and `"customer_id"` into the same column.
- `source_column="source"` names the column that records where each row came from
  (`None` to leave it out).
- `errors="skip"` loads what it can; failures are listed in `df.attrs["skipped"]`.
- Sources load in parallel (`max_workers=4`), and the output keeps your input order.
- `df.attrs["sources"]` lists every part and how many rows it contributed.
- Database passwords are never written into the `source` column.

### Any link or cloud path

```python
df = Load_data.from_url("https://example.com/train.csv")

# Share links are fixed for you
df = Load_data.from_url("https://github.com/owner/repo/blob/main/data/train.csv")
df = Load_data.from_url("https://www.dropbox.com/s/abc123/train.csv?dl=0")

# Cloud and remote storage
df = Load_data.from_cloud("s3://my-bucket/data/train.parquet")
df = Load_data.from_cloud("gs://my-bucket/train.csv")
df = Load_data.from_cloud("abfs://container/train.csv")       # Azure
df = Load_data.from_cloud("sftp://user@host/exports/train.csv")

# Public bucket: no credentials
df = Load_data.from_cloud("s3://public-bucket/x.csv", storage_options={"anon": True})
```

- Archives (`.zip`, `.tar.gz`, ...) are extracted automatically.
- Downloads are cached in `./Data` and reused next time (`overwrite=True` to refresh).
- If a link holds several files, pass `file="train.csv"`. The error lists the choices.
- Google Drive and Kaggle links passed to `from_url` go to their own downloaders.

### Data lakes

Read a table straight out of a lake without downloading it: only the files and columns
you ask for are fetched.

```python
# Folder of Parquet files with Hive partitions: s3://lake/sales/year=2025/country=IN/...
df = Load_data.from_lake(
    "s3://company-lake/sales",
    columns=["user_id", "amount"],
    filters=[("year", "=", 2025), ("country", "in", ["IN", "US"])],
)

# Quick sample of a huge table
sample = Load_data.from_lake("s3://company-lake/events", limit=10_000)

# Delta Lake table (detected automatically), including time travel
df = Load_data.from_lake("s3://company-lake/delta/orders", version=12)

# Not sure what's in there? Look before you load
Load_data.describe_lake("s3://company-lake/sales")
# {'format': 'parquet', 'columns': {...}, 'partition_columns': ['year', 'country'], 'files': 812}
```

Works on `s3://`, `gs://`, `az://`/`abfs://`, other fsspec storage, and local folders.
`format=` can be `"auto"` (default), `"parquet"`, `"delta"`, `"csv"` or `"json"`.
Filters use `(column, op, value)` with `=`, `!=`, `<`, `<=`, `>`, `>=`, `in`, `not in`;
a list of lists means OR.

### Hugging Face datasets

```python
df = Load_data.from_huggingface("stanfordnlp/imdb", split="train")
df = Load_data.from_huggingface("stanfordnlp/imdb", split="train[:1000]")   # sample
splits = Load_data.from_huggingface("stanfordnlp/imdb", split=None)         # dict of all
df = Load_data.from_huggingface("glue", config="sst2", split="validation")
```

### Image datasets for deep learning

```python
df = Load_data.from_images("data/pets")                  # local folder
df = Load_data.from_images("data/flowers.zip")           # local archive
df = Load_data.from_images("https://www.kaggle.com/datasets/owner/cats-vs-dogs")
```

Returns a DataFrame with `path`, `label` (from class folders such as `cat/`, `dog/`) and
`split` (from `train/`, `val`/`validation/`, `test/` folders) ready for a PyTorch or
TensorFlow data loader. Wrapper folders inside zips are handled.

### Kaggle and Google Drive

```python
df = Load_data.from_kaggle("uciml/iris", file="Iris.csv")

# Public or private Drive file: same call
df = Load_data.from_drive("https://drive.google.com/file/d/<FILE_ID>/view?usp=sharing")
```

For Google Drive you don't set anything up. Public links download directly. If the file
is private, your browser opens once so you can sign in with Google (read-only access), and
the sign-in is remembered. Prefer your own Google Cloud credentials? Pass
`credentials="path/to/client.json"`. See [Credentials](https://github.com/Monal-Bhiwgade/DataElevate#credentials).

### Local files

```python
df = Load_data.from_local("data/train.csv")
```

Supported: `.csv`, `.tsv`, `.txt` (delimiter auto-detected), `.xlsx`/`.xls`, `.parquet`,
`.json` (nested JSON is flattened), `.jsonl`, `.feather`, and compressed text such as
`train.csv.gz` or `train.csv.zip`. Extra keyword arguments go to pandas,
e.g. `Load_data.from_local("big.csv", nrows=1000)`.

### Databases

```python
import os

df = Load_data.Database.from_postgresql(
    db_name="shop", table_name="orders",
    username="analyst", password=os.environ["DB_PASSWORD"], host="localhost",
)
df = Load_data.Database.from_mssql(
    "shop", query="SELECT * FROM orders WHERE year = :y", params={"y": 2025},
    username="analyst", password=os.environ["DB_PASSWORD"], host="sql.example.com",
)
```

Available: `from_postgresql`, `from_mysql`, `from_mariadb`, `from_mssql`, `from_azure_sql`,
`from_oracle`, `from_amazon_rds` (`engine="mysql"` or `"postgresql"`), `from_sqlite`, and
`from_url` for any SQLAlchemy URL. Table names are quoted safely, so they can't inject SQL.

---

## Download without loading

```python
from DataElevate import Download_data, Extractor

paths = Download_data.from_url("s3://bucket/images/*.jpg", destination="data/")
paths = Download_data.Kaggle.from_kaggle("owner/dataset-name", destination="data/")
path  = Download_data.GoogleDrive.download_file("<link or ID>", destination="data/")
paths = Download_data.GoogleDrive.download_folder("<folder link or ID>", destination="data/")
folder = Download_data.HuggingFace.download("stanfordnlp/imdb", destination="data/imdb")

Extractor.extract_archive("data/images.zip", destination="data/images")
```

Extraction supports `.zip`, `.tar`, `.tar.gz`/`.tgz`, `.tar.bz2`, `.tar.xz`, `.gz`, `.bz2`
and `.xz`. Archives that try to write outside the destination folder are blocked.

---

## Credentials

**The DataElevate package contains no credentials, and your keys and sign-ins never leave
your machine.** Each service uses your own access, from where it normally keeps it:

| Service | Where your credentials come from |
|---|---|
| Amazon S3 | `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`, `~/.aws/credentials`, or an IAM role |
| Google Cloud Storage | `gcloud auth application-default login` or `GOOGLE_APPLICATION_CREDENTIALS` |
| Azure | `AZURE_STORAGE_ACCOUNT_NAME` + key/SAS, or `az login` |
| SFTP | Your SSH key / agent, or `storage_options={"username": ..., "key_filename": ...}` |
| Hugging Face | Public datasets: none. Gated/private: `HF_TOKEN` or `token=` |
| Kaggle | Public datasets: none. Private: `KAGGLE_USERNAME` + `KAGGLE_KEY`, or `~/.kaggle/kaggle.json` |
| Google Drive | Public links: none. Private: just sign in with Google, or use your own file (below) |

You can always pass settings directly with `storage_options={...}` (for Delta tables these
are the `deltalake` storage options, e.g. `{"AWS_REGION": "ap-south-1"}`).

### Google Drive: two ways to access private files

**1. Sign in with Google (default, zero setup).** When a file isn't public, DataElevate
opens your browser, you sign in and allow read-only access, and that's it. The sign-in is
saved in `~/.dataelevate/tokens/` (readable only by you) and reused. Your token never
leaves your machine.

```python
df = Load_data.from_drive(private_link)                 # tries public, then signs in
df = Load_data.from_drive(private_folder, auth="oauth")  # go straight to sign-in
df = Load_data.from_drive(link, auth="public")           # never sign in
```

Notes: sign-in needs a browser on the same machine, so on remote servers and CI use option
2 with a service account. DataElevate's sign-in app is not yet verified by Google, so
you'll see a "Google hasn't verified this app" screen; choose *Advanced → continue*.

**2. Your own credentials file.** Full control, no shared app, works on servers.

1. In [Google Cloud Console](https://console.cloud.google.com/), enable the **Google Drive
   API** and create an **OAuth client ID** of type **Desktop app** (or a **service account**
   key, and share the files with the service account). Download the JSON.
2. Pass it per call (`credentials="~/secrets/gdrive.json"`) or once with
   `export DATAELEVATE_GDRIVE_CREDENTIALS=~/secrets/gdrive.json`.

Your own credentials always take priority over the built-in sign-in. Access is read-only
either way. Set `DATAELEVATE_HOME` to move the token folder.

Keep credential files outside your project folder and never commit them.

---

## Errors

All errors inherit from `DataElevateError`:

| Error | When |
|---|---|
| `InvalidInput` | Bad URL/ID, inaccessible data, bad filters, unsafe archive, missing table |
| `Invalid_Directory` | File or archive not found |
| `Invalid_File_Support` | Unsupported file type |
| `MultipleFilesError` | Several data files; pass `file=` (the error lists them) |
| `MissingDependencyError` | An optional extra isn't installed (tells you the exact `pip install`) |
| `CredentialsError` | Google credentials missing or invalid |

---

## FAQ

**How do I load a Kaggle dataset into pandas?**
`Load_data.from_kaggle("owner/dataset-name")`, or `file="train.csv"` if it has several files.
Public datasets need no API key.

**How do I download a file from Google Drive in Python?**
`Download_data.GoogleDrive.download_file(link)` downloads it; `Load_data.from_drive(link)`
loads it into pandas. Private files open a browser once to sign in with Google.

**How do I read a Parquet or Delta Lake table from S3 into pandas?**
`Load_data.from_lake("s3://bucket/table", columns=[...], filters=[...])`, after
`pip install "DataElevate[lake]"`. Only the needed files and columns are read.

**How do I load a Hugging Face dataset as a DataFrame?**
`Load_data.from_huggingface("owner/name", split="train")`, after
`pip install "DataElevate[huggingface]"`.

**Can I combine data from several sources into one DataFrame?**
Yes: `Load_data.load([...])` accepts any mix of files, links, cloud paths, Kaggle, Hugging
Face, databases and DataFrames.

**Does it work on Windows?**
Yes. It's tested on Windows, macOS and Linux, and SQL Server works without an ODBC driver.

---

## Contributing

DataElevate is open source (MIT) and contributions are very welcome: new data sources,
performance improvements, bug fixes and docs. Start with the
[contributing guide](https://github.com/Monal-Bhiwgade/DataElevate/blob/main/CONTRIBUTING.md),
which covers setup, how the code is organised, how to add a data source, and a list of
ideas to work on. To run the tests:

```bash
pip install -e ".[dev]"
pytest
```

### Releasing

Publishing to PyPI is automatic. To release a new version:

1. In your pull request, bump the version in **both** `pyproject.toml` and
   `DataElevate/__init__.py`, and add a `## <version>` section to `CHANGELOG.md`.
2. Merge the pull request into `main`.

The `publish` workflow then sees that this version isn't on PyPI yet, runs the tests,
builds, scans for secrets, uploads to PyPI, and creates the `v<version>` tag and GitHub
Release. Merges that don't change the version publish nothing.

See [SECURITY.md](https://github.com/Monal-Bhiwgade/DataElevate/blob/main/SECURITY.md) to report a security issue and [CHANGELOG.md](https://github.com/Monal-Bhiwgade/DataElevate/blob/main/CHANGELOG.md)
for release notes.

## License

MIT. See [LICENSE](https://github.com/Monal-Bhiwgade/DataElevate/blob/main/LICENSE).

## Author

**Monal Bhiwgade**
