"""Exceptions raised by DataElevate.

Every exception inherits from :class:`DataElevateError`, so callers can catch
all library errors with a single ``except DataElevateError``.
"""


class DataElevateError(Exception):
    """Base class for all DataElevate errors."""


class InvalidInput(DataElevateError, ValueError):
    """A URL, ID, path or argument is invalid or cannot be accessed."""


class Invalid_Directory(DataElevateError, FileNotFoundError):
    """An expected file or directory does not exist."""


class Invalid_File_Support(DataElevateError, ValueError):
    """The file type is not supported for loading or extraction."""


class MultipleFilesError(DataElevateError):
    """A dataset contains several loadable files and none was chosen."""

    def __init__(self, source, files):
        self.source = source
        self.files = list(files)
        names = "\n  - ".join(self.files)
        super().__init__(
            f"'{source}' contains {len(self.files)} loadable files:\n  - {names}\n"
            "Pass file='<name>' to choose one, or download the dataset with "
            "Download_data and load the files you need with Load_data.from_local()."
        )


class MissingDependencyError(DataElevateError, ImportError):
    """An optional dependency needed for this feature is not installed."""

    def __init__(self, package, extra):
        self.package = package
        self.extra = extra
        target = f'"DataElevate[{extra}]"' if extra else "--upgrade DataElevate"
        super().__init__(
            f"This feature needs '{package}'. Install it with:\n"
            f"    pip install {target}"
        )


class CredentialsError(DataElevateError):
    """Google credentials are missing or invalid."""
