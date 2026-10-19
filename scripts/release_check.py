"""Decide whether the current version should be published to PyPI.

Prints ``version=<x>`` and ``publish=true|false`` (also written to $GITHUB_OUTPUT when
running in GitHub Actions). Fails if pyproject.toml and DataElevate/__init__.py disagree
on the version, so a half-bumped version can never be released.

    python scripts/release_check.py
"""

import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "DataElevate"


def project_version():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("No version found in pyproject.toml")
    return match.group(1)


def package_version():
    text = (ROOT / PACKAGE / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit(f"No __version__ found in {PACKAGE}/__init__.py")
    return match.group(1)


def on_pypi(version):
    url = f"https://pypi.org/pypi/{PACKAGE}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        raise


def main():
    version = project_version()
    if package_version() != version:
        raise SystemExit(
            f"Version mismatch: pyproject.toml has {version}, "
            f"{PACKAGE}/__init__.py has {package_version()}. Bump both.")
    publish = not on_pypi(version)
    lines = [f"version={version}", f"publish={'true' if publish else 'false'}"]
    print("\n".join(lines))
    print(f"{version} is {'NOT yet' if publish else 'already'} on PyPI.", file=sys.stderr)
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
