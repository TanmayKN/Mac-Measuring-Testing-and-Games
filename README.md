# MacBook Screen Tilt Detector

Real-time screen/lid angle detector for Apple Silicon MacBooks using the built-in Bosch BMI286 IMU sensor.

## Features

- **Lid angle** — exact degrees the screen is open
- **Body tilt & roll** — how level the laptop base is
- **Gyroscope** — rotation rate (if available)
- Live arc gauge with colour-coded needle (green / yellow / red)

## Requirements

- Apple Silicon Mac (M1 / M2 / M3)
- Homebrew Python 3.11
- `macimu` + `pygame`

## Install

```bash
/opt/homebrew/bin/pip3.11 install macimu pygame flask
```

## Run — Desktop App

```bash
sudo /opt/homebrew/bin/python3.11 angle_app.py
```

> `sudo` is required because macOS blocks unprivileged access to the HID sensor.

Open/close the lid slightly once on first launch to wake the lid angle sensor.

## Run — Web App (iPhone / any browser on LAN)

```bash
/opt/homebrew/bin/python3.11 web_server.py
```

Open the printed URL on your iPhone. Tap **Enable Sensor** — the phone's accelerometer gives live tilt via `DeviceOrientationEvent`.

## How it works

Apple Silicon Macs have a hidden MEMS IMU (Bosch BMI286) in the Sensor Processing Unit (SPU). It's accessible via IOKit HID at `AppleSPUHIDDevice` with root privileges. The [`macimu`](https://github.com/olvvier/apple-silicon-accelerometer) library handles the low-level IOKit calls and shared-memory ring buffer reads.

## Controls

- **Esc** or close window to quit
