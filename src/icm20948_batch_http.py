import time
import json
import requests
from datetime import datetime, timedelta, timezone

import board
import adafruit_icm20x
import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL")
DEVICE_ID = os.getenv("DEVICE_ID", "unknown-device")
SAMPLE_RATE_HZ = int(os.getenv("SAMPLE_RATE_HZ", 50))
WINDOW_SECONDS = int(os.getenv("WINDOW_SECONDS", 10))
TIMEOUT_S = int(os.getenv("TIMEOUT_S", 5))
JWT_TOKEN = os.getenv("JWT_TOKEN")


HEADERS = {
    "Content-Type": "application/json",
}

if JWT_TOKEN:
    HEADERS["Authorization"] = f"Bearer {JWT_TOKEN}"

def current_time_millis():
    return datetime.now(timezone(timedelta(hours=-5), 'EST')).isoformat()

def main():
    i2c = board.I2C()
    icm = adafruit_icm20x.ICM20948(i2c)

    period = 1.0 / SAMPLE_RATE_HZ
    max_samples = int(SAMPLE_RATE_HZ * WINDOW_SECONDS)
    print(f"Sampling at {SAMPLE_RATE_HZ} Hz, sending every {WINDOW_SECONDS} seconds ({max_samples} samples per batch)")

    accel_ax_buf = []
    accel_ay_buf = []
    accel_az_buf = []
    gyro__gx_buf = []
    gyro__gy_buf = []
    gyro__gz_buf = []

    ts_start = None

    while True:
        if ts_start is None:
            ts_start = current_time_millis()
        
        t0 = time.time()
        ax, ay, az = icm.acceleration
        gx, gy, gz = icm.gyro

        accel_ax_buf.append(ax)
        accel_ay_buf.append(ay)
        accel_az_buf.append(az)
        gyro__gx_buf.append(gx)
        gyro__gy_buf.append(gy)
        gyro__gz_buf.append(gz)
        

        if len(accel_ax_buf) >= max_samples:
            ts_end = current_time_millis()
            payload = {
                "start": ts_start,
                "end": ts_end,
                "data" : {
                    "ax" : accel_ax_buf,
                    "ay" : accel_ay_buf,
                    "az" : accel_az_buf,
                    "gx" : gyro__gx_buf,
                    "gy" : gyro__gy_buf,
                    "gz" : gyro__gz_buf,
                }
                
            }
            try:
                #with open("data.json", "w") as file:
                #    json.dump(payload, file, indent=2)

                r = requests.post(
                    BACKEND_URL,
                    headers=HEADERS,
                    data=json.dumps(payload, indent=2),
                    timeout=TIMEOUT_S,
                )
                if 200 <= r.status_code < 300:
                    print(f"Data sent successfully: {r.status_code}")
                    accel_ax_buf.clear()
                    accel_ay_buf.clear()
                    accel_az_buf.clear()
                    gyro__gx_buf.clear()
                    gyro__gy_buf.clear()
                    gyro__gz_buf.clear()
                    ts_start = None
                else:
                    print(f"Error sending data: {r.status_code} - {r.text}")
            except Exception as e:
                print(f"Exception during data send: {e}")
            

        elapsed = time.time() - t0
        #print(f"Elapsed time for batch send: {elapsed:.2f} seconds")
        sleep_s = period - elapsed
        if sleep_s > 0:
            print(f"Sleeping for {sleep_s:.2f} seconds to maintain sample rate")
            time.sleep(sleep_s)
            
        #accel_buf.clear()
        #gyro_buf.clear()
        #mag_buf.clear()
        #ts_start = None

if __name__ == "__main__":
    main()