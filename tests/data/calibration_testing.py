from dotenv import load_dotenv
from pathlib import Path
import os
from resistics.time import ChanMetadata

from resistics_readers.metronix import SensorCalibrationMetronix
from resistics_readers.spam import SensorCalibrationRSP, SensorCalibrationRSPX

load_dotenv()
data_path = Path(os.getenv("TEST_DATA_PATH_CALIBRATION"))
metronix_path = data_path / "MFS06e607.TXT"
rsp_path = data_path / "Metronix_Coil-----TYPE-006_HF-ID-000135.RSP"
rspx_path = data_path / "Metronix_Coil-----TYPE-006_HF-ID-000135.RSPX"

chan_metadata = ChanMetadata(name="Hx", data_files=["test.dat"], chan_type="magnetic")

cal_data = SensorCalibrationMetronix().read_calibration_data(
    metronix_path, chan_metadata
)
cal_data.plot().show()

cal_data = SensorCalibrationRSP().read_calibration_data(rsp_path, chan_metadata)
cal_data.plot().show()

cal_data = SensorCalibrationRSPX().read_calibration_data(rspx_path, chan_metadata)
cal_data.plot().show()
