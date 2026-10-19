"""Google Drive helpers.

Three ways in, tried in this order:

1. Your own credentials file (``credentials=`` or ``DATAELEVATE_GDRIVE_CREDENTIALS``):
   an OAuth client JSON (Desktop app) or a service-account key JSON.
2. Public files and folders ("Anyone with the link") through ``gdown``. No sign-in.
3. Built-in sign-in: a browser window opens once, you sign in with Google, and
   DataElevate gets read-only access. The app's desktop OAuth client config is NOT
   shipped in the package; it is fetched from the DataElevate repository (so it can
   be rotated without a new release) and cached for a week. Your sign-in token
   never leaves your machine.

Access is always read-only.
"""

import hashlib
import io
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

from ._deps import require
from .errors import CredentialsError, InvalidInput

log = logging.getLogger(__name__)

ENV_VAR = "DATAELEVATE_GDRIVE_CREDENTIALS"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
FOLDER_MIME = "application/vnd.google-apps.folder"
EXPORT_MIME_TYPES = {
    "application/vnd.google-apps.document": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"),
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
    "application/vnd.google-apps.presentation": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"),
}
DEFAULT_DIR = "GoogleDrive_Data"

# Built-in sign-in: where the app's (public, desktop-type) OAuth client config lives.
CLIENT_URL_ENV = "DATAELEVATE_GDRIVE_CLIENT_URL"
DEFAULT_CLIENT_URL = ("https://raw.githubusercontent.com/Monal-Bhiwgade/DataElevate/"
                      "main/oauth/gdrive-client.json")
CLIENT_CACHE_SECONDS = 7 * 24 * 3600
AUTH_MODES = ("auto", "public", "oauth")

_ID_PATTERNS = (
    re.compile(r"/folders/([\w-]+)"),
    re.compile(r"/d/([\w-]+)"),
    re.compile(r"[?&]id=([\w-]+)"),
)


# --------------------------------------------------------------------------- ids

def get_file_id(link):
    """Return the Drive file/folder ID from a share link, or the ID itself."""
    if not isinstance(link, str) or not link.strip():
        raise InvalidInput("Google Drive link or ID must be a non-empty string.")
    link = link.strip()
    if "/" not in link and "?" not in link:
        if re.fullmatch(r"[\w-]{10,}", link):
            return link
        raise InvalidInput(f"'{link}' is not a valid Google Drive ID.")
    for pattern in _ID_PATTERNS:
        match = pattern.search(link)
        if match:
            return match.group(1)
    raise InvalidInput(f"Could not find a file or folder ID in '{link}'.")


def is_url(link):
    return isinstance(link, str) and link.strip().lower().startswith(("http://", "https://"))


# ------------------------------------------------------------------ credentials

def config_dir():
    """Where DataElevate keeps per-user state such as cached OAuth tokens."""
    return Path(os.environ.get("DATAELEVATE_HOME") or Path.home() / ".dataelevate")


def resolve_credentials(credentials=None):
    """Return the path to the user's credentials file, or None for public mode."""
    value = credentials or os.environ.get(ENV_VAR)
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_file():
        raise CredentialsError(f"Google credentials file not found: {path}")
    return path


def _write_private(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(text)


def _user_oauth_credentials(client_config):
    oauth_creds = require("google.oauth2.credentials", "google-auth", "gdrive")
    transport = require("google.auth.transport.requests", "google-auth", "gdrive")
    flow_mod = require("google_auth_oauthlib.flow", "google-auth-oauthlib", "gdrive")

    section = client_config.get("installed") or client_config.get("web") or {}
    client_id = section.get("client_id", "")
    digest = hashlib.sha256(client_id.encode()).hexdigest()[:12]
    token_path = config_dir() / "tokens" / f"gdrive-{digest}.json"

    creds = None
    if token_path.is_file():
        try:
            creds = oauth_creds.Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except ValueError:
            creds = None

    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(transport.Request())
            _write_private(token_path, creds.to_json())
            return creds
        except Exception:  # refresh token revoked or expired: sign in again
            log.info("Stored Google token could not be refreshed; signing in again.")

    flow = flow_mod.InstalledAppFlow.from_client_config(client_config, SCOPES)
    print("DataElevate: opening your browser to sign in to Google (read-only Drive access)."
          " If no browser opens, use the link printed below.", file=sys.stderr)
    creds = flow.run_local_server(port=0)
    _write_private(token_path, creds.to_json())
    return creds


def build_service(credentials_path):
    """Build a read-only Drive v3 client from the user's own credentials file."""
    try:
        info = json.loads(Path(credentials_path).read_text())
    except (OSError, ValueError) as exc:
        raise CredentialsError(f"Could not read Google credentials JSON: {exc}") from exc
    return _service_from_info(info)


def _service_from_info(info):
    if info.get("type") == "service_account":
        sa = require("google.oauth2.service_account", "google-auth", "gdrive")
        creds = sa.Credentials.from_service_account_info(info, scopes=SCOPES)
    elif "installed" in info or "web" in info:
        creds = _user_oauth_credentials(info)
    else:
        raise CredentialsError(
            "Credentials JSON must be an OAuth client (Desktop app) file or a "
            "service-account key file from Google Cloud Console."
        )
    discovery = require("googleapiclient.discovery", "google-api-python-client", "gdrive")
    return discovery.build("drive", "v3", credentials=creds, cache_discovery=False)


def _validate_client_config(info, source):
    """Only accept a desktop ("installed") OAuth client. Never a service-account key."""
    section = info.get("installed") if isinstance(info, dict) else None
    if not isinstance(section, dict) or not section.get("client_id"):
        raise CredentialsError(
            f"{source} is not a Desktop-app OAuth client config; refusing to use it.")
    return {"installed": section}


def builtin_client_config(force_refresh=False):
    """Return DataElevate's desktop OAuth client config (fetched, then cached)."""
    url = os.environ.get(CLIENT_URL_ENV) or DEFAULT_CLIENT_URL
    if not url.lower().startswith("https://"):
        raise CredentialsError(f"{CLIENT_URL_ENV} must be an https:// URL.")
    cache = config_dir() / "gdrive-client.json"

    cached = None
    if cache.is_file():
        try:
            cached = _validate_client_config(json.loads(cache.read_text()), "Cached client")
        except (OSError, ValueError, CredentialsError):
            cached = None
        fresh = time.time() - cache.stat().st_mtime < CLIENT_CACHE_SECONDS
        if cached and fresh and not force_refresh:
            return cached

    requests = require("requests", "requests", None)
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        info = _validate_client_config(resp.json(), url)
    except Exception as exc:
        if cached:
            log.warning("Could not refresh Google sign-in config (%s); using cached copy.", exc)
            return cached
        raise CredentialsError(
            f"Could not get DataElevate's Google sign-in config from {url}: {exc}\n"
            f"Alternatively pass credentials='path/to/your-client.json' or set {ENV_VAR}."
        ) from exc
    _write_private(cache, json.dumps(info))
    return info


_ROTATED_CLIENT_ERRORS = ("invalid_client", "deleted_client", "unauthorized_client")


def builtin_service():
    """Drive client using the built-in sign-in, retrying once if the app client was rotated."""
    info = builtin_client_config()
    try:
        return _service_from_info(info)
    except Exception as exc:
        if not any(code in str(exc) for code in _ROTATED_CLIENT_ERRORS):
            raise
        newer = builtin_client_config(force_refresh=True)
        if newer == info:
            raise
        return _service_from_info(newer)


def private_service(credentials=None):
    """Drive client from the user's own credentials if given, else built-in sign-in."""
    path = resolve_credentials(credentials)
    return build_service(path) if path else builtin_service()


# ------------------------------------------------------------------- downloads

def safe_name(name):
    """Make a Drive item name safe to use as a single local path component."""
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name or "").strip()
    return cleaned if cleaned not in ("", ".", "..") else "_"


def _http_error():
    return require("googleapiclient.errors", "google-api-python-client", "gdrive").HttpError


def api_download_file(service, file_id, dest_dir, name=None, mime_type=None):
    """Download one file with the Drive API. Returns the local path."""
    http = require("googleapiclient.http", "google-api-python-client", "gdrive")
    HttpError = _http_error()
    try:
        if name is None or mime_type is None:
            meta = service.files().get(
                fileId=file_id, fields="name, mimeType", supportsAllDrives=True).execute()
            name, mime_type = meta["name"], meta["mimeType"]
        if mime_type == FOLDER_MIME:
            raise InvalidInput(f"'{file_id}' is a folder; use download_folder() instead.")

        filename = safe_name(name)
        if mime_type in EXPORT_MIME_TYPES:
            export_mime, ext = EXPORT_MIME_TYPES[mime_type]
            request = service.files().export_media(fileId=file_id, mimeType=export_mime)
            if not filename.lower().endswith(ext):
                filename += ext
        elif mime_type.startswith("application/vnd.google-apps."):
            raise InvalidInput(f"Google file type '{mime_type}' cannot be downloaded.")
        else:
            request = service.files().get_media(fileId=file_id, supportsAllDrives=True)

        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / filename
        with io.FileIO(str(path), "wb") as fh:
            downloader = http.MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        return path
    except HttpError as exc:
        raise InvalidInput(f"Google Drive could not download '{file_id}': {exc}") from exc


def _list_children(service, folder_id):
    items, token = [], None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType)",
            pageSize=1000, pageToken=token,
            includeItemsFromAllDrives=True, supportsAllDrives=True,
        ).execute()
        items.extend(resp.get("files", []))
        token = resp.get("nextPageToken")
        if not token:
            return items


def api_download_folder(service, folder_id, dest_dir, progress=True):
    """Recursively download a folder with the Drive API. Returns local file paths."""
    HttpError = _http_error()
    try:
        children = _list_children(service, folder_id)
    except HttpError as exc:
        raise InvalidInput(f"Google Drive could not list folder '{folder_id}': {exc}") from exc

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    iterator = children
    if progress:
        from tqdm.auto import tqdm
        iterator = tqdm(children, desc=f"Downloading {dest_dir.name}", unit="file")
    for item in iterator:
        if item["mimeType"] == FOLDER_MIME:
            paths += api_download_folder(
                service, item["id"], dest_dir / safe_name(item["name"]), progress)
        else:
            paths.append(api_download_file(
                service, item["id"], dest_dir, item["name"], item["mimeType"]))
    return paths


def public_download_file(link, dest_dir, progress=True):
    """Download a public file with gdown. Returns the local path."""
    gdown = require("gdown", "gdown", None)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    output = str(dest_dir) + os.sep
    try:
        if is_url(link):
            result = gdown.download(url=link.strip(), output=output, quiet=not progress, fuzzy=True)
        else:
            result = gdown.download(id=get_file_id(link), output=output, quiet=not progress)
    except Exception as exc:
        raise InvalidInput(_public_hint(link, exc)) from exc
    if not result:
        raise InvalidInput(_public_hint(link))
    return Path(result)


def public_download_folder(link, dest_dir, progress=True):
    """Download a public folder with gdown. Returns local file paths."""
    gdown = require("gdown", "gdown", None)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        if is_url(link):
            result = gdown.download_folder(url=link.strip(), output=str(dest_dir), quiet=not progress)
        else:
            result = gdown.download_folder(id=get_file_id(link), output=str(dest_dir), quiet=not progress)
    except Exception as exc:
        raise InvalidInput(_public_hint(link, exc, folder=True)) from exc
    if result is None:
        raise InvalidInput(_public_hint(link, folder=True))
    return [Path(p) for p in result]


def _public_hint(link, exc=None, folder=False):
    what = "folder" if folder else "file"
    detail = f" ({exc})" if exc else ""
    extra = (" Public folder downloads are limited to 50 files per folder;"
             " use auth='oauth' (sign in) for larger folders.") if folder else ""
    return (
        f"Could not download the Google Drive {what} '{link}'{detail}. "
        f"Share it as 'Anyone with the link', or if it is private use auth='oauth' to "
        f"sign in with Google, or pass "
        f"credentials='path/to/credentials.json'.{extra}"
    )
