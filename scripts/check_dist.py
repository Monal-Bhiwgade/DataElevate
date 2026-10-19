"""Check built distributions before uploading to PyPI.

Fails if a wheel or sdist contains anything that is not expected package content, or
anything that looks like a credential. Run after `python -m build`:

    python scripts/check_dist.py dist/*
"""

import re
import sys
import tarfile
import zipfile
from pathlib import PurePosixPath

SECRET = re.compile(
    r"GOCSPX-[\w-]{10,}"
    r"|[\"']client_secret[\"']\s*:"
    r"|eyJpbnN0" r"YWxsZWQi|eyJ3ZWIi" r"OnsiY2xpZW50X2lk|eyJ0eXBl" r"Ijoic2VydmljZV9hY2NvdW50"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|AKIA[0-9A-Z]{16}"
)
FORBIDDEN_NAME = re.compile(
    r"(^|/)(env\.py|\.env(\..*)?|token[^/]*\.json|credentials[^/]*|client_secret[^/]*"
    r"|service_account[^/]*|kaggle\.json|[^/]*\.pem|[^/]*\.key)$",
    re.IGNORECASE,
)


def members(path):
    if path.endswith(".whl"):
        with zipfile.ZipFile(path) as zf:
            for name in zf.namelist():
                yield name, zf.read(name)
    elif path.endswith(".tar.gz"):
        with tarfile.open(path) as tf:
            for m in tf.getmembers():
                if m.isfile():
                    yield m.name, tf.extractfile(m).read()
    else:
        raise SystemExit(f"Unknown distribution type: {path}")


def check(path):
    problems = []
    for name, data in members(path):
        if FORBIDDEN_NAME.search(name):
            problems.append(f"forbidden file: {name}")
        if SECRET.search(data.decode("utf-8", "ignore")):
            problems.append(f"possible credential in: {name}")
        parts = PurePosixPath(name).parts
        if "DataElevate" in parts:
            inner = parts[parts.index("DataElevate"):]
            if len(inner) > 1 and not inner[-1].endswith(".py"):
                problems.append(f"unexpected non-Python file in package: {name}")
    return problems


def main(paths):
    if not paths:
        raise SystemExit("usage: python scripts/check_dist.py dist/*")
    failed = False
    for path in paths:
        problems = check(path)
        status = "OK" if not problems else "FAILED"
        print(f"{status}: {path}")
        for p in problems:
            print(f"   - {p}")
        failed |= bool(problems)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
