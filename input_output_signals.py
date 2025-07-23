from pickle import FALSE

import serial
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button

# ─── USER-TUNABLE SMOOTHING ───────────────────────────────────────
alpha = 0.3          # EMA smoothing factor (0 < alpha ≤ 1)
smoothed_flow = None  # holds the last EMA output ekrem is played with this line


# ─── CONFIGURE SERIAL PORT ────────────────────────────────────────
# Match Arduino’s COM port and baud; non-blocking reads
ser = serial.Serial('COM7', 9600, timeout=0.05, dsrdtr=False)
time.sleep(2)                       # allow MCU to reset
ser.reset_input_buffer()            # flush startup bytes

# ─── DATA BUFFERS & TIMING ────────────────────────────────────────
times             = []             # timestamps
flows             = []             # flow‐rate readings (L/min)
pwms              = []             # PWM % readings
start_time        = time.time()    # t = 0 reference
max_points        = 100            # how many points to keep
sampling_interval = 0.1            # seconds/sample (match Arduino)

window_sec = max_points * sampling_interval  # visible time span

# ─── AXIS PARAMS ─────────────────────────────────────────────────
# Left (flow) axis
min_y_flow   = 0       # L/min
max_y_flow   = 10.0     # L/min
y_step_flow  = 1       # 1 L/min ticks

# Right (PWM) axis reused from VB style
min_y        = 0       # %
max_y        = 105.0   # %
y_step        = 10     # 10% ticks

# ─── SET UP FIGURE & DUAL AXES ────────────────────────────────────
fig, ax = plt.subplots()
ax2     = ax.twinx()   # second Y-axis

# Flow‐rate line (blue)
line_flow, = ax.plot([], [], lw=2, color='b', label='Flow (L/min)')
# PWM line (red)
line_pwm,  = ax2.plot([], [], lw=2, color='r', label='ENA PWM (%)')

# ─── TITLES & LABELS (VA styling for flow axis) ────────────────
ax.set_title("Flow Rate Sensor Reading", fontname="Comic Sans MS", fontsize=18)
ax.set_xlabel("Time (s)", fontname="Times New Roman")
ax.set_ylabel("Flow (L/min)", fontname="Times New Roman")
ax2.set_ylabel("ENA PWM (%)", fontname="Times New Roman")

# ─── X-AXIS TICKS & GRID (VB style) ──────────────────────────────
ax.set_xlim(0, window_sec)
ax.xaxis.set_major_locator(MultipleLocator(0.5))   # 0.5 s major
ax.xaxis.set_minor_locator(MultipleLocator(0.25))  # 0.25 s minor

# ─── Y-AXES TICKS & GRID (uniform MultipleLocator) ────────────
# Left axis (flow)
ax.set_ylim(min_y_flow, max_y_flow)
ax.yaxis.set_major_locator(MultipleLocator(y_step_flow))
ax.yaxis.set_minor_locator(MultipleLocator(y_step_flow / 2))
# Right axis (PWM)
ax2.set_ylim(min_y, max_y)
ax2.yaxis.set_major_locator(MultipleLocator(y_step))
ax2.yaxis.set_minor_locator(MultipleLocator(y_step / 2))

# ─── GRID LINES (VB style) ──────────────────────────────────────
ax.grid(which='major', linestyle='-', linewidth=0.8)
ax.grid(which='minor', linestyle='--', linewidth=0.5)

# ─── PAUSE / RESUME BUTTON ───────────────────────────────────────
paused = False
def toggle_pause(event):
    global paused
    if paused:
        ani.event_source.start()
        pause_button.label.set_text('Pause')
    else:
        ani.event_source.stop()
        pause_button.label.set_text('Resume')
    paused = not paused

plt.subplots_adjust(bottom=0.15)
pause_ax     = fig.add_axes([0.8, 0.02, 0.1, 0.04])
pause_button = Button(pause_ax, 'Pause')
pause_button.on_clicked(toggle_pause)

# ─── UPDATE FUNCTION ─────────────────────────────────────────────
def update(frame):
    # 1) Read all pending serial lines, keep only the latest flow & PWM
    global smoothed_flow
    latest_flow = latest_pwm = None
    while ser.in_waiting:
        raw = ser.readline().decode(errors='ignore').strip()
        parts = raw.split(',')
        if len(parts) != 2:
            continue
        try:
            latest_flow = float(parts[0])
            latest_pwm  = float(parts[1])
        except ValueError:
            continue

    # If no valid new data, skip this frame
    if latest_flow is None:
        return

    # 2) Timestamp & rolling buffers
    t = time.time() - start_time
    times.append(t)
    flows.append(latest_flow)
    # ── EMA smoothing of raw flow ─────────────────────────────
    # if smoothed_flow is None:
    #     print("works")
    #     smoothed_flow = latest_flow
    # else:
    #     smoothed_flow = alpha * latest_flow + (1 - alpha) * smoothed_flow
    # flows[-1] = smoothed_flow  # overwrite last raw with smoothed
    flows[-1] = latest_flow
    pwms.append(latest_pwm / 255 * 100)  # map 0–255 → 0–100%

    times_trim  = times[-max_points:]
    flows_trim  = flows[-max_points:]
    pwms_trim   = pwms[-max_points:]

    # 3) Update both lines
    line_flow.set_data(times_trim, flows_trim)
    line_pwm.set_data(times_trim, pwms_trim)

    # 4) Slide the X-window
    left  = max(0, t - window_sec)
    right = t + sampling_interval
    ax.set_xlim(left, right)

# ─── ANIMATE ───────────────────────────────────────────────────────
ani = FuncAnimation(
    fig,
    update,
    interval=int(sampling_interval * 1000),
    cache_frame_data=False
)

plt.tight_layout(rect=[0, 0.15, 1, 1])
plt.show()
