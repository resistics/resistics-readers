"""
This module has utility functions to help when single recordings are split into
multiple data files.

In this scenario, it is possible for each data file to have specfic parameters
such as differing levels or scalings required to conver to field units.

Further, it is useful to check that the first and last times of each individual
file are continuous and without gaps.
"""
from loguru import logger
from typing import List, Dict, Any
from pathlib import Path
import pandas as pd
from resistics.time import TimeMetadata


class TimeMetadataSingle(TimeMetadata):
    """
    TimeMetadata class for a single file in a multi data file recording

    In most cases, individual data formats may inherit from this as there could
    be other parameters that are useful to save per data file.
    """

    data_file: str
    """The name of a single data file in a multi file recording"""


class TimeMetadataMerge(TimeMetadata):
    """
    This is an extension of TimeMetadata for situations where a single
    continuous recording has been split into multiple data files.

    This is applicable to SPAM data as well as Lemi B423 for example.

    To keep track of the metadata about all the contributing files, this
    extension to TimeMetadata adds a dictionary storing file specific details
    such as first and last time, specific scalings or reading parameters etc.
    """

    data_table: Dict[str, Any]
    """The data table that will help with scaling and selecting data files"""


def validate_consistency(dir_path: Path, metadata_list: List[TimeMetadata]) -> bool:
    """
    Validate multi file metadata with each other to ensure they are consistent

    This function checks:

    - Matching sampling frequency
    - Matching number of chans
    - Matching channels

    Parameters
    ----------
    dir_path : Path
        The data path
    metadata_list : List[TimeMetadata]
        List of TimeMetadata, one for each data file in a continuous recording

    Returns
    -------
    bool
        True if validation was successful, otherwise raises an Exception

    Raises
    ------
    MetadataReadError
        If multiple values are found for sampling frequency
    MetadataReadError
        If multiple values are found for number of chans
    MetadataReadError
        If different XTR files have different channels
    """
    from resistics.errors import MetadataReadError

    set_fs = set([x.fs for x in metadata_list])
    if len(set_fs) > 1:
        raise MetadataReadError(dir_path, f"More than one fs, {set_fs}")
    set_n_chans = set([x.n_chans for x in metadata_list])
    if len(set_n_chans) > 1:
        raise MetadataReadError(
            dir_path, f"Inconsistent number of channels {set_n_chans}"
        )
    set_chans = set([", ".join(x.chans) for x in metadata_list])
    if len(set_chans) > 1:
        raise MetadataReadError(dir_path, f"Inconsistent channels {set_chans}")
    return True


def validate_continuous(
    dir_path: Path, metadata_list: List[TimeMetadataSingle]
) -> bool:
    """
    Validate that metadata is continuous

    For data formats such as SPAM and Lemi B423 which separate a single
    continuous recording into multiple data files, it needs to be validated that
    there is no missing data.

    This function validates that metadata from each individual data file does
    define a single continuous recording with no missing data.

    Parameters
    ----------
    dir_path : Path
        The directory path
    metadata_list : List[TimeMetadata]
        List of TimeMetadata with metadata from a set of data files that
        constitute a single continuous recording

    Returns
    -------
    bool
        True if recording is continuous

    Raises
    ------
    MetadataReadError
        If gaps were found
    """
    from resistics.errors import MetadataReadError
    from resistics.sampling import to_timedelta

    if len(metadata_list) == 0:
        raise MetadataReadError(dir_path, "No metadata in list")
    if len(metadata_list) == 1:
        return True

    dt = to_timedelta(1 / metadata_list[0].fs)
    data = [(x.data_file, x.first_time, x.last_time) for x in metadata_list]
    df = pd.DataFrame(data=data, columns=["file", "first_time", "last_time"])
    df = df.sort_values("first_time")
    time_chk = (df["first_time"] - df.shift(1)["last_time"]).dropna()
    time_chk = time_chk - dt
    gaps = time_chk[time_chk > to_timedelta(0)]
    if len(gaps.index) > 0:
        logger.error("Found gaps between files...")
        data_files = df["file"].values
        info = pd.DataFrame(
            {
                "From": data_files[gaps.index - 1],
                "To": data_files[gaps.index],
                "Gap": gaps.values,
            }
        )
        logger.error(f"\n{info.to_string(index=False)}")
        raise MetadataReadError(dir_path, "Gaps found, unable to read data")
    return True


def add_cumulative_samples(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add cumulative samples to data table

    This is useful for multi file recordings and helping to decide which files
    to read to get a certain time range

    Parameters
    ----------
    df : pd.DataFrame
        Data table with an n_samples column

    Returns
    -------
    pd.DataFrame
        Data table with a first_sample and last_sample column added
    """
    cumsum_samples = df["n_samples"].cumsum()
    df["first_sample"] = cumsum_samples.shift(1).fillna(value=0).astype(int)
    df["last_sample"] = df["first_sample"] + df["n_samples"] - 1
    return df


def samples_to_sources(
    dir_path: Path,
    df: pd.DataFrame,
    from_sample: int,
    to_sample: int,
) -> pd.DataFrame:
    """
    Find the data sources for a sample range

    This can be used for a multi-file measurement or for a measurement that is
    split up into multiple records. It maps a sample range defined by
    from_sample and to_sample to the sources and returns a DataFrame providing
    information about the samples that need to be read from each source (file
    or record) to cover the range.

    Parameters
    ----------
    dir_path : Path
        The directory with the data
    df : pd.DataFrame
        Table of all the sources and their sample ranges
    from_sample : int
        Reading from sample
    to_sample : int
        Reading to sample

    Returns
    -------
    pd.DataFrame
        DataFrame with data files to read as indices and reading information
        as columns such as number of samples to read, channel scalings etc.

    Raises
    ------
    TimeDataReadError
        If somehow there's a mismatch in the total number of samples to read
        per file and the expected number of samples.
    """
    from resistics.errors import TimeDataReadError

    df = df[~(df["first_sample"] > to_sample)]
    df = df[~(df["last_sample"] < from_sample)]
    # get read from samples
    # correct those where the data file first sample is before the from sample
    df["read_from"] = 0
    adjust_from = df["first_sample"] < from_sample
    df.loc[adjust_from, "read_from"] = from_sample - df["first_sample"]
    # get read to samples
    # correct those where the data file last sample is after the to sample
    df["read_to"] = df["n_samples"] - 1
    adjust_to = df["last_sample"] > to_sample
    df.loc[adjust_to, "read_to"] = to_sample - df["first_sample"]
    df["n_samples_read"] = df["read_to"] - df["read_from"] + 1

    if df["n_samples_read"].sum() != to_sample - from_sample + 1:
        sum_files = df["n_samples_read"].sum()
        expected = to_sample - from_sample + 1
        raise TimeDataReadError(
            dir_path, f"Samples to read {sum_files} does not match expected {expected}"
        )
    return df
