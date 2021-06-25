from loguru import logger
from typing import List, Dict, Any, Tuple
from pathlib import Path
import math
import numpy as np
import pandas as pd
from resistics.errors import CalibrationFileReadError
from resistics.time import ChanMetadata
from resistics.calibrate import SensorCalibrationReader, CalibrationData


class SensorCalibrationMetronix(SensorCalibrationReader):
    """
    Metronix calibration data has the following units

    - F [Hz]
    - Magnitude [V/nT*Hz]
    - Phase [deg]

    For both chopper on and off.

    Data is returned with units:

    - F [Hz]
    - Magnitude [mV/nT]
    - Phase [radians]

    Static gain is set to 1 as this is already included in the magnitude

    It is recommended to do extension of the calibration data here as the
    calibration data should be extended in the original units.
    """

    extension: str = ".TXT"
    file_str: str = "$sensor$serial$extension"
    extend: bool = True
    extend_low: float = 0.00001
    extend_high: float = 1000000

    def read_calibration_data(
        self, file_path: Path, chan_metadata: ChanMetadata
    ) -> CalibrationData:
        """
        Read data from metronix calibration file

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
        chopper = chan_metadata.chopper
        data_dict["chopper"] = chopper
        logger.debug(f"Reading calibration data for chopper = {chopper}")
        df = self._read_data(file_path, lines, chopper)
        data_dict["frequency"] = df.index.values.tolist()
        data_dict["magnitude"] = df["magnitude"].values.tolist()
        data_dict["phase"] = df["phase"].values.tolist()
        data_dict["file_path"] = file_path
        return CalibrationData(**data_dict)

    def _read_metadata(self, lines: List[str]) -> Dict[str, Any]:
        """Get the calibration data metadata"""
        sensor, serial = self._get_sensor_details(lines)
        return {
            "serial": serial,
            "sensor": sensor,
            "static_gain": 1,
            "magnitude_unit": "mV/nT",
            "phase_unit": "radians",
        }

    def _get_sensor_details(self, lines: List[str]) -> Tuple[int, str]:
        """Get sensor and serial details"""
        sensor = ""
        serial = 1
        magnetometer = [x for x in lines if "Magnetometer" in x]
        if len(magnetometer) != 1:
            return serial, sensor

        magnetometer_line = magnetometer[0]
        try:
            split1 = magnetometer_line.split(":")[1].strip()
            split2 = split1.split()[0]
            if "#" in split1:
                tmp = split2.split("#")
                sensor = tmp[0].strip()
                serial = int(tmp[1].strip())
            else:
                serial = int(split2.strip())
        except Exception:
            logger.warning("Unable to read serial number from calibration file")
        return sensor, serial

    def _read_data(
        self, file_path: Path, lines: List[str], chopper: bool
    ) -> pd.DataFrame:
        """Read the calibration data"""
        if chopper:
            data_lines = self._get_chopper_on_data(file_path, lines)
        else:
            data_lines = self._get_chopper_off_data(file_path, lines)
        # convert lines to data frame
        data = np.array([x.split() for x in data_lines], dtype=np.float32)
        df = pd.DataFrame(data=data, columns=["frequency", "magnitude", "phase"])
        df = df.set_index("frequency").sort_index()
        if self.extend:
            df = self._extend_data(df)
        # unit manipulation - change V/(nT*Hz) to mV/nT
        df["magnitude"] = df["magnitude"] * df.index.values * 1000
        # unit manipulation - change phase to radians
        df["phase"] = df["phase"] * (math.pi / 180)
        return df

    def _get_chopper_on_data(self, file_path: Path, lines: List[str]) -> List[str]:
        """Get chopper on data"""
        chopper_on_line = None
        for il, line in enumerate(lines):
            if "Chopper On" in line:
                chopper_on_line = il
                break
        if chopper_on_line is None:
            raise CalibrationFileReadError(file_path, "Chopper on line not found")
        return self._get_data_lines(lines, chopper_on_line + 1)

    def _get_chopper_off_data(self, file_path: Path, lines: List[str]) -> List[str]:
        """Get chopper off data"""
        chopper_off_line = None
        for il, line in enumerate(lines):
            if "Chopper Off" in line:
                chopper_off_line = il
                break
        if chopper_off_line is None:
            raise CalibrationFileReadError(file_path, "Chopper off line not found")
        return self._get_data_lines(lines, chopper_off_line + 1)

    def _get_data_lines(self, lines: List[str], idx: int) -> List[str]:
        """Get data lines from the calibration file"""
        data_lines: List = []
        while idx < len(lines) and lines[idx] != "":
            data_lines.append(lines[idx])
            idx += 1
        return data_lines

    def _extend_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extend the calibration data before adjusting units"""
        if self.extend_low < df.index.min():
            df = df.append(
                pd.DataFrame(
                    data={"magnitude": np.nan, "phase": np.nan},
                    index=[self.extend_low],
                )
            )
        if self.extend_high > df.index.max():
            df = df.append(
                pd.DataFrame(
                    data={"magnitude": np.nan, "phase": np.nan},
                    index=[self.extend_high],
                )
            )
        return df.sort_index().ffill().bfill()
