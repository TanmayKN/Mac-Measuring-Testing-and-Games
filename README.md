# Mac Measuring Testing and Games

Uses the hidden **Bosch BMI286 IMU** inside Apple Silicon Macs to read real screen tilt, lid angle, and gyroscope data. Includes a measurement tool and two Flappy Bird-style games.

## Requirements

- Apple Silicon Mac (M1 / M2 / M3)
- Homebrew Python 3.11
- Run with `sudo` (needed to access the HID sensor)

## Install

```bash
/opt/homebrew/bin/pip3.11 install macimu pygame flask
```

## Run

```bash
sudo /opt/homebrew/bin/python3.11 angle_app.py
```

---

## Modes

### 📐 Measurement
Live readout of lid angle, body tilt, pitch, roll, and gyroscope.

### 🐦 Flappy Tilt
Flappy Bird clone — tilt your screen UP to flap. Space also works.

### 🪁 Plappy Constant
Screen angle is directly proportional to bird height. No flapping — just tilt to move.

### 🎨 Skins
6 unlockable bird skins. Unlock by hitting score milestones. Saves to disk.

---

## Difficulty Modes

| | Pipe Speed | Gap | Gravity |
|---|---|---|---|
| Easy | slow | wide | floaty |
| Normal | medium | medium | standard |
| Hard | fast | narrow | heavy |

---

## Unlockable Skins

| Skin | How to unlock |
|---|---|
| 🐦 Classic | Always unlocked |
| 🔥 Fire | Score 5 on Normal+ Flappy |
| ❄️ Ice | Score 5 in Plappy |
| 👻 Ghost | Score 10 on any mode |
| 🏆 Gold | Score 15 on Normal+ |
| 🟢 Neon | Score 10 on Hard |

---

## Web App (iPhone)

```bash
/opt/homebrew/bin/python3.11 web_server.py
```

Open the printed URL on your iPhone in Safari. Tap **Enable Sensor** — uses the phone's accelerometer for live tilt.

---

## How it works

Apple Silicon Macs contain a hidden MEMS IMU (Bosch BMI286) in the Sensor Processing Unit. It's accessible via IOKit HID at `AppleSPUHIDDevice` with root privileges using the [`macimu`](https://github.com/olvvier/apple-silicon-accelerometer) library.
