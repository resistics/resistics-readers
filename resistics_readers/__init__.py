"""
A package with readers for various formats of electromagnetic geophysical time
series data with an initial focus on magnetotellurics.

This package is an extension to resistics and requires the resistics package.

Resistics readers broadly puts time series data into two catergories that it
treats differently:

- Single sampling frequency data (e.g. ATS, SPAM, Lemi)
- Multi sampling frequency data (e.g. Phoenix, Miniseed)

For single sampling frequency files, the approach is to use the data files as
they are in the resistics projects and import the appropriate time data readers.

Unfortunately, resistics does not currently support multi-sampling frequency
data files. Therefore, the approach here is to reformat data from the various
sampling frequencies into the resistics Numpy time data format.
"""
from importlib.metadata import version, PackageNotFoundError

__name__ = "resistics_readers"
try:
    __version__ = version(__name__)
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"
