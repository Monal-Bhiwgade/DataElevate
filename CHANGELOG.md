# Changelog

## 1.2.1

Better discoverability on PyPI and GitHub. No code changes.

- Clearer PyPI summary, more search keywords, Python 3.9–3.13 and OS classifiers, and
  Documentation, Source and Release notes links.
- README: search-friendly introduction, badges, a "Why DataElevate?" section and an FAQ.
  Links now work on the PyPI page.
- Releases now publish to PyPI automatically when a version bump is merged into `main`.
- CI also tests Python 3.13.

## 1.2.0

More sources, focused on data that is painful to fetch by hand.

### Added
- **Smart loader:** `Load_data.load()` / `smart_load()` takes one source, a list, a
  `{name: source}` dict or per-source spec dicts, detects each source (local file/folder/
  archive, https, cloud path/glob, lake table, Kaggle, Drive, Hugging Face, database URL,
  DataFrame), loads them in parallel and combines them: stacked with a `source` column when
  columns match, otherwise a dict (`combine=`). Folders of many files are combined too.
  Also `normalize_columns=`, `errors="skip"`, `df.attrs["sources"]`, and
  `Load_data.detect_source()`. Database passwords are masked in the source column.
- **Data lakes:** `Load_data.from_lake()` reads Hive-partitioned Parquet/CSV/JSON folders
  and Delta Lake tables on S3, GCS, Azure, other fsspec storage or local disk, with
  `columns=`, `filters=` and `limit=` pushed down so only the needed files and columns
  are read. Delta tables are auto-detected and support time travel (`version=`).
  `Load_data.describe_lake()` shows format, columns, partitions and file count.
- **Any link:** `Load_data.from_url()` / `Download_data.from_url()` for `https://`,
  GitHub and Dropbox share links (rewritten automatically), Google Drive and Kaggle links,
  and `s3://`, `gs://`, `az://`/`abfs://`, `sftp://`, `ftp://`, `github://`, `hf://`.
  Folders and globs work; archives are extracted; downloads are cached.
  `from_cloud()` is an alias.
- **Google sign-in for private Drive files, zero setup:** if a file isn't public, a browser
  opens once to sign in with Google (read-only); the sign-in is cached on the user's machine.
  The app's Desktop-app OAuth client is not shipped in the package. It is fetched from
  `oauth/gdrive-client.json` in the repository (cached 7 days, re-fetched if the client is
  rotated) and must be a Desktop-app client; anything else is refused. `auth="auto"`
  (default), `"public"` or `"oauth"`. Your own `credentials=` file still takes priority.
- **Hugging Face:** `Load_data.from_huggingface()` and `Download_data.HuggingFace.download()`.
- **Image datasets:** `Load_data.from_images()` indexes class/split folders (local, archive
  or any link) into a `path`, `label`, `split` DataFrame.
- **Formats:** Parquet, Feather/Arrow, JSON (nested JSON flattened), JSONL, and compressed
  text (`.csv.gz`, `.csv.zip`, `.jsonl.gz`, ...).
- Extras: `s3`, `gcs`, `azure`, `sftp`, `cloud`, `delta`, `lake`, `huggingface`,
  `mssql-odbc`. A missing extra raises an error with the exact `pip install` command.

### Changed
- SQL Server / Azure SQL use `pymssql` by default, so no Microsoft ODBC driver install is
  needed. Pass `driver="ODBC Driver 18 for SQL Server"` to use pyodbc (`[mssql-odbc]`).
- Core dependencies now include `pyarrow`, `fsspec`, `requests` and the Google auth
  libraries (wheels on every OS). The `[gdrive]` extra is now empty and kept for compatibility.
- `GoogleDrive.check_filename()` uses the built-in sign-in when no credentials are given.

## 1.1.0

A foundation release: install works everywhere, every documented feature works, and the
package ships no credentials.

### Security
- Removed the Google OAuth client credentials that were bundled in 1.0.7. DataElevate now
  only uses credentials the user supplies (`credentials=` or `DATAELEVATE_GDRIVE_CREDENTIALS`).
- Google Drive access is now read-only (`drive.readonly`) instead of full Drive access.
- Database table names are quoted through SQLAlchemy, so they can no longer inject SQL;
  passwords with special characters are escaped.
- Archive extraction blocks path traversal ("zip slip"), unsafe symlinks and device files.
- Drive file names are sanitised before being used as local paths.
- OAuth tokens are cached in `~/.dataelevate/tokens/` with owner-only permissions.
- A test now fails the build if anything that looks like a credential is in the package.

### Fixed
- `pip install DataElevate` failed on Linux/macOS because of the `mysql` dependency.
- `Load_data.from_kaggle` and `Load_data.from_drive` crashed with `AttributeError`.
- Errors were returned instead of raised.
- Kaggle cache cleanup and token paths only worked on Windows; cleanup could delete other
  datasets from the same owner.
- Google Drive folders over 100 items were silently truncated (no paging).
- `from_sqlite` created an empty database when the file didn't exist.
- `Load_data.Database.sqlite`, `check_filename` and the `destination=` / `username=`
  arguments shown in the README now exist.

### Added
- Public Google Drive files and folders download with no credentials.
- `file=` to choose a file when a dataset has several; error lists the choices.
- `query=` / `params=` for custom SQL, `Database.from_url()`, `schema=`.
- Extraction of `.tar.bz2`, `.bz2`, `.xz`; `.tsv` files; delimiter sniffing for text files.
- Optional extras: `[gdrive]`, `[db]`, `[mssql]`, `[all]`.
- Test suite and CI on Linux, macOS and Windows.

### Changed
- Requires Python 3.9+.
- `GoogleDrive.download_file` returns the downloaded path (was a status message).
- MySQL/MariaDB use PyMySQL; Oracle uses python-oracledb; SQL Server defaults to ODBC Driver 18.
- Old keyword names (`to_path=`, `folder_path=`, `user=`) still work.

## 1.0.0 – 1.0.7 (January 2025)
- Initial releases.
