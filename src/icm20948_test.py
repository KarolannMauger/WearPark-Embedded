import time
import board
import adafruit_icm20x

def main():
    i2c = board.I2C()
    icm = adafruit_icm20x.ICM20948(i2c)

    while True:
        ax, ay, az = icm.acceleration
        gx, gy, gz = icm.gyro
        mx, my, mz = icm.magnetic

        print(f"Accel (m/s²): {ax:.2f}, {ay:.2f}, {az:.2f}")
        print(f"Gyro  (rad/s): {gx:.2f}, {gy:.2f}, {gz:.2f}")
        print(f"Mag   (uT):    {mx:.2f}, {my:.2f}, {mz:.2f}")
        print("-" * 40)
        time.sleep(1)

if __name__ == "__main__":
    main()