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


def make_subdir_b423_metadata(
    dir_path: str,
    fs: float,
    hx_sensor: int = 0,
    hy_sensor: int = 0,
    hz_sensor: int = 0,
    h_gain: int = 1,
    dx: float = 1,
    dy: float = 1,
    folders: Optional[List[str]] = None,
) -> None:
    """
    Construct B423 headers for sub directories of a folder

    Parameters
    ----------
    dir_path : str
        The path to the folder
    fs : float
        The sampling frequency, Hz
    hx_sensor : str, optional
        The x direction magnetic sensor, used for calibration
    hy_sensor : str, optional
        The y direction magnetic sensor, used for calibration
    hz_sensor : str, optional
        The z direction magnetic sensor, used for calibration
    h_gain : int
        Any gain on the magnetic channels which will need to be removed
    dx : float, optional
        Distance between x electrodes
    dy : float, optional
        Distance between y electrodes
    folders : List, optional
        An optional list of subfolders
    """
    from resistics.common import dir_subdirs

    if folders is None:
        folders = dir_subdirs(dir_path)
    else:
        folders = [dir_path / folder for folder in folders]
    for folder in folders:
        make_b423_metadata(folder, fs, hx_sensor, hy_sensor, hz_sensor, h_gain, dx, dy)


def make_b423_metadata(
    dir_path: Path,
    fs: float,
    hx_sensor: int = 0,
    hy_sensor: int = 0,
    hz_sensor: int = 0,
    h_gain: int = 1,
    dx: float = 1,
    dy: float = 1,
) -> TimeMetadata:
    """
    Read a single B423 measurement directory and construct headers

    Parameters
    ----------
    dir_path : str
        The path to the measurement
    fs : float
        The sampling frequency, Hz
    hx_sensor : str, optional
        The x direction magnetic sensor, used for calibration
    hy_sensor : str, optional
        The y direction magnetic sensor, used for calibration
    hz_sensor : str, optional
        The z direction magnetic sensor, used for calibration
    h_gain : int
        Any gain on the magnetic channels which will need to be removed
    dx : float, optional
        Distance between x electrodes
    dy : float, optional
        Distance between y electrodes
    """
    metadata_list = _get_b423_metadata_list(dir_path, fs)
    validate_consistency(dir_path, metadata_list)
    validate_continuous(dir_path, metadata_list)
    metadata = _merge_metadata(
        metadata_list, hx_sensor, hy_sensor, hz_sensor, h_gain, dx, dy
    )
    logger.info(f"Writing metadata in {dir_path}")
    metadata.write(dir_path / "metadata.json")


def _get_b423_metadata_list(dir_path: Path, fs: float) -> List[TimeMetadataB423]:
    """
    Get list of TimeMetadataB423 for each data file

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
        metadata_b423 = _read_b423_headers(data_path, fs)
        metadata_list.append(metadata_b423)
    return metadata_list


def _read_b423_headers(
    data_path: str,
    fs: float,
    data_byte_offset: Optional[int] = None,
    record_bytes: Optional[int] = None,
) -> TimeMetadataB423:
    """
    Get metadata from single B423 file headers

    Parameters
    ----------
    data_path : str
        The data path to the file
    fs : float
        The sampling frequency, Hz
    data_byte_offset : int, optional
        The number of bytes to the start of the data, by default None
    record_bytes : int, optional
        The size of a single recors, by default None

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

    name = data_path.name
    f_size = data_path.stat().st_size
    time_dict = {"fs": fs, "data_file": name, "data_byte_start": data_byte_offset}

    n_samples = (f_size - data_byte_offset) / record_bytes
    if not n_samples.is_integer():
        TimeDataReadError(data_path, f"Non-integer number of samples {n_samples}")
    time_dict["n_samples"] = int(n_samples)

    f = data_path.open("rb")
    ascii_bytes = f.read(data_byte_offset)
    ascii_metadata = _read_b423_ascii_headers(ascii_bytes)
    time_dict["northing"] = ascii_metadata.pop("Lat")
    time_dict["easting"] = ascii_metadata.pop("Lon")
    time_dict["elevation"] = ascii_metadata.pop("Alt")
    time_dict["scalings"] = ascii_metadata

    time_dict["first_time"] = _get_b423_time(f.read(6), fs)
    f.seek(f_size - record_bytes, 0)
    time_dict["last_time"] = _get_b423_time(f.read(6), fs)
    if n_samples != to_n_samples(time_dict["last_time"] - time_dict["first_time"], fs):
        raise TimeDataReadError(data_path, "Number of samples mismatch")

    time_dict["chans"] = B423_CHANS
    time_dict["chans_metadata"] = {}
    for chan in B423_CHANS:
        time_dict["chans_metadata"][chan] = {"data_files": [name]}
    return TimeMetadataB423(**time_dict)


def _read_b423_ascii_headers(metadata_bytes: bytes) -> Dict[str, float]:
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
    location = {x[0:3]: x[3:].split(",")[0] for x in location}
    location = {k: float(v.strip()) for k, v in location.items()}
    metadata.update(location)
    return metadata


def _get_b423_time(time_bytes: bytes, fs: float) -> RSDateTime:
    """Parse bytes to a RSDateTime"""
    from datetime import datetime
    from resistics.sampling import to_datetime

    timestamp = struct.unpack("L", time_bytes[0:4])[0]
    n_sample = struct.unpack("H", time_bytes[4:])[0]
    return to_datetime(datetime.utcfromtimestamp(timestamp + (n_sample / fs)))


def _merge_metadata(
    metadata_list: List[TimeMetadataB423],
    hx_sensor: int = 0,
    hy_sensor: int = 0,
    hz_sensor: int = 0,
    h_gain: int = 1,
    dx: float = 1,
    dy: float = 1,
) -> TimeMetadata:
    """Merge the metadata list into a TimeMetadata"""
    from resistics.common import is_magnetic

    metadata = TimeMetadata(**metadata_list[0].dict())
    metadata.first_time = min([x.first_time for x in metadata_list])
    metadata.last_time = max([x.last_time for x in metadata_list])
    metadata.n_samples = np.sum([x.n_samples for x in metadata_list])

    # channel headers
    data_files = [x.data_file for x in metadata_list]
    sensors = {"Hx": hx_sensor, "Hy": hy_sensor, "Hz": hz_sensor, "Ex": "0", "Ey": "0"}
    posX2 = {"Hx": 1, "Hy": 1, "Hz": 1, "Ex": dx, "Ey": 1}
    posY2 = {"Hx": 1, "Hy": 1, "Hz": 1, "Ex": 1, "Ey": dy}

    for chan in metadata.chans:
        metadata.chans_metadata[chan].data_files = data_files
        metadata.chans_metadata[chan].gain1 = h_gain if is_magnetic(chan) else 1
        metadata.chans_metadata[chan].dx = posX2[chan]
        metadata.chans_metadata[chan].dy = posY2[chan]
        metadata.chans_metadata[chan].serial = sensors[chan]
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

    Which is equivalent to still applying the scalings in the B423 headers

    With apply_scaling True, the following additional scaling will be applied:

    - Dipole length corrections are applied to electric channels
    - Magnetic channel gains are removed

    .. notes::

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
        metadata_list = _get_b423_metadata_list(dir_path, metadata.fs)
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
        from resistics_readers.multifile import samples_to_files

        dtype = np.float32
        n_samples = read_to - read_from + 1

        messages = [f"Reading raw data from {dir_path}"]
        messages.append(f"Sampling rate {metadata.fs} Hz")
        # loop over RAW files and read data
        df_to_read = samples_to_files(dir_path, metadata, read_from, read_to)
        data = np.empty(shape=(metadata.n_chans, n_samples), dtype=dtype)
        sample = 0
        for data_file, info in df_to_read.iterrows():
            file_from = info.loc["read_from"]
            file_to = info.loc["read_to"]
            n_samples_file = info.loc["n_samples_file"]
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
            sample = sample + n_samples_file  # get ready for the next data read
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
            [x[2:7] for x in struct.iter_unpack(record_format, data_bytes)],
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
        from resistics.common import is_electric, is_magnetic

        logger.info("Applying scaling to data to give field units")
        messages = ["Scaling raw data to physical units"]
        for chan in time_data.metadata.chans:
            chan_metadata = time_data.metadata.chans_metadata[chan]
            if is_electric(chan):
                time_data[chan] = time_data[chan] / 1000.0
                messages.append(
                    f"Dividing chan {chan} by 1000 to convert from uV to mV"
                )
            if chan == "Ex":
                dx_km = chan_metadata.dx / 1000
                time_data[chan] = time_data[chan] / dx_km
                messages.append(f"Dividing {chan} by dipole length {dx_km:.6f} km")
            if chan == "Ey":
                dy_km = chan_metadata.dy / 1000
                time_data[chan] = time_data[chan] / dy_km
                messages.append(f"Dividing {chan} by dipole length {dy_km:.6f} km")
            if is_magnetic(chan):
                gain = time_data.metadata.chans_metadata[chan].gain1
                time_data[chan] = time_data[chan] / gain
                messages.append(f"Dividing chan {chan} by {gain} to remove gain")
        record = self._get_record(messages)
        time_data.metadata.history.add_record(record)
        return time_data


# def folderB423EHeaders(
#     folderpath: str,
#     sampleFreq: float,
#     ex: str = "E1",
#     ey: str = "E2",
#     dx: float = 1,
#     dy: float = 1,
#     folders: List = [],
# ) -> None:
#     """Construct B423E headers for subfolders of a folder

#     Parameters
#     ----------
#     folderpath : str
#         The path to the folder
#     sampleFreq : float
#         The sampling frequency of the data
#     ex : str, optional
#         The channel E1, E2, E3 or E4 in the data that represents Ex. Default E1.
#     ey : str, optional
#         The channel E1, E2, E3 or E4 in the data that represents Ey. Default E2.
#     dx : float, optional
#         Distance between x electrodes
#     dy : float, optional
#         Distance between y electrodes
#     folder : List, optional
#         An optional list of subfolders
#     """
#     if len(folders) == 0:
#         folders = [f.path for f in os.scandir(folderpath) if f.is_dir()]
#     # now construct headers for each folder
#     for folder in folders:
#         measB423EHeaders(folder, sampleFreq, ex=ex, ey=ey, dx=dx, dy=dy)


# def measB423EHeaders(
#     datapath: str,
#     sampleFreq: float,
#     ex: str = "E1",
#     ey: str = "E2",
#     dx: float = 1,
#     dy: float = 1,
# ) -> None:
#     """Read a single B423 measurement directory and construct headers

#     Parameters
#     ----------
#     site : str
#         The path to the site
#     sampleFreq : float
#         The sampling frequency of the data
#     ex : str, optional
#         The channel E1, E2, E3 or E4 in the data that represents Ex. Default E1.
#     ey : str, optional
#         The channel E1, E2, E3 or E4 in the data that represents Ey. Default E2.
#     dx : float, optional
#         Distance between x electrodes
#     dy : float, optional
#         Distance between y electrodes
#     """
#     from resistics.common.print import generalPrint, warningPrint, errorPrint
#     from resistics.time.writer import TimeWriter

#     dataFiles = glob.glob(os.path.join(datapath, "*.B423"))
#     dataFilenames = [os.path.basename(dFile) for dFile in dataFiles]
#     starts = []
#     stops = []
#     cumSamples = 0
#     for idx, dFile in enumerate(dataFiles):
#         generalPrint("constructB423EHeaders", "Reading data file {}".format(dFile))
#         dataHeaders, firstDatetime, lastDatetime, numSamples = readB423Params(
#             dFile, sampleFreq, 1024, 26
#         )
#         print(dataHeaders)
#         generalPrint(
#             "constructB423EHeaders",
#             "start time = {}, end time = {}".format(firstDatetime, lastDatetime),
#         )
#         generalPrint(
#             "constructB423EHeaders", "number of samples = {}".format(numSamples)
#         )
#         cumSamples += numSamples
#         starts.append(firstDatetime)
#         stops.append(lastDatetime)
#     # now need to search for any missing data
#     sampleTime = timedelta(seconds=1.0 / sampleFreq)
#     # sort by start times
#     sortIndices = sorted(list(range(len(starts))), key=lambda k: starts[k])
#     check = True
#     for i in range(1, len(dataFiles)):
#         # get the stop time of the previous dataset
#         stopTimePrev = stops[sortIndices[i - 1]]
#         startTimeNow = starts[sortIndices[i]]
#         if startTimeNow != stopTimePrev + sampleTime:
#             warningPrint(
#                 "constructB423EHeaders", "There is a gap between the datafiles"
#             )
#             warningPrint(
#                 "constructB423EHeaders",
#                 "Please separate out datasets with gaps into separate folders",
#             )
#             warningPrint("constructB423EHeaders", "Gap found between datafiles:")
#             warningPrint(
#                 "constructB423EHeaders", "1. {}".format(dataFiles[sortIndices[i - 1]])
#             )
#             warningPrint(
#                 "constructB423EHeaders", "2. {}".format(dataFiles[sortIndices[i]])
#             )
#             check = False
#     # if did not pass check, then exit
#     if not check:
#         errorPrint(
#             "constructB423EHeaders",
#             "All data for a single recording must be continuous.",
#             quitrun=True,
#         )

#     # time of first and last sample
#     datetimeStart = starts[sortIndices[0]]
#     datetimeStop = stops[sortIndices[-1]]

#     # global headers
#     globalHeaders = {
#         "sample_freq": sampleFreq,
#         "num_samples": cumSamples,
#         "start_time": datetimeStart.strftime("%H:%M:%S.%f"),
#         "start_date": datetimeStart.strftime("%Y-%m-%d"),
#         "stop_time": datetimeStop.strftime("%H:%M:%S.%f"),
#         "stop_date": datetimeStop.strftime("%Y-%m-%d"),
#         "meas_channels": 4,
#     }
#     writer = TimeWriter()
#     globalHeaders = writer.setGlobalHeadersFromKeywords({}, globalHeaders)

#     # channel headers
#     channels = ["E1", "E2", "E3", "E4"]
#     chanMap = {"E1": 0, "E2": 1, "E3": 2, "E4": 3}
#     sensors = {"E1": "0", "E2": "0", "E3": "0", "E4": "0"}
#     posX2 = {"E1": 1, "E2": 1, "E3": 1, "E4": 1}
#     posY2 = {"E1": 1, "E2": 1, "E3": 1, "E4": 1}
#     posX2[ex] = dx
#     posY2[ey] = dy

#     chanHeaders = []
#     for chan in channels:
#         # sensor serial number
#         cHeader = dict(globalHeaders)
#         cHeader["ats_data_file"] = ", ".join(dataFilenames)
#         if ex == chan:
#             cHeader["channel_type"] = "Ex"
#         elif ey == chan:
#             cHeader["channel_type"] = "Ey"
#         else:
#             cHeader["channel_type"] = chan
#         cHeader["scaling_applied"] = False
#         cHeader["ts_lsb"] = 1
#         cHeader["gain_stage1"] = 1
#         cHeader["gain_stage2"] = 1
#         cHeader["hchopper"] = 0
#         cHeader["echopper"] = 0
#         cHeader["pos_x1"] = 0
#         cHeader["pos_x2"] = posX2[chan]
#         cHeader["pos_y1"] = 0
#         cHeader["pos_y2"] = posY2[chan]
#         cHeader["pos_z1"] = 0
#         cHeader["pos_z2"] = 1
#         cHeader["sensor_sernum"] = sensors[chan]
#         chanHeaders.append(cHeader)
#     chanHeaders = writer.setChanHeadersFromKeywords(chanHeaders, {})
#     writer.setOutPath(datapath)
#     writer.writeHeaders(
#         globalHeaders, channels, chanMap, chanHeaders, rename=False, ext="h423E"
#     )


# class TimeReaderLemiB423E(TimeReaderLemiB423):
#     """Data reader for Lemi B423E data

#     Lemi B423E data has the following characteristics:

#     - 1024 bytes of ASCII headers in the data file with basic scaling information
#     - There is no separate header file for Lemi B423E data. No information for number of samples, sampling rate etc
#     - Header files need to be constructed before Lemi B423E data can be read in by resistics. There are helper methods to do this.
#     - Lemi B423 raw measurement data is signed long integer format
#     - Getting unscaled samples returns data with unit count for electric fields.
#     - Optionally, a scaling can be applied for unscaled samples which returns electric fields in microvolt.

#     In situations where a Lemi B423E dataset is recorded in multiple files, it is required that the recording is continuous.

#     Attributes
#     ----------
#     recChannels : Dict
#         Channels in each data file
#     dtype : np.float32
#         The data type
#     numHeaderFiles : int
#         The number of header files
#     numDataFiles : int
#         The number of data files

#     Methods
#     -------
#     setParameters()
#         Set parameters specific to a data format
#     getPhysicalSamples(**kwargs)
#         Get data in physical units
#     getScalars(paramsDict)
#         Get the scalars for each channel as given in the data files
#     """

#     def setParameters(self) -> None:
#         """Set some data reader parameters for reading Lemi B423E data"""
#         # get a list of the header and data files in the folder
#         self.headerExt = "h423E"
#         self.headerF = glob.glob(
#             os.path.join(self.dataPath, "*.{}".format(self.headerExt))
#         )
#         self.dataF = glob.glob(os.path.join(self.dataPath, "*.B423"))
#         # data byte information
#         self.dataByteSize = 4
#         self.recordByteSize = 26
#         self.dataByteOffset = 1024
#         # data type
#         self.dtype = np.int_
#         # get the number of data files and header files - this should be equal
#         self.numHeaderFiles: int = len(self.headerF)
#         self.numDataFiles: int = len(self.dataF)

#     def getPhysicalSamples(self, **kwargs):
#         """Get data scaled to physical values

#         resistics uses field units, meaning physical samples will return the following:

#         - Electrical channels in mV/km
#         - Magnetic channels in mV
#         - To get magnetic fields in nT, calibration needs to be performed

#         Notes
#         -----
#         Once Lemi B423E data is scaled (which optionally happens in getUnscaledSamples), the electric channels are in uV (micro volts). Therefore:

#         - Electric channels need to divided by 1000 along with dipole length division in km (east-west spacing and north-south spacing) to return mV/km.

#         Parameters
#         ----------
#         chans : List[str]
#             List of channels to return if not all are required
#         startSample : int
#             First sample to return
#         endSample : int
#             Last sample to return
#         remaverage : bool
#             Remove average from the data
#         remzeros : bool
#             Remove zeroes from the data
#         remnans: bool
#             Remove NanNs from the data

#         Returns
#         -------
#         TimeData
#             Time data object
#         """
#         # initialise chans, startSample and endSample with the whole dataset
#         options = self.parseGetDataKeywords(kwargs)
#         # get unscaled data but with gain scalings applied
#         timeData = self.getUnscaledSamples(
#             chans=options["chans"],
#             startSample=options["startSample"],
#             endSample=options["endSample"],
#             scale=True,
#         )
#         # convert to field units and divide by dipole lengths
#         for chan in options["chans"]:
#             # divide by the 1000 to convert electric channels from microvolt to millivolt
#             timeData[chan] = timeData[chan] / 1000.0
#             timeData.addComment(
#                 "Dividing channel {} by 1000 to convert microvolt to millivolt".format(
#                     chan
#                 )
#             )
#             if chan == "Ex":
#                 # multiply by 1000/self.getChanDx same as dividing by dist in km
#                 timeData[chan] = (
#                     1000.0 * timeData[chan] / self.getChanDx(chan)
#                 )
#                 timeData.addComment(
#                     "Dividing channel {} by electrode distance {} km to give mV/km".format(
#                         chan, self.getChanDx(chan) / 1000.0
#                     )
#                 )
#             if chan == "Ey":
#                 # multiply by 1000/self.getChanDy same as dividing by dist in km
#                 timeData[chan] = 1000 * timeData[chan] / self.getChanDy(chan)
#                 timeData.addComment(
#                     "Dividing channel {} by electrode distance {} km to give mV/km".format(
#                         chan, self.getChanDy(chan) / 1000.0
#                     )
#                 )

#             # if remove zeros - False by default
#             if options["remzeros"]:
#                 timeData[chan] = removeZerosChan(timeData[chan])
#             # if remove nans - False by default
#             if options["remnans"]:
#                 timeData[chan] = removeNansChan(timeData[chan])
#             # remove the average from the data - True by default
#             if options["remaverage"]:
#                 timeData[chan] = timeData[chan] - np.average(
#                     timeData[chan]
#                 )

#         # add comments
#         timeData.addComment(
#             "Remove zeros: {}, remove nans: {}, remove average: {}".format(
#                 options["remzeros"], options["remnans"], options["remaverage"]
#             )
#         )
#         return timeData

#     def getScalars(self, paramsDict: Dict) -> Dict:
#         """Returns the scalars from a parameter dictionary

#         Parameters
#         ----------
#         paramsDict : Dict
#             The parameter dictionary for a data file usually read from the headers in the file

#         Returns
#         -------
#         Dict
#             Dictionary with channels as keys and scalings as values
#         """
#         # need to get the channel orders here
#         chans = []
#         for cH in self.chanHeaders:
#             chans.append(cH["channel_type"])
#         return {
#             chans[0]: [paramsDict["Ke1"], paramsDict["Ae1"]],
#             chans[1]: [paramsDict["Ke2"], paramsDict["Ae2"]],
#             chans[2]: [paramsDict["Ke3"], paramsDict["Ae3"]],
#             chans[3]: [paramsDict["Ke4"], paramsDict["Ae4"]],
#         }
