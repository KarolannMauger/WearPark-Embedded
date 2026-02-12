import board
import adafruit_icm20x

class ICM20948Sensor:
    def __init__(self):
        i2c = board.I2C()
        self._icm = adafruit_icm20x.ICM20948(i2c)

    def read(self) -> tuple[float, float, float, float, float, float]:
        ax, ay, az = self._icm.acceleration
        gx, gy, gz = self._icm.gyro
        return ax, ay, az, gx, gy, gz
