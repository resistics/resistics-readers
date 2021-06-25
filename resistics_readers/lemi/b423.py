"""
Module for Lemi B423 data
Lemi B423 always records channels in the following order

- Hx, Hy, Hz, Ex, Ey

The Lemi B423 binary files are constructed from a 1024 text header followed
by repeating records with the following definitions (PPS is short for
deviation from PPS and PLL is short for PLL accuracy):

SECOND_TIMESTAMP, SAMPLE_NUM [0-FS], HX, HY, HZ, EX, EY, PPS, PLL

These are interpreted to have byte types

L, H, l, l, l, l, l, h, h
"""
from loguru import logger
from typing import List, Dict, Optional
from pathlib import Path
import struct
import numpy as np
import pandas as pd
from resistics.sampling import RSDateTime
from resistics.time import TimeMetadata, TimeData, TimeReader

from resistics_readers.multifile import validate_consistency, validate_continuous
from resistics_readers.multifile import TimeMetadataSingle, TimeMetadataMerge

B423_CHANS = ["Hx", "Hy", "Hz", "Ex", "Ey"]
B423_CHAN_TYPES = {
    "E1": "electric",
    "E2": "electric",
    "E3": "electric",
    "E4": "electric",
    "Ex": "electric",
    "Ey": "electric",
    "Hx": "magnetic",
    "Hy": "magnetic",
    "Hz": "magnetic",
}
B423_RECORD_BYTES = 30
B423_HEADER_LENGTH = 1024
B423_MULT = {"Hx": "Kmx", "Hy": "Kmy", "Hz": "Kmz", "Ex": "Ke1", "Ey": "Ke2"}
B423_ADD = {"Hx": "Ax", "Hy": "Ay", "Hz": "Az", "Ex": "Ae1", "Ey": "Ae2"}


class TimeMetadataB423(TimeMetadataSingle):
    """This is an extension of TimeMetadataSingle for a single B423 file"""

    data_byte_start: int
    """The byte offset from the beginning of the file to the start of the data"""
    scalings: Dict[str, float]
    """Scalings in the B423 ASCII header"""


def make_subdir_B423_metadata(
    dir_path: Path,
    fs: float,
    hx_serial: int = 0,
    hy_serial: int = 0,
    hz_serial: int = 0,
    h_gain: int = 1,
    dx: float = 1,
    dy: float = 1,
    folders: Optional[List[str]] = None,
) -> None:
    """
    Construct B423 headers for sub directories of a folder

    Parameters
    ----------
    dir_path : Path
        The path to the folder
    fs : float
        The sampling frequency, Hz
    hx_serial : str, optional
        The x direction magnetic serial, used for calibration
    hy_serial : str, optional
        The y direction magnetic serial, used for calibration
    hz_serial : str, optional
        The z direction magnetic serial, used for calibration
    h_gain : int
        Any gain on the magnetic channels which will need to be removed
    dx : float, optional
        Distance between x electrodes
    dy : float, optional
        Distance between y electrodes
    folders : List, optional
        An optional list of subfolders, by default None. If None, all the
        subfolders will be processed
    """
    from resistics.common import dir_subdirs

    if folders is None:
        folder_paths = dir_subdirs(dir_path)
    else:
        folder_paths = [dir_path / folder for folder in folders]
    for folder in folder_paths:
        make_B423_metadata(folder, fs, hx_serial, hy_serial, hz_serial, h_gain, dx, dy)


def make_B423_metadata(
    dir_path: Path,
    fs: float,
    hx_serial: int = 0,
    hy_serial: int = 0,
    hz_serial: int = 0,
    h_gain: int = 1,
    dx: float = 1,
    dy: float = 1,
) -> None:
    """
    Read a single B423 measurement directory, construct and write out metadata

    Parameters
    ----------
    dir_path : Path
        The path to the measurement
    fs : float
        The sampling frequency, Hz
    hx_serial : str, optional
        The x direction magnetic serial, used for calibration
    hy_serial : str, optional
        The y direction magnetic serial, used for calibration
    hz_serial : str, optional
        The z direction magnetic serial, used for calibration
    h_gain : int
        Any gain on the magnetic channels which will need to be removed
    dx : float, optional
        Distance between x electrodes
    dy : float, optional
        Distance between y electrodes
    """
    metadata_list = _get_B423_metadata_list(dir_path, fs)
    validate_consistency(dir_path, metadata_list)
    validate_continuous(dir_path, metadata_list)
    metadata = _merge_metadata(
        metadata_list, hx_serial, hy_serial, hz_serial, h_gain, dx, dy
    )
    logger.info(f"Writing metadata in {dir_path}")
    metadata.write(dir_path / "metadata.json")


def _get_B423_metadata_list(dir_path: Path, fs: float) -> List[TimeMetadataB423]:
    """
    Get list of TimeMetadataB423, one for each data file

    Parameters
    ----------
    dir_path : Path
        The data path
    fs : float
        The sampling frequency, Hz

    Returns
    -------
    List[TimeMetadataB423]
        List of TimeMetadata
    """
    data_paths = list(dir_path.glob("*.B423"))
    metadata_list = []
    for data_path in data_paths:
        logger.debug(f"Reading data file {data_path}")
        metadata_B423 = _read_B423_headers(data_path, fs)
        metadata_list.append(metadata_B423)
    return metadata_list


def _read_B423_headers(
    data_path: Path,
    fs: float,
    data_byte_offset: Optional[int] = None,
    record_bytes: Optional[int] = None,
    chans: Optional[List[str]] = None,
) -> TimeMetadataB423:
    """
    Get metadata from single B423 file headers

    Parameters
    ----------
    data_path : Path
        The data path to the file
    fs : float
        The sampling frequency, Hz
    data_byte_offset : int, optional
        The number of bytes to the start of the data, by default None
    record_bytes : int, optional
        The size of a single recors, by default None
    chans : List[str]
        The channels in the data

    Returns
    -------
    TimeMetadataB423
        Metadata for the B423 file

    Raises
    ------
    TimeDataReadError
        If number of samples is non-integer
    """
    from resistics.errors import TimeDataReadError
    from resistics.sampling import to_n_samples

    if data_byte_offset is None:
        data_byte_offset = B423_HEADER_LENGTH
    if record_bytes is None:
        record_bytes = B423_RECORD_BYTES
    if chans is None:
        chans = B423_CHANS

    name = data_path.name
    f_size = data_path.stat().st_size
    time_dict = {"fs": fs, "data_file": name, "data_byte_start": data_byte_offset}

    n_samples = (f_size - data_byte_offset) / record_bytes
    if not n_samples.is_integer():
        TimeDataReadError(data_path, f"Non-integer number of samples {n_samples}")
    time_dict["n_samples"] = int(n_samples)

    f = data_path.open("rb")
    ascii_bytes = f.read(data_byte_offset)
    ascii_metadata = _read_B423_ascii_headers(ascii_bytes)
    time_dict["northing"] = ascii_metadata.pop("Lat")
    time_dict["easting"] = ascii_metadata.pop("Lon")
    time_dict["elevation"] = ascii_metadata.pop("Alt")
    time_dict["scalings"] = ascii_metadata

    time_dict["first_time"] = _get_B423_time(f.read(6), fs)
    f.seek(f_size - record_bytes, 0)
    time_dict["last_time"] = _get_B423_time(f.read(6), fs)
    if n_samples != to_n_samples(time_dict["last_time"] - time_dict["first_time"], fs):
        raise TimeDataReadError(data_path, "Number of samples mismatch")

    time_dict["chans"] = chans
    time_dict["chans_metadata"] = {}
    for chan in chans:
        time_dict["chans_metadata"][chan] = {
            "name": chan,
            "data_files": [name],
            "chan_type": B423_CHAN_TYPES[chan],
        }
    return TimeMetadataB423(**time_dict)


def _read_B423_ascii_headers(metadata_bytes: bytes) -> Dict[str, float]:
    """
    Parse the ASCII part of the B423 file

    Parameters
    ----------
    metadata_bytes : bytes
        The bytes string with the metadata

    Returns
    -------
    Dict[str, float]
        Parsed metadata which includes scalings and location information
    """
    metadata_lines = metadata_bytes.decode().split("\r\n")
    metadata_lines = [x.replace("%", "") for x in metadata_lines]
    # scaling information
    metadata = [x.split(" = ") for x in metadata_lines if "=" in x]
    metadata = {x[0].strip(): float(x[1].strip()) for x in metadata}
    # loxcation information
    location = [x for x in metadata_lines if ("Lat" in x or "Lon" in x or "Alt" in x)]
    location_dict = {x[0:3]: x[3:].split(",")[0] for x in location}
    location_dict = {k: float(v.strip()) for k, v in location_dict.items()}
    metadata.update(location_dict)
    return metadata


def _get_B423_time(time_bytes: bytes, fs: float) -> RSDateTime:
    """Parse bytes to a RSDateTime"""
    from datetime import datetime
    from resistics.sampling import to_datetime

    timestamp = struct.unpack("L", time_bytes[0:4])[0]
    n_sample = struct.unpack("H", time_bytes[4:])[0]
    return to_datetime(datetime.utcfromtimestamp(timestamp + (n_sample / fs)))


def _merge_metadata(
    metadata_list: List[TimeMetadataB423],
    hx_serial: int = 0,
    hy_serial: int = 0,
    hz_serial: int = 0,
    h_gain: int = 1,
    dx: float = 1,
    dy: float = 1,
) -> TimeMetadata:
    """Merge the metadata list into a TimeMetadata"""
    metadata = TimeMetadata(**metadata_list[0].dict())
    metadata.first_time = min([x.first_time for x in metadata_list])
    metadata.last_time = max([x.last_time for x in metadata_list])
    metadata.n_samples = np.sum([x.n_samples for x in metadata_list])

    # channel headers
    data_files = [x.data_file for x in metadata_list]
    serials = {"Hx": hx_serial, "Hy": hy_serial, "Hz": hz_serial}
    dipoles = {"Ex": dx, "Ey": dy}
    for chan in metadata.chans:
        metadata.chans_metadata[chan].data_files = data_files
        if metadata.chans_metadata[chan].magnetic():
            metadata.chans_metadata[chan].gain1 = h_gain
            metadata.chans_metadata[chan].serial = serials[chan]
        if metadata.chans_metadata[chan].electric():
            metadata.chans_metadata[chan].dipole_dist = dipoles[chan]
    return metadata


class TimeReaderB423(TimeReader):
    """
    Data reader for Lemi B423 data

    There is no separate metadata file for Lemi B423 data detailing the sampling
    frequency, the number of samples, the sensors etc.. Unfortunately, such a
    metadata file is a pre-requisite for resistics. There are helper methods to
    make one.

    In situations where a Lemi B423 dataset is recorded in multiple files, it is
    required that the recording is continuous.

    Other important notes about Lemi B423 files

    - 1024 bytes of ASCII metadata in the data file with scaling information
    - Lemi B423 raw measurement data is signed long integer format

    Important points about scalings

    - Raw data is integer counts for electric and magnetic channels
    - Scalings in B423 files convert electric channels to uV (microvolt)
    - Scalings in B423 files convert magnetic channels to millivolts
    - Scaling for the magnetic channels in B423 files leaves internal gain on
    - Internal gain should be specified when creating metadata

    If apply_scaling is False, data will be returned in:

    - microvolts for the electric channels
    - millivolts for the magnetic with the gain applied

    Which is equivalent to applying the scalings in the B423 headers

    With apply_scaling True, the following additional scaling will be applied:

    - Electric channels converted to mV
    - Dipole length corrections are applied to electric channels
    - Magnetic channel gains are removed

    .. note::

        For more information about Lemi B423 format, please see:
        http://lemisensors.com/?p=485
    """

    extension = ".B423"
    record_bytes: int = B423_RECORD_BYTES

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
            If the channels are not correct for B423
        TimeDataReadError
            If not all data files exist
        TimeDataReadError
            If extensions do not match
        """
        from resistics.errors import MetadataReadError, TimeDataReadError
        from resistics_readers.multifile import validate_consistency
        from resistics_readers.multifile import validate_continuous

        metadata = TimeMetadata.parse_file(dir_path / "metadata.json")
        if metadata.chans != B423_CHANS:
            raise MetadataReadError(
                dir_path, f"Channels {metadata.chans} != B423 chans {B423_CHANS}"
            )
        metadata_list = _get_B423_metadata_list(dir_path, metadata.fs)
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

    def _generate_table(self, metadata_list: List[TimeMetadataB423]) -> pd.DataFrame:
        """
        Generate a table mapping RAW file to  first time, last time, number of
        samples, data byte offsets and scalings

        Parameters
        ----------
        metadata_list : List[TimeMetadataXTR]
            List of TimeMetadataXTR, one for each XTR/RAW file combination

        Returns
        -------
        pd.DataFrame
            The table mapping data file to various properties
        """
        from resistics_readers.multifile import add_cumulative_samples

        df = pd.DataFrame()
        df["data_file"] = [x.data_file for x in metadata_list]
        df["first_time"] = [x.first_time for x in metadata_list]
        df["last_time"] = [x.last_time for x in metadata_list]
        df["n_samples"] = [x.n_samples for x in metadata_list]
        df["data_byte_start"] = [x.data_byte_start for x in metadata_list]
        # save scaling information
        scalings = metadata_list[0].scalings.keys()
        for scaling in scalings:
            df[scaling] = [x.scalings[scaling] for x in metadata_list]
        df = df.sort_values("first_time")
        df = df.set_index("data_file")
        return add_cumulative_samples(df)

    def read_data(
        self, dir_path: Path, metadata: TimeMetadata, read_from: int, read_to: int
    ) -> TimeData:
        """
        Get data from data files

        Lemi B423 data always has five channels, in order Hx, Hy, Hz, Ex, Ey.
        The raw data is integer counts. However, additional scalings from the
        B423 files are applied to give:

        - microvolts for the electric channels
        - millivolts for the magnetic with the gain applied

        The scalings are as follows:

        - Hx = (Hx * Kmx) + Ax
        - Hx = (Hy * Kmy) + Ay
        - Hx = (Hz * Kmz) + Az
        - Ex = (Ex * Ke1) + Ae1
        - Ey = (Ey * Ke2) + Ae2

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

        messages = [f"Reading raw data from {dir_path}"]
        messages.append(f"Sampling rate {metadata.fs} Hz")
        # loop over B423 files and read data
        data_table = pd.DataFrame(data=metadata.data_table)
        df_to_read = samples_to_sources(dir_path, data_table, read_from, read_to)
        data = np.empty(shape=(metadata.n_chans, n_samples), dtype=dtype)
        sample = 0
        for data_file, info in df_to_read.iterrows():
            file_from = info.loc["read_from"]
            file_to = info.loc["read_to"]
            n_samples_file = info.loc["n_samples_read"]
            data_byte_start = info.loc["data_byte_start"]
            mult = np.array([info.loc[B423_MULT[chan]] for chan in metadata.chans])
            add = np.array([info.loc[B423_ADD[chan]] for chan in metadata.chans])

            messages.append(f"{data_file}: Reading samples {file_from} to {file_to}")
            logger.debug(f"{data_file}: Reading samples {file_from} to {file_to}")
            byte_read_start = data_byte_start + file_from * self.record_bytes
            n_bytes_to_read = n_samples_file * self.record_bytes
            with (dir_path / data_file).open("rb") as f:
                f.seek(byte_read_start, 0)
                data_bytes = f.read(n_bytes_to_read)

            data_read = self._parse_records(metadata.chans, data_bytes)
            data_read = (data_read * mult[:, None]) + add[:, None]
            data[:, sample : sample + n_samples_file] = data_read
            sample = sample + n_samples_file
        metadata = self._get_return_metadata(metadata, read_from, read_to)
        messages.append(f"From sample, time: {read_from}, {str(metadata.first_time)}")
        messages.append(f"To sample, time: {read_to}, {str(metadata.last_time)}")
        metadata.history.add_record(self._get_record(messages))
        logger.info(f"Data successfully read from {dir_path}")
        return TimeData(metadata, data)

    def _parse_records(self, chans: List[str], data_bytes: bytes) -> np.ndarray:
        """
        Read a number of B423 records from bytes

        Records are blocks that repeat like:

        SECOND_TIMESTAMP, SAMPLE_NUM [0-FS], HX, HY, HZ, EX, EY, PPS, PLL

        These are interpreted to have byte types

        L, H, l, l, l, l, l, h, h

        Parameters
        ----------
        chans : List[str]
            The channels
        data_bytes : bytes
            The bytes string

        Returns
        -------
        np.ndarray
            Data array of size n_chans x n_records
        """
        n_chans = len(chans)
        n_bytes = len(data_bytes)
        record_format = f"=LH{n_chans}l2h"
        record_size = struct.calcsize(record_format)
        logger.debug(
            f"Unpacking {n_bytes} bytes, format {record_format}, size {record_size}"
        )
        return np.array(
            [x[2 : 2 + n_chans] for x in struct.iter_unpack(record_format, data_bytes)],
            dtype=np.float32,
        ).T

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
            if chan_metadata.electric():
                time_data[chan] = time_data[chan] / 1000.0
                messages.append(
                    f"Dividing chan {chan} by 1000 to convert from uV to mV"
                )
                dipole_dist_km = chan_metadata.dipole_dist / 1_000
                time_data[chan] = time_data[chan] / dipole_dist_km
                messages.append(f"Dividing {chan} by dipole length {dipole_dist_km} km")
            if chan_metadata.magnetic():
                gain = chan_metadata.gain1
                time_data[chan] = time_data[chan] / gain
                messages.append(f"Dividing chan {chan} by {gain} to remove gain")
        record = self._get_record(messages)
        time_data.metadata.history.add_record(record)
        return time_data
