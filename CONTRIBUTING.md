# Contributing to DataElevate

Thanks for helping! DataElevate aims to make getting training data into pandas a one-line
job from anywhere. New data sources, faster loading, better errors, docs and bug reports
are all welcome.

## Ways to contribute

- **Report a bug** or **request a data source**: open an issue using one of the templates.
- **Pick something to build**: see [Ideas to work on](#ideas-to-work-on) below, or issues
  labelled `good first issue` / `help wanted`.
- **Improve docs**: clearer examples in the README are always valuable.

For anything bigger than a small fix, please open an issue first so we can agree on the
approach before you spend time on it.

## Development setup

```bash
git clone https://github.com/<your-username>/DataElevate.git
cd DataElevate
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

All tests run offline in a few seconds. Python 3.9 or newer.

## How the code is organised

| File | What it does |
|---|---|
| `DataElevate/load_data.py` | Public `Load_data` API: `load()`, `from_*()`, `Database` |
| `DataElevate/download.py` | Public `Download_data` API |
| `DataElevate/_smart.py` | Smart loader: source detection and combining |
| `DataElevate/_remote.py` | Downloads from https and fsspec storage (S3, GCS, Azure, SFTP, ...) |
| `DataElevate/_lake.py` | Partitioned Parquet / Delta Lake reading with push-down |
| `DataElevate/_loaders.py` | Reading local files (CSV, Excel, Parquet, JSON, ...) |
| `DataElevate/_kaggle.py`, `_gdrive.py`, `_hf.py`, `_images.py` | Source-specific helpers |
| `DataElevate/extractor.py` | Safe archive extraction |
| `DataElevate/errors.py` | All exceptions (inherit from `DataElevateError`) |
| `DataElevate/_deps.py` | `require()` for optional dependencies |

### Adding a new data source

1. Put the logic in a private module, e.g. `DataElevate/_snowflake.py`.
2. Import its third-party library **lazily** with `require(module, package, extra)`, so
   `import DataElevate` stays fast and users get a clear "pip install DataElevate[extra]"
   message if it's missing.
3. Add the extra to `[project.optional-dependencies]` in `pyproject.toml`, and to `all`.
4. Expose it as `Load_data.from_<source>()` (and `Download_data` if it downloads files).
5. Teach the smart loader to recognise it in `_smart.detect()` and `_smart.load_one()`.
6. Add tests and a README section.

## Rules every change must follow

These keep the library safe and usable everywhere; CI checks most of them.

- **No credentials in the code or package, ever.** Use the user's own credentials, from
  arguments, environment variables or the service's standard config files. A test fails
  if anything secret-looking is in the package.
- **Works on Windows, macOS and Linux with `pip` only.** Prefer dependencies with wheels
  for all three; no system installs (ODBC drivers, Java, CLIs) for the default path.
- **Tests never touch the network.** Use a local HTTP server, fsspec's `memory://`
  filesystem, temp files or fakes (see `tests/` for examples).
- **Raise, don't return, errors**, using the classes in `errors.py`, with a message that
  tells the user how to fix the problem.
- **Read-only access** to user data. Never build SQL by string formatting.
- Keep the old public names working (`Load_data`, `Download_data`, `Extractor`, ...);
  add new names alongside rather than renaming.

## Pull requests

1. Fork the repo and create a branch from `main`.
2. Make your change with tests, and update `README.md` if users will notice it.
3. Add a line under a new `## Unreleased` heading in `CHANGELOG.md`.
4. Run `pytest` and open the pull request. CI runs the tests on Windows, macOS and Linux.

Please **don't bump the version** in your PR. The maintainer does that when releasing,
and merging a version bump into `main` publishes to PyPI automatically.

## Ideas to work on

- **Warehouses:** Snowflake, BigQuery, Databricks, Redshift, Athena loaders.
- **Apache Iceberg** tables in `from_lake()`.
- **`prepare()` for training:** dataset link → train/validation/test splits in one call.
- **Google Sheets** and **OneDrive / SharePoint** loaders.
- **More formats:** ORC, Avro, XML, `.ods`.
- **REST APIs:** paginated JSON endpoints → DataFrame.
- **Polars output** as an option alongside pandas.
- **Docs:** a documentation site with a page per source.

## Code of conduct

By taking part you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Security

Please report security problems privately as described in [SECURITY.md](SECURITY.md),
not in public issues.
