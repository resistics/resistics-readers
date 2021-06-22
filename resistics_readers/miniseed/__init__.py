"""
This subpackage implements reformatting for miniseed data.

Miniseed data is not directly read in resistics as it is a multi-sampling
frequency data format that with no guarantee of matching timestamps for all
channels. Therefore, the safest strategy for interacting with miniseed data
is to reformat it as required for usage in resistics.

Obspy is used to read the miniseed data.
"""
from resistics_readers.miniseed.mseed import reformat  # noqa
