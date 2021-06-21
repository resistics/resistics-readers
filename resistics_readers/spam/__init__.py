"""
Subpackage with readers for SPAM data, including

- Readers for time series data
- Readers for calibration files
"""
from resistics_readers.spam.spam import TimeReaderXTR  # noqa
from resistics_readers.spam.calibration import SensorCalibrationRSP  # noqa
from resistics_readers.spam.calibration import SensorCalibrationRSPX  # noqa
