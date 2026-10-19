# Changelog

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
