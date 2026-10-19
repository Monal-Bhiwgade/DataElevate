# DataElevate

**Get training data into pandas in a few lines of code, from wherever it lives.**

Any link, cloud storage, data lakes, Kaggle, Google Drive, Hugging Face, image folders and
databases: DataElevate handles the downloading, unzipping, partition files, auth hand-off
and format detection, and gives you a DataFrame. It works the same on Windows, macOS and
Linux, with nothing to install outside `pip`.

```python
from DataElevate import Load_data

df = Load_data.from_url("https://example.com/data/train.csv")
df = Load_data.from_lake("s3://company-lake/sales", columns=["user_id", "amount"],
                         filters=[("year", "=", 2025)])
df = Load_data.from_huggingface("stanfordnlp/imdb", split="train")
```

---

## Installation

```bash
pip install DataElevate
```

The core install covers local files, any `https://` link, local data-lake folders, Kaggle
and public Google Drive links. Add extras only for what you need:

| Extra | Adds |
|---|---|
| `s3`, `gcs`, `azure`, `sftp` | Amazon S3, Google Cloud Storage, Azure Blob/ADLS, SFTP |
| `cloud` | All four storage backends |
| `delta` | Delta Lake tables (no Spark or Java needed) |
| `lake` | `cloud` + `delta` |
| `huggingface` | Hugging Face Hub datasets |
| `gdrive` | Private Google Drive files (your own credentials) |
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
df = Load_data.from_drive("https://drive.google.com/file/d/<FILE_ID>/view?usp=sharing")
```

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

**DataElevate never ships or stores anyone else's credentials.** It always uses yours,
from the place each service normally keeps them:

| Service | Where your credentials come from |
|---|---|
| Amazon S3 | `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`, `~/.aws/credentials`, or an IAM role |
| Google Cloud Storage | `gcloud auth application-default login` or `GOOGLE_APPLICATION_CREDENTIALS` |
| Azure | `AZURE_STORAGE_ACCOUNT_NAME` + key/SAS, or `az login` |
| SFTP | Your SSH key / agent, or `storage_options={"username": ..., "key_filename": ...}` |
| Hugging Face | Public datasets: none. Gated/private: `HF_TOKEN` or `token=` |
| Kaggle | Public datasets: none. Private: `KAGGLE_USERNAME` + `KAGGLE_KEY`, or `~/.kaggle/kaggle.json` |
| Google Drive | Public links: none. Private: see below |

You can always pass settings directly with `storage_options={...}` (for Delta tables these
are the `deltalake` storage options, e.g. `{"AWS_REGION": "ap-south-1"}`).

### Private Google Drive files

1. `pip install "DataElevate[gdrive]"`
2. In [Google Cloud Console](https://console.cloud.google.com/), enable the **Google Drive API**
   and create an **OAuth client ID** of type **Desktop app**. Download the JSON.
   (A **service account** key JSON also works; share the files with the service account.)
3. Point DataElevate at it per call (`credentials="~/secrets/gdrive.json"`) or once with
   `export DATAELEVATE_GDRIVE_CREDENTIALS=~/secrets/gdrive.json`.

The first call opens a browser to sign in. Access is **read-only**. The token is cached in
`~/.dataelevate/tokens/` (readable only by you); set `DATAELEVATE_HOME` to move it.

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
