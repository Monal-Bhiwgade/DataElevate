"""Download datasets from Kaggle and Google Drive."""

from pathlib import Path

from . import _gdrive, _kaggle
from .errors import CredentialsError


class Download_data:
    """Entry point for downloads: ``Download_data.Kaggle`` and ``Download_data.GoogleDrive``."""

    class Kaggle:

        @staticmethod
        def from_kaggle(dataset, destination=None, keep_cache=False, *, to_path=None):
            """Download a Kaggle dataset.

            Args:
                dataset: Dataset URL (``https://www.kaggle.com/datasets/owner/name``)
                    or ID (``owner/name``, optionally ``owner/name/versions/3``).
                destination: Folder to save into. Defaults to ``./Data/<name>``.
                keep_cache: Keep kagglehub's cached copy as well (default: remove it).

            Returns:
                List of paths to the downloaded files and folders.
            """
            return _kaggle.download(dataset, destination or to_path, keep_cache)

    class GoogleDrive:
        """Google Drive downloads.

        Public files and folders ("Anyone with the link") need no setup. For private
        ones, pass ``credentials=`` the path to your own Google OAuth client JSON
        (Desktop app) or service-account key JSON, or set the
        ``DATAELEVATE_GDRIVE_CREDENTIALS`` environment variable to that path.
        """

        @staticmethod
        def get_file_id(url):
            """Return the file or folder ID from a Google Drive link (or the ID itself)."""
            return _gdrive.get_file_id(url)

        @staticmethod
        def download_file(url, destination=None, credentials=None, progress=True, *,
                          folder_path=None):
            """Download one file. Google Docs/Sheets/Slides are exported to .docx/.xlsx/.pptx.

            Returns:
                Path to the downloaded file, as a string.
            """
            dest = Path(destination or folder_path or Path.cwd() / _gdrive.DEFAULT_DIR)
            creds_path = _gdrive.resolve_credentials(credentials)
            if creds_path is None:
                return str(_gdrive.public_download_file(url, dest, progress))
            service = _gdrive.build_service(creds_path)
            return str(_gdrive.api_download_file(service, _gdrive.get_file_id(url), dest))

        @staticmethod
        def download_folder(url, destination=None, credentials=None, progress=True, *,
                            folder_path=None):
            """Download a folder and its subfolders.

            Returns:
                List of paths to the downloaded files, as strings.
            """
            dest = Path(destination or folder_path or Path.cwd() / _gdrive.DEFAULT_DIR)
            creds_path = _gdrive.resolve_credentials(credentials)
            if creds_path is None:
                paths = _gdrive.public_download_folder(url, dest, progress)
            else:
                service = _gdrive.build_service(creds_path)
                paths = _gdrive.api_download_folder(
                    service, _gdrive.get_file_id(url), dest, progress)
            return [str(p) for p in paths]

        @staticmethod
        def check_filename(url, credentials=None):
            """Return the name of a Drive file without downloading it.

            Needs credentials, because Google only exposes file names through its API.
            """
            creds_path = _gdrive.resolve_credentials(credentials)
            if creds_path is None:
                raise CredentialsError(
                    "check_filename() needs Google credentials. Pass credentials="
                    f"'path/to/credentials.json' or set {_gdrive.ENV_VAR}.")
            service = _gdrive.build_service(creds_path)
            meta = service.files().get(
                fileId=_gdrive.get_file_id(url), fields="name", supportsAllDrives=True).execute()
            return meta["name"]
