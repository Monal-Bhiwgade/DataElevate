"""DataElevate: get training data from Kaggle, Google Drive, archives and databases
into pandas with a few lines of code."""

from .download import Download_data
from .errors import (
    CredentialsError,
    DataElevateError,
    Invalid_Directory,
    Invalid_File_Support,
    InvalidInput,
    MissingDependencyError,
    MultipleFilesError,
)
from .extractor import Extractor
from .load_data import Load_data

__all__ = [
    "Download_data",
    "Load_data",
    "Extractor",
    "DataElevateError",
    "InvalidInput",
    "Invalid_Directory",
    "Invalid_File_Support",
    "MultipleFilesError",
    "MissingDependencyError",
    "CredentialsError",
]

__version__ = "1.1.0"
__author__ = "Monal Bhiwgade"
