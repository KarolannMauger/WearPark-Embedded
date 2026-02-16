import board
import adafruit_icm20x

# The ICM20948Sensor class provides an interface to read data from the ICM20948 sensor, which includes an accelerometer and a gyroscope.
class ICM20948Sensor:
    # The constructor initializes the ICM20948 sensor by setting up the I2C communication and creating an instance of the sensor class from the adafruit_icm20x library.
    def __init__(self):
        i2c = board.I2C()
        self._icm = adafruit_icm20x.ICM20948(i2c)

    # The read method retrieves the current accelerometer and gyroscope readings from the sensor and returns them as a tuple of six float values: ax, ay, az for acceleration, and gx, gy, gz for gyroscope data.
    def read(self) -> tuple[float, float, float, float, float, float]:
        ax, ay, az = self._icm.acceleration
        gx, gy, gz = self._icm.gyro
        return ax, ay, az, gx, gy, gz
