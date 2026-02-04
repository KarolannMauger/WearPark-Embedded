# WearPark-Embedded — ICM-20948 (Raspberry Pi 5 + Ubuntu)

Objectif : lire Accel / Gyro / Mag d’un capteur **Adafruit ICM-20948** en **I2C** avec **Adafruit Blinka** (sans `.venv`).

---

## 1) Branchement (I2C)
- SDA -> GPIO2 (pin 3)
- SCL -> GPIO3 (pin 5)
- GND -> GND (pin 6)
- VIN -> 3.3V (pin 1) ou 5V si ton breakout accepte VIN (souvent oui)

---

## 2) Activer I2C (Ubuntu sur Raspberry Pi)
Vérifie que le module I2C est chargé :
lsmod | grep i2c


sudo apt update
sudo apt install -y i2c-tools
sudo i2cdetect -y 1


sudo apt update
sudo apt install -y python3 python3-pip gpiod python3-libgpiod
sudo pip3 install --upgrade pip
sudo pip3 install --upgrade adafruit-blinka adafruit-circuitpython-icm20x lgpio

### (Optionnel) utile si Blinka détecte mal le Pi 5
export BLINKA_FORCEBOARD=RPI_5
export BLINKA_FORCECHIP=BCM2712

python3 src/icm20948_test.py