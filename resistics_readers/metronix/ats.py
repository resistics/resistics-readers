"""
Classes for reading Metronix time series and calibration data
"""
from typing import Dict, Any
from logging import getLogger
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd

from resistics.common import DatasetHeaders
from resistics.time import TimeReader, TimeData, get_time_headers

logger = getLogger(__name__)


class TimeReaderATS(TimeReader):
    r"""Data reader for ATS formatted data

    For ATS files, header information is XML formatted. The end time in ATS header files is actually one sample past the time of the last sample. The dataReader handles this and gives an end time corresponding to the actual time of the last sample.

    Notes
    -----
    The raw data units for ATS data are in counts. To get data in field units, ATS data is first multipled by the least significat bit (lsb) defined in the header files,

    .. math::

        data = data * lsb,

    giving data in mV. The lsb includes the gain removal, so no separate gain removal needs to be performed.

    For electrical channels, there is additional step of dividing by the electrode spacing, which is provided in metres. The extra factor of a 1000 is to convert this to km to give mV/km for electric channels

    .. math::

        data = \frac{1000 * data}{spacing}

    Finally, to get magnetic channels in nT, the magnetic channels need to be calibrated.
    """

    def check(self) -> bool:
        """
        Checks before reading a dataset

        Returns
        -------
        bool
            True if all checks are passed and data can be read
        """
        xml_files = list(self.dir_path.glob("*.xml"))
        if len(xml_files) != 1:
            logger.error(f"Number of XML files {len(xml_files)} must be 1")
            return False
        header_path = xml_files[0]
        try:
            headers = self.read_headers(header_path)
        except:
            logger.error("Unable to read headers from XML file")
            return False

        self.headers = headers
        chk_files = True
        for chan in self.headers.chans:
            chan_path = self.dir_path / self.headers[chan, "data_files"]
            if not chan_path.exists():
                logger.error(f"{chan} data file {chan_path.name} not found")
                chk_files = False
        if not chk_files:
            return False
        logger.info(f"Passed checks and successfully read headers from {header_path}")
        return True

    def read_headers(self, header_path: Path) -> DatasetHeaders:
        """
        Read the time series data headers and return

        Recall, for Metronix headers, the stop time is not the timestamp of the last sample, but instead the time of the next sample.

        Parameters
        ----------
        header_path : Path
            Header

        Returns
        -------
        Union[TimeHeaders, None]
            TimeHeaders if reading was successful, else None
        """
        root = ET.parse(header_path).getroot()
        dataset_headers = self._read_dataset_headers(header_path, root)
        chan_headers = self._read_chan_headers(header_path, root)
        chans = list(chan_headers.keys())
        # check consistent number of chans between dates and data files
        print("Here1")
        first_time = dataset_headers["first_time"]
        print("Here2")
        last_time = dataset_headers["last_time"]
        print("Here3")
        dt = dataset_headers["dt"]
        print("Here4")
        n_samples = int(((last_time - first_time) / pd.Timedelta(dt, "s")) + 1)
        print(dataset_headers)
        print(chan_headers)
        print(n_samples)
        for chan in chan_headers:
            print(chan_headers[chan]["n_samples"])
            assert n_samples == chan_headers[chan]["n_samples"]
        dataset_headers["n_samples"] = chan_headers[chans[0]]["n_samples"]
        return get_time_headers(dataset_headers, chan_headers)

    def _read_dataset_headers(
        self, header_path: Path, root: ET.Element
    ) -> Dict[str, Any]:
        """
        Read dataset headers from the XML file

        Parameters
        ----------
        header_path: Path
            The path to the header file
        root : ET.Element
            Root element of XML file

        Returns
        -------
        Dict[str, Any]
            Dictionary of dataset headers
        """
        rec_key = "./recording"
        glo_key = "./input/ADU07Hardware/global_config"
        # recording section
        rec = root.find(rec_key)
        first_time = rec.find("start_date").text + " " + rec.find("start_time").text
        stop_time = rec.find("stop_date").text + " " + rec.find("stop_time").text
        # global config section
        glo = rec.find(glo_key)
        n_chans = glo.find("meas_channels").text
        fs = float(glo.find("sample_freq").text)
        dt = 1 / fs
        return {
            "fs": fs,
            "dt": dt,
            "first_time": pd.Timestamp(first_time),
            "last_time": pd.Timestamp(stop_time) - pd.Timedelta(dt, "s"),
            "n_chans": n_chans,
        }

    def _read_chan_headers(
        self, header_path: Path, root: ET.Element
    ) -> Dict[str, Dict[str, Any]]:
        """
        Read channel headers

        Parameters
        ----------
        header_path: Path
            The path to the header file
        root : ET.Element
            Root element of XML file

        Returns
        -------
        Dict[str, Dict[str, Any]]
            Channel headers

        Raises
        ------
        HeaderReadError
            Failed to find recording outputs channel information (wrong key)
        HeaderReadError
            No channel information found in recording outputs channel information
        HeaderReadError
            Mismatch between input and output channel sections
        """
        from resistics.errors import HeaderReadError

        chan_input_key = "./recording/input/ADU07Hardware/channel_config/channel"
        chan_output_key = "./recording/output/"
        chan_inputs = root.findall(chan_input_key)
        try:
            chan_outputs = root.find(chan_output_key)
            chan_outputs = chan_outputs.find(".//ATSWriter")
            chan_outputs = chan_outputs.findall("configuration/channel")
        except:
            raise HeaderReadError(
                header_path, f"Failed to read channel data from {chan_output_key}"
            )
        if chan_outputs is None or len(chan_outputs) == 0:
            raise HeaderReadError(
                header_path, f"No channels found in {chan_output_key}"
            )
        if len(chan_outputs) != len(chan_inputs):
            raise HeaderReadError(
                header_path,
                f"Channel mismatch between {chan_input_key}, {chan_output_key}",
            )

        chan_headers = {}
        for chan_in, chan_out in zip(chan_inputs, chan_outputs):
            chan_header = {}
            # out section
            chan = chan_out.find("channel_type").text
            chan_header["data_files"] = chan_out.find("ats_data_file").text
            chan_header["n_samples"] = int(chan_out.find("num_samples").text)
            chan_header["sensor"] = chan_out.find("sensor_type").text
            chan_header["serial"] = chan_out.find("sensor_sernum").text
            chan_header["scaling"] = chan_out.find("ts_lsb").text
            x1 = float(chan_out.find("pos_x1").text)
            x2 = float(chan_out.find("pos_x2").text)
            y1 = float(chan_out.find("pos_y1").text)
            y2 = float(chan_out.find("pos_y2").text)
            z1 = float(chan_out.find("pos_z1").text)
            z2 = float(chan_out.find("pos_z2").text)
            chan_header["dx"] = abs(x1) + abs(x2)
            chan_header["dy"] = abs(y1) + abs(y2)
            chan_header["dz"] = abs(z1) + abs(z2)
            # in section
            chan_header["gain1"] = chan_in.find("gain_stage1").text
            chan_header["gain2"] = chan_in.find("gain_stage2").text
            chan_header["hchopper"] = chan_in.find("hchopper").text
            chan_header["echopper"] = chan_in.find("echopper").text
            # add data
            chan_headers[chan] = chan_header
        return chan_headers

    def read_data(self, read_from: int, read_to: int) -> TimeData:
        """
        Get unscaled data from an ATS file

        The data units for ATS and internal data formats are as follows:

        - ATS data format has raw data in counts.
        - The raw data unit of the internal format is dependent on what happened to the data before writing it out in the internal format. If the channel header scaling_applied is set to True, no scaling happens in either getUnscaledSamples or getPhysicalSamples. However, if the channel header scaling_applied is set to False, the internal format data will be treated like ATS data, meaning raw data in counts.

        Other notes:

        - ATS files have a header of size 1024 bytes. This offset is applied when reading data.

        Parameters
        ----------
        read_from : int
            Sample to read data from
        read_to : int
            Sample to read data to

        Returns
        -------
        TimeData
            A TimeData instance
        """
        from resistics.common import ProcessHistory

        assert self.headers is not None

        dtype = np.int32
        byteoff = 1024 + np.dtype(dtype).itemsize * read_from
        chans = self.headers.chans
        n_samples = read_to - read_from + 1

        messages = [f"Reading raw data from {self.dir_path}"]
        messages.append(f"Sampling rate {self.headers['fs']} Hz")
        messages.append(f"Reading samples {read_from} to {read_to}")
        data = np.empty(shape=(len(chans), n_samples))
        for idx, chan in enumerate(chans):
            chan_path = self.dir_path / self.headers[chan, "data_files"]
            messages.append(f"Reading data for {chan} from {chan_path.name}")
            data[idx] = np.memmap(
                chan_path, dtype=dtype, mode="r", offset=byteoff, shape=(n_samples)
            )
        headers = self._get_return_headers(read_from, read_to)
        messages.append(f"Time range {headers['first_time']} to {headers['last_time']}")
        record = self._get_process_record(messages)
        logger.info(f"Data successfully read from {self.dir_path}")
        return TimeData(headers, chans, data, ProcessHistory([record]))

    def scale_data(self, time_data: TimeData) -> TimeData:
        r"""
        Get ATS data in physical units

        Resistics will always provide physical samples in field units. That means:

        - Electrical channels in mV/km
        - Magnetic channels in mV
        - To get magnetic fields in nT, calibration needs to be performed

        The raw data units for ATS data are in counts. To get data in field units, ATS data is first multipled by the least significat bit (lsb) defined in the header files,

        .. math::

            data = data * lsb,

        giving data in mV. The lsb includes the gain removal, so no separate gain removal needs to be performed.

        For electrical channels, there is additional step of dividing by the electrode spacing, which is provided in metres. The extra factor of a 1000 is to convert this to km to give mV/km for electric channels

        .. math::

            data = \frac{1000 * data}{spacing}

        To get magnetic channels in nT, the magnetic channels need to be calibrated.

        Parameters
        ----------
        time_data : TimeData
            TimeData read in from file

        Returns
        -------
        TimeData
            TimeData scaled to give physically meaningful units
        """
        messages = ["Scaling raw data to physical units"]
        for chan in time_data.chans:
            lsb = self.headers[chan, "scaling"]
            time_data[chan] = time_data[chan] * lsb
            messages.append(f"Scaling {chan} by least significant bit {lsb}")
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
