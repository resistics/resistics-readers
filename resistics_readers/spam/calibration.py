from typing import List, Dict, Any, Tuple
from pathlib import Path
import re
import numpy as np
import pandas as pd
from xml.etree.ElementTree import Element  # noqa: S405
import defusedxml.ElementTree as ET
from resistics.time import ChanMetadata
from resistics.calibrate import SensorCalibrationReader, CalibrationData
from resistics.spectra import SpectraMetadata


class SensorCalibration_RSP_RSPX_Base(SensorCalibrationReader):
    """Base class for RSP and RSPX calibration data readers"""

    file_str: str = "Metronix_Coil-----TYPE-$sensor_$chopper-ID-$serial$extension"
    """The file string to search for. Various parameters will be substituted"""

    def _get_path(self, dir_path: Path, metadata: SpectraMetadata, chan: str) -> Path:
        """
        Get the path to the calibration file

        Parameters
        ----------
        dir_path : Path
            The directory  path to look for calibration files
        metadata : SpectraMetadata
            SpectraMetadata with data information
        chan : str
            The channel to calibrate

        Returns
        -------
        Path
            The path to the calibration file
        """
        chan_metadata = metadata.chans_metadata[chan]
        chopper_str = "LF" if chan_metadata.chopper else "HF"
        sensor_str = re.sub("[^0-9]", "", chan_metadata.sensor)
        sensor_str = f"{int(sensor_str):03d}"
        serial_str = f"{int(chan_metadata.serial):06d}"
        file_name = self.file_str.replace("$sensor", sensor_str)
        file_name = file_name.replace("$serial", serial_str)
        file_name = file_name.replace("$chopper", chopper_str)
        file_name = file_name.replace("$extension", self.extension)
        return dir_path / file_name

    def _get_chopper(self, file_path: Path) -> bool:
        """Get whether the calibration is chopper on or off"""
        if "LF" in file_path.stem or "BB" in file_path.stem:
            return True
        return False


class SensorCalibrationRSP(SensorCalibration_RSP_RSPX_Base):
    """
    Reader for RSP calibration files

    RSP data is in units:

    - F [Hz]
    - Magnitude [mv/nT]
    - Phase [deg]

    Data is returned with units:

    - F [Hz]
    - Magnitude [mV/nT]
    - Phase [radians]

    The static gain for RSP files is applied to the magnitude as it is read in
    """

    extension: str = ".RSP"

    def read_calibration_data(
        self, file_path: Path, chan_metadata: ChanMetadata
    ) -> CalibrationData:
        """
        Read data from a RSP calibration file

        Parameters
        ----------
        file_path : Path
            The file path of the calibration file
        chan_metadata : ChanMetadata
            The channel metadata for the channel to be calibrated

        Returns
        -------
        CalibrationData
            The calibration data
        """
        with file_path.open("r") as f:
            lines = f.readlines()
        lines = [x.strip() for x in lines]
        data_dict = self._read_metadata(lines)
        data_dict["chopper"] = self._get_chopper(file_path)
        df = self._read_data(lines)
        df["magnitude"] = df["magnitude"] * data_dict["static_gain"]
        df["phase"] = df["phase"] * (np.pi / 180)
        data_dict["frequency"] = df.index.values.tolist()
        data_dict["magnitude"] = df["magnitude"].values.tolist()
        data_dict["phase"] = df["phase"].values.tolist()
        data_dict["file_path"] = file_path
        return CalibrationData(**data_dict)

    def _read_metadata(self, lines: List[str]) -> Dict[str, Any]:
        """Read the calibration file metadata"""
        serial, sensor = self._get_sensor_details(lines)
        static_gain = self._get_static_gain(lines)
        return {
            "serial": serial,
            "sensor": sensor,
            "static_gain": static_gain,
            "magnitude_unit": "mV/nT",
            "phase_unit": "radians",
        }

    def _get_sensor_details(self, lines: List[str]) -> Tuple[int, str]:
        """Get sensor details from the file"""
        serial: int = 1
        sensor: str = ""
        for line in lines:
            if "induction coil no" in line:
                split1 = line.split(":")[1]
                serial = int(split1.split("-")[0].strip())
            if "SensorType" in line:
                sensor = line.split()[1]
        return serial, sensor

    def _get_static_gain(self, lines: List[str]) -> float:
        static_gain: float = 1.0
        for line in lines:
            if "StaticGain" in line:
                static_gain = float(line.split()[1])
                return static_gain
        return static_gain

    def _read_data(self, lines: List[str]) -> pd.DataFrame:
        """Read data from calibration file"""
        read_from = self._get_read_from(lines)
        data_lines = self._get_data_lines(lines, read_from)
        data = np.array([x.split() for x in data_lines], dtype=np.float32)
        df = pd.DataFrame(data=data, columns=["frequency", "magnitude", "phase"])
        return df.set_index("frequency").sort_index()

    def _get_read_from(self, lines: List[str]) -> int:
        """Get the line number to read from"""
        for idx, line in enumerate(lines):
            if "FREQUENCY" in line:
                return idx + 2
        raise ValueError("Unable to determine location of data in file")

    def _get_data_lines(self, lines: List[str], idx: int) -> List[str]:
        """Get the data lines out of the file"""
        data_lines: List[str] = []
        while idx < len(lines) and lines[idx] != "":
            data_lines.append(lines[idx])
            idx += 1
        return data_lines


class SensorCalibrationRSPX(SensorCalibration_RSP_RSPX_Base):
    """
    Read data from RSPX calibration file

    RSPX data is in units:

    - F [Hz]
    - Magnitude [mv/nT]
    - Phase [deg]

    Data is returned with units:

    - F [Hz]
    - Magnitude [mV/nT]
    - Phase [radians]

    Static gain is applied to the magnitude
    """

    extension: str = ".RSPX"

    def read_calibration_data(
        self, file_path: Path, chan_metadata: ChanMetadata
    ) -> CalibrationData:
        """
        Read RSPX file

        Parameters
        ----------
        file_path : Path
            The file path of the calibration file
        chan_metadata : ChanMetadata
            The channel metadata for the channel to be calibrated

        Returns
        -------
        CalibrationData
            The calibration data
        """
        root = ET.parse(file_path).getroot()
        data_dict = self._read_metadata(root)
        data_dict["chopper"] = self._get_chopper(file_path)
        df = self._read_data(root)
        df["magnitude"] = df["magnitude"] * data_dict["static_gain"]
        df["phase"] = df["phase"] * (np.pi / 180)
        data_dict["frequency"] = df.index.values.tolist()
        data_dict["magnitude"] = df["magnitude"].values.tolist()
        data_dict["phase"] = df["phase"].values.tolist()
        data_dict["file_path"] = file_path
        return CalibrationData(**data_dict)

    def _read_metadata(self, root: Element) -> Dict[str, Any]:
        """Read the calibration file metadata"""
        serial, sensor = self._get_sensor_details(root)
        static_gain = self._get_static_gain(root)
        return {
            "serial": serial,
            "sensor": sensor,
            "static_gain": static_gain,
            "magnitude_unit": "mV/nT",
            "phase_unit": "radians",
        }

    def _get_sensor_details(self, root: Element) -> Tuple[int, str]:
        """Get sensor details"""
        serial: int = 1
        if root.find("SensorId") is not None:
            serial = int(root.find("SensorId").text)
        sensor: str = ""
        if root.find("SensorSpecification") is not None:
            sensor = root.find("SensorSpecification").text
        return serial, sensor

    def _get_static_gain(self, root) -> float:
        """Get the static gain"""
        static_gain: float = 1.0
        if root.find("StaticGain") is not None:
            static_gain = float(root.find("StaticGain").text)
        return static_gain

    def _read_data(self, root: Element) -> pd.DataFrame:
        """Get data in a DataFrame"""
        data = []
        for resp in root.findall("ResponseData"):
            data.append(
                [
                    np.float32(resp.get("Frequency")),
                    np.float32(resp.get("Magnitude")),
                    np.float32(resp.get("Phase")),
                ]
            )
        df = pd.DataFrame(data=data, columns=["frequency", "magnitude", "phase"])
        return df.set_index("frequency").sort_index()
