"""
Classes for reading Metronix time series data
"""
from loguru import logger
from typing import Dict, Any
from pathlib import Path
from xml.etree.ElementTree import Element  # noqa: S405
import defusedxml.ElementTree as ET
import numpy as np
from resistics.time import TimeMetadata, TimeData, TimeReader


class TimeReaderATS(TimeReader):
    r"""Data reader for ATS formatted data

    For ATS files, header information is XML formatted. The end time in ATS
    header files is actually one sample past the time of the last sample.
    TimeReaderATS handles this and gives a last time corresponding to the actual
    timestamp of the last sample.

    Notes
    -----
    The raw data units for ATS data are in counts. To get data in field units,
    ATS data is first multipled by the least significat bit (lsb) defined in the
    metadata files,

    .. math::

        data = data * lsb,

    giving data in mV. The lsb includes the gain removal, so no separate gain
    removal needs to be performed.

    For electrical channels, there is additional step of dividing by the
    electrode spacing, which is provided in metres. The extra factor of a 1000
    is to convert this to km to give mV/km for electric channels

    .. math::

        data = \frac{1000 * data}{spacing}

    Finally, to get magnetic channels in nT, the magnetic channels need to be
    calibrated.
    """

    extension = ".ats"

    def read_metadata(self, dir_path: Path) -> TimeMetadata:
        """
        Read the time series data metadata and return

        Parameters
        ----------
        dir_path : Path
            Path to time series data directory

        Returns
        -------
        TimeMetadata
            Metadata for time series data

        Raises
        ------
        TimeDataReadError
            If extension is not defined
        MetadataReadError
            If incorrect number of xml files found
        MetadataReadError
            If there is a mismatch between number of channels and actual
            channels found
        MetadataReadError
            If there is a mismatch between the number of samples calculated from
            the first and last times and the number of samples provided for each
            channel
        TimeDataReadError
            If not all data files exist
        TimeDataReadError
            if the data files have the wrong extension
        """
        from resistics.errors import MetadataReadError, TimeDataReadError
        from resistics.time import get_time_metadata

        xml_files = list(dir_path.glob("*.xml"))
        if len(xml_files) != 1:
            raise MetadataReadError(dir_path, "> 1 xml file in data directory")
        metadata_path = xml_files[0]
        root = ET.parse(metadata_path).getroot()
        time_dict = self._read_common_metadata(root)
        chans_dict = self._read_chans_metadata(metadata_path, root)
        chans = list(chans_dict.keys())
        if time_dict["n_chans"] != len(chans_dict):
            raise MetadataReadError(
                metadata_path,
                f"Mismatch between n_chans {len(chans_dict)} and channels {chans}",
            )
        time_dict["chans"] = chans
        # check consistency in number of samples
        rec_samples = time_dict["n_samples"]
        for chan, chan_metadata in chans_dict.items():
            chan_samples = chan_metadata["n_samples"]
            if rec_samples != chan_samples:
                logger.warning(
                    f"Recording samples {rec_samples} != {chan} samples {chan_samples}"
                )
            if rec_samples > chan_samples:
                raise MetadataReadError("Recording samples > chan samples")
        metadata = get_time_metadata(time_dict, chans_dict)

        if not self._check_data_files(dir_path, metadata):
            raise TimeDataReadError(dir_path, "All data files do not exist")
        if not self._check_extensions(dir_path, metadata):
            raise TimeDataReadError(dir_path, f"Data file suffix not {self.extension}")
        return metadata

    def _read_common_metadata(self, root: Element) -> Dict[str, Any]:
        """
        Read common time metadata from the XML file

        .. note::

            Metronix stop time is the timestamp after the last sample. This is
            corrected here.

        Parameters
        ----------
        root : Element
            Root element of XML file

        Returns
        -------
        Dict[str, Any]
            Dictionary of dataset headers
        """
        from resistics.sampling import to_datetime, to_timedelta, to_n_samples

        rec_key = "./recording"
        glo_key = "./input/ADU07Hardware/global_config"
        # recording section
        rec = root.find(rec_key)
        first_time = rec.find("start_date").text + " " + rec.find("start_time").text
        last_time = rec.find("stop_date").text + " " + rec.find("stop_time").text
        # global config section
        glo = rec.find(glo_key)
        fs = float(glo.find("sample_freq").text)
        n_chans = int(glo.find("meas_channels").text)
        # convert to datetime formats
        first_time = to_datetime(first_time)
        last_time = to_datetime(last_time) - to_timedelta(1 / fs)
        n_samples = to_n_samples(last_time - first_time, fs)
        return {
            "fs": fs,
            "n_chans": n_chans,
            "n_samples": n_samples,
            "first_time": first_time,
            "last_time": last_time,
        }

    def _read_chans_metadata(
        self, metadata_path: Path, root: Element
    ) -> Dict[str, Dict[str, Any]]:
        """
        Read channel metadata

        Parameters
        ----------
        metadata_path: Path
            The path to the header file
        root : Element
            Root element of XML file

        Returns
        -------
        Dict[str, Dict[str, Any]]
            Channel headers

        Raises
        ------
        MetadataReadError
            Failed to find recording outputs channel information (wrong key)
        MetadataReadError
            No channel information found in recording outputs channel information
        MetadataReadError
            Mismatch between input and output channel sections
        """
        from resistics.errors import MetadataReadError

        chan_input_key = "./recording/input/ADU07Hardware/channel_config/channel"
        chan_output_key = "./recording/output/"
        chan_inputs = root.findall(chan_input_key)
        try:
            chan_outputs = root.find(chan_output_key)
            chan_outputs = chan_outputs.find(".//ATSWriter")
            chan_outputs = chan_outputs.findall("configuration/channel")
        except Exception:
            raise MetadataReadError(
                metadata_path, f"Failed to read channel data from {chan_output_key}"
            )
        if chan_outputs is None or len(chan_outputs) == 0:
            raise MetadataReadError(
                metadata_path, f"No channels found in {chan_output_key}"
            )
        if len(chan_outputs) != len(chan_inputs):
            raise MetadataReadError(
                metadata_path,
                f"Channel mismatch between {chan_input_key}, {chan_output_key}",
            )

        chans_dict = {}
        for chan_in, chan_out in zip(chan_inputs, chan_outputs):
            chan_metadata = {}
            # out section
            chan = chan_out.find("channel_type").text
            chan_metadata["data_files"] = chan_out.find("ats_data_file").text
            chan_metadata["n_samples"] = int(chan_out.find("num_samples").text)
            chan_metadata["sensor"] = chan_out.find("sensor_type").text
            chan_metadata["serial"] = chan_out.find("sensor_sernum").text
            chan_metadata["scaling"] = chan_out.find("ts_lsb").text
            x1 = float(chan_out.find("pos_x1").text)
            x2 = float(chan_out.find("pos_x2").text)
            y1 = float(chan_out.find("pos_y1").text)
            y2 = float(chan_out.find("pos_y2").text)
            z1 = float(chan_out.find("pos_z1").text)
            z2 = float(chan_out.find("pos_z2").text)
            chan_metadata["dx"] = abs(x1) + abs(x2)
            chan_metadata["dy"] = abs(y1) + abs(y2)
            chan_metadata["dz"] = abs(z1) + abs(z2)
            # in section
            chan_metadata["gain1"] = chan_in.find("gain_stage1").text
            chan_metadata["gain2"] = chan_in.find("gain_stage2").text
            chan_metadata["hchopper"] = chan_in.find("hchopper").text
            chan_metadata["echopper"] = chan_in.find("echopper").text
            # add data
            chans_dict[chan] = chan_metadata
        return chans_dict

    def read_data(
        self, dir_path: Path, metadata: TimeMetadata, read_from: int, read_to: int
    ) -> TimeData:
        """
        Get unscaled data from an ATS file

        The raw data units for ATS are counts.

        Other notes:

        - ATS files have a header of size 1024 bytes
        - A byte offset of 1024 is therefore applied when reading data

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
            A TimeData instance
        """
        dtype = np.int32
        byteoff = 1024 + np.dtype(dtype).itemsize * read_from
        n_samples = read_to - read_from + 1

        messages = [f"Reading raw data from {dir_path}"]
        messages.append(f"Sampling rate {metadata.fs} Hz")
        messages.append(f"Reading samples {read_from} to {read_to}")
        data = np.empty(shape=(metadata.n_chans, n_samples), dtype=np.float32)
        for idx, chan in enumerate(metadata.chans):
            chan_path = dir_path / metadata.chans_metadata[chan].data_files[0]
            messages.append(f"Reading data for {chan} from {chan_path.name}")
            data[idx] = np.memmap(
                chan_path, dtype=dtype, mode="r", offset=byteoff, shape=(n_samples)
            )
        metadata = self._get_return_metadata(metadata, read_from, read_to)
        messages.append(f"From sample, time: {read_from}, {str(metadata.first_time)}")
        messages.append(f"To sample, time: {read_to}, {str(metadata.last_time)}")
        metadata.history.add_record(self._get_record(messages))
        logger.info(f"Data successfully read from {dir_path}")
        return TimeData(metadata, data)

    def scale_data(self, time_data: TimeData) -> TimeData:
        r"""
        Get ATS data in physical units

        Resistics will always provide physical samples in field units. That
        means:

        - Electrical channels in mV/km
        - Magnetic channels in mV
        - To get magnetic fields in nT, calibration needs to be performed

        The raw data units for ATS data are in counts. To get data in field
        units, ATS data is first multipled by the least significat bit (lsb)
        defined in the header files,

        .. math::

            data = data * lsb,

        giving data in mV. The lsb includes the gain removal, so no separate
        gain removal needs to be performed.

        For electrical channels, there is additional step of dividing by the
        electrode spacing, which is provided in metres. The extra factor of a
        1000 is to convert this to km to give mV/km for electric channels

        .. math::

            data = \frac{1000 * data}{spacing}

        To get magnetic channels in nT, the magnetic channels need to be
        calibrated.

        Parameters
        ----------
        time_data : TimeData
            TimeData read in from file

        Returns
        -------
        TimeData
            TimeData scaled to give physically meaningful units
        """
        logger.info("Applying scaling to data to give field units")
        messages = ["Scaling raw data to physical units"]
        for chan in time_data.metadata.chans:
            chan_metadata = time_data.metadata.chans_metadata[chan]
            lsb = chan_metadata.scaling
            time_data[chan] = time_data[chan] * lsb
            messages.append(f"Scaling {chan} by least significant bit {lsb}")
            if chan == "Ex":
                dx_km = chan_metadata.dx / 1000
                time_data[chan] = time_data[chan] / dx_km
                messages.append(f"Dividing {chan} by dipole length {dx_km} km")
            if chan == "Ey":
                dy_km = chan_metadata.dy / 1000
                time_data[chan] = time_data[chan] / dy_km
                messages.append(f"Dividing {chan} by dipole length {dy_km} km")
        record = self._get_record(messages)
        time_data.metadata.history.add_record(record)
        return time_data
