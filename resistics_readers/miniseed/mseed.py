"""
Reformatting for miniseed data

Miniseed data is potentially multi sampling frequency. Resistics does not
support multi sampling frequency data files, therefore, miniseed data files
need to be reformatted before they can be used.

.. warning::

    This an initial implementation and there are likely to be numerous scenarios
    where this breaks. It is suggested to compare this with the output from
    miniseed to ascii thoroughly before using.
    https://github.com/iris-edu/mseed2ascii

    Contributors are welcomed and ecouraged to improve the code and particularly
    add tests to ensure that the reformatting is occuring as expected.
"""
from loguru import logger
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import numpy as np
import pandas as pd
import obspy
from obspy.core.utcdatetime import UTCDateTime
from obspy.core.stream import Stream
from resistics.common import dir_files
from resistics.time import ChanMetadata, TimeMetadata, TimeData
from resistics.time import TimeProcess, TimeWriterNumpy


CHAN_TYPES = {
    "Ex": "electric",
    "Ey": "electric",
    "Hx": "magnetic",
    "Hy": "magnetic",
    "Hz": "magnetic",
}


class NoDataInInterval(Exception):
    def __init__(
        self,
        first_time: pd.Timestamp,
        last_time: pd.Timestamp,
        from_time: pd.Timestamp,
        to_time: pd.Timestamp,
    ):
        """Exception for the no miniseed data in a time interval"""
        self.first_time = first_time
        self.last_time = last_time
        self.from_time = from_time
        self.to_time = to_time

    def __str__(self):
        """The Exception string"""
        outstr = f"Data between {self.first_time} to {self.last_time}"
        outstr += f" does not intersect interval {self.from_time} to {self.to_time}"
        return outstr


def get_miniseed_stream(data_path: Path):
    """Get the miniseed file stream"""
    return obspy.read(str(data_path))


def get_streams(data_paths: List[Path]) -> Dict[Path, Stream]:
    """
    Get the stream object for each data_path

    Parameters
    ----------
    data_paths : List[Path]
        The data paths

    Returns
    -------
    Dict[Path, Stream]
        The stream objects
    """
    streams = {}
    for data_path in data_paths:
        try:
            logger.info(f"Attempting to read file {data_path}")
            streams[data_path] = get_miniseed_stream(data_path)
            traces = [trace.id for trace in streams[data_path]]
            logger.info(f"Successfully read file with traces {traces}")
        except Exception:
            logger.error(f"Unable to read data from {data_path}. Skipping.")
    return streams


def get_table(streams: Dict[Path, Stream], trace_ids: List[str]) -> pd.DataFrame:
    """
    Get table with start and ends for each trace of interest in each file

    The table additionally contains the trace index for each trace for every
    file

    Parameters
    ----------
    streams : Dict[Path, Stream]
        Dictionary of file paths to streams
    trace_ids : List[str]
        The ids of the traces that are of interest

    Returns
    -------
    pd.DataFrame
        The data table
    """
    data = []
    for data_path, stream in streams.items():
        file_trace_ids = [x.id for x in stream.traces]
        for trace_id in trace_ids:
            trace_index = file_trace_ids.index(trace_id)
            trace = stream[trace_index]
            first_time = pd.to_datetime(
                trace.stats.starttime.ns, unit="ns", origin="unix"
            )
            last_time = pd.to_datetime(trace.stats.endtime.ns, unit="ns", origin="unix")
            data.append((data_path.name, trace_id, trace_index, first_time, last_time))
    return pd.DataFrame(
        data=data,
        columns=["data_file", "trace_id", "trace_index", "first_time", "last_time"],
    )


def get_first_last_times(table: pd.DataFrame) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """
    Get the minimum first time and maximum last time for the data

    Each trace may have different date ranges in the miniseed files. This
    function calculates the first and last times where data is present for each
    requested trace.

    Parameters
    ----------
    table : pd.DataFrame
        The information table with the details about trace duration in each data
        file

    Returns
    -------
    Tuple[pd.Timestamp, pd.Timestamp]
        The first and last time
    """
    grouped = table.groupby("data_file")
    first_time = (grouped["first_time"].max()).min()
    last_time = (grouped["last_time"].min()).max()
    return first_time, last_time


def get_streams_to_read(
    trace_id: str,
    table: pd.DataFrame,
    from_time: pd.Timestamp,
    to_time: pd.Timestamp,
) -> pd.DataFrame:
    """
    Get the streams to read and the time intervals to read for each stream

    Note that this finds time intervals to cover from_time to to_time inclusive

    Parameters
    ----------
    trace_id : str
        The trace id
    table : pd.DataFrame
        The table with details about date ranges covered by each miniseed file
    from_time : pd.Timestamp
        The time to get data from
    to_time : pd.Timestamp
        The time to get data to

    Returns
    -------
    pd.DataFrame
        A row for each data file to read and the time range to read from it
    """
    table_trace = table[table["trace_id"] == trace_id]
    to_exclude = table_trace["first_time"] > to_time
    to_exclude = to_exclude | (table_trace["last_time"] < from_time)
    table_trace = table_trace[~to_exclude]
    # get the time ranges to read for each file
    streams_to_read = []
    for _idx, row in table_trace.iterrows():
        # get the read from time for this data file
        if row.loc["first_time"] > from_time:
            read_from = row.loc["first_time"]
        else:
            read_from = from_time
        # get the read to time for this data file
        if row.loc["last_time"] > to_time:
            read_to = to_time
        else:
            read_to = row.loc["last_time"]
        # save the data to read
        streams_to_read.append(
            (row.loc["data_file"], row.loc["trace_index"], read_from, read_to)
        )
    return pd.DataFrame(
        data=streams_to_read,
        columns=["data_file", "trace_index", "read_from", "read_to"],
    )


def get_stream_data(
    dt: pd.Timedelta,
    stream: Stream,
    trace_index: int,
    read_from: pd.Timestamp,
    read_to: pd.Timestamp,
) -> np.ndarray:
    """
    Get data for a single trace from a stream

    Parameters
    ----------
    dt : pd.Timedelta
        The sampling rate
    stream : Stream
        The miniseed file stream
    trace_index : int
        The index of the trace
    read_from : pd.Timestamp
        The time to read from
    read_to : pd.Timestamp
        The time to read to

    Returns
    -------
    np.ndarray
        The trace data from the stream

    Raises
    ------
    ValueError
        If the number of expected samples does not give an integer. This is
        currently a safety first approach until more testing is done
    ValueError
        If the number of samples expected != the number of samples returned by
        the trace in the time interval
    """
    trace = stream[trace_index]
    n_samples_expected = ((read_to - read_from) / dt) + 1
    if not n_samples_expected.is_integer():
        raise ValueError(
            f"Number of samples expected {n_samples_expected} is not an integer"
        )
    n_samples_expected = int(n_samples_expected)
    obspy_read_from = UTCDateTime(read_from.timestamp())
    obspy_read_to = UTCDateTime(read_to.timestamp())
    subtrace = trace.slice(starttime=obspy_read_from, endtime=obspy_read_to)
    if subtrace.count() != n_samples_expected:
        raise ValueError(
            f"samples expected {n_samples_expected} != found {subtrace.count()}"
        )
    logger.debug(f"Expecting {n_samples_expected} samples, found {subtrace.count()}")
    return subtrace.data


def get_trace_data(
    fs: float,
    streams: Dict[Path, Stream],
    streams_to_read: Dict[str, Tuple[pd.Timestamp, pd.Timestamp]],
    from_time: pd.Timestamp,
    n_samples: int,
) -> np.ndarray:
    """
    Get data for a single trace beginning at from_time and for n_samples

    Parameters
    ----------
    fs : float
        The sampling frequency
    streams : Dict[Path, Stream]
        The streams
    streams_to_read : Dict[str, Tuple[pd.Timestamp, pd.Timestamp]]
        The streams to read for this trace and time interval
    from_time : pd.Timestamp
        The time to get the data from
    n_samples : int
        The number of samples to get

    Returns
    -------
    np.ndarray
        The data

    Raises
    ------
    ValueError
        If converting read_from date to samples does not give an integer. This
        is a safety first approach but problems could be encountered at very
        high sampling frequencies. In this case, much more testing needs to be
        done about expected behaviour
    ValueError
        If converting read_to date to samples does not give an integer. This
        is a safety first approach but problems could be encountered at very
        high sampling frequencies. In this case, much more testing needs to be
        done about expected behaviour
    """
    dt = pd.Timedelta(1 / fs, "s")
    streams_from_name = {k.name: v for k, v in streams.items()}
    data = np.empty(shape=(n_samples), dtype=np.float32)
    data[:] = np.nan
    for _idx, row in streams_to_read.iterrows():
        data_file = row.loc["data_file"]
        trace_index = row.loc["trace_index"]
        read_from = row.loc["read_from"]
        read_to = row.loc["read_to"]
        data_sample_from = (read_from - from_time) / dt
        data_sample_to = (read_to - from_time) / dt

        if not data_sample_from.is_integer():
            raise ValueError(f"Date sample from {data_sample_from} is not an integer")
        if not data_sample_to.is_integer():
            raise ValueError(f"Date sample to {data_sample_to} is not an integer")
        data_sample_from = int(data_sample_from)
        data_sample_to = int(data_sample_to)

        logger.debug(f"Reading range {read_from} to {read_to} from stream {data_file}")
        logger.debug(f"Data will cover samples {data_sample_from} to {data_sample_to}")
        stream = streams_from_name[data_file]
        data[data_sample_from : data_sample_to + 1] = get_stream_data(
            dt, stream, trace_index, read_from, read_to
        )
    return data


def get_time_data(
    fs: float,
    id_map: Dict[str, str],
    streams: Dict[Path, Stream],
    table: pd.DataFrame,
    first_time: pd.Timestamp,
    last_time: pd.Timestamp,
    from_time: pd.Timestamp,
    to_time: pd.Timestamp,
) -> TimeData:
    """
    Get time data covering from_time to to_time

    Parameters
    ----------
    fs : float
        The sampling frequency
    id_map : Dict[str, str]
        The map from trace id to channel
    streams : Dict[Path, Stream]
        The streams
    table : pd.DataFrame
        The table with information about trace ranges for each file
    first_time : pd.Timestamp
        The common first_time for all traces and streams
    last_time : pd.Timestamp
        The common last_time for all traces and streams
    from_time : pd.Timestamp
        The from time for this interval of data
    to_time : pd.Timestamp
        The to time for this intervel of data

    Returns
    -------
    TimeData
        TimeData

    Raises
    ------
    NoDataInInterval
        If there is no trace data in the interval from_time and to_time
    ValueError
        If the number of samples in the interval is not an integer. This is a
        safety first approach for now that could fail at very high sampling
        frequencies, in which case much more thorough testing would be better.
    """
    # check there is actually data in the date range
    if (first_time > last_time) or (to_time < first_time):
        raise NoDataInInterval(first_time, last_time, from_time, to_time)
    # correct the times if they are earlier than first time or after last time
    if from_time < first_time:
        logger.debug(f"Adjusted from time {from_time} to first time {first_time}")
        from_time = first_time
    if to_time > last_time:
        logger.debug(f"Adjusted to time {to_time} to last time {last_time}")
        to_time = last_time

    logger.info(f"Extracting chunk between {from_time} and {to_time}")
    n_samples = ((to_time - from_time) / pd.Timedelta(1 / fs, "s")) + 1
    if not n_samples.is_integer():
        raise ValueError("Number of calculated samples is not an integer")
    n_samples = int(n_samples)
    logger.debug(f"Expecting {n_samples} samples between {from_time} to {to_time}")

    trace_ids = list(id_map.keys())
    chans = [id_map[trace_id] for trace_id in trace_ids]
    n_chans = len(chans)
    chans_metadata: Dict[str, ChanMetadata] = {}
    data = np.empty(shape=(n_chans, n_samples), dtype=np.float32)
    for idx, trace_id in enumerate(trace_ids):
        logger.info(f"Extracting data for trace {trace_id}, channel {chans[idx]}")
        streams_to_read = get_streams_to_read(trace_id, table, from_time, to_time)
        data[idx, :] = get_trace_data(
            fs, streams, streams_to_read, from_time, n_samples
        )
        chans_metadata[chans[idx]] = ChanMetadata(
            name=chans[idx],
            data_files=list(streams_to_read["data_file"].values.tolist()),
            chan_type=CHAN_TYPES[chans[idx]],
            chan_source=trace_id,
        )
    metadata = TimeMetadata(
        fs=fs,
        first_time=from_time,
        last_time=to_time,
        n_samples=n_samples,
        chans=chans,
        n_chans=len(chans),
        chans_metadata=chans_metadata,
    )
    return TimeData(metadata, data)


def get_processed_data(time_data: TimeData, processors: List[TimeProcess]) -> TimeData:
    """
    Process time data

    Parameters
    ----------
    time_data : TimeData
        TimeData to process
    processors : List[TimeProcess]
        The processors to run

    Returns
    -------
    TimeData
        The processed TimeData
    """
    for process in processors:
        time_data = process.run(time_data)
    return time_data


def reformat(
    dir_path: Path,
    fs: float,
    id_map: Dict[str, str],
    chunk_time: pd.Timedelta,
    write_path: Path,
    from_time: Optional[pd.Timestamp] = None,
    to_time: Optional[pd.Timestamp] = None,
    processors: Optional[List[TimeProcess]] = None,
) -> None:
    """
    Reformat miniseed data into resistics numpy format in intervals

    Parameters
    ----------
    dir_path : Path
        The directory with the miniseed files
    fs : float
        The sampling frequencies being extracted
    id_map : Dict[str, str]
        Map from trace ids to be extracted to channel names
    chunk_time : pd.Timedelta
        The intervals to extract the data in, for example 1H, 12H, 1D
    write_path : Path
        The path to write out the TimeData to
    from_time : Optional[pd.Timestamp], optional
        Optionally provide a from time, by default None. If None, the from time
        will be the earliest timestamp shared by all traces that are requested
        to be reformatted
    to_time : Optional[pd.Timestamp], optional
        Optionally provide a to time, by default None. If None, the last time
        will be the earliest timestamp shared by all traces that are requested
        to be reformatted
    processors : Optional[List[TimeProcess]], optional
        Any processors to run, by default None. For example resampling of data.
    """
    logger.info(f"Reformatting miniseed data in {dir_path}")
    data_paths = dir_files(dir_path)
    trace_ids = list(id_map.keys())
    # get the streams and update data paths with just the files that were read
    streams = get_streams(data_paths)
    logger.info(f"Found {len(streams)} readable files")
    data_paths = list(streams.keys())
    table = get_table(streams, trace_ids)
    first_time, last_time = get_first_last_times(table)
    logger.info(f"Found maximum data range of {first_time} to {last_time}")

    if from_time is None:
        from_time = first_time
    if to_time is None:
        to_time = last_time
    from_time = from_time.floor(freq=chunk_time)
    to_time = to_time.ceil(freq=chunk_time)
    logger.info(f"Extracting data from {from_time} to {to_time} for ids {trace_ids}")

    starts = pd.date_range(
        start=from_time, end=to_time - pd.Timedelta(chunk_time), freq=chunk_time
    )
    ends = pd.date_range(
        start=from_time + pd.Timedelta(chunk_time), end=to_time, freq=chunk_time
    )
    # minus 1 sample from ends to avoid any double gathering of samples
    ends = ends - pd.Timedelta(1 / fs, "s")
    for date_start, date_end in zip(starts, ends):
        try:
            time_data = get_time_data(
                fs, id_map, streams, table, first_time, last_time, date_start, date_end
            )
        except NoDataInInterval:
            logger.debug(f"No data in interval {date_start} - {date_end}")
            continue

        if processors is not None:
            time_data = get_processed_data(time_data, processors)
        first_str = time_data.metadata.first_time.strftime("%Y-%m-%d_%H-%M-%S")
        last_str = time_data.metadata.last_time.strftime("%Y-%m-%d_%H-%M-%S")
        meas_name = f"{first_str}_to_{last_str}_mseed"
        save_path = write_path / meas_name
        TimeWriterNumpy().run(save_path, time_data)
