class CalibrationMetronix(SensorCalibrationReader):
    def __init__(self, dir_path):
        """Initialise"""
        super().__init__(dir_path, ["sensor", "serial"], ".txt")
        self.optional_metadata = {"chopper": False}

    def check_run(self, metadata: Dict[str, Any]) -> bool:
        """Check to ensure there is sufficient metadata"""
        for required in self.required_metadata:
            if required not in metadata:
                return False
        if metadata["sensor"] <= 0:
            return False
        return True

    def get_names(self, metadata: Dict[str, Any]) -> List[str]:
        """Get the expected name of the calibrate file for the metadata"""
        return [f"{metadata['sensor']}{metadata['serial']}.{self.extension}"]

    def read(self, file_path: Path, metadata: Dict[str, Any]) -> CalibrationData:
        """Read data from metronix calibration file

        Notes
        -----
        Metronix data is in units: F [Hz], Magnitude [V/nT*Hz], Phase [deg] for both chopper on and off.
        Data is returned with units: F [Hz], Magnitude [mV/nT], Phase [radians].

        Dummy values are entered for serial and sensor as these are not specified in the file. Static gain is set to 1 as this is already included in the magnitude.

        Returns
        -------
        CalibrationData
            A calibration data object
        """
        from resistics.common import lines_to_array
        import math

        with file_path.open("r") as f:
            lines = f.readlines()
        lines = [x.strip() for x in lines]

        serial, sensor = self._get_sensor_details(lines)
        il_chopper_on, il_chopper_off = self._get_chopper_lines(lines)
        read_from = il_chopper_on if metadata["chopper"] else il_chopper_off
        data_lines = self._get_data_lines(lines, read_from + 1)
        # convert lines to data frame
        data = lines_to_array(data_lines)
        df = pd.DataFrame(data=data, columns=["frequency", "magnitude", "phase"])
        # unit manipulation - change V/(nT*Hz) to mV/nT
        df["magnitude"] = df["magnitude"] * df["frequency"] * 1000
        # unit manipulation - change phase to radians
        df["phase"] = df["phase"] * (math.pi / 180)
        df = df.set_index("frequency").sort_index()

        return CalibrationData(
            file_path,
            df,
            ProcessHistory(),
            chopper=metadata["chopper"],
            serial=serial,
            sensor=sensor,
            static_gain=1,
        )

    def _get_sensor_details(self, lines: List[str]) -> Tuple[int, str]:
        """Get sensor details from lines read in from a Metronix calibration file

        Parameters
        ----------
        lines : List[str]
            A list of strings read in from a Metronix calibration file

        Returns
        -------
        serial : int
            The serial number of the sensor
        sensor : str
            The type of sensor
        """
        serial = 1
        sensor = ""
        for line in lines:
            if "Magnetometer" in line:
                try:
                    split1 = line.split(":")[1].strip()
                    split2 = split1.split()[0]
                    if "#" in split1:
                        tmp = split2.split("#")
                        sensor = tmp[0].strip()
                        serial = int(tmp[1].strip())
                    else:
                        serial = int(split2.strip())
                    break
                except:
                    logger.warning("Unable to read serial number from calibration file")
        return serial, sensor

    def _get_chopper_lines(self, lines: List[str]) -> Tuple[int, int]:
        """Get the lines indices for starting chopper on and chopper off data

        Parameters
        ----------
        lines : List[str]
            A list of strings read in from a Metronix calibration file

        Returns
        -------
        il_chopper_on : int
            Line number for chopper on
        il_chopper_off : int
            Line number for chopper off
        """
        il_chopper_on: int = 0
        il_chopper_off: int = 0
        for il, line in enumerate(lines):
            if "Chopper On" in line:
                il_chopper_on = il
            if "Chopper Off" in line:
                il_chopper_off = il
        return il_chopper_on, il_chopper_off

    def _get_data_lines(self, lines: List[str], idx: int) -> List[str]:
        """Get the lines of data from the calibration file

        Parameters
        ----------
        lines : List[str]
            List of lines read in from a Metronix calibration file
        idx : int
            Index to start reading from

        Returns
        -------
        List[str]
            List of lines with data in them
        """
        data_lines: List = []
        while idx < len(lines) and lines[idx] != "":
            data_lines.append(lines[idx])
            idx += 1
        return data_lines


class CalibrationRSP(SensorCalibrationReader):
    def __init__(self, dir_path):
        """Initialise"""
        super().__init__(dir_path, ["sensor", "serial", "chopper"], ".RSP")

    def check_run(self, metadata: Dict[str, Any]) -> bool:
        """Check to ensure there is sufficient metadata"""
        for required in self.required_metadata:
            if required not in metadata:
                return False
        if len(metadata["sensor"]) < 5:
            return False
        try:
            int(metadata["sensor"])
        except:
            return False
        return True

    def get_names(self, metadata: Dict[str, Any]) -> List[str]:
        """Get the expected name of the calibrate file for the metadata"""
        serial = metadata["serial"]
        board = "LF" if metadata["chopper"] else "HF"
        sensor_num = int(metadata["sensor"])
        names = [
            f"TYPE-{sensor_num:03d}_BB-ID-{serial:06d}.{self.extension}",
            f"TYPE-{sensor_num:03d}_{board}-ID-{serial:06d}.{self.extension}",
        ]
        return names

    def read(self, file_path: Path, metadata: Dict[str, Any]) -> CalibrationData:
        """Read data from a RSP calibration file

        Notes
        -----
        RSP data is in units: F [Hz], Magnitude [mv/nT], Phase [deg]
        Data is returned with units: F [Hz], Magnitude [mV/nT], Phase [radians]

        Returns
        -------
        CalibrationData
            A calibration data object
        """
        from resistics.common import lines_to_array
        import math

        with open(file_path, "r") as f:
            lines = f.readlines()
        lines = [x.strip() for x in lines]

        serial, sensor = self._get_sensor_details(lines)
        static_gain = self._get_static_gain(lines)
        read_from = self._get_read_from(lines)
        data_lines = self._get_data_lines(lines, read_from + 2)
        # convert lines to data frame
        data = lines_to_array(data_lines)
        df = pd.DataFrame(data=data, columns=["frequency", "magnitude", "phase"])
        # unit manipulation - change V/(nT*Hz) to mV/nT
        df["magnitude"] = df["magnitude"] * static_gain
        # unit manipulation - change phase to radians
        df["phase"] = df["phase"] * (math.pi / 180)
        df = df.set_index("frequency").sort_index()

        return CalibrationData(
            file_path,
            df,
            ProcessHistory(),
            chopper=metadata["chopper"],
            serial=serial,
            sensor=sensor,
            static_gain=1,
        )

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


class CalibrationRSPX(SensorCalibrationReader):
    def __init__(self, dir_path: Path):
        """Initialise"""
        super().__init__(dir_path, ["sensor", "serial", "chopper"], ".RSPX")

    def check_run(self, metadata: Dict[str, Any]) -> bool:
        """Check to ensure there is sufficient metadata"""
        for required in self.required_metadata:
            if required not in metadata:
                return False
        if len(metadata["sensor"]) < 6:
            return False
        return True

    def get_names(self, metadata: Dict[str, Any]) -> List[str]:
        """Get possible calibration file names"""
        serial = metadata["serial"]
        board = "LF" if metadata["chopper"] else "HF"
        sensor_num = int(metadata["sensor"][3:5])
        names = [
            f"TYPE-{sensor_num:03d}_BB-ID-{serial:06d}.{self.extension}",
            f"TYPE-{sensor_num:03d}_{board}-ID-{serial:06d}.{self.extension}",
        ]
        return names

    def read(self, file_path: Path, metadata: Dict[str, Any]) -> CalibrationData:
        """Read data from calibration file

        Notes
        -----
        RSPX data is in units: F [Hz], Magnitude [mv/nT], Phase [deg]
        Data is returned with units: F [Hz], Magnitude [mV/nT], Phase [radians]

        Returns
        -------
        CalibrationData
            A calibration data object
        """
        import xml.etree.ElementTree as ET
        import math

        tree = ET.parse(file_path)
        root = tree.getroot()
        serial, sensor = self._get_sensor_details(root)
        static_gain = self._get_static_gain(root)
        data_list = self._get_data_list(root)
        # convert to data frame
        data = np.array(data_list)
        df = pd.DataFrame(data=data, columns=["frequency", "magnitude", "phase"])
        # unit manipulation - change V/(nT*Hz) to mV/nT
        df["magnitude"] = df["magnitude"] * static_gain
        # unit manipulation - change phase to radians
        df["phase"] = df["phase"] * (math.pi / 180)
        df = df.set_index("frequency").sort_index()

        return CalibrationData(
            file_path,
            df,
            ProcessHistory(),
            chopper=metadata["chopper"],
            serial=serial,
            sensor=sensor,
            static_gain=1,
        )

    def _get_sensor_details(self, root) -> Tuple[int, str]:
        """Get sensor details"""
        # serial
        serial: int = 1
        if root.find("SensorId") is not None:
            serial = int(root.find("SensorId").text)
        # sensor
        sensor: str = ""
        if root.find("SensorSpecification") is not None:
            sensor = root.find("SensorSpecification").text
        return serial, sensor

    def _get_static_gain(self, root) -> float:
        static_gain: float = 1.0
        if root.find("StaticGain") is not None:
            static_gain = float(root.find("StaticGain").text)
        return static_gain

    def _get_data_list(self, root) -> List[List[float]]:
        """Get a list of the data"""
        data_list = []
        for resp in root.findall("ResponseData"):
            data_list.append(
                [
                    float(resp.get("Frequency")),
                    float(resp.get("Magnitude")),
                    float(resp.get("Phase")),
                ]
            )
        return data_list
