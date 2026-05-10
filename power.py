#!/usr/bin/env python3
"""
Gaming Mode — MacBook Air M2 Max Performance App
Requires: Python 3.8+ (built-in tkinter)
Run with: python3 gaming_mode.py
"""

import tkinter as tk
from tkinter import font as tkfont
import subprocess
import threading
import time
import sys
import os
import signal

# ─────────────────────────────────────────────
#  COLOUR PALETTE
# ─────────────────────────────────────────────
BG       = "#08090d"
PANEL    = "#0e1018"
BORDER   = "#1a1e2e"
ACCENT   = "#0084ff"       # neon green
ACCENT2  = "#00c8ff"       # cyan
WARN     = "#ff6b35"
DIM      = "#3a3f55"
TEXT     = "#e0e4f0"
SUBTEXT  = "#6b7290"
RED      = "#ff3355"

# ─────────────────────────────────────────────
#  PERFORMANCE TWEAKS
#  -a = all power states (battery + AC)
#  -c = AC only
# ─────────────────────────────────────────────
GAMING_COMMANDS = [
    "pmset -a lowpowermode 0",
    "pmset -a sleep 0",
    "pmset -a disksleep 0",
    "pmset -a displaysleep 0",
    "pmset -a powernap 0",
    "pmset -a disablesleep 1",   # keeps running with lid closed
    "pmset -c womp 0",
    "pmset -c tcpkeepalive 0",
    "pmset -a ttyskeepawake 1",
]

RESTORE_COMMANDS = [
    "pmset -a lowpowermode 0",
    "pmset -a sleep 1",
    "pmset -a disksleep 10",
    "pmset -a displaysleep 2",
    "pmset -a powernap 1",
    "pmset -a disablesleep 0",
    "pmset -c womp 1",
    "pmset -c tcpkeepalive 1",
    "pmset -a ttyskeepawake 0",
]

OPTIMIZATIONS = [
    ("Low Power Mode",       "Disabled — full chip speed"),
    ("Sleep",                "Blocked — system stays awake"),
    ("Lid Close",            "Ignored — runs with lid shut"),
    ("Disk Sleep",           "Disabled — instant I/O"),
    ("Display Sleep",        "Disabled — no interruptions"),
    ("Power Nap",            "Off — no background wake"),
    ("App Nap",              "Disabled — foreground priority"),
    ("caffeinate",           "Active — sleep prevention"),
]


def run_as_admin(commands: list[str]) -> bool:
    """Run a list of shell commands combined, with a single macOS auth dialog."""
    combined = " && ".join(commands)
    # Escape for embedding in an AppleScript string
    escaped = combined.replace("\\", "\\\\").replace('"', '\\"')
    script = f'do shell script "{escaped}" with administrator privileges'
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True
    )
    return result.returncode == 0


def get_power_source() -> str:
    """Return 'AC' or 'Battery'."""
    try:
        out = subprocess.check_output(
            ["pmset", "-g", "ps"], text=True, stderr=subprocess.DEVNULL
        )
        if "AC Power" in out:
            return "AC"
    except Exception:
        pass
    return "Battery"


def get_battery_percent() -> int | None:
    try:
        out = subprocess.check_output(
            ["pmset", "-g", "batt"], text=True, stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            if "%" in line:
                pct = line.split("%")[0].split()[-1].strip()
                return int(pct)
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────
#  CANVAS HELPERS
# ─────────────────────────────────────────────

def rounded_rect(canvas, x1, y1, x2, y2, r=12, **kwargs):
    """Draw a rectangle with rounded corners on a Canvas."""
    pts = [
        x1+r, y1,   x2-r, y1,
        x2,   y1,   x2,   y1+r,
        x2,   y2-r, x2,   y2,
        x2-r, y2,   x1+r, y2,
        x1,   y2,   x1,   y2-r,
        x1,   y1+r, x1,   y1,
        x1+r, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kwargs)


# ─────────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────────

class GamingModeApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("M2 Max Performance")
        self.root.geometry("520x720")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self.gaming_active  = False
        self.caffeinate_proc: subprocess.Popen | None = None
        self._monitor_running = True
        self._anim_step = 0

        # Dynamic labels list (updated on toggle)
        self._opt_status_labels: list[tk.Label] = []

        self._build_ui()
        self._start_monitor()

    # ── UI CONSTRUCTION ──────────────────────

    def _build_ui(self):
        root = self.root

        # ── Header bar ───────────────────────
        header = tk.Frame(root, bg=BG, height=70)
        header.pack(fill="x", padx=0, pady=0)

        tk.Label(
            header, text="Max output",
            bg=BG, fg=ACCENT,
            font=("Courier New", 22, "bold"),
        ).pack(side="left", padx=24, pady=18)

        self.power_badge = tk.Label(
            header, text="  AC POWER  ",
            bg=BORDER, fg=ACCENT2,
            font=("Courier New", 10, "bold"),
            padx=8, pady=4,
        )
        self.power_badge.pack(side="right", padx=24, pady=22)

        # Thin separator
        tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=0)

        # ── Status card ───────────────────────
        card_frame = tk.Frame(root, bg=BG)
        card_frame.pack(fill="x", padx=20, pady=18)

        self.status_canvas = tk.Canvas(
            card_frame, bg=PANEL, bd=0, highlightthickness=0,
            width=480, height=130
        )
        self.status_canvas.pack()
        self._draw_status_card()

        # ── Big toggle button ─────────────────
        btn_area = tk.Frame(root, bg=BG)
        btn_area.pack(pady=6)

        self.toggle_btn = tk.Canvas(
            btn_area, width=220, height=64,
            bg=BG, bd=0, highlightthickness=0,
            cursor="hand2"
        )
        self.toggle_btn.pack()
        self._draw_toggle_btn()
        self.toggle_btn.bind("<Button-1>", self._on_toggle)
        self.toggle_btn.bind("<Enter>",    lambda e: self._btn_hover(True))
        self.toggle_btn.bind("<Leave>",    lambda e: self._btn_hover(False))

        # ── Optimizations list ────────────────
        tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=20, pady=(16, 0))

        tk.Label(
            root, text="OPTIMIZATIONS",
            bg=BG, fg=SUBTEXT,
            font=("Courier New", 10, "bold"),
        ).pack(anchor="w", padx=24, pady=(10, 4))

        opt_frame = tk.Frame(root, bg=BG)
        opt_frame.pack(fill="x", padx=20)

        self._opt_status_labels.clear()
        for i, (name, detail) in enumerate(OPTIMIZATIONS):
            row = tk.Frame(opt_frame, bg=PANEL if i % 2 == 0 else BG)
            row.pack(fill="x", pady=1)

            # Dot indicator
            dot = tk.Canvas(row, width=12, height=12, bg=row["bg"],
                            bd=0, highlightthickness=0)
            dot.pack(side="left", padx=(12, 6), pady=10)
            dot.create_oval(2, 2, 10, 10, fill=DIM, outline="")
            dot._circle_id = dot.find_all()[0]
            dot._is_active = False

            # Name
            tk.Label(row, text=name, bg=row["bg"], fg=TEXT,
                     font=("Courier New", 11, "bold"),
                     anchor="w", width=18).pack(side="left")

            # Status
            status_lbl = tk.Label(row, text="standby", bg=row["bg"], fg=SUBTEXT,
                                   font=("Courier New", 10),
                                   anchor="w")
            status_lbl.pack(side="left", padx=4)
            status_lbl._detail = detail
            status_lbl._dot    = dot
            self._opt_status_labels.append(status_lbl)

        # ── Log strip ─────────────────────────
        tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=20, pady=(14, 0))
        self.log_var = tk.StringVar(value="● Ready — connect power adapter for best results")
        tk.Label(
            root, textvariable=self.log_var,
            bg=BG, fg=SUBTEXT,
            font=("Courier New", 10),
            wraplength=480, justify="left"
        ).pack(anchor="w", padx=24, pady=10)

        # ── Footer ────────────────────────────
        tk.Label(
            root,
            text="MacBook Air M2  ·  pmset + caffeinate  ·  AC-power mode",
            bg=BG, fg=DIM,
            font=("Courier New", 9),
        ).pack(side="bottom", pady=10)

    # ── STATUS CARD ──────────────────────────

    def _draw_status_card(self):
        c = self.status_canvas
        c.delete("all")

        # Background rounded rect
        rounded_rect(c, 0, 0, 480, 130, r=10,
                     fill=PANEL, outline=BORDER)

        # Left big label
        color  = ACCENT if self.gaming_active else DIM
        label  = "ACTIVE" if self.gaming_active else "INACTIVE"

        c.create_text(24, 40, text=label,
                      font=("Courier New", 26, "bold"),
                      fill=color, anchor="w")

        # Pulsing dot
        dot_x = 24 + 8 * len(label) + 16
        dot_r = 7
        self._pulse_dot_id = c.create_oval(
            dot_x - dot_r, 40 - dot_r,
            dot_x + dot_r, 40 + dot_r,
            fill=color if self.gaming_active else DIM,
            outline=""
        )
        self._pulse_dot_x = dot_x

        # Sub-lines
        src = get_power_source()
        pct = get_battery_percent()
        batt_str = f"{pct}%" if pct is not None else "—"

        c.create_text(24, 70, text=f"Power source:  {src}",
                      font=("Courier New", 11), fill=TEXT, anchor="w")
        c.create_text(24, 90, text=f"Battery level:  {batt_str}",
                      font=("Courier New", 11), fill=TEXT, anchor="w")

        # Right side — mode hint
        hint = "All systems at max\nperformance" if self.gaming_active \
               else "System in normal\npower mode"
        c.create_text(456, 50, text=hint,
                      font=("Courier New", 10), fill=SUBTEXT,
                      anchor="e", justify="right")

        if self.gaming_active:
            c.create_text(456, 100, text="caffeinate ● running",
                          font=("Courier New", 9), fill=ACCENT, anchor="e")

    # ── TOGGLE BUTTON ────────────────────────

    def _draw_toggle_btn(self, hover=False):
        c = self.toggle_btn
        c.delete("all")

        if self.gaming_active:
            fill    = RED
            outline = RED
            label   = "DISABLE POWER MODE"
            fg      = "#ffffff"
        elif hover:
            fill    = "#001a0d"
            outline = ACCENT
            label   = "ENABLE POWER MODE"
            fg      = ACCENT
        else:
            fill    = "#0a1a10"
            outline = ACCENT
            label   = "ENABLE POWER MODE"
            fg      = ACCENT

        rounded_rect(c, 2, 2, 218, 62, r=10,
                     fill=fill, outline=outline, width=2)
        c.create_text(110, 32, text=label,
                      font=("Courier New", 11, "bold"),
                      fill=fg)

    def _btn_hover(self, state: bool):
        if not self.gaming_active:
            self._draw_toggle_btn(hover=state)

    # ── TOGGLE LOGIC ─────────────────────────

    def _on_toggle(self, _event=None):
        if self.gaming_active:
            self._set_log("● Disabling power mode…")
            threading.Thread(target=self._disable, daemon=True).start()
        else:
            src = get_power_source()
            if src != "AC":
                self._set_log("⚠  Plug in power adapter for maximum performance!")
            self._set_log("● Requesting admin privileges…")
            threading.Thread(target=self._enable, daemon=True).start()

    def _enable(self):
        ok = run_as_admin(GAMING_COMMANDS)
        if not ok:
            self.root.after(0, lambda: self._set_log("✗  Admin auth failed or cancelled."))
            return

        # Disable App Nap (no sudo needed)
        subprocess.run(
            ["defaults", "write", "NSGlobalDomain", "NSAppSleepDisabled", "-bool", "YES"],
            capture_output=True
        )

        # Start caffeinate
        self.caffeinate_proc = subprocess.Popen(
            ["caffeinate", "-i", "-d", "-m", "-s"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        self.gaming_active = True
        self.root.after(0, self._refresh_ui)
        self.root.after(0, lambda: self._set_log("✓  Power Mode is ON — maximum performance active"))

    def _disable(self):
        ok = run_as_admin(RESTORE_COMMANDS)
        if not ok:
            self.root.after(0, lambda: self._set_log("✗  Admin auth failed or cancelled."))
            return

        # Re-enable App Nap
        subprocess.run(
            ["defaults", "delete", "NSGlobalDomain", "NSAppSleepDisabled"],
            capture_output=True
        )

        # Kill caffeinate
        if self.caffeinate_proc:
            self.caffeinate_proc.terminate()
            self.caffeinate_proc = None

        self.gaming_active = False
        self.root.after(0, self._refresh_ui)
        self.root.after(0, lambda: self._set_log("● Power Mode OFF — normal power settings restored"))

    # ── UI REFRESH ───────────────────────────

    def _refresh_ui(self):
        self._draw_status_card()
        self._draw_toggle_btn()
        for lbl in self._opt_status_labels:
            if self.gaming_active:
                lbl.config(text=lbl._detail, fg=ACCENT)
                lbl._dot.itemconfig(lbl._dot._circle_id, fill=ACCENT)
            else:
                lbl.config(text="standby", fg=SUBTEXT)
                lbl._dot.itemconfig(lbl._dot._circle_id, fill=DIM)

    def _set_log(self, msg: str):
        self.log_var.set(msg)

    # ── BACKGROUND MONITOR ───────────────────

    def _start_monitor(self):
        t = threading.Thread(target=self._monitor_loop, daemon=True)
        t.start()

    def _monitor_loop(self):
        """Refresh power source badge & pulse animation every second."""
        tick = 0
        while self._monitor_running:
            src  = get_power_source()
            pct  = get_battery_percent()
            tick += 1

            def _update(src=src, pct=pct, tick=tick):
                # Power badge
                if src == "AC":
                    self.power_badge.config(text="  ⚡ AC POWER  ", fg=ACCENT2)
                else:
                    p = pct if pct is not None else "?"
                    self.power_badge.config(text=f"  🔋 {p}%  ", fg=WARN)

                # Pulse dot on status card
                if self.gaming_active:
                    alpha = abs((tick % 20) - 10) / 10  # 0 → 1 → 0
                    r = int(0x00 + alpha * 0xff)
                    g = int(0x88 + alpha * 0x77)
                    b = int(0x00 + alpha * 0x88)
                    pulse_color = f"#{r:02x}{g:02x}{b:02x}"
                    try:
                        self.status_canvas.itemconfig(
                            self._pulse_dot_id, fill=pulse_color
                        )
                    except Exception:
                        pass

            self.root.after(0, _update)
            time.sleep(1)

    # ── CLEANUP ──────────────────────────────

    def on_close(self):
        self._monitor_running = False
        if self.gaming_active and self.caffeinate_proc:
            self.caffeinate_proc.terminate()
            # Best-effort restore on close
            threading.Thread(
                target=lambda: run_as_admin(RESTORE_COMMANDS), daemon=True
            ).start()
        self.root.destroy()


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

def main():
    root = tk.Tk()
    app  = GamingModeApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)

    # macOS: bring window to front
    try:
        root.lift()
        root.attributes("-topmost", True)
        root.after(200, lambda: root.attributes("-topmost", False))
    except Exception:
        pass

    root.mainloop()


if __name__ == "__main__":
    main()
