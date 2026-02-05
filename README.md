# WearPark-Embedded — ICM-20948 (Raspberry Pi 5 + Ubuntu)

Objectif : lire Accel / Gyro d’un capteur **Adafruit ICM-20948** en **I2C** avec **Adafruit Blinka**

---

## 1) Branchement (I2C)
- SDA -> GPIO2
- SCL -> GPIO3
- GND -> GND
- VIN -> 3.3V

---

## 2) Activer I2C (Ubuntu sur Raspberry Pi)
Vérifie que le module I2C est chargé :
lsmod | grep i2c

sudo apt update
sudo apt install -y i2c-tools
sudo i2cdetect -y 1

Si nécessaire :
sudo modprobe i2c-dev
sudo modprobe i2c-bcm2835

---

## 3) Création de l'environment
Prerequis nécessaire avant la création de l'environement :
- Vérifier si vous avez comme version python 3.11, car nécessaire pour la librairie adafruit-blinka python --version

Installation de python3.11 :
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-dev

Création de l'environment :
python3.11 -m venv icm-env
source icm-env/bin/activate

Installation librairie nécessaire :
sudo apt update
sudo apt install -y python3 python3-pip gpiod python3-libgpiod
pip install --upgrade pip
pip install --upgrade adafruit-blinka adafruit-circuitpython-icm20x lgpio
pip install requests
pip install python-dotenv

### (Optionnel) utile si Blinka détecte mal le Pi 5
export BLINKA_FORCEBOARD=RPI_5
export BLINKA_FORCECHIP=BCM2712

