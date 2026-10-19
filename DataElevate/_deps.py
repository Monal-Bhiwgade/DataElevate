"""Lazy imports for optional dependencies, with a clear install hint."""

import importlib

from .errors import MissingDependencyError


def require(module, package, extra):
    """Import ``module`` or raise MissingDependencyError naming the extra to install."""
    try:
        return importlib.import_module(module)
    except ImportError as exc:
        raise MissingDependencyError(package, extra) from exc
