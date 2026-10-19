"""Package-level guards: light imports, and no secrets ever shipped."""

import re
import subprocess
import sys
from pathlib import Path

import DataElevate

PACKAGE_DIR = Path(DataElevate.__file__).parent

# Patterns for credentials that must never be inside the package.
SECRET_PATTERNS = {
    "Google OAuth client secret": re.compile(r"GOCSPX-[\w-]{10,}"),
    "client_secret in JSON": re.compile(r"[\"']client_secret[\"']\s*:\s*[\"'][^\"']+"),
    "base64 Google OAuth client": re.compile(r"eyJpbnN0" r"YWxsZWQi|eyJ3ZWIi" r"OnsiY2xpZW50X2lk"),
    "base64 service account": re.compile(r"eyJ0eXBl" r"Ijoic2VydmljZV9hY2NvdW50"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "Kaggle key in JSON": re.compile(r"[\"']key[\"']\s*:\s*[\"'][0-9a-f]{32}[\"']"),
}


def test_no_secrets_in_package():
    hits = []
    for path in PACKAGE_DIR.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        text = path.read_text(errors="ignore")
        hits += [f"{path.name}: {label}" for label, rx in SECRET_PATTERNS.items()
                 if rx.search(text)]
    assert not hits, f"Possible credentials in package: {hits}"


def test_only_python_files_and_no_env_module():
    files = [p for p in PACKAGE_DIR.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    assert all(p.suffix == ".py" for p in files), [p.name for p in files if p.suffix != ".py"]
    assert not (PACKAGE_DIR / "env.py").exists()


def test_import_does_not_load_optional_dependencies():
    code = ("import sys, DataElevate; "
            "print(','.join(m for m in ('sqlalchemy', 'googleapiclient', 'google_auth_oauthlib',"
            " 'kagglehub', 'gdown') if m in sys.modules))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == ""


def test_public_api_and_version():
    assert DataElevate.__version__ == "1.1.0"
    for name in ("Download_data", "Load_data", "Extractor", "DataElevateError"):
        assert hasattr(DataElevate, name)
    from DataElevate.EDAerror import InvalidInput  # old module path still works
    assert InvalidInput is DataElevate.InvalidInput
