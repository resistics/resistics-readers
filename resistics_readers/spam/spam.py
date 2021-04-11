from logging import getLogger
from typing import List, Dict, Any
from pathlib import Path
import numpy as np
import pandas as pd

from resistics.common import DatasetHeaders
from resistics.time import TimeReader, TimeData, get_time_headers

logger = getLogger(__name__)


def read_xtr(xtr_path: Path) -> Dict[str, Any]:
    """
    Function to read an XTR file.

    XTR files are similar to INI files but with duplicate entries making them more annoying to read.

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
    xtr_data = {}
    section = "GLOBAL"
    for line in lines:
        if line[0] == "[" and line[-1] == "]":
            section = line[1:-1]
            xtr_data[section] = {}
        else:
            key, val = line.split("=")
            key = key.strip()
            val = val.strip()
            if key in xtr_data[section] and not isinstance(
                xtr_data[section][key], list
            ):
                xtr_data[section][key] = [xtr_data[section][key], val]
            elif key in xtr_data[section]:
                xtr_data[section][key].append(val)
            else:
                xtr_data[section][key] = val
    return xtr_data


class TimeReaderRAW(TimeReader):
    """
    Parent reader for reading from .RAW SPAM files. Associated headers can come in XTR or XTRX (an XML style) format. Header reading from specific header file formats should be added in child classes inheriting from this one.

    The raw data for SPAM is raw sensor Voltage in single precision float. However, if there are multiple data files for a single continuous dataset, each one may have a different gain. Therefore, a scaling has to be calculated for each data file and channel. Applying these scalings will convert all channels to mV.

    More information about scalings can be found in readers for the various header types, where the scalars are calculated. This class simply implements the reading of data and not the calculation of the scalars.
    """

    def _read_RAW_headers(self, data_path: Path) -> Dict[str, Any]:
        """
        Read headers from the .RAW data files

        First begin by reading the general header at the start of the file. This can be followed by multiple event headers. However, multiple event headers in RAW files are largely deprecated and only single event headers are supported in this reader.

        Each .RAW file can have its own data byte offset

        Notes
        -----
        Open with encoding ISO-8859-1 because it has a value for all bytes unlike other encoding. In particular, want to find number of samples and the size of the header. The extended header is ignored.

        Parameters
        ----------
        data_path : Path
            Path to RAW file

        Returns
        -------
        Dict[str, Any]
            Dictionary of headers from RAW file

        Raises
        ------
        HeaderReadError
            If the number of event headers is greater than 1. This is not currently supported
        """
        from resistics.errors import HeaderReadError

        f = data_path.open("r", encoding="ISO-8859-1")
        # read enough bytes to read the general header
        raw_headers = self._read_RAW_general_headers(f.read(1000))
        # read event headers
        event_headers = []
        f_size = data_path.stat().st_size
        record = raw_headers["first_event"]
        for _ir in range(raw_headers["n_events"]):
            # seek to the record from the beginning of the file
            seek_pt = (record - 1) * raw_headers["rec_length"]
            if not seek_pt > f_size:
                f.seek(seek_pt, 0)
                event = self._read_RAW_event_headers(f.read(1000))
                event_headers.append(event)
                if event["next_event_header"] < raw_headers["total_rec"]:
                    # byte location of next record
                    record = event["next_event_header"]
                else:
                    break
        f.close()
        if len(event_headers) > 1:
            logger.error(f"{len(event_headers)} > events in RAW file. Only 1 expected.")
            raise HeaderReadError(
                data_path, f"More than 1 ({len(event_headers)}) events in RAW file."
            )
        raw_headers.update(event_headers[0])
        raw_headers["data_byte_start"] = (raw_headers["start_data"] - 1) * raw_headers[
            "rec_length"
        ]
        return raw_headers

    def _read_RAW_general_headers(self, general: str) -> Dict[str, Any]:
        """
        Note that rec_chans is the number of channels recorded, not the number of channels connected acquiring good data. This is usually five.

        Parameters
        ----------
        general : str
            The general data as a string

        Returns
        -------
        Dict[str, Any]
            Dictionary with general headers and values
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

    def _read_RAW_event_headers(self, event: str) -> Dict[str, Any]:
        """
        Parse the event header

        Parameters
        ----------
        event : str
            The event data as a string

        Returns
        -------
        Dict[str, Any]
            Dictionary with event headers and values
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
            "event_header_infile": int(event_split[7]),
            "next_event_header": int(event_split[8]),
            "previous_event_header": int(event_split[9]),
            "n_samples": int(event_split[10]),
            "start_data": int(event_split[11]),
            "extended": int(event_split[12]),
        }

    def read_data(self, read_from: int, read_to: int) -> TimeData:
        """
        Get data from data file, returned in mV

        Calling this applies scalings calculated when the headers are read. When a recording consists of multiple data files, each channel of each data file might have a different scaling, therefore, gain removals and other RAW file unique scalings need to be applied before the data is stitched together.

        Generally, this method returns the data in mV for all channels.

        Parameters
        ----------
        read_from : int
            Sample to read data from
        read_to : int
            Sample to read data to

        Returns
        -------
        TimeData
            Time data object
        """
        from resistics.common import ProcessHistory

        assert self.headers is not None

        dtype = np.float32
        dtype_size = np.dtype(np.float32).itemsize
        chans = self.headers.chans
        n_samples = read_to - read_from + 1

        messages = [f"Reading raw data from {self.dir_path}"]
        messages.append(f"Sampling rate {self.headers.dataset('fs')} Hz")
        messages.append(f"Reading samples {read_from} to {read_to}")
        # loop over RAW files and read data
        df_to_read = self._samples_to_files(read_from, read_to)
        print(self._data_table)
        print(df_to_read)
        data = np.empty(shape=(len(chans), n_samples), dtype=dtype)
        sample = 0
        for data_file, info in df_to_read.iterrows():
            file_from = info.loc["read_from"]
            file_to = info.loc["read_to"]
            n_samples_file = info.loc["n_samples_file"]
            rec_chans = info.loc["rec_chans"]
            data_byte_start = info.loc["data_byte_start"]

            messages.append(f"{data_file}: Reading samples {file_from} to {file_to}")
            n_samples_read = n_samples_file * rec_chans
            byteoff = data_byte_start + (file_from * rec_chans * dtype_size)
            data_path = self.dir_path / str(data_file)
            data_read = np.memmap(
                data_path, dtype=dtype, mode="r", offset=byteoff, shape=(n_samples_read)
            )
            for idx, chan in enumerate(chans):
                scaling = info[f"{chan} scaling"]
                data[idx, sample : sample + n_samples_file] = (
                    data_read[idx:n_samples_read:rec_chans] * scaling
                )
            sample = sample + n_samples_file
        headers = self._get_return_headers(read_from, read_to)
        messages.append(f"Time range {headers['first_time']} to {headers['last_time']}")
        record = self._get_process_record(messages)
        logger.info(f"Data successfully read from {self.dir_path}")
        return TimeData(headers, chans, data, ProcessHistory([record]))

    def _samples_to_files(self, from_sample: int, to_sample: int) -> pd.DataFrame:
        """
        Get a DataFrame of data files that should be read to cover the sample range

        Parameters
        ----------
        from_sample : int
            Reading from sample
        to_sample : int
            Reading to sample

        Returns
        -------
        pd.DataFrame
            DataFrame with data files to read as indices and reading information as columns such as number of samples to read, channel scalings etc.

        Raises
        ------
        TimeDataReadError
            If somehow there's a mismatch in the total number of samples to read per file and the expected number of samples.
        """
        from resistics.errors import TimeDataReadError

        df = self._data_table[~(self._data_table["first_sample"] > to_sample)]
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
        df["n_samples_file"] = df["read_to"] - df["read_from"] + 1

        if df["n_samples_file"].sum() != to_sample - from_sample + 1:
            sum_files = df["n_samples_file"].sum()
            expected = to_sample - from_sample + 1
            raise TimeDataReadError(
                self.dir_path,
                f"Samples found to read {sum_files} does not match expected {expected}",
            )

        return df

    def scale_data(self, time_data: TimeData) -> TimeData:
        """
        Scale data to physically meaningful units

        Resistics uses field units, meaning physical samples will return the following:

        - Electrical channels in mV/km
        - Magnetic channels in mV or nT depending on the sensor. If in mV, calibration will be required to give data in nT

        Notes
        -----
        Conversion to mV (gain removal) is performed on read as each RAW file in a dataset can have a separate scalar. Because gain is removed when reading the data and all channel data is in mV, the only calculation that has to be done is to divide by the dipole lengths (east-west spacing and north-south spacing).

        Parameters
        ----------
        time_data : TimeData
            TimeData read in from files

        Returns
        -------
        TimeData
            Scaled TimeData
        """
        messages = ["Scaling raw data to physical units"]
        for chan in time_data.chans:
            if chan == "Ex":
                dx_km = self.headers[chan, "dx"] / 1000
                time_data[chan] = time_data[chan] / dx_km
                messages.append(f"Dividing {chan} by dipole length {dx_km} km")
            if chan == "Ey":
                dy_km = self.headers[chan, "dy"] / 1000
                time_data[chan] = time_data[chan] / dy_km
                messages.append(f"Dividing {chan} by dipole length {dy_km} km")
        record = self._get_process_record(messages)
        time_data.history.add_record(record)
        logger.info("Scaling applied to time data")
        return time_data


class TimeReaderXTR(TimeReaderRAW):
    """Data reader for SPAM RAW data with XTR headers"""

    def check(self) -> bool:
        """
        Check SPAM data directory

        Parameters
        ----------
        dir_path : Path
            Data directory

        Returns
        -------
        bool
            Flag indicating whether checks have been passed
        """
        header_paths = list(self.dir_path.glob("*.XTR"))
        if len(header_paths) == 0:
            logger.error(f"No XTR files found in data folder {self.dir_path}")
            return False

        data_paths = list(self.dir_path.glob("*.RAW"))
        if not len(header_paths) == len(data_paths):
            logger.error(
                f"Mismatch between number of data ({len(data_paths)}) and header ({len(header_paths)}) files"
            )
            return False

        try:
            self.headers = self.read_headers(header_paths)
        except:
            logger.error("Unable to read header data from XTR header files")
            return False
        return True

    def read_headers(self, header_paths: List[Path]) -> DatasetHeaders:
        """
        Read XTR header files

        For SPAM data, there may be more than one XTR header file as data can be split up into smaller files as it is recorded and each data file will have an associated XTR header file. In this case, the following steps are taken:

        - Read all XTR files
        - Generate a table mapping each data file to first and last time, sample range and scalings
        - Merge headers

        Parameters
        ----------
        header_paths : List[Path]
            Paths to XTR files to read

        Returns
        -------
        DatasetHeaders
            The merged DatasetHeaders
        """
        time_headers_list = []
        for header_path in header_paths:
            time_headers = self._read_xtr(header_path)
            time_headers_list.append(time_headers)
        self._xtr_headers = {x.dataset("data_files"): x for x in time_headers_list}
        self._validate_headers(time_headers_list)
        self._data_table = self._generate_table(time_headers_list)
        return self._merge_headers(time_headers_list)

    def _read_xtr(self, header_path: Path) -> DatasetHeaders:
        """
        Read an individual XTR header file and return DatasetHeaders for that file

        There are also headers in RAW files associated with XTR files. To get the full set of headers and ensure the data makes sense, XTR headers are validated against those in the RAW file.

        Parameters
        ----------
        headerFile : Path
            The XTR header path to read in
        """
        from resistics.errors import HeaderReadError

        xtr_data = read_xtr(header_path)
        xtr_dataset_headers = self._read_xtr_dataset_headers(xtr_data)
        xtr_chan_headers = self._read_xtr_chan_headers(xtr_data)
        data_path = self.dir_path / xtr_dataset_headers["data_files"]
        raw_headers = self._read_RAW_headers(data_path)
        # check to make sure sample length in file matches calculated samples
        if xtr_dataset_headers["n_samples"] != raw_headers["n_samples"]:
            raise HeaderReadError(
                header_path,
                f"Sample mismatch between headers in {header_path} and data in {data_path}",
            )
        xtr_dataset_headers["data_byte_start"] = raw_headers["data_byte_start"]
        xtr_dataset_headers["rec_chans"] = raw_headers["rec_chans"]
        return get_time_headers(xtr_dataset_headers, xtr_chan_headers)

    def _read_xtr_dataset_headers(self, xtr_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read the data in the XTR file that relates to TimeData dataset headers

        Parameters
        ----------
        xtr_data : Dict[str, Any]
            Information from the xtr file

        Returns
        -------
        Dict[str, Any]
            Headers as a dictionary
        """
        xtr_dataset_headers = {}
        # raw file name and fs
        split = xtr_data["FILE"]["NAME"].split()
        xtr_dataset_headers["data_files"] = split[0]
        xtr_dataset_headers["fs"] = np.absolute(float(split[-1]))
        xtr_dataset_headers["dt"] = 1 / xtr_dataset_headers["fs"]
        # first, last time info which are in unix timestamp
        split = xtr_data["FILE"]["DATE"].split()
        first_time = pd.to_datetime(int(split[0] + split[1]), unit="us", origin="unix")
        last_time = pd.to_datetime(int(split[2] + split[3]), unit="us", origin="unix")
        duration = (last_time - first_time).total_seconds()
        n_samples = int((duration * xtr_dataset_headers["fs"]) + 1)
        xtr_dataset_headers["first_time"] = first_time
        xtr_dataset_headers["last_time"] = last_time
        xtr_dataset_headers["n_samples"] = n_samples
        # get number of channels
        xtr_dataset_headers["n_chans"] = xtr_data["CHANNAME"]["ITEMS"]
        # location information
        split = xtr_data["SITE"]["COORDS"].split()
        xtr_dataset_headers["wgs84_latitude"] = float(split[1])
        xtr_dataset_headers["wgs84_longitude"] = float(split[2])
        xtr_dataset_headers["elevation"] = float(split[3])
        return xtr_dataset_headers

    def _read_xtr_chan_headers(
        self, xtr_data: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get headers for each channel

        There are some tricky notes here regarding scalers that are extracted. This information was provided by Reinhard.

        - Data is in raw voltage of sensors
        - Scaling is extracted from DATA section of XTR file for electric channel (ignored for magnetic channel)
        - Both electric and magnetic fields need polarity reversals, hence scalars are multiplied by -1.
        - For electric channels, in addition to the scaling provided in the XTR file, an additional 1000x scaling is applied to convert Volts to mV.
        - The scaling for the magnetic channels in the XTR files is ignored as this is simply the static gain scaling which will be applied during calibration
        - There is an unknown additional scaling of 1000 that needs to be applied to both magnetic and electric channels

        As a result, the scaling for electric channels becomes,

        .. math::

            scaling = scaling extracted from DATA section of XTR file
            scaling = scaling * -1000 (to perform polarity reversal and convert Volts to milliVolts),
            scaling = scaling * 1000 (unknown 1000 scaling).

        And for magnetic channels,

        .. math::

            scaling = -1000 (Polarity reversal and unknown 1000 factor)

        .. note::

            Board LF is currently translated to chopper being True or On. Not sure how applicable this is, but it's in there.

        Parameters
        ----------
        xtr_data : Dict[str, Any]
            Data from the XTR file

        Returns
        -------
        Dict[Dict[str, Any]]
            Headers for channels as a dictionary
        """
        from resistics.common import to_resistics_chan, is_electric, is_magnetic

        chans = [x.split()[1] for x in xtr_data["CHANNAME"]["NAME"]]
        chans = [to_resistics_chan(x) for x in chans]

        xtr_chan_headers = {}
        for idx, chan in enumerate(chans):
            chan_headers = {
                "data_files": xtr_data["FILE"]["NAME"].split()[0],
            }
            data_split = xtr_data["DATA"]["CHAN"][idx].split()
            # correction required for field units
            scaling = float(data_split[-2])
            if is_electric(chan):
                scaling = -1000.0 * scaling * 1000
            if is_magnetic(chan):
                scaling = -1000
            chan_headers["scaling"] = scaling
            # positions for electric channels
            if chan == "Ex":
                chan_headers["dx"] = float(data_split[3])
            if chan == "Ey":
                chan_headers["dy"] = float(data_split[3])
            if chan == "Ez":
                chan_headers["dz"] = float(data_split[3])
            # sensors
            sensor_section = f"200{idx + 1}003"
            sensor_split = xtr_data[sensor_section]["MODULE"].split()
            chan_headers["serial"] = sensor_split[1]
            # get the board and coil type from name of calibration file
            cal_file = sensor_split[0]
            split = cal_file.split("-")
            info = split[split.index("TYPE") + 1]
            chan_headers["sensor"] = info.split("_")[0]
            if is_electric(chan):
                chan_headers["echopper"] = "LF" in info
            if is_magnetic(chan):
                chan_headers["hchopper"] = "LF" in info
            # add to main dictionary
            xtr_chan_headers[chan] = chan_headers
        return xtr_chan_headers

    def _validate_headers(self, headers_list: List[DatasetHeaders]) -> bool:
        """
        Validate XTR headers with each other to ensure there are not issues

        Parameters
        ----------
        headers_list : List[DatasetHeaders]
            List of DatasetHeaders, one for each XTR file

        Returns
        -------
        bool
            True if validation was successful, false if not

        Raises
        ------
        HeaderReadError
            If multiple values are found for sampling frequency or number of chans
        HeaderReadError
            If different XTR files have different channels
        """
        from resistics.errors import HeaderReadError

        headers_to_check = ["fs", "n_chans"]
        for header in headers_to_check:
            unique = set([x.dataset(header) for x in headers_list])
            if len(unique) != 1:
                raise HeaderReadError(
                    self.dir_path,
                    f"Multiple entries found for headers {header}: {unique}",
                )
        unique = set([",".join(x.chans) for x in headers_list])
        if len(unique) != 1:
            raise HeaderReadError(self.dir_path, f"Different channels found, {unique}")
        return True

    def _generate_table(self, headers_list: List[DatasetHeaders]) -> pd.DataFrame:
        """
        Generate a table mapping RAW file to sample range for the dataset, number of samples and scalings

        Parameters
        ----------
        headers_list : List[DatasetHeaders]
            List of DatasetHeaders, one for each XTR/RAW file combination

        Returns
        -------
        pd.DataFrame
            The table mapping data file to various properties

        Raises
        ------
        HeaderReadError
            If there are gaps between data files. Data must be continous
        """
        from resistics.errors import HeaderReadError

        df = pd.DataFrame()
        for_table = [
            "data_files",
            "first_time",
            "last_time",
            "n_samples",
            "data_byte_start",
            "rec_chans",
        ]
        for header in for_table:
            df[header] = [x.dataset(header) for x in headers_list]
        # save scaling information
        chans = headers_list[0].chans
        for chan in chans:
            df[f"{chan} scaling"] = [x.chan(chan, "scaling") for x in headers_list]
        df = df.sort_values("first_time")
        # look for gaps
        dt = headers_list[0]["dt"]
        time_chk = df["first_time"] - df.shift(1)["last_time"]
        time_chk = (time_chk - pd.Timedelta(dt, "s")).dropna()
        gaps = time_chk[time_chk > pd.Timedelta(0, "s")]
        if len(gaps.index) > 0:
            logger.error("Found gaps between files...")
            data_files = df["data_files"].values
            info = pd.DataFrame(
                {
                    "From": data_files[gaps.index - 1],
                    "To": data_files[gaps.index],
                    "Gap": gaps.values,
                }
            )
            logger.error(f"\n{info.to_string(index=False)}")
            raise HeaderReadError(self.dir_path, "Gaps found, unable to read data")
        # add running sample counts
        cumsum_samples = df["n_samples"].cumsum()
        df["first_sample"] = cumsum_samples.shift(1).fillna(value=0).astype(int)
        df["last_sample"] = df["first_sample"] + df["n_samples"] - 1
        return df.set_index("data_files")

    def _merge_headers(self, headers_list: List[DatasetHeaders]) -> DatasetHeaders:
        """
        Merge headers from all the header files

        The following assumptions are made:

            - Assume no change in location over time (latitude and longitude remain the same)
            - Assume no change in sensors over time as this should have caused a pause in recordings
            - Assume no change in electrode spacing over time as this should have caused a pause in recordings

        As each data file can have different scalings, the most common scaling (mode) for each channel is taken.

        Parameters
        ----------
        headers_list : List[DatasetHeaders]
            List of DatasetHeaders, one for each XTR/RAW file combination

        Returns
        -------
        DatasetHeaders
            A single DatasetHeaders for the whole dataset
        """
        data_files = self._data_table.index.values.tolist()
        data_files_string = ",".join(data_files)
        first_time = self._data_table["first_time"].min()
        last_time = self._data_table["last_time"].max()
        n_samples = self._data_table["n_samples"].sum()
        headers = headers_list[0].copy()
        headers["data_files"] = data_files_string
        headers["first_time"] = first_time
        headers["last_time"] = last_time
        headers["n_samples"] = n_samples
        # chan headers
        for chan in headers.chans:
            headers[chan, "data_files"] = data_files_string
            scaling = self._data_table[f"{chan} scaling"].mode(dropna=True)
            headers[chan, "scaling"] = scaling
        return headers