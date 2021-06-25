from loguru import logger
from typing import List, Dict, Any
from pathlib import Path
import numpy as np
import pandas as pd
from resistics.time import TimeMetadata, TimeData, TimeReader

from resistics_readers.multifile import TimeMetadataSingle, TimeMetadataMerge


CHAN_MAP = {"Ex": "Ex", "Ey": "Ey", "Bx": "Hx", "By": "Hy", "Bz": "Hz"}
CHAN_TYPES = {
    "Ex": "electric",
    "Ey": "electric",
    "Bx": "magnetic",
    "By": "magnetic",
    "Bz": "magnetic",
}


def update_xtr_data(
    xtr_data: Dict[str, Any], section: str, key: str, val: str
) -> Dict[str, Any]:
    """
    Decide how to deal with an XTR file entry

    Parameters
    ----------
    xtr_data : Dict[str, Any]
        The dictionary with the existing XTR data
    section : str
        The section which has the key, value pair
    key : str
        The key
    val : str
        the value

    Returns
    -------
    Dict[str, Any]
        The updated XTR dictionary
    """
    if key in xtr_data[section] and not isinstance(xtr_data[section][key], list):
        # the key has already been encountered once but has now reappeared
        # this now needs to be converted to a list
        xtr_data[section][key] = [xtr_data[section][key], val]
    elif key in xtr_data[section]:
        # a new value for an existing key that is already a list
        xtr_data[section][key].append(val)
    else:
        # a new value for a key that has not appeared before
        # still unknown whether this will become a list later
        xtr_data[section][key] = val
    return xtr_data


def read_xtr(xtr_path: Path) -> Dict[str, Any]:
    """
    Function to read an XTR file.

    XTR files are similar to INI files but with duplicate entries making them
    more annoying to read.

    Parameters
    ----------
    xtr_path : Path
        Path to the XTR file

    Returns
    -------
    Dict[str, Any]
        Data from the XTR file
    """
    with xtr_path.open("r") as f:
        lines = f.readlines()
    lines = [x.strip().replace("'", "").strip() for x in lines]
    lines = [x for x in lines if x != ""]
    xtr_data: Dict[str, Any] = {}
    section = "GLOBAL"
    for line in lines:
        if line[0] == "[" and line[-1] == "]":
            section = line[1:-1]
            xtr_data[section] = {}
        else:
            key, val = line.split("=")
            xtr_data = update_xtr_data(xtr_data, section, key.strip(), val.strip())
    return xtr_data


class TimeMetadataXTR(TimeMetadataSingle):
    """This is an extension of TimeMetadataSingle for a single XTR file"""

    xtr_file: str
    """The XTR metadata file"""
    data_byte_start: int
    """The byte offset from beginning of the file to the start of the data"""
    rec_chans: int
    """The recorded channels"""


class TimeReaderRAW(TimeReader):
    """
    Parent reader for reading from .RAW SPAM files. Associated metadata can come
    in XTR or XTRX (an XML style) format. Methods for reading from specific
    metadata file formats should be added in child classes inheriting from this
    one.

    The raw data for SPAM is sensor Voltage in single precision float. However,
    if there are multiple data files for a single continuous dataset, each one
    may have a different gain. Therefore, a scaling has to be calculated for
    each data file and channel. Applying these scalings will convert all
    channels to mV.

    More information about scalings can be found in readers for the various
    metadata types, where the scalars are calculated. This class simply
    implements the reading of data and not the calculation of the scalars.
    """

    extension = ".RAW"

    def _read_RAW_metadata(self, raw_path: Path) -> Dict[str, Any]:
        """
        Read metadata directly from the .RAW data files' header bytes

        First begin by reading the general metadata at the start of the file.
        This can be followed by multiple event metadata. However, multiple event
        metadata in RAW files are largely deprecated and only single event
        metadata are supported in this reader.

        Each .RAW file can have its own data byte offset

        Notes
        -----
        Open with encoding ISO-8859-1 because it has a value for all bytes
        unlike other encoding. In particular, want to find number of samples
        and the size of the metadata. The extended metadata is ignored.

        Parameters
        ----------
        raw_path : Path
            Path to RAW file

        Returns
        -------
        Dict[str, Any]
            Dictionary of metadata from RAW file

        Raises
        ------
        MetadataReadError
            If the number of event metadata is greater than 1. This is not
            currently supported
        """
        from resistics.errors import MetadataReadError

        f_size = raw_path.stat().st_size
        f = raw_path.open("r", encoding="ISO-8859-1")
        # read general metadata - provide enough bytes to read
        raw_metadata = self._read_RAW_general_metadata(f.read(1000))
        # read event metadata
        event_metadata = []
        record = raw_metadata["first_event"]
        for _ir in range(raw_metadata["n_events"]):
            # seek to the record from the beginning of the file
            seek_pt = (record - 1) * raw_metadata["rec_length"]
            if not seek_pt > f_size:
                f.seek(seek_pt, 0)
                event = self._read_RAW_event_metadata(f.read(1000))
                event_metadata.append(event)
                if event["next_event_metadata"] < raw_metadata["total_rec"]:
                    # byte location of next record
                    record = event["next_event_metadata"]
                else:
                    break
        f.close()
        if len(event_metadata) > 1:
            raise MetadataReadError(
                raw_path, f"({len(event_metadata)}) > 1 events in RAW file."
            )
        raw_metadata.update(event_metadata[0])
        raw_metadata["data_byte_start"] = (
            raw_metadata["start_data"] - 1
        ) * raw_metadata["rec_length"]
        return raw_metadata

    def _read_RAW_general_metadata(self, general: str) -> Dict[str, Any]:
        """
        Note that rec_chans is the number of channels recorded, not the number
        of channels connected acquiring good data. This is usually five.

        Parameters
        ----------
        general : str
            The general data as a string

        Returns
        -------
        Dict[str, Any]
            Dictionary with general metadata and values
        """
        gen_split = general.split()
        return {
            "rec_length": int(gen_split[0]),
            "file_type": gen_split[1],
            "word_length": int(gen_split[2]),
            "version": gen_split[3],
            "proc_id": gen_split[4],
            "rec_chans": int(gen_split[5]),
            "total_rec": int(gen_split[6]),
            "first_event": int(gen_split[7]),
            "n_events": int(gen_split[8]),
            "extend": int(gen_split[9]),
        }

    def _read_RAW_event_metadata(self, event: str) -> Dict[str, Any]:
        """
        Parse the event metadata

        Parameters
        ----------
        event : str
            The event data as a string

        Returns
        -------
        Dict[str, Any]
            Dictionary with event metadata and values
        """
        event_split = event.split()
        return {
            "start": int(event_split[0]),
            "startms": int(event_split[1]),
            "stop": int(event_split[2]),
            "stopms": int(event_split[3]),
            "cvalue1": float(event_split[4]),
            "cvalue2": float(event_split[5]),
            "cvalue3": float(event_split[6]),
            "event_metadata_infile": int(event_split[7]),
            "next_event_metadata": int(event_split[8]),
            "previous_event_metadata": int(event_split[9]),
            "n_samples": int(event_split[10]),
            "start_data": int(event_split[11]),
            "extended": int(event_split[12]),
        }

    def read_data(
        self, dir_path: Path, metadata: TimeMetadata, read_from: int, read_to: int
    ) -> TimeData:
        """
        Get data from data file, returned in mV

        Calling this applies scalings calculated when the metadata are read.
        When a recording consists of multiple data files, each channel of each
        data file might have a different scaling, therefore, gain removals and
        other RAW file unique scalings need to be applied before the data is
        stitched together.

        This method returns the data in mV for all channels.

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
        dtype_size = np.dtype(np.float32).itemsize
        n_samples = read_to - read_from + 1

        messages = [f"Reading raw data from {dir_path}"]
        messages.append(f"Sampling rate {metadata.fs} Hz")
        # loop over RAW files and read data
        data_table = pd.DataFrame(data=metadata.data_table)
        df_to_read = samples_to_sources(dir_path, data_table, read_from, read_to)
        data = np.empty(shape=(metadata.n_chans, n_samples), dtype=dtype)
        sample = 0
        for data_file, info in df_to_read.iterrows():
            file_from = info.loc["read_from"]
            file_to = info.loc["read_to"]
            n_samples_file = info.loc["n_samples_read"]
            rec_chans = info.loc["rec_chans"]
            data_byte_start = info.loc["data_byte_start"]

            messages.append(f"{data_file}: Reading samples {file_from} to {file_to}")
            logger.debug(f"{data_file}: Reading samples {file_from} to {file_to}")
            n_samples_read = n_samples_file * rec_chans
            byteoff = data_byte_start + (file_from * rec_chans * dtype_size)
            data_path = dir_path / str(data_file)
            data_read = np.memmap(
                data_path, dtype=dtype, mode="r", offset=byteoff, shape=(n_samples_read)
            )
            for idx, chan in enumerate(metadata.chans):
                scaling = info[f"{chan} scaling"]
                data[idx, sample : sample + n_samples_file] = (
                    data_read[idx:n_samples_read:rec_chans] * scaling
                )
            sample = sample + n_samples_file
        metadata = self._get_return_metadata(metadata, read_from, read_to)
        messages.append(f"From sample, time: {read_from}, {str(metadata.first_time)}")
        messages.append(f"To sample, time: {read_to}, {str(metadata.last_time)}")
        metadata.history.add_record(self._get_record(messages))
        logger.info(f"Data successfully read from {dir_path}")
        return TimeData(metadata, data)

    def scale_data(self, time_data: TimeData) -> TimeData:
        """
        Scale data to physically meaningful units

        Resistics uses field units, meaning physical samples will return the
        following:

        - Electrical channels in mV/km
        - Magnetic channels in mV or nT depending on the sensor
        - To convert magnetic in mV to nT, calibration is required

        Notes
        -----
        Conversion to mV (gain removal) is performed on read as each RAW file in
        a dataset can have a separate scalar. Because gain is removed when
        reading the data and all channel data is in mV, the only calculation
        that has to be done is to divide by the dipole lengths (east-west
        spacing and north-south spacing).

        Parameters
        ----------
        time_data : TimeData
            TimeData read in from files

        Returns
        -------
        TimeData
            Scaled TimeData
        """
        logger.info("Applying scaling to data to give field units")
        messages = ["Scaling raw data to physical units"]
        for chan in time_data.metadata.chans:
            chan_metadata = time_data.metadata.chans_metadata[chan]
            if chan_metadata.electric():
                dipole_dist_km = chan_metadata.dipole_dist / 1_000
                time_data[chan] = time_data[chan] / dipole_dist_km
                messages.append(f"Dividing {chan} by dipole length {dipole_dist_km} km")
        record = self._get_record(messages)
        time_data.metadata.history.add_record(record)
        return time_data


class TimeReaderXTR(TimeReaderRAW):
    """Data reader for SPAM RAW data with XTR metadata"""

    def read_metadata(self, dir_path: Path) -> TimeMetadataMerge:
        """
        Read and merge XTR metadata files

        For SPAM data, there may be more than one XTR metadata file as data can
        be split up into smaller files as it is recorded and each data file will
        have an associated XTR metadata file. In this case, the following steps
        are taken:

        - Read all XTR files
        - Generate a table with metadata about each data file (times, scalings)
        - Merge metadata for all the data files

        Parameters
        ----------
        dir_path : Path
            Directory path with SPAM data

        Returns
        -------
        TimeMetadataMerge
            Merged TimeMetadataXTR

        Raises
        ------
        TimeDataReadError
            If not all data files exist
        TimeDataReadError
            If the extension of the data files is incorrect
        """
        from resistics.errors import MetadataReadError, TimeDataReadError
        from resistics_readers.multifile import validate_consistency
        from resistics_readers.multifile import validate_continuous

        metadata_paths = list(dir_path.glob("*.XTR"))
        if len(metadata_paths) == 0:
            MetadataReadError(dir_path, "No XTR files found.")

        raw_paths = list(dir_path.glob("*.RAW"))
        if not len(metadata_paths) == len(raw_paths):
            TimeDataReadError(
                dir_path, "Mismatch between number data files and XTR files"
            )
        metadata_list = []
        for metadata_path in metadata_paths:
            time_metadata = self._read_xtr(metadata_path)
            metadata_list.append(time_metadata)
        validate_consistency(dir_path, metadata_list)
        validate_continuous(dir_path, metadata_list)
        data_table = self._generate_table(metadata_list)
        metadata = self._merge_metadata(metadata_list, data_table)

        if not self._check_data_files(dir_path, metadata):
            raise TimeDataReadError(dir_path, "All data files do not exist")
        if not self._check_extensions(dir_path, metadata):
            raise TimeDataReadError(dir_path, f"Data file suffix not {self.extension}")
        return metadata

    def _read_xtr(self, xtr_path: Path) -> TimeMetadataXTR:
        """
        Read an individual XTR metadata file and return TimeMetadata

        There is also metadata in RAW files associated with XTR files. To get
        the full set of metadata and ensure the data makes sense, XTR metadata
        are validated against those in the RAW file.

        Parameters
        ----------
        xtr_path : Path
            The XTR metadata path to read in

        Returns
        -------
        TimeMetadataXTR
            Metadata for the XTR file

        Raises
        ------
        MetadataReadError
            If there is a mismatch in samples between XTR file and RAW file
        """
        from resistics.errors import MetadataReadError

        xtr_data = read_xtr(xtr_path)
        xtr_time_dict = self._read_xtr_dataset_metadata(xtr_data)
        xtr_time_dict["xtr_file"] = xtr_path.name
        xtr_time_dict["chans_metadata"] = self._read_xtr_chan_metadata(xtr_data)
        xtr_time_dict["chans"] = list(xtr_time_dict["chans_metadata"].keys())

        raw_path = xtr_path.parent / xtr_time_dict["data_file"]
        raw_metadata = self._read_RAW_metadata(raw_path)
        # check to make sure sample length in file matches calculated samples
        if xtr_time_dict["n_samples"] != raw_metadata["n_samples"]:
            raise MetadataReadError(
                xtr_path,
                f"Sample mismatch between XTR {xtr_path} and RAW in {raw_path}",
            )
        xtr_time_dict["data_byte_start"] = raw_metadata["data_byte_start"]
        xtr_time_dict["rec_chans"] = raw_metadata["rec_chans"]
        return TimeMetadataXTR(**xtr_time_dict)

    def _read_xtr_dataset_metadata(self, xtr_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read the data in the XTR file that relates to TimeData dataset metadata

        Parameters
        ----------
        xtr_data : Dict[str, Any]
            Information from the xtr file

        Returns
        -------
        Dict[str, Any]
            Metadatas as a dictionary
        """
        from resistics.sampling import to_datetime

        xtr_time_metadata = {}
        # raw file name and fs
        split = xtr_data["FILE"]["NAME"].split()
        xtr_time_metadata["data_file"] = split[0]
        xtr_time_metadata["fs"] = np.absolute(float(split[-1]))
        # first, last time info which are in unix timestamp
        split = xtr_data["FILE"]["DATE"].split()
        first_time = pd.to_datetime(int(split[0] + split[1]), unit="us", origin="unix")
        last_time = pd.to_datetime(int(split[2] + split[3]), unit="us", origin="unix")
        duration = (last_time - first_time).total_seconds()
        n_samples = int((duration * xtr_time_metadata["fs"]) + 1)
        xtr_time_metadata["first_time"] = to_datetime(first_time)
        xtr_time_metadata["last_time"] = to_datetime(last_time)
        xtr_time_metadata["n_samples"] = n_samples
        # get number of channels
        xtr_time_metadata["n_chans"] = xtr_data["CHANNAME"]["ITEMS"]
        # location information
        split = xtr_data["SITE"]["COORDS"].split()
        xtr_time_metadata["wgs84_latitude"] = float(split[1])
        xtr_time_metadata["wgs84_longitude"] = float(split[2])
        xtr_time_metadata["elevation"] = float(split[3])
        return xtr_time_metadata

    def _read_xtr_chan_metadata(
        self, xtr_data: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get metadata for each channel

        There are some tricky notes here regarding scalers that are extracted.
        This information was provided by Reinhard.

        For electric channels:

        - Data is in raw voltage of sensors
        - Scaling is taken from DATA section of XTR file and will be applied
        - Polarity reversal is applied (multiply by -1)
        - 1000x scaling is applied to convert Volts to mV
        - A final unknown scaling of 1000 is applied

        Mathematically this becomes:

        .. math::

            scaling = scaling extracted from DATA section of XTR file
            scaling = scaling * -1000 (polarity reversal and convert V to mV),
            scaling = scaling * 1000 (unknown 1000 scaling).

        For magnetic channels:

        - Scaling in DATA section ignored
        - This scaling is applied as the static gain during calibration
        - Polarity reversal is applied (multiply by -1)
        - A final unknown scaling of 1000

        Mathematically, this is,

        .. math::

            scaling = -1000 (Polarity reversal and unknown 1000 factor)

        .. note::

            Board LF is currently translated to chopper being True or On. Not
            sure how applicable this is, but it's in there.

        Parameters
        ----------
        xtr_data : Dict[str, Any]
            Data from the XTR file

        Returns
        -------
        Dict[Dict[str, Any]]
            Metadatas for channels as a dictionary
        """
        chans = [x.split()[1] for x in xtr_data["CHANNAME"]["NAME"]]
        xtr_chans_metadata = {}
        for idx, chan in enumerate(chans):
            chan_metadata = {
                "name": CHAN_MAP[chan],
                "data_files": xtr_data["FILE"]["NAME"].split()[0],
            }
            chan_metadata["chan_type"] = CHAN_TYPES[chan]
            chan_metadata["chan_source"] = chan
            data_split = xtr_data["DATA"]["CHAN"][idx].split()
            chan_metadata["scaling"] = self._get_xtr_chan_scaling(
                CHAN_TYPES[chan], data_split
            )
            chan_metadata["dipole_dist"] = float(data_split[3])
            # sensors
            sensor_section = f"200{idx + 1}003"
            sensor_split = xtr_data[sensor_section]["MODULE"].split()
            chan_metadata["serial"] = sensor_split[1]
            # get the board and coil type from name of calibration file
            cal_file = sensor_split[0]
            split = cal_file.split("-")
            info = split[split.index("TYPE") + 1]
            chan_metadata["sensor"] = info.split("_")[0]
            chan_metadata["chopper"] = "LF" in info
            # add to main dictionary
            xtr_chans_metadata[CHAN_MAP[chan]] = chan_metadata
        return xtr_chans_metadata

    def _get_xtr_chan_scaling(self, chan_type: str, data_split: List[str]) -> float:
        """Get the correction required for field units"""
        scaling = float(data_split[-2])
        if chan_type == "electric":
            scaling = -1000.0 * scaling * 1000
        if chan_type == "magnetic":
            scaling = -1000
        return scaling

    def _generate_table(self, metadata_list: List[TimeMetadataXTR]) -> pd.DataFrame:
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
        df["rec_chans"] = [x.rec_chans for x in metadata_list]
        # save scaling information
        chans = metadata_list[0].chans
        for chan in chans:
            col = f"{chan} scaling"
            df[col] = [x.chans_metadata[chan].scaling for x in metadata_list]
        df = df.sort_values("first_time")
        df = df.set_index("data_file")
        return add_cumulative_samples(df)

    def _merge_metadata(
        self, metadata_list: List[TimeMetadataXTR], df: pd.DataFrame
    ) -> TimeMetadataMerge:
        """
        Merge metadata from all the metadata files

        The following assumptions are made:

        - Assume no change in location over time (lat and long remain the same)
        - Assume no change in sensors over time
        - Assume no change in electrode spacing over time

        As each data file can have different scalings, the most common scaling
        (mode) for each channel is taken.

        Parameters
        ----------
        metadata_list : List[TimeMetadataXTR]
            List of TimeMetadataXTR, one for each XTR/RAW file combination
        df : pd.DataFrame
            The data table with information about each raw file

        Returns
        -------
        TimeMetadataMerge
            Merged metadata
        """
        data_files = df.index.values.tolist()
        metadata = metadata_list[0]
        for chan in metadata.chans:
            metadata.chans_metadata[chan].data_files = data_files
            scaling = df[f"{chan} scaling"].mode(dropna=True)
            metadata.chans_metadata[chan].scaling = scaling
        metadata_dict = metadata.dict()
        metadata_dict["first_time"] = df["first_time"].min()
        metadata_dict["last_time"] = df["last_time"].max()
        metadata_dict["n_samples"] = df["n_samples"].sum()
        metadata_dict["data_table"] = df.to_dict()
        return TimeMetadataMerge(**metadata_dict)
