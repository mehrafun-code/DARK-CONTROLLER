"""DARK CONTROLLER - sci-fi controller battery monitor (Windows, XInput)
By DarkDeath Evil
"""
import ctypes
import math
import os
import sys
import time
import tkinter as tk

BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(BASE, "assets")

# ---------- XInput (battery) ----------
try:
    xinput = ctypes.windll.xinput1_4
except (AttributeError, OSError):
    xinput = None


class BATTERY_INFO(ctypes.Structure):
    _fields_ = [("BatteryType", ctypes.c_ubyte),
                ("BatteryLevel", ctypes.c_ubyte)]


LEVEL_TEXT = {0: "EMPTY", 1: "LOW", 2: "MEDIUM", 3: "FULL"}
LEVEL_PERCENT = {0: 5, 1: 25, 2: 60, 3: 100}  # XInput = 4 levels only


def read_battery():
    if xinput is None:
        return None
    for slot in range(4):
        info = BATTERY_INFO()
        if xinput.XInputGetBatteryInformation(slot, 0, ctypes.byref(info)) == 0 and info.BatteryType != 0:
            return {"slot": slot, "type": info.BatteryType, "level": info.BatteryLevel}
    return None


# ---------- Theme ----------
BG = "#07070b"
GRID = "#0e0e16"
PANEL = "#0f0f17"
RED = "#ff2e1f"
ORANGE = "#ff8a00"
DIM = "#2a1210"
TEXT = "#e8e8ee"
MUTED = "#76768a"
GOOD = "#27ffb0"
MONO = "Consolas"

W, H = 420, 650
CX, CY, R = 210, 275, 100
POLL_MS = 2000
FRAME_MS = 33


def lerp_color(c1, c2, f):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * f) for i in range(3))


def level_color(pct):
    if pct <= 30:
        return RED
    if pct <= 70:
        return ORANGE
    return GOOD


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Dark Controller")
        self.geometry(f"{W}x{H}")
        self.resizable(False, False)
        self.configure(bg=BG)
        try:
            self.iconbitmap(os.path.join(ASSETS, "icon.ico"))
        except tk.TclError:
            pass

        self.cv = tk.Canvas(self, width=W, height=H, bg=BG, highlightthickness=0)
        self.cv.pack()

        self.logo = None
        try:
            self.logo = tk.PhotoImage(file=os.path.join(ASSETS, "logo.png")).subsample(2, 2)
        except tk.TclError:
            pass

        self.data = None
        self.target = 0.0
        self.shown = 0.0
        self.charging = False
        self.t0 = time.time()

        self.draw_static()
        self.poll()
        self.tick()

    # ----- helpers -----
    def bracket(self, x1, y1, x2, y2, color, l=16):
        c = self.cv
        for (x, y, dx, dy) in ((x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)):
            c.create_line(x, y, x + dx * l, y, fill=color, width=2)
            c.create_line(x, y, x, y + dy * l, fill=color, width=2)

    # ----- static layer -----
    def draw_static(self):
        c = self.cv
        for x in range(0, W, 30):
            c.create_line(x, 0, x, H, fill=GRID)
        for y in range(0, H, 30):
            c.create_line(0, y, W, y, fill=GRID)

        # header
        if self.logo:
            c.create_image(18, 14, image=self.logo, anchor="nw")
        c.create_text(112, 38, text="DARK", anchor="w", fill=RED, font=(MONO, 12, "bold"))
        c.create_text(113, 66, text="CONTROLLER", anchor="w", fill=RED, font=(MONO, 24, "bold"))
        c.create_text(111, 65, text="CONTROLLER", anchor="w", fill=ORANGE, font=(MONO, 24, "bold"))
        c.create_text(112, 92, text="DARKDEATH EVIL // BATTERY MONITOR", anchor="w",
                      fill=MUTED, font=(MONO, 8))
        c.create_line(18, 112, W - 18, 112, fill=RED, width=2)
        c.create_line(18, 116, 140, 116, fill=ORANGE, width=1)

        # gauge panel
        self.bracket(25, 130, W - 25, 420, RED)
        c.create_text(40, 143, text="// POWER CORE", anchor="w", fill=MUTED, font=(MONO, 8))
        c.create_oval(CX - R, CY - R, CX + R, CY + R, outline=DIM, width=1)
        c.create_arc(CX - R, CY - R, CX + R, CY + R, start=225, extent=-270,
                     style=tk.ARC, outline=DIM, width=14)
        for i in range(28):
            a = math.radians(225 - i * 10)
            r1, r2 = R + 14, R + (24 if i % 9 == 0 else 19)
            c.create_line(CX + r1 * math.cos(a), CY - r1 * math.sin(a),
                          CX + r2 * math.cos(a), CY - r2 * math.sin(a),
                          fill=MUTED if i % 9 == 0 else DIM, width=2)
        c.create_text(CX - 78, CY + 98, text="0", fill=MUTED, font=(MONO, 8))
        c.create_text(CX + 78, CY + 98, text="100", fill=MUTED, font=(MONO, 8))

        # segment panel
        self.bracket(25, 435, W - 25, 505, RED)
        c.create_text(40, 447, text="// CELL STATUS", anchor="w", fill=MUTED, font=(MONO, 8))
        for i, name in enumerate(("EMPTY", "LOW", "MED", "FULL")):
            x = 38 + i * 87
            c.create_text(x + 38, 494, text=name, fill=MUTED, font=(MONO, 7))

        # status panel
        self.bracket(25, 520, W - 25, 605, RED)
        c.create_text(40, 532, text="// LINK STATUS", anchor="w", fill=MUTED, font=(MONO, 8))

        # footer
        c.create_line(18, 622, W - 18, 622, fill=DIM)
        c.create_text(W // 2, 636, text="DARKDEATH EVIL  //  DARK CONTROLLER v1.0",
                      fill=MUTED, font=(MONO, 8))

    # ----- data -----
    def poll(self):
        self.data = read_battery()
        if self.data:
            self.target = LEVEL_PERCENT.get(self.data["level"], 0)
            self.charging = self.data["type"] == 1  # wired USB = charging
        else:
            self.target = 0
            self.charging = False
        self.after(POLL_MS, self.poll)

    # ----- dynamic layer -----
    def tick(self):
        c = self.cv
        c.delete("dyn")
        t = time.time() - self.t0
        self.shown += (self.target - self.shown) * 0.12
        pct = self.shown
        col = level_color(self.target)

        # value arc
        if pct > 0.5:
            c.create_arc(CX - R, CY - R, CX + R, CY + R, start=225, extent=-270 * pct / 100,
                         style=tk.ARC, outline=col, width=14, tags="dyn")

        # charging pulse ring
        pulse = (math.sin(t * 4) + 1) / 2
        if self.charging:
            ring = lerp_color(DIM, ORANGE, pulse)
            c.create_oval(CX - R - 32, CY - R - 32, CX + R + 32, CY + R + 32,
                          outline=ring, width=2, tags="dyn")

        # center text
        if self.data:
            c.create_text(CX, CY - 8, text=f"~{int(round(pct))}%", fill=TEXT,
                          font=(MONO, 34, "bold"), tags="dyn")
            c.create_text(CX, CY + 30, text="BATTERY", fill=MUTED, font=(MONO, 9), tags="dyn")
        else:
            c.create_text(CX, CY - 8, text="--", fill=MUTED, font=(MONO, 34, "bold"), tags="dyn")
            c.create_text(CX, CY + 30, text="NO SIGNAL", fill=RED, font=(MONO, 10, "bold"), tags="dyn")
        if self.charging:
            c.create_text(CX, CY + 56, text="\u26A1 CHARGING",
                          fill=lerp_color(RED, ORANGE, pulse), font=(MONO, 11, "bold"), tags="dyn")

        # segments
        lvl = self.data["level"] if self.data else -1
        for i in range(4):
            x = 38 + i * 87
            on = i <= lvl
            fill = level_color(LEVEL_PERCENT[i]) if on else PANEL
            if on and self.charging and i == lvl:
                fill = lerp_color(PANEL, fill, 0.4 + 0.6 * pulse)
            c.create_rectangle(x, 462, x + 76, 480, fill=fill, outline=RED if not on else fill,
                               tags="dyn")

        # status rows
        if self.data:
            link = {1: "WIRED (USB)", 2: "WIRELESS", 3: "WIRELESS"}.get(self.data["type"], "UNKNOWN")
            rows = (("LINK ", link), ("LEVEL", LEVEL_TEXT.get(self.data["level"], "?")),
                    ("PAD  ", f"#{self.data['slot']}"))
        else:
            rows = (("LINK ", "OFFLINE"), ("LEVEL", "--"), ("PAD  ", "--"))
        for i, (k, v) in enumerate(rows):
            y = 553 + i * 18
            c.create_text(45, y, text=k + " :", anchor="w", fill=MUTED, font=(MONO, 10), tags="dyn")
            c.create_text(125, y, text=v, anchor="w", fill=TEXT, font=(MONO, 10, "bold"), tags="dyn")

        # status dot
        dot = GOOD if self.data else RED
        if self.data is None and pulse > 0.5:
            dot = DIM
        c.create_oval(W - 48, 538, W - 38, 548, fill=dot, outline="", tags="dyn")

        self.after(FRAME_MS, self.tick)


if __name__ == "__main__":
    App().mainloop()
