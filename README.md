# WearPark Embedded

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![Raspberry Pi](https://img.shields.io/badge/Raspberry_Pi-5-C51A4A?style=flat&logo=raspberrypi&logoColor=white)
![ICM-20948](https://img.shields.io/badge/IMU-ICM--20948-00979D?style=flat)
![Coverage](https://img.shields.io/badge/coverage-%E2%89%A580%25-brightgreen?style=flat)

> Embedded data acquisition and streaming application for the WearPark wrist-worn IMU sensor.
> Part of the **WearPark** research project.

---

## Overview

WearPark Embedded runs on a **Raspberry Pi 5** and continuously reads 6-axis motion data (accelerometer + gyroscope) from an **Adafruit ICM-20948** sensor at 50 Hz via I2C. Samples are packed into a custom little-endian binary protocol and streamed in real time over TCP (with optional mutual TLS) to the WearPark backend server.

A producer-consumer architecture with a bounded in-memory queue ensures resilience against network interruptions — data is buffered locally and flushed on reconnection.

---

## System Architecture

```
ICM-20948 (50 Hz, I2C)
      │
      ▼
  ICM20948Sensor
      │  (ax, ay, az, gx, gy, gz)
      ▼
  Producer Thread
      │  Sample dataclass
      ▼
  MemQueue (bounded FIFO)
      │  batch pop
      ▼
  Sender Thread
      ├─ TCP connect / reconnect loop
      ├─ mTLS handshake (optional)
      ├─ Auth frame exchange
      └─ Binary frame stream
            │
            ▼
      Backend (Java Spring Boot / Netty port 9000)
```

---

## Features

- **50 Hz sampling** — Reads accelerometer and gyroscope at configurable rate
- **Binary protocol** — Little-endian struct-packed frames (auth + sensor data), minimizing payload size
- **mTLS support** — Optional mutual TLS with CA cert, client cert and key
- **Auth handshake** — Timestamp-based auth frame exchanged before streaming begins
- **Producer-consumer** — Sensor reads and network sends run in separate threads
- **Bounded queue** — `MemQueue` evicts oldest samples on overflow to cap memory usage
- **Auto-reconnect** — Exponential backoff reconnection loop on network failure
- **Structured logging** — Rotating file + console handler, configurable log level

---

## Repository Structure

```
WearPark-Embedded/
├── src/
│   ├── main.py                  # Entry point
│   ├── icm20948_test.py         # Direct sensor test script
│   └── wearpark/
│       ├── config.py            # Settings dataclass (env vars)
│       ├── errors.py            # ErrorCode enum + WearParkError
│       ├── sensor.py            # ICM20948 wrapper (Adafruit Blinka)
│       ├── protocol.py          # Binary frame encoding
│       ├── tcp_client.py        # TCP client with TLS/mTLS
│       ├── mem_queue.py         # Bounded FIFO queue
│       ├── streamer.py          # Producer-consumer orchestration
│       └── logging_config.py   # Rotating file handler setup
├── src/tests/
│   ├── conftest.py              # Pytest fixtures
│   └── unit/
│       ├── test_protocol.py
│       ├── test_sensor.py
│       ├── test_tcp_client.py
│       ├── test_mem_queue.py
│       └── test_streamer.py
├── .env.example                 # Configuration template
├── Makefile                     # test / security / clean commands
├── pytest.ini                   # Test config (80% coverage threshold)
├── bandit.ini                   # Security scan config
└── requirements-test.txt        # Test dependencies
```

---

## Getting Started

### 1. Prerequisites

- Raspberry Pi 5 running Ubuntu
- Python 3.11+
- I2C enabled
- Required system packages:

```bash
sudo apt install -y i2c-tools python3-libgpiod
```

Verify I2C is loaded:

```bash
lsmod | grep i2c
sudo i2cdetect -y 1
# Should show address 0x68 or 0x69
```

If not detected:

```bash
sudo modprobe i2c-dev
sudo modprobe i2c-bcm2835
```

### 2. Hardware wiring (ICM-20948)

| ICM-20948 Pin | Raspberry Pi 5 Pin |
|---|---|
| VIN | 3.3V (Pin 1) |
| GND | GND (Pin 6) |
| SDA | GPIO 2 (Pin 3) |
| SCL | GPIO 3 (Pin 5) |

### 3. Install dependencies

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install adafruit-blinka adafruit-circuitpython-icm20x lgpio python-dotenv
```

> If Blinka does not detect the Raspberry Pi 5 correctly:
> ```bash
> export BLINKA_FORCEBOARD=RPI_5
> export BLINKA_FORCECHIP=BCM2712
> ```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your backend host, TLS certificates, and JWT token. See the [Configuration](#configuration) section for all available variables.

### 5. Run

```bash
python src/main.py
```

To verify the sensor is working before streaming:

```bash
python src/icm20948_test.py
```

---

## Configuration

All settings are loaded from environment variables via `.env`.

### Network

| Variable | Default | Description |
|---|---|---|
| `TCP_HOST` | `127.0.0.1` | Backend server IP or hostname |
| `TCP_PORT` | `9000` | Netty TCP port on the backend |
| `CONNECT_TIMEOUT_S` | `5` | TCP connection timeout (seconds) |
| `IO_TIMEOUT_S` | `5` | Socket read/write timeout (seconds) |
| `RECONNECT_BACKOFF_S` | `2` | Delay between reconnection attempts |
| `SEND_LOOP_SLEEP_S` | `0.01` | Sender loop idle sleep (seconds) |

### Sampling

| Variable | Default | Description |
|---|---|---|
| `SAMPLE_RATE_HZ` | `50` | IMU read frequency in Hz |
| `PACKED_ITEMS` | `25` | Samples batched per TCP send |
| `MAX_QUEUE_SAMPLES` | `200000` | Queue capacity before oldest eviction |

### TLS / mTLS

| Variable | Default | Description |
|---|---|---|
| `TLS_ENABLED` | `false` | Enable TLS encryption |
| `TLS_CA_CERT_PATH` | `` | Path to CA certificate for server verification |
| `TLS_CLIENT_CERT_PATH` | `` | Path to client certificate (mTLS) |
| `TLS_CLIENT_KEY_PATH` | `` | Path to client private key (mTLS) |
| `TLS_CLIENT_KEY_PASSWORD` | `` | Client key passphrase (if encrypted) |

### Auth

| Variable | Description |
|---|---|
| `JWT_TOKEN` | JWT token sent in the auth frame handshake |

### Logging

| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_FILE` | `logs/wearpark.log` | Log file path |
| `LOG_MAX_BYTES` | `10485760` | Max log file size before rotation (10 MB) |
| `LOG_BACKUP_COUNT` | `3` | Number of rotated log files to keep |

---

## Binary Protocol

Frames are little-endian struct-packed and sent over raw TCP.

### Auth frame (type `0x00`)

```
┌──────────┬──────────────────┐
│  1 byte  │     8 bytes      │
│   type   │  timestamp (ms)  │
└──────────┴──────────────────┘
```

### Data frame (type `0x01`)

```
┌──────────┬────────────────┬──────────────────────────────────────────┐
│  1 byte  │    4 bytes     │               24 bytes                   │
│   type   │  offset (ms)   │  ax  ay  az  gx  gy  gz  (6 × float32)  │
└──────────┴────────────────┴──────────────────────────────────────────┘
```

### Handshake sequence

```
Server → "OK\n"
Client → auth frame (timestamp)
Server → "OK\n"
Client → data frames (continuous)
```

---

## Tests

Tests are written with **pytest** and run entirely without hardware — all sensor and socket calls are mocked.

| Module | Cases covered |
|---|---|
| `test_protocol.py` | Auth frame encoding, data frame encoding, `epoch_ms` |
| `test_sensor.py` | Init success/failure, read success/failure, hardware unavailable |
| `test_tcp_client.py` | Plain TCP, TLS/mTLS connect, send, recv, timeouts, cert validation, keepalive |
| `test_mem_queue.py` | FIFO ordering, overflow eviction, empty queue |
| `test_streamer.py` | Producer collection, handshake flow, reconnect loop, sender batching |

```bash
# All tests + coverage report
make test

# Security scan (bandit + pip-audit)
make security

# Clean build artifacts
make clean
```

> Coverage target: **≥ 80%** on all modules. Enforced by CI on every PR and push.

### CI

GitHub Actions runs on every **push** and **pull request** targeting `develop` and `main`:

1. Install test dependencies (`pip install -r requirements-test.txt`)
2. Run all tests with coverage (`pytest`)
3. Enforce ≥ 80% threshold — PR is blocked if coverage drops below
4. Post a coverage summary comment on the pull request

---

## Tech Stack

| Component | Technology |
|---|---|
| Platform | Raspberry Pi 5 (Ubuntu) |
| Language | Python 3.11 |
| Sensor | Adafruit ICM-20948 (9-axis IMU) |
| Hardware abstraction | Adafruit Blinka + `adafruit-circuitpython-icm20x` |
| GPIO / I2C | `lgpio` |
| Configuration | `python-dotenv` |
| Testing | `pytest`, `pytest-cov`, `pytest-html` |
| Security scanning | `bandit`, `pip-audit` |

---

## Related Repositories

| Repository | Description |
|---|---|
| [WearPark-Backend](https://github.com/KarolannMauger/WearPark-Backend) | Java Spring Boot — Netty TCP server, REST API, ML orchestration |
| [WearPark-App](https://github.com/KarolannMauger/WearPark-App) | React Native Expo — real-time dashboard and monthly reports |
| [WearPark-ML](https://github.com/KarolannMauger/WearPark-ML) | Residual CNN — binary Parkinson tremor classification |

---

## License

Copyright © 2026 WearPark. All rights reserved.
This project is released under the [MIT License](./LICENSE).

> **Medical disclaimer:** This software is a research prototype and is NOT a certified medical device. It must not be used as a substitute for professional medical diagnosis or treatment.
