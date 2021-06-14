"""
A package with readers for various formats of electromagnetic geophysical time
series data with an initial focus on magnetotellurics.

This package is an extension to resistics and requires the resistics package
"""
from importlib.metadata import version, PackageNotFoundError

__name__ = "resistics_readers"
try:
    __version__ = version(__name__)
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"
