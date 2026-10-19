"""Deprecated module name, kept so ``from DataElevate.EDAerror import ...`` keeps working.

Import exceptions from ``DataElevate`` or ``DataElevate.errors`` instead.
"""

from .errors import (  # noqa: F401
    CredentialsError,
    DataElevateError,
    Invalid_Directory,
    Invalid_File_Support,
    InvalidInput,
    MissingDependencyError,
    MultipleFilesError,
)
