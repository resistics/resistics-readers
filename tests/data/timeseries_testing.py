from dotenv import load_dotenv
import os
from typing import Optional, Dict
from pathlib import Path
import resistics.letsgo as letsgo
from resistics.config import Configuration
from resistics.time import TimeReader
from resistics.calibrate import SensorCalibrator, SensorCalibrationReader
from resistics.decimate import DecimationSetup
from resistics.window import WindowerTarget


load_dotenv()
data_path = Path(os.getenv("TEST_DATA_PATH_TIME"))
ats_path = data_path / "metronix_ats"
spam_path = data_path / "spam_raw"
lemi_b423_path = data_path / "lemi_b423"
lemi_b423e_path = data_path / "lemi_b423e"
phoenix_mtu5_path = data_path / "phoenix_mtu5"


def process(
    dir_path: Path,
    reader: TimeReader,
    calibration_reader: Optional[SensorCalibrationReader] = None,
    calibration_path: Optional[Path] = None,
):
    """Process the data"""
    dec_setup = DecimationSetup(n_levels=4, per_level=5)
    windower = WindowerTarget(target=2_000)
    config = Configuration(
        name="test", time_readers=[reader], dec_setup=dec_setup, windower=windower
    )
    if calibration_reader is not None:
        config.sensor_calibrator = SensorCalibrator(readers=[calibration_reader])
    return letsgo.quick_tf(dir_path, config, calibration_path)


def run_ats():
    """Run ATS processing"""
    from resistics_readers.metronix import TimeReaderATS
    from resistics_readers.spam import SensorCalibrationRSP

    solution = process(
        ats_path / "meas_2012-02-10_11-05-00",
        TimeReaderATS(chan_output_key="./recording/output/ATSWriter"),
        SensorCalibrationRSP(
            file_str="Metronix_Coil-----TYPE-$sensor_BB-ID-$serial$extension"
        ),
        ats_path,
    )
    solution.tf.plot(solution.freqs, solution.components).show()


def run_spam():
    """Run SPAM processing"""
    from resistics_readers.spam import TimeReaderXTR, SensorCalibrationRSP

    solution = process(
        spam_path / "wittstock",
        TimeReaderXTR(),
        SensorCalibrationRSP(),
        spam_path,
    )
    solution.tf.plot(solution.freqs, solution.components).show()


def run_lemi_b423():
    """Run Lemi B423 processing"""
    from resistics_readers.lemi.b423 import make_B423_metadata
    from resistics_readers.lemi import TimeReaderB423
    from resistics.calibrate import SensorCalibrationTXT

    make_B423_metadata(
        lemi_b423_path / "GTB6B",
        500,
        hx_serial=712,
        hy_serial=710,
        hz_serial=714,
        h_gain=16,
        dx=60,
        dy=60.7,
    )
    solution = process(
        lemi_b423_path / "GTB6B",
        TimeReaderB423(),
        SensorCalibrationTXT(file_str="lemi120_IC_$serial$extension"),
        lemi_b423_path,
    )
    solution.tf.plot(solution.freqs, solution.components).show()


def run_lemi_b423e():
    """Run Lemi B423E processing"""
    from resistics_readers.lemi.b423e import make_B423E_metadata
    from resistics_readers.lemi import TimeReaderB423E

    make_B423E_metadata(
        lemi_b423e_path / "GTB7T", 500, chans=["Ex", "Ey", "E3", "E4"], dx=60, dy=60.7
    )
    config = Configuration(name="testing", time_readers=[TimeReaderB423E()])
    letsgo.quick_view(lemi_b423e_path / "GTB7T", config)


def run_phoenix_mtu5():
    """Run Phoenix processing"""
    from resistics_readers.phoenix import TimeReaderTS

    solution = process(phoenix_mtu5_path / "RV021", TimeReaderTS())
    solution.tf.plot(solution.freqs, solution.components).show()


def run_phoenix_mtu5_reformat():
    """Run phoenix reformatting followed up by processing"""
    from resistics_readers.phoenix.mtu5 import read_metadata, reformat
    from resistics.time import TimeReaderNumpy

    metadata = read_metadata(phoenix_mtu5_path / "RV021")
    for ts in metadata.ts_nums:
        ts_path = phoenix_mtu5_path / "reformat" / f"ts_{ts:d}"
        reformat(phoenix_mtu5_path / "RV021", metadata, ts, ts_path)
    for ts in metadata.ts_nums:
        ts_path = phoenix_mtu5_path / "reformat" / f"ts_{ts:d}"
        solution = process(ts_path, TimeReaderNumpy())
        solution.tf.plot(solution.freqs, solution.components).show()


def run_miniseed_reformat(dir_path: Path, fs: float, id_map: Dict[str, str]):
    """An example for miniseed reformatting. Ideally want a smaller file for testing"""
    from resistics_readers.miniseed.mseed import reformat
    from pathlib import Path

    # id_map = {"XM.EDD..HHE": "Hx", "XM.EDD..HHN": "Hy", "XM.EDD..HHZ": "Hz"}
    chunk_time = "1D"
    reformat(dir_path, fs, id_map, chunk_time, Path("..", "reformatted"))


if __name__ == "__main__":
    run_ats()
    run_spam()
    run_lemi_b423()
    run_lemi_b423e()
    run_phoenix_mtu5()
    run_phoenix_mtu5_reformat()
