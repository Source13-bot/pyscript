import serial
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# ─── USER-TUNABLE SMOOTHING ───────────────────────────────────────
alpha = 0.1           # EMA smoothing factor (0 < alpha ≤ 1)
smoothed_flow = None  # holds the last EMA output

# ─── CONFIGURE SERIAL PORT ────────────────────────────────────────
ser = serial.Serial('COM7', 9600, timeout=0.0, dsrdtr=False)
time.sleep(2)                       # allow MCU to reset
ser.reset_input_buffer()            # drop any startup bytes

# ─── DATA BUFFERS & TIMING ────────────────────────────────────────
times             = []             # timestamps
vals              = []             # smoothed readings
start_time        = time.time()    # reference t = 0
max_points        = 5000           # how many points to keep
sampling_interval = 0.001          # expected seconds/sample
window_sec        = max_points * sampling_interval

# ─── FIXED Y-AXIS SETTINGS ────────────────────────────────────────
min_y  = -0.5    # lower bound
max_y  = 12.0    # upper bound
y_step = 1       # major tick interval

# ─── SET UP FIGURE & AXES ────────────────────────────────────────
fig, ax = plt.subplots()

def update(frame):
    global smoothed_flow

    # ─── 1) DRAIN SERIAL BUFFER ──────────────────────────────────
    latest = None
    while True:
        raw = ser.readline().decode(errors='ignore').strip()
        if not raw:
            break
        try:
            latest = float(raw)   # parse new sample
        except ValueError:
            continue              # skip non-numeric

    if latest is None:
        return  # no new data this frame

    # ─── 2) EMA SMOOTHING ────────────────────────────────────────
    if smoothed_flow is None:
        smoothed_flow = latest    # seed on first sample
    else:
        smoothed_flow = alpha * latest + (1 - alpha) * smoothed_flow

    flow = max(0.0, smoothed_flow)  # clamp below zero

    # ─── 3) TIMESTAMP & ROLLING BUFFERS ──────────────────────────
    t = time.time() - start_time
    times.append(t)
    vals.append(flow)
    times_trim = times[-max_points:]
    vals_trim  = vals[-max_points:]

    # ─── 4) COMPUTE WINDOW EDGES ─────────────────────────────────
    left  = max(0, t - window_sec)
    right = t + sampling_interval

    # ─── 5) CLEAR & PLOT ─────────────────────────────────────────
    ax.clear()
    ax.plot(times_trim, vals_trim, lw=2)

    # ─── 6) TITLES & LABELS ──────────────────────────────────────
    ax.set_title("Flow Rate Sensor Reading", fontname="Comic Sans MS", fontsize=18)
    ax.set_xlabel("Time (s)", fontname="Times New Roman")
    ax.set_ylabel("Flow (L/min)", fontname="Times New Roman")

    # ─── 7) FIXED Y-AXIS ──────────────────────────────────────────
    ax.set_ylim(min_y, max_y)

    # ─── 8) MOVING X-WINDOW ──────────────────────────────────────
    ax.set_xlim(left, right)

    # ─── 9) CUSTOM Y-TICKS & GRID ────────────────────────────────
    major_ticks = np.arange(min_y, max_y + y_step, y_step)
    minor_ticks = np.arange(min_y, max_y + y_step/2, y_step/2)
    ax.set_yticks(major_ticks)
    ax.set_yticks(minor_ticks, minor=True)
    ax.grid(which='major', linestyle='-', linewidth=0.8)
    ax.grid(which='minor', linestyle='--', linewidth=0.5)

# ─── ANIMATE ───────────────────────────────────────────────────────
ani = FuncAnimation(
    fig,
    update,
    interval=int(sampling_interval * 1000),
    cache_frame_data=False
)

plt.tight_layout()
plt.show()
