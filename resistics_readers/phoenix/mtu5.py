"""
Data readers for Phoenix time series data

Phoenix data has multiple concurrent sampling frequencies per measurement. This
does not fit the resistics model of data very well.

There is usually one continuous recording sampling frequency and two other
discontinuous recording sampling frequencies. Sampling frequencies are
determined by the TS file and are usually as below (though they could change).

- .TS2: 24000 Hz
- .TS3: 2400 Hz
- .TS4: 150 Hz
- .TS5: 15 Hz

It is usally the highest .TS file that is the continuous recording.

.. note::

    The scaling has not been thoroughly tested with multiple different Phoenix
    instruments. Where in doubt, it is suggested to check the values from
    this package versus those from Phoenix software. As more people use the
    package, confidence will grow and bug fixes will take place as required.
"""
from loguru import logger
from typing import List, Dict, OrderedDict, Tuple, Any, BinaryIO, Optional
import collections
from pathlib import Path
import struct
import numpy as np
import pandas as pd
from resistics.errors import MetadataReadError, TimeDataReadError
from resistics.sampling import RSDateTime, to_datetime, to_timedelta
from resistics.common import Metadata, get_record
from resistics.time import ChanMetadata, TimeMetadata, TimeData, TimeReader, TimeProcess
from resistics.time import TimeWriterNumpy, adjust_time_metadata

from resistics_readers.phoenix.headers import phoenix_headers
from resistics_readers.multifile import samples_to_sources


HEADER_NAME_SIZE = 4
HEADER_SIZE = 12
HEADER_VALUE_SIZE = 13
HEADER_ENTRY_SIZE = HEADER_SIZE + HEADER_VALUE_SIZE
TAG_SIZE = 32
# three byte two's complement for the data
SAMPLE_SIZE = 3
SAMPLE_DTYPE = np.int32
# channel type mapping
CHAN_TYPES = {
    "Ex": "electric",
    "Ey": "electric",
    "Hx": "magnetic",
    "Hy": "magnetic",
    "Hz": "magnetic",
}


class TimeMetadataTS(TimeMetadata):
    """TimeMetadata for a single TS file"""

    data_table: Any
    """The record sample ranges"""

    def json(self):
        """Get the JSON, but exclude the df"""
        return super().json(exclude={"data_table"})


class TimeMetadataPhoenix(Metadata):
    """TimeMetadata for the Phoenix data"""

    ts_nums: List[int]
    """The TS file numbers"""
    ts_files: Dict[int, str]
    """The name of the TS files"""
    ts_continuous: int
    """The continuous TS"""
    ts_metadata: Dict[int, TimeMetadataTS]
    """Metadata for a single TS"""


def strip_control(in_bytes: bytes) -> str:
    """Strip control characters from byte string"""
    return in_bytes.strip(b"\x00").decode()


def read_table_entry(entry_bytes: bytes) -> Tuple[str, Any]:
    """
    Read a single table entry, this should return an entry name and value

    Parameters
    ----------
    entry_bytes : bytes
        The entry bytes

    Returns
    -------
    Tuple[str, Any]
        The name and value

    Raises
    ------
    ValueError
        If unable to read entry name
    KeyError
        If entry name is unknown
    TypeError
        If unable to read entry value
    """
    header_name_fmt = f"{HEADER_NAME_SIZE}s"
    try:
        name = struct.unpack(header_name_fmt, entry_bytes[:HEADER_NAME_SIZE])
        name = strip_control(name[0])
    except Exception:
        raise ValueError("Unable to read entry header name")
    if name not in phoenix_headers:
        logger.error(f"Unknown table name {name}")
        raise KeyError(f"Unknown table name '{name}'")
    # read data
    value_info = phoenix_headers[name]
    value_bytes = entry_bytes[HEADER_SIZE : HEADER_SIZE + value_info["vSize"]]
    try:
        if value_info["ptyp"] == "AmxPT":
            value = struct.unpack(value_info["typ"], value_bytes)
        else:
            value = struct.unpack(value_info["typ"], value_bytes)[0]
        if "s" in value_info["typ"]:
            value = strip_control(value)
    except Exception:
        raise TypeError(f"Unable to read value for header {name}")
    return name, value


def read_table_file(table_path: Path) -> OrderedDict[str, Any]:
    """
    Read a TBL file

    Parameters
    ----------
    table_path : Path
        Path to the table file

    Returns
    -------
    Dict[str, Any]
        The table data in an Ordered dictionary
    """
    import math

    byte_inc = HEADER_SIZE + HEADER_VALUE_SIZE
    table_data = collections.OrderedDict()

    with table_path.open("rb") as f:
        table_bytes = f.read()
    num_headers = int(math.floor(len(table_bytes) / byte_inc))
    logger.debug(f"Reading {num_headers} entries from table file")

    for ientry in range(0, num_headers):
        byte_start = ientry * byte_inc
        entry_bytes = table_bytes[byte_start : byte_start + byte_inc]
        try:
            name, value = read_table_entry(entry_bytes)
            table_data[name] = value
        except ValueError:
            logger.error(f"Unable to read table entry name {ientry}")
        except KeyError:
            logger.error("Unknown entry name")
        except TypeError:
            logger.error("Unable to read data value")
    return table_data


def get_date(value: bytes) -> RSDateTime:
    """
    Convert bytes to a resistics DateTime

    Parameters
    ----------
    value : bytes
        The bytes with the datetime information

    Returns
    -------
    RSDateTime
        The datetime
    """
    seconds = value[0]
    minutes = value[1]
    hour = value[2]
    day = value[3]
    month = value[4]
    year = value[5]
    century = value[-1]
    date = f"{century:02d}{year:02d}-{month:02d}-{day:02d}"
    date += f"T{hour:02d}:{minutes:02d}:{seconds:02d}.000Z"
    return to_datetime(date)


def read_tag(f: BinaryIO) -> Dict[str, Any]:
    """
    Read the tag from a .TS data file

    Tags are used to separate records in a data file. Each tag is 32 bytes long
    and contains data about the next data record

    Some notes about particular tag entries

    - units of sample rate: 0 = Hz, 1 = minute, 2 = hour, 3 = day
    - bit-wise saturation flags
    - clock error in micro seconds

    Parameters
    ----------
    f : BinaryIO
        Binary file type object

    Returns
    -------
    Dict[str, Any]
        The tag data
    """
    tag_data = {}
    tag_data["from_time"] = get_date(struct.unpack("8b", f.read(8)))
    tag_data["serial"] = struct.unpack("h", f.read(2))
    tag_data["n_scans"] = struct.unpack("h", f.read(2))[0]
    tag_data["n_chans"] = struct.unpack("b", f.read(1))[0]
    tag_data["tag_length"] = struct.unpack("b", f.read(1))
    tag_data["status_code"] = struct.unpack("b", f.read(1))
    tag_data["saturation_flag"] = struct.unpack("b", f.read(1))
    tag_data["reserved"] = struct.unpack("b", f.read(1))
    tag_data["sample_length"] = struct.unpack("b", f.read(1))
    tag_data["fs"] = struct.unpack("h", f.read(2))
    tag_data["fs_units"] = struct.unpack("b", f.read(1))
    tag_data["clock_status"] = struct.unpack("b", f.read(1))
    tag_data["clock_error"] = struct.unpack("i", f.read(4))
    for res in range(6):
        key = f"res{res+1}"
        tag_data[key] = struct.unpack("b", f.read(1))
    return tag_data


def get_records(dir_path: Path, ts_file: str) -> pd.DataFrame:
    """
    Get details for all the records

    Phoenix MTU5C data files have multiple records separated by tags. Each
    record will have a number of scans. A single scan is all the channel data
    for one timestamp. The number of scans in a record is equal to the number
    of samples in the record.

    Usually, a record will be a second long, so the number of scans in the
    record is determined by the sampling frequency.

    When reading data, it commonly needs to be read from multiple scans,
    therefore this table helps find which records need to be read to get the
    data to cover a particular time range.

    Note that the time given in the tag is the start time of the next record.

    Parameters
    ----------
    dir_path : Path
        The path with the data file
    ts_file : str
        The name of the data file

    Returns
    -------
    pd.DataFrame
        A DataFrame with details about each record
    """
    data_path = dir_path / ts_file
    n_bytes = data_path.stat().st_size
    record_from_times = []
    record_first_samples = []
    record_last_samples = []
    record_scans = []
    record_byte_starts = []
    # start number of samples at 0
    sample = 0
    bytes_read = 0
    with data_path.open("rb") as f:
        while bytes_read < n_bytes:
            tag_data = read_tag(f)
            record_byte_starts.append(bytes_read + TAG_SIZE)
            record_scans.append(tag_data["n_scans"])
            record_first_samples.append(sample)
            record_last_samples.append(sample + tag_data["n_scans"] - 1)
            record_from_times.append(tag_data["from_time"])
            # increment the samples
            sample += tag_data["n_scans"]
            # go to start of next tag
            data_bytes = tag_data["n_scans"] * tag_data["n_chans"] * SAMPLE_SIZE
            f.seek(data_bytes, 1)
            bytes_read += TAG_SIZE + data_bytes
    return pd.DataFrame(
        data={
            "from_time": record_from_times,
            "first_sample": record_first_samples,
            "last_sample": record_last_samples,
            "n_samples": record_scans,
            "data_byte_start": record_byte_starts,
        }
    )


def get_time_dict(
    ts: int,
    table_data: OrderedDict[str, Any],
    record_df: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Get the time dictionary for a single TS that will be used to initialise a
    TimeMetadata instance.

    Start and end times are provided in the metadata. However, it is only for
    the continuous sampling frequency that the data is continuous between these
    dates. For the other frequencies, whilst these may be the timestamps of the
    first and last sample, it is not necessary that all the timestamps in
    between are present.

    Parameters
    ----------
    ts : int
        The TS number
    table_data : OrderedDict[str, Any]
        The data read in from the .TBL file
    record_df : pd.DataFrame
        Information about the records. This will be primarily be used to get the
        total number of samples in the recording and the last time.

    Returns
    -------
    Dict[str, Any]
        A dictionary of data about the recording
    """
    time_dict = {}
    time_dict["fs"] = table_data[f"SRL{ts}"]
    time_dict["n_samples"] = record_df["n_samples"].sum()
    time_dict["first_time"] = to_datetime(record_df.loc[0, "from_time"])
    # don't add 1 because only using this to calculate the duration
    last_record_start_time = record_df.loc[record_df.index[-1], "from_time"]
    record_n_samples = record_df["last_sample"] - record_df["first_sample"]
    last_record_n_samples = record_n_samples.iloc[-1]
    time_dict["last_time"] = last_record_start_time + to_timedelta(
        last_record_n_samples / time_dict["fs"]
    )
    time_dict["serial"] = table_data["SNUM"]
    time_dict["system"] = table_data["HW"]
    time_dict["elevation"] = table_data["ELEV"]
    time_dict["wgs84_latitude"] = float(table_data["LATG"].split(",")[0])
    time_dict["wgs84_longitude"] = float(table_data["LNGG"].split(",")[0])
    return time_dict


def get_chans_metadata(
    table_data: OrderedDict[str, Any], ts_file: str
) -> Dict[str, Any]:
    """
    Get ChanMetadata for each channel

    Parameters
    ----------
    table_data : OrderedDict[str, Any]
        The table data
    ts_file : str
        The TS file name

    Returns
    -------
    Dict[str, Any]
        Channel metadata for each channel
    """
    chans = ["Ex", "Ey", "Hx", "Hy", "Hz"]
    order = [table_data[f"CH{chan.upper()}"] for chan in chans]
    _order, chans = (
        list(x) for x in zip(*sorted(zip(order, chans), key=lambda pair: pair[0]))
    )
    chans_dict = {}
    for chan in chans:
        chan_dict = {}
        chan_dict["name"] = chan
        chan_dict["data_files"] = [ts_file]
        chan_dict["chan_type"] = CHAN_TYPES[chan]
        # to convert integers to machine volts
        chan_dict["scaling"] = table_data["FSCV"] / np.power(2, 23)

        if CHAN_TYPES[chan] == "magnetic":
            chan_dict["serial"] = table_data[f"{chan.upper()}SN"][-4:]
            chan_dict["sensor"] = "Phoenix"
            chan_dict["gain1"] = table_data["HGN"] * table_data["HATT"]
            chan_dict["gain2"] = (
                (1000.0 / table_data["HNUM"]) if "HNUM" in table_data else 1
            )
        dipoles = {"Ex": "EXLN", "Ey": "EYLN"}
        if CHAN_TYPES[chan] == "electric":
            dipole_dist_key = dipoles[chan]
            chan_dict["dipole_dist"] = float(table_data[dipole_dist_key])
            chan_dict["gain1"] = table_data["EGN"]

        chans_dict[chan] = ChanMetadata(**chan_dict)
    return chans, chans_dict


def get_ts_metadata(
    dir_path: Path, ts_file: str, ts: int, table_data: Dict[str, Any]
) -> TimeMetadata:
    """
    Get TimeMetadata for a single .TS file

    Parameters
    ----------
    dir_path : Path
        The directory path with the data file
    ts_file : str
        The name of the data file
    ts : int
        The TS number
    table_data : Dict[str, Any]
        The table data

    Returns
    -------
    TimeMetadata
        TimeMetadata
    """
    df = get_records(dir_path, ts_file)
    time_dict = get_time_dict(ts, table_data, df)
    chans, chans_dict = get_chans_metadata(table_data, ts_file)
    time_dict["chans"] = chans
    time_dict["n_chans"] = len(chans)
    time_dict["chans_metadata"] = chans_dict
    time_dict["data_table"] = df
    return TimeMetadataTS(**time_dict)


def read_metadata(dir_path: Path) -> TimeMetadataPhoenix:
    """
    Read metadata for Phoenix data

    For phoenix data, the metadata is in the table file and it is binary
    formatted.

    Parameters
    ----------
    dir_path : Path
        The directory path with the data

    Returns
    -------
    TimeMetadataPhoenix
        TimeMetadataPhoenix which has a dictionary of TimeMetadata for each
        .TS file

    Raises
    ------
    MetadataReadError
        If the number of .TBL files in the directory != 1
    """
    table_files = list(dir_path.glob("*.TBL"))
    if len(table_files) != 1:
        raise MetadataReadError(f"Number of table files {len(table_files)} != 1")
    table_path = table_files[0]
    logger.info(f"Reading metadata from {table_path}")
    table_data = read_table_file(table_path)

    data_files = list(dir_path.glob("*.TS*"))
    ts_files = {int(f.name[-1]): f.name for f in data_files}
    ts_nums = sorted(list(ts_files.keys()))
    logger.info(f"Found TS files {ts_nums}")
    ts_metadata = {}
    logger.info("Reading metadata and verifying records for TS files")
    for ts, ts_file in ts_files.items():
        metadata = get_ts_metadata(dir_path, ts_file, ts, table_data)
        ts_metadata[ts] = metadata
    return TimeMetadataPhoenix(
        ts_nums=ts_nums,
        ts_files=ts_files,
        ts_continuous=max(ts_nums),
        ts_metadata=ts_metadata,
    )


def read_record(
    data_bytes: bytes, n_chans: int, from_sample: int, to_sample: int
) -> np.ndarray:
    """
    Read a record

    Parameters
    ----------
    data_bytes : bytes
        The bytes in the record
    n_chans : int
        The number of channels
    from_sample : int
        The first sample to read in the record
    to_sample : int
        The last sample to read in the record

    Returns
    -------
    np.ndarray
        Data with shape n_chans x n_samples
    """
    n_samples = to_sample - from_sample + 1
    index_from = n_chans * from_sample * SAMPLE_SIZE
    index_to = n_chans * (to_sample + 1) * SAMPLE_SIZE
    values = [
        struct.unpack("<I", data_bytes[ii : ii + SAMPLE_SIZE] + b"\x00")[0]
        for ii in range(index_from, index_to, SAMPLE_SIZE)
    ]
    values = [x if not (x & 0x800000) else (x - 0x1000000) for x in values]
    return np.array(values).reshape(n_samples, n_chans).T


def read_records(
    data_path: Path, metadata: TimeMetadataTS, df_to_read: pd.DataFrame
) -> np.ndarray:
    """
    Read data records from a TS file

    Parameters
    ----------
    data_path : Path
        The path to the TS file
    metadata : TimeMetadataTS
        The metadata for the TS file
    df_to_read : pd.DataFrame
        The DataFrame with the records to read

    Returns
    -------
    np.ndarray
        The read data
    """
    n_samples = df_to_read["n_samples_read"].sum()
    data = np.empty(shape=(metadata.n_chans, n_samples), dtype=SAMPLE_DTYPE)
    with data_path.open("rb") as f:
        sample = 0
        for record, info in df_to_read.iterrows():
            record_from = info.loc["read_from"]
            record_to = info.loc["read_to"]
            n_samples_record = info.loc["n_samples_read"]
            data_byte_start = info.loc["data_byte_start"]
            # read bytes for the full record
            n_bytes_to_read = info.loc["n_samples"] * metadata.n_chans * SAMPLE_SIZE
            f.seek(data_byte_start, 0)
            data_bytes = f.read(n_bytes_to_read)
            # parse the record bytes
            data_record = read_record(
                data_bytes, metadata.n_chans, record_from, record_to
            )
            data[:, sample : sample + n_samples_record] = data_record
            sample = sample + n_samples_record
    return data


class TimeReaderTS(TimeReader):
    """
    Phoenix time data reader only for the continuous time series data

    There is no data reader for the other TS files, these should be reformatted.
    """

    extension = ".TS"

    def read_metadata(self, dir_path: Path) -> TimeMetadataTS:
        """
        Read the metadata for the continuous data

        Parameters
        ----------
        dir_path : Path
            The directory path to the data

        Returns
        -------
        TimeMetadataTS
            Metadata for the continuous TS file

        Raises
        ------
        TimeDataReadError
            If the data files do not exist
        """
        metadata = read_metadata(dir_path)
        ts_metadata = metadata.ts_metadata[metadata.ts_continuous]

        if not self._check_data_files(dir_path, ts_metadata):
            raise TimeDataReadError(dir_path, "All data files do not exist")
        return ts_metadata

    def read_data(
        self, dir_path: Path, metadata: TimeMetadata, read_from: int, read_to: int
    ) -> TimeData:
        """
        Read data from the continuous time series data

        In a TS file, each sample is recorded as a scan (all channels recorded
        at the same time). To get the number of bytes to read, multiply number
        of samples by number of channels by the number of bytes for a single
        sample

        Parameters
        ----------
        dir_path : Path
            The directory path
        metadata : TimeMetadata
            The phoenix data metadata
        read_from : int
            Sample to read from
        read_to : int
            Sample to read to

        Returns
        -------
        TimeData
            The read in time data
        """
        data_file = metadata.chans_metadata[metadata.chans[0]].data_files[0]
        data_path = dir_path / data_file
        logger.info(
            f"Reading data from continuous data file {data_path} at {metadata.fs} Hz"
        )
        messages = [f"Reading raw data from {data_path}"]
        messages.append(f"Sampling rate {metadata.fs} Hz")

        # read the records
        data_table = pd.DataFrame(data=metadata.data_table)
        df_to_read = samples_to_sources(dir_path, data_table, read_from, read_to)
        logger.info(f"Reading data from {len(df_to_read.index)} records")
        messages.append(f"Reading data from {len(df_to_read.index)} records")
        data = read_records(data_path, metadata, df_to_read)
        metadata = self._get_return_metadata(metadata, read_from, read_to)
        messages.append(f"From sample, time: {read_from}, {str(metadata.first_time)}")
        messages.append(f"To sample, time: {read_to}, {str(metadata.last_time)}")
        metadata.history.add_record(self._get_record(messages))
        logger.info(f"Data successfully read from {dir_path}")
        return TimeData(metadata, data.astype(np.float32))

    def scale_data(self, time_data: TimeData) -> TimeData:
        r"""
        Get data scaled to physical values

        This information comes from:

        Instrument and Sensor Calibration: Concepts and Utility Programs

        And applies to:

        V5 System 2000, System2000.net, and MTU-net (MTU, MTU-A, V8, RXU,
        MTU-net; MTC and AMTC coils and AL-100 loop).

        The important factors for scaling the data and defined in the TBL file

        - FSCV: the full scale value in volts [V8, RXU, MTU-A, 2.45V] [MTU, 6.40V];
          full scale is 2^23 or 8,388,608 du
        - ExLN: the length of the N–S dipole (Ex) in metres
        - EyLN: the length of the E–W dipole (Ey) in metres
        - EGN: the gain used for the E channels [MTU-A x1 x4 x16] [MTU x10 x40 x160]
        - HGN: the gain used for the H channels [MTU-A x1 x4 x16] [MTU x3 x12 x48]
        - HNUM: the scale factor for coil sensors in (mV/nT) [AMTC-30 100] [MTC-50 1000]
        - HATT: interconect board factor [MTU, MTU-A, MTU-net 0.233] [V8, RXU 1]

        du refers to the digital unit or the value out of the machine

        Note that HNUM is only applicable to AMTC-30 and MTC-50. For other
        systems, HNUM does not appear in the table file.

        These are read in and kept in the metadata

        - FSCV / 2^23 is in the scaling key for each channel
        - ExLn and EyLn are in their appropriate channel in metres
        - EGN is in gain1 for electric channels
        - HGN * HATT is in gain1 for magnetic channels
        - If HNUM is in the table file, gain2 is set to (1000/HNUM) for magnetic
          channels. If HNUM is not present, gain2 is set to 1 for magnetic
          channels.

        To scale the electric channels, apply the following:

        - E-Channel (mV/km) = du * (FSCV/2^23) * (1/EGN) * (1/E_LN) * (1000*1000)
        - Units derivation: (mV/km) = integer * (V/integer) * real * (1/m) * (mV/V * m/km)

        Given the metadata, this becomes

        .. math::

            Ex = Ex * scaling * (1/gain1) * (1/dx) * (1000*1000)

            Ey = Ey * scaling * (1/gain1) * (1/dy) * (1000*1000)

        For the magnetic channels:

        - H-Channel (nT) = du * (FSCV/2^23) * (1/HGN) * (1/HATT) * (1000/HNUM)
        - Units derivation: (nT) = integer * (V/integer) * real* real * (mV/V / mV/nT)

        With the metadata, this is:

        .. math::

            Hx = Hx * scaling * (1/gain1) * gain2

            Hy = Hz * scaling * (1/gain1) * gain2

            Hy = Hz * scaling * (1/gain1) * gain2

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
        logger.warning("Phoenix scaling still requires validation")
        messages = ["Scaling raw data to physical units"]
        for chan in time_data.metadata.chans:
            chan_metadata = time_data.metadata.chans_metadata[chan]
            if chan_metadata.electric():
                mult = (
                    chan_metadata.scaling
                    * (1 / chan_metadata.gain1)
                    * (1 / chan_metadata.dipole_dist)
                    * (1_000 * 1_000)
                )
                time_data[chan] = time_data[chan] * mult
                messages.append(
                    f"Scaling {chan} by (FSCV/2^23) * (1/EGN) * (1/E_LN) * (1000*1000) = {mult:.6f}"
                )
            if chan_metadata.magnetic():
                mult = (
                    chan_metadata.scaling
                    * (1 / chan_metadata.gain1)
                    * (chan_metadata.gain2)
                )
                time_data[chan] = time_data[chan] * mult
                messages.append(
                    f"Scaling {chan} by (FSCV/2^23) * (1/HGN) * (1/HATT) [* (1000/HNUM)] = {mult:.6f}"
                )
        record = self._get_record(messages)
        time_data.metadata.history.add_record(record)
        return time_data


def read_discontinuous_data(
    dir_path: Path, ts_num: int, metadata: TimeMetadataTS
) -> TimeData:
    """
    Read data from a discontinuous TS file

    Note that all the gaps are lost and the data is essentially considered
    single continuous data beginning at the first record.

    Parameters
    ----------
    dir_path : Path
        The directory path to read from
    ts_num : int
        The TS file to read
    metadata : TimeMetadataTS
        The TimeMetadataTS for the TS file with details about all records

    Returns
    -------
    TimeData
        The read time data

    Raises
    ------
    TimeDataReadError
        If an incorrect number of files are found for the TS number
    """
    data_list = list(dir_path.glob(f"*.TS{ts_num}"))
    if len(data_list) != 1:
        raise TimeDataReadError(f"Number TS{ts_num} files in {dir_path} != 1")
    data_path = data_list[0]
    logger.info(f"Reading discontinous data from {data_path} at {metadata.fs} Hz")
    messages = [f"Reading discontinuous data from {data_path}"]
    messages.append(f"Sampling frequency {metadata.fs} Hz")
    # get the records to read
    n_samples = int(metadata.data_table["n_samples"].sum())
    df_to_read = samples_to_sources(dir_path, metadata.data_table, 0, n_samples - 1)
    logger.info(f"Reading data from {len(df_to_read.index)} records")
    messages.append(f"Reading data from {len(df_to_read.index)} records")
    data = read_records(data_path, metadata, df_to_read)
    new_metadata = adjust_time_metadata(
        metadata, metadata.fs, metadata.first_time, n_samples
    )
    record = get_record(creator={"name": "read_discontinuous_data"}, messages=messages)
    new_metadata.history.add_record(record)
    logger.info(f"Data successfully read from {dir_path}")
    time_data = TimeData(new_metadata, data.astype(np.float32))
    return TimeReaderTS().scale_data(time_data)


def reformat(
    dir_path: Path,
    metadata: TimeMetadataPhoenix,
    ts_num: int,
    write_path: Path,
    processors: Optional[List[TimeProcess]] = None,
) -> None:
    """Reformat a discountinuous TS file"""
    if ts_num == metadata.ts_continuous:
        time_data = TimeReaderTS().run(dir_path, metadata=metadata.ts_metadata[ts_num])
    else:
        time_data = read_discontinuous_data(
            dir_path, ts_num, metadata.ts_metadata[ts_num]
        )
    if processors is not None:
        for process in processors:
            time_data = process.run(time_data)
    writer = TimeWriterNumpy()
    writer.run(write_path, time_data)
