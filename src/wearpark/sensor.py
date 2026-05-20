try:
    import board
    import adafruit_icm20x
    _SENSOR_AVAILABLE = True
    _SENSOR_IMPORT_ERROR = None
except Exception as e:
    board = None
    adafruit_icm20x = None
    _SENSOR_AVAILABLE = False
    _SENSOR_IMPORT_ERROR = e
from .errors import ErrorCode, WearParkError

# The ICM20948Sensor class provides an interface to read data from the ICM20948 sensor, which includes an accelerometer and a gyroscope.
class ICM20948Sensor:
    # The constructor initializes the ICM20948 sensor by setting up the I2C communication and creating an instance of the sensor class from the adafruit_icm20x library.
    def __init__(self):
        try:
            if not _SENSOR_AVAILABLE:
                raise WearParkError(
                    ErrorCode.SENSOR_INIT_FAILED,
                    f"ICM20948 dependencies not available: {_SENSOR_IMPORT_ERROR}",
                )
            i2c = board.I2C()
            self._icm = adafruit_icm20x.ICM20948(i2c)
        except Exception as e:
            raise WearParkError(ErrorCode.SENSOR_INIT_FAILED, str(e)) from e

    # The read method retrieves the current accelerometer and gyroscope readings from the sensor and returns them as a tuple of six float values: ax, ay, az for acceleration, and gx, gy, gz for gyroscope data.
    def read(self) -> tuple[float, float, float, float, float, float]:
        try:
            ax, ay, az = self._icm.acceleration
            gx, gy, gz = self._icm.gyro
            return ax, ay, az, gx, gy, gz
        except Exception as e:
            raise WearParkError(ErrorCode.SENSOR_READ_FAILED, str(e)) from e