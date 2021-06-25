"""
Module for Lemi B423E data
Lemi B423E always records channels in the following order

- E1, E2, E3, E4

The Lemi B423E binary files are constructed from a 1024 text header followed
by repeating records with the following definitions (PPS is short for
deviation from PPS and PLL is short for PLL accuracy):

SECOND_TIMESTAMP, SAMPLE_NUM [0-FS], E1, E2, E3, E4, PPS, PLL

These are interpreted to have byte types

L, H, l, l, l, l, h, h

The channels labels are not that useful for magnetotelluric projects. When
creating metadata it is best to map them to standard channels such as Ex or Ey
"""
from loguru import logger
from typing import List, Optional, Tuple
from pathlib import Path
import numpy as np
import pandas as pd
from resistics.time import TimeMetadata, TimeData

from resistics_readers.multifile import validate_consistency, validate_continuous
from resistics_readers.multifile import TimeMetadataMerge
from resistics_readers.lemi.b423 import TimeMetadataB423, TimeReaderB423

B423E_CHANS = ["E1", "E2", "E3", "E4"]
B423E_RECORD_BYTES = 26
B423E_HEADER_LENGTH = 1024
B423E_MULT = ["Ke1", "Ke2", "Ke3", "Ke4"]
B423E_ADD = ["Ae1", "Ae2", "Ae3", "Ae4"]


def make_sudbir_B423E_metadata(
    dir_path: Path,
    fs: float,
    chans: Optional[List[str]] = None,
    dx: float = 1,
    dy: float = 1,
    folders: Optional[List[str]] = None,
) -> None:
    """
    Generate metadata for every subdirectory in a folder

    Parameters
    ----------
    dir_path : Path
        Root directory
    fs : float
        Sampling frequency, Hz
    chans : Optional[List[str]], optional
        The channels, by default None
    dx : float, optional
        Dipole distance Ex, by default 1
    dy : float, optional
        Dipole distance Ey, by default 1
    folders : Optional[List[str]], optional
        An optional list of subfolders, by default None. If None, all the
        subfolders will be processed
    """
    from resistics.common import dir_subdirs

    if chans is None:
        chans = B423E_CHANS

    if folders is None:
        folders = dir_subdirs(dir_path)
    else:
        folders = [dir_path / folder for folder in folders]
    for folder in folders:
        make_B423E_metadata(folder, fs, chans=chans, dx=dx, dy=dy)


def make_B423E_metadata(
    dir_path: Path,
    fs: float,
    chans: Optional[List[str]] = None,
    dx: float = 1,
    dy: float = 1,
) -> None:
    """
    Read a single B423E measurement directory, construct and write out metadata

    Parameters
    ----------
    dir_path : Path
        Directory path
    fs : float
        The sampling frequency, Hz
    chans : Optional[List[str]], optional
        Optional list of chans, by default None
    dx : float, optional
        Dipole distance Ex, by default 1
    dy : float, optional
        Dipole distance Ey, by default 1
    """
    metadata_list = _get_B423E_metadata_list(dir_path, fs, chans)
    validate_consistency(dir_path, metadata_list)
    validate_continuous(dir_path, metadata_list)
    metadata = _merge_metadata(metadata_list, dx, dy)
    logger.info(f"Writing metadata in {dir_path}")
    metadata.write(dir_path / "metadata.json")


def _get_B423E_metadata_list(
    dir_path: Path, fs: float, chans: Optional[List[str]] = None
) -> List[TimeMetadataB423]:
    """
    Get list of TimeMetadataB423, one for each data file

    Parameters
    ----------
    dir_path : Path
        The data path
    fs : float
        The sampling frequency, Hz
    chans : Optional[List[str]]
        The channels, by default None. Standard channels are E1, E2, E3 and E4,
        but these have little meaning geophysically, so it is possible to
        set different labels for the four channels

    Returns
    -------
    List[TimeMetadataB423]
        List of TimeMetadata
    """
    from resistics_readers.lemi.b423 import _read_B423_headers

    if chans is None:
        chans = B423E_CHANS
    data_paths = list(dir_path.glob("*.B423"))
    metadata_list = []
    for data_path in data_paths:
        logger.debug(f"Reading data file {data_path}")
        metadata_B423E = _read_B423_headers(
            data_path,
            fs,
            data_byte_offset=B423E_HEADER_LENGTH,
            record_bytes=B423E_RECORD_BYTES,
            chans=chans,
        )
        metadata_list.append(metadata_B423E)
    return metadata_list


def _merge_metadata(
    metadata_list: List[TimeMetadataB423], dx: float = 1, dy: float = 1
) -> TimeMetadata:
    """Merge the metadata list into a TimeMetadata"""
    metadata = TimeMetadata(**metadata_list[0].dict())
    metadata.first_time = min([x.first_time for x in metadata_list])
    metadata.last_time = max([x.last_time for x in metadata_list])
    metadata.n_samples = np.sum([x.n_samples for x in metadata_list])

    # channel headers
    data_files = [x.data_file for x in metadata_list]
    for chan in metadata.chans:
        metadata.chans_metadata[chan].data_files = data_files
        if chan == "Ex":
            metadata.chans_metadata[chan].dipole_dist = dx
        if chan == "Ey":
            metadata.chans_metadata[chan].dipole_dist = dy
    return metadata


class TimeReaderB423E(TimeReaderB423):
    """
    Data reader for Lemi B423E data

    There is no separate metadata file for Lemi B423E data detailing the
    sampling frequency, the number of samples, the sensors etc.. Such a
    metadata file is a pre-requisite for resistics. There are helper methods to
    make one.

    In situations where a Lemi B423E dataset is recorded in multiple files, it
    is required that the recording is continuous.

    Other important notes about Lemi B423E files

    - 1024 bytes of ASCII metadata in the data file with scaling information
    - Lemi B423E raw measurement data is signed long integer format

    Important points about scalings

    - Raw data is integer counts for electric channels
    - Scalings in B423E files convert electric channels to uV (microvolt)

    If apply_scaling is False, data will be returned in:

    - microvolts for the electric channels

    Which is equivalent to applying the scalings in the B423E headers

    With apply_scaling True, the following additional scaling will be applied:

    - Electric channels converted to mV
    - Dipole length corrections are applied to electric channels

    .. note::

        For more information about Lemi B423 format, please see:
        http://lemisensors.com/?p=485
    """

    record_bytes: int = B423E_RECORD_BYTES
    limit_chans: Optional[List[str]] = None

    def read_metadata(self, dir_path: Path) -> TimeMetadataMerge:
        """
        Read metadata

        Parameters
        ----------
        dir_path : Path
            The data directory

        Returns
        -------
        TimeMetadataMerge
            TimeMetadata with a data table

        Raises
        ------
        MetadataReadError
            If the number of channels is incorrect
        TimeDataReadError
            If not all data files exist
        TimeDataReadError
            If extensions do not match
        """
        from resistics.errors import MetadataReadError, TimeDataReadError
        from resistics_readers.multifile import validate_consistency
        from resistics_readers.multifile import validate_continuous

        metadata = TimeMetadata.parse_file(dir_path / "metadata.json")
        if metadata.n_chans != len(B423E_CHANS):
            raise MetadataReadError(
                dir_path, f"Number channels {metadata.chans} != {len(B423E_CHANS)}"
            )
        metadata_list = _get_B423E_metadata_list(dir_path, metadata.fs)
        validate_consistency(dir_path, metadata_list)
        validate_continuous(dir_path, metadata_list)
        data_table = self._generate_table(metadata_list)
        metadata_dict = metadata.dict()
        metadata_dict["data_table"] = data_table.to_dict()
        metadata = TimeMetadataMerge(**metadata_dict)

        if not self._check_data_files(dir_path, metadata):
            raise TimeDataReadError(dir_path, "All data files do not exist")
        if not self._check_extensions(dir_path, metadata):
            raise TimeDataReadError(dir_path, f"Data file suffix not {self.extension}")
        return metadata

    def read_data(
        self, dir_path: Path, metadata: TimeMetadata, read_from: int, read_to: int
    ) -> TimeData:
        """
        Get data from data files

        Lemi B423E data always has four channels, in order E1, E2, E3, E4. When
        writing out the metadata, it is possible to relabel these channels, for
        example:

        - Ex, Ey, E3, E4

        The raw data is integer counts. However, additional scalings from the
        B423 files are applied to give:

        - microvolts for the electric channels
        - millivolts for the magnetic with the gain applied

        The scalings are as follows:

        - Channel 1 = (Channel 1 * Ke1) + Ae1
        - Channel 2 = (Channel 1 * Ke2) + Ae2
        - Channel 3 = (Channel 1 * Ke3) + Ae3
        - Channel 4 = (Channel 1 * Ke4) + Ae4

        Unlike most other readers, the channels returned can be explicity
        selected by setting the limit_chans attribute of the class. This is
        because in many cases, only two of the B423Echannels are actually
        useful.

        Parameters
        ----------
        dir_path : path
            The directory path to read from
        metadata : TimeMetadata
            Time series data metadata
        read_from : int
            Sample to read data from
        read_to : int
            Sample to read data to

        Returns
        -------
        TimeData
            Time data object
        """
        from resistics_readers.multifile import samples_to_sources

        dtype = np.float32
        n_samples = read_to - read_from + 1
        chans, chan_indices = self._get_chans(dir_path, metadata)
        n_chans = len(chans)
        logger.info(f"Reading channels {chans}, indices {chan_indices}")

        messages = [f"Reading raw data from {dir_path}"]
        messages.append(f"Sampling rate {metadata.fs} Hz")
        # loop over B423 files and read data
        data_table = pd.DataFrame(data=metadata.data_table)
        df_to_read = samples_to_sources(dir_path, data_table, read_from, read_to)
        data = np.empty(shape=(n_chans, n_samples), dtype=dtype)
        sample = 0
        for data_file, info in df_to_read.iterrows():
            file_from = info.loc["read_from"]
            file_to = info.loc["read_to"]
            n_samples_file = info.loc["n_samples_read"]
            data_byte_start = info.loc["data_byte_start"]
            mult = np.array([info.loc[B423E_MULT[idx]] for idx in chan_indices])
            add = np.array([info.loc[B423E_ADD[idx]] for idx in chan_indices])

            messages.append(f"{data_file}: Reading samples {file_from} to {file_to}")
            logger.debug(f"{data_file}: Reading samples {file_from} to {file_to}")
            byte_read_start = data_byte_start + file_from * self.record_bytes
            n_bytes_to_read = n_samples_file * self.record_bytes
            with (dir_path / data_file).open("rb") as f:
                f.seek(byte_read_start, 0)
                data_bytes = f.read(n_bytes_to_read)

            data_read = self._parse_records(metadata.chans, data_bytes)
            data_read = (data_read[chan_indices] * mult[:, None]) + add[:, None]
            data[:, sample : sample + n_samples_file] = data_read
            sample = sample + n_samples_file
        metadata = self._adjust_metadata_chans(metadata, chans)
        metadata = self._get_return_metadata(metadata, read_from, read_to)
        messages.append(f"From sample, time: {read_from}, {str(metadata.first_time)}")
        messages.append(f"To sample, time: {read_to}, {str(metadata.last_time)}")
        metadata.history.add_record(self._get_record(messages))
        logger.info(f"Data successfully read from {dir_path}")
        return TimeData(metadata, data)

    def _get_chans(
        self, dir_path: Path, metadata: TimeMetadataMerge
    ) -> Tuple[List[str], List[int]]:
        """
        Get the channels to read and their indices

        This is mainly used because it is likely that not all the channels are
        used or recording anything worthwhile

        Parameters
        ----------
        dir_path : Path
            The directory path
        metadata : TimeMetadataMerge
            The metadata for the recording

        Returns
        -------
        Tuple[List[str], List[int]]
            The channels and the channel indices

        Raises
        ------
        TimeDataReadError
            If any of limit_chans are not in the metadata.chans
        """
        from resistics.errors import TimeDataReadError

        if self.limit_chans is None:
            return metadata.chans, list(range(metadata.n_chans))
        chk = set(self.limit_chans) - set(metadata.chans)
        if len(chk) > 0:
            raise TimeDataReadError(
                dir_path, f"Chans {chk} not in metadata {metadata.chans}"
            )
        indices = [metadata.chans.index(x) for x in self.limit_chans]
        return self.limit_chans, indices

    def _adjust_metadata_chans(
        self, metadata: TimeMetadataMerge, chans: List[str]
    ) -> TimeMetadataMerge:
        """Adjust the channels in the metadata"""
        metadata.chans_metadata = {c: metadata.chans_metadata[c] for c in chans}
        metadata.chans = chans
        metadata.n_chans = len(chans)
        return metadata

    def scale_data(self, time_data: TimeData) -> TimeData:
        """
        Get data scaled to physical values

        resistics uses field units, meaning physical samples will return the
        following:

        - Electrical channels in mV/km
        - Magnetic channels in mV
        - To get magnetic fields in nT, calibration needs to be performed

        Notes
        -----
        When Lemi data is read in, scaling in the headers is applied. Therefore,
        the magnetic channels is in mV with gain applied and the electric
        channels are in uV (microvolts). To complete the scaling to field units,
        the below additional corrections need to be applied.

        Electric channels need to divided by 1000 along with dipole length
        division in km (east-west spacing and north-south spacing) to return
        mV/km.

        Magnetic channels need to be divided by the internal gain value which
        should be set in the metadata

        Parameters
        ----------
        time_data : TimeData
            Input time data

        Returns
        -------
        TimeData
            Time data in field units
        """
        logger.info("Applying scaling to data to give field units")
        messages = ["Scaling raw data to physical units"]
        for chan in time_data.metadata.chans:
            chan_metadata = time_data.metadata.chans_metadata[chan]
            time_data[chan] = time_data[chan] / 1000.0
            messages.append(f"Dividing chan {chan} by 1000 to convert from uV to mV")
            dipole_dist_km = chan_metadata.dipole_dist / 1_000
            time_data[chan] = time_data[chan] / dipole_dist_km
            messages.append(f"Dividing {chan} by dipole length {dipole_dist_km} km")
        record = self._get_record(messages)
        time_data.metadata.history.add_record(record)
        return time_data
