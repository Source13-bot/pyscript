from pickle import FALSE

import serial
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button

# ─── CONFIGURE SERIAL PORT ────────────────────────────────────────
ser = serial.Serial('COM7', 9600, timeout=0.05, dsrdtr=False)
time.sleep(2)                       # allow MCU to reset
ser.reset_input_buffer()            # drop any startup bytes

# ─── DATA BUFFERS & TIMING ────────────────────────────────────────
times             = []             # timestamps
pwms              = []             # PWM % readings
start_time        = time.time()    # reference t = 0
max_points        = 100           # how many points to keep
sampling_interval = 0.1            # seconds/sample (match serial tx)
window_sec        = max_points * sampling_interval

# ─── FIXED Y-AXIS SETTINGS (PWM 0–100%) ───────────────────────────
min_y  = 0       # lower bound
max_y  = 100.0   # upper bound (PWM %)
y_step = 10      # major tick interval (10%)

# ─── SET UP FIGURE & AXES ────────────────────────────────────────
fig, ax     = plt.subplots()
line,       = ax.plot([], [], lw=2, color='r')
ax.set_xlabel("Time (s)", fontname="Times New Roman")
ax.set_ylabel("ENA PWM (%)", fontname="Times New Roman")
ax.set_title("ENA PWM Signal", fontname="Comic Sans MS", fontsize=18)
ax.set_xlim(0, window_sec)
ax.set_ylim(min_y, max_y)
# major_ticks = np.arange(min_y, max_y + y_step, y_step)
# ax.set_yticks(major_ticks)
ax.yaxis.set_major_locator(MultipleLocator(y_step))     # major ticks every y_step
ax.yaxis.set_minor_locator(MultipleLocator(y_step/2))   # minor ticks every y_step/2
ax.xaxis.set_major_locator(MultipleLocator(0.5))  # major ticks every 0.5 s
ax.xaxis.set_minor_locator(MultipleLocator(0.25))  # minor ticks every 0.25 s
ax.grid(which='major', linestyle='-', linewidth=0.8)
ax.grid(which='minor', linestyle='--', linewidth=0.5)

def update(frame):

    print("▶ update called")

    # ─── 1) DRAIN SERIAL BUFFER FOR PWM ───────────────────────────
    latest_pwm = None
    # Read everything currently in the buffer, but only keep the last value
    while ser.in_waiting:
        raw = ser.readline().decode(errors='ignore').strip()
        parts = raw.split(',')
        if len(parts) != 2:
            continue
        try:
            latest_pwm = float(parts[1])
        except ValueError:
            continue

    # If nothing valid arrived, skip this frame
    if latest_pwm is None:
        return


    # ─── 2) TIMESTAMP & ROLLING BUFFERS ──────────────────────────
    t = time.time() - start_time
    times.append(t)
    pwms.append(latest_pwm / 255 * 100)
    times_trim = times[-max_points:]
    pwms_trim = pwms[-max_points:]

    # ─── 4) COMPUTE WINDOW EDGES ─────────────────────────────────
    left  = max(0, t - window_sec)
    right = t + sampling_interval

    # ─── 3) UPDATE LINE DATA ─────────────────────────────────────────
    line.set_data(times_trim, pwms_trim)

    # ─── 5) MOVING X-WINDOW ────────────────────────────────────────
    ax.set_xlim(left, right)

# ─── ANIMATE ───────────────────────────────────────────────────────
ani = FuncAnimation(
    fig,
    update,
    interval=int(sampling_interval * 1000),
    cache_frame_data=False)

# ─── PAUSE / RESUME BUTTON ─────────────────────────────────────────
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
pause_ax    = fig.add_axes([0.8, 0.02, 0.1, 0.04])
pause_button = Button(pause_ax, 'Pause')
pause_button.on_clicked(toggle_pause)

plt.tight_layout(rect=[0, 0.15, 1, 1])
plt.show()
