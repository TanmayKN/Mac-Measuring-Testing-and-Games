#!/opt/homebrew/bin/python3.11
"""
Surface Angle Detector — serve on LAN, open on iPhone for live tilt.
Sensor runs in the phone browser via DeviceOrientationEvent.
"""
from flask import Flask, Response
import socket

app = Flask(__name__)

PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
<title>Tilt</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
html, body {
  width:100%; height:100%;
  background:#0d0d0d; color:#fff;
  font-family: -apple-system, "Helvetica Neue", sans-serif;
  display:flex; flex-direction:column; align-items:center;
  justify-content:flex-start; overflow:hidden;
  touch-action: none;
}

#header {
  font-size:11px; letter-spacing:.18em; color:#444;
  text-transform:uppercase; padding: 28px 0 0;
}

#big {
  font-size: min(28vw, 130px);
  font-weight:700;
  color:#00e676;
  line-height:1;
  margin: 8px 0 0;
  transition: color .12s;
}

#unit { font-size: min(10vw, 48px); color: inherit; }

canvas {
  display:block;
  margin: 6px auto 0;
}

#row {
  display:flex; gap:40px;
  margin-top:12px;
}
.cell { text-align:center; }
.cell .lbl { font-size:10px; letter-spacing:.12em; color:#444; margin-bottom:3px; }
.cell .val { font-size: min(9vw, 38px); font-weight:700; color:#00e5ff; transition:color .12s; }

#gyro {
  margin-top:10px;
  font-family: "Courier New", monospace;
  font-size:12px; color:#2e2e2e;
  min-height:18px;
}

#hint {
  margin-top:8px;
  font-size:13px; font-style:italic; color:#555;
}

#permit {
  position:fixed; inset:0;
  background:rgba(0,0,0,.92);
  display:flex; flex-direction:column;
  align-items:center; justify-content:center;
  gap:20px; padding:30px; text-align:center;
}
#permit h2 { font-size:22px; }
#permit p  { font-size:14px; color:#777; line-height:1.6; }
#permit button {
  background:#00e5ff; color:#000;
  border:none; border-radius:12px;
  padding:14px 36px; font-size:17px; font-weight:700;
  cursor:pointer;
}
</style>
</head>
<body>

<div id="permit">
  <h2>Allow Motion Access</h2>
  <p>Tap below so the browser can read your phone's tilt sensor.</p>
  <button id="permitBtn">Enable Sensor</button>
</div>

<div id="header">SCREEN &nbsp; TILT</div>
<div id="big">--<span id="unit">°</span></div>

<canvas id="c"></canvas>

<div id="row">
  <div class="cell">
    <div class="lbl">PITCH &nbsp; front/back</div>
    <div class="val" id="pitch">+0.0°</div>
  </div>
  <div class="cell">
    <div class="lbl">ROLL &nbsp; left/right</div>
    <div class="val" id="roll">+0.0°</div>
  </div>
</div>

<div id="gyro"></div>
<div id="hint">waiting for sensor…</div>

<script>
// ── canvas setup ─────────────────────────────────────────────────────────────
const canvas = document.getElementById('c');
const ctx    = canvas.getContext('2d');
const DPR    = window.devicePixelRatio || 1;
const SIZE   = Math.min(window.innerWidth, 320);
canvas.style.width  = SIZE + 'px';
canvas.style.height = (SIZE * 0.55) + 'px';
canvas.width  = SIZE * DPR;
canvas.height = SIZE * 0.55 * DPR;
ctx.scale(DPR, DPR);

const CX = SIZE / 2, CY = SIZE * 0.55 - 10, R = SIZE * 0.42;

function drawStatic() {
  ctx.clearRect(0, 0, SIZE, SIZE);
  ctx.strokeStyle = '#2a2a2a'; ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(CX, CY, R, Math.PI, 0);
  ctx.stroke();

  for (let d = 0; d <= 180; d += 10) {
    const rad   = Math.PI - d * Math.PI / 180;
    const inner = R - (d % 30 === 0 ? 16 : 7);
    ctx.strokeStyle = d % 30 === 0 ? '#444' : '#222';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(CX + inner * Math.cos(rad), CY - inner * Math.sin(rad));
    ctx.lineTo(CX + R     * Math.cos(rad), CY - R     * Math.sin(rad));
    ctx.stroke();
    if (d % 30 === 0) {
      ctx.fillStyle = '#444';
      ctx.font = '9px -apple-system';
      ctx.textAlign = 'center';
      const lx = CX + (R - 24) * Math.cos(rad);
      const ly = CY - (R - 24) * Math.sin(rad);
      ctx.fillText(d / 2 + '°', lx, ly + 4);
    }
  }
}

function drawNeedle(tiltDeg, color) {
  drawStatic();
  const sweep = Math.max(0, Math.min(180, tiltDeg * 2));
  const rad   = Math.PI - sweep * Math.PI / 180;
  const nx = CX + (R - 10) * Math.cos(rad);
  const ny = CY - (R - 10) * Math.sin(rad);

  // sweep arc
  if (sweep > 1) {
    ctx.strokeStyle = color; ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.arc(CX, CY, R, Math.PI, Math.PI - sweep * Math.PI / 180, true);
    ctx.stroke();
  }

  // needle
  ctx.strokeStyle = color; ctx.lineWidth = 5;
  ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(CX, CY); ctx.lineTo(nx, ny); ctx.stroke();
  ctx.fillStyle = color;
  ctx.beginPath(); ctx.arc(nx, ny, 9, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#00e5ff';
  ctx.beginPath(); ctx.arc(CX, CY, 6, 0, Math.PI * 2); ctx.fill();
}

// ── colour helper ─────────────────────────────────────────────────────────────
function col(a) {
  a = Math.abs(a);
  if (a < 5)  return '#00e676';
  if (a < 20) return '#ffe600';
  return '#ff1744';
}

// ── sensor ────────────────────────────────────────────────────────────────────
let hasGyro = false;

function startSensor() {
  if (!window.DeviceOrientationEvent) {
    document.getElementById('hint').textContent = 'No motion sensor on this device';
    return;
  }

  window.addEventListener('deviceorientation', e => {
    // beta  = pitch: front/back tilt (–180..180)
    // gamma = roll:  left/right tilt (–90..90)
    // alpha = compass heading
    const pitch = e.beta  ?? 0;
    const roll  = e.gamma ?? 0;

    // tilt from flat: 0=lying flat, 90=standing upright
    const tilt = Math.abs(pitch);

    const c = col(tilt);

    // big number
    document.getElementById('big').textContent  = tilt.toFixed(1);
    document.getElementById('unit').textContent = '°';
    document.getElementById('big').style.color  = c;

    // needle
    drawNeedle(tilt, c);

    // pitch/roll
    const pe = document.getElementById('pitch');
    const re = document.getElementById('roll');
    pe.textContent  = (pitch >= 0 ? '+' : '') + pitch.toFixed(1) + '°';
    re.textContent  = (roll  >= 0 ? '+' : '') + roll.toFixed(1)  + '°';
    pe.style.color  = col(pitch);
    re.style.color  = col(roll);

    // hint
    const hint = document.getElementById('hint');
    if (tilt < 2)             hint.textContent = 'flat';
    else if (Math.abs(tilt - 90) < 5) hint.textContent = 'upright / vertical';
    else                      hint.textContent = `${tilt.toFixed(1)}° from flat`;
  }, true);

  if (window.DeviceMotionEvent) {
    window.addEventListener('devicemotion', e => {
      const rr = e.rotationRate;
      if (!rr) return;
      hasGyro = true;
      document.getElementById('gyro').textContent =
        `gyro  x${rr.alpha?.toFixed(1)||0}  y${rr.beta?.toFixed(1)||0}  z${rr.gamma?.toFixed(1)||0}  °/s`;
    });
  }
}

// ── iOS permission gate ───────────────────────────────────────────────────────
const permitDiv = document.getElementById('permit');
document.getElementById('permitBtn').addEventListener('click', async () => {
  if (typeof DeviceOrientationEvent.requestPermission === 'function') {
    try {
      const r = await DeviceOrientationEvent.requestPermission();
      if (r === 'granted') { permitDiv.remove(); startSensor(); }
      else permitDiv.querySelector('p').textContent = 'Permission denied.';
    } catch { permitDiv.remove(); startSensor(); }
  } else {
    permitDiv.remove();
    startSensor();
  }
});

drawStatic();
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return PAGE

if __name__ == "__main__":
    ip = socket.gethostbyname(socket.gethostname())
    print("\n  Open on your iPhone:")
    print(f"  http://{ip}:5050\n")
    app.run(host="0.0.0.0", port=5050, threaded=True)
