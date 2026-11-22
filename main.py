"""DARK CONTROLLER v1.1 - sci-fi controller battery monitor (Windows)
By DarkDeath Evil

- Link type (USB wired / 2.4GHz dongle / Bluetooth) is detected from HID devices.
- Battery is shown ONLY when it is really reported (Windows Bluetooth battery,
  or XInput wireless battery). Otherwise it shows N/A instead of fake values.
- CHARGING is shown only when the controller is connected by USB cable.
- Press D (or click the button) to save diagnostic.txt for debugging.
"""
import ctypes
import math
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from datetime import datetime

try:
    import hid  # pip install hidapi
except Exception:
    hid = None

BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(BASE, "assets")
OUT_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) \
    else os.path.dirname(os.path.abspath(__file__))

# ---------- XInput ----------
try:
    xinput = ctypes.windll.xinput1_4
except (AttributeError, OSError):
    xinput = None


class BATTERY_INFO(ctypes.Structure):
    _fields_ = [("BatteryType", ctypes.c_ubyte),
                ("BatteryLevel", ctypes.c_ubyte)]


LEVEL_PERCENT = {0: 5, 1: 25, 2: 60, 3: 100}


def read_xinput():
    """First connected XInput pad -> dict, else None."""
    if xinput is None:
        return None
    for slot in range(4):
        info = BATTERY_INFO()
        if xinput.XInputGetBatteryInformation(slot, 0, ctypes.byref(info)) == 0 and info.BatteryType != 0:
            return {"slot": slot, "type": info.BatteryType, "level": info.BatteryLevel}
    return None


# ---------- Bluetooth battery (Windows property) ----------
CREATE_NO_WINDOW = 0x08000000
PS_BT = r"""
$ErrorActionPreference='SilentlyContinue'
Get-PnpDevice -Class Bluetooth -PresentOnly | ForEach-Object {
  $p = Get-PnpDeviceProperty -InstanceId $_.InstanceId -KeyName '{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2'
  if ($p -and $p.Data -ne $null) { "$($_.FriendlyName)|$($p.Data)" }
}
"""


def bt_batteries():
    if os.name != "nt":
        return []
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", PS_BT],
                           capture_output=True, text=True, timeout=25,
                           creationflags=CREATE_NO_WINDOW)
    except Exception:
        return []
    res = []
    for line in r.stdout.splitlines():
        name, _, val = line.partition("|")
        try:
            res.append((name.strip(), int(float(val))))
        except ValueError:
            pass
    return res


def match_bt(batts, pad_name):
    tokens = [t for t in ("lumora", "cosmic", (pad_name or "").lower()) if t]
    for name, val in batts:
        if any(t in name.lower() for t in tokens):
            return val
    return None


# ---------- HID link detection ----------
def path_str(d):
    p = d.get("path", b"")
    return (p.decode("utf-8", "ignore") if isinstance(p, (bytes, bytearray)) else str(p)).lower()


def is_pad(d):
    return (d.get("usage_page") == 1 and d.get("usage") in (4, 5)) or "&ig_" in path_str(d)


def classify_link(p, name):
    if any(k in p for k in ("{00001124", "{00001812", "bthenum", "bthle")):
        return "BLUETOOTH"
    n = (name or "").lower()
    if any(k in n for k in ("2.4", "dongle", "receiver", "wireless")):
        return "2.4GHZ DONGLE"
    return "USB WIRED"


def find_pads():
    if hid is None:
        return []
    try:
        devs = hid.enumerate()
    except Exception:
        return []
    pads = {}
    for d in devs:
        if not is_pad(d):
            continue
        p = path_str(d)
        name = d.get("product_string") or "Controller"
        key = (d.get("vendor_id"), d.get("product_id"))
        if key not in pads:
            pads[key] = {"name": name, "link": classify_link(p, name)}
    return list(pads.values())


# ---------- Diagnostic ----------
def diagnostic():
    path = os.path.join(OUT_DIR, "diagnostic.txt")
    L = ["", f"===== {datetime.now():%Y-%m-%d %H:%M:%S} =====",
         f"hidapi available: {'yes' if hid else 'NO'}"]
    if xinput:
        for s in range(4):
            info = BATTERY_INFO()
            r = xinput.XInputGetBatteryInformation(s, 0, ctypes.byref(info))
            L.append(f"XInput slot {s}: ret={r} type={info.BatteryType} level={info.BatteryLevel}")
    L.append("Bluetooth battery (name, %): " + repr(bt_batteries()))
    if hid:
        try:
            devs = [d for d in hid.enumerate() if is_pad(d)]
        except Exception as e:
            devs = []
            L.append(f"enumerate error: {e}")
        for d in devs:
            L.append("HID vid=%04X pid=%04X product=%r manuf=%r usage=%s/%s iface=%s\n   path=%s" % (
                d.get("vendor_id", 0), d.get("product_id", 0), d.get("product_string"),
                d.get("manufacturer_string"), d.get("usage_page"), d.get("usage"),
                d.get("interface_number"), path_str(d)))
        L.append("--- raw reports (move sticks / press buttons) ---")
        for d in devs:
            if "&ig_" in path_str(d):
                L.append(f"{d.get('product_string')}: XInput interface, skipped")
                continue
            try:
                h = hid.device()
                h.open_path(d["path"])
                h.set_nonblocking(True)
                seen, t0 = [], time.time()
                while time.time() - t0 < 3 and len(seen) < 6:
                    data = h.read(64)
                    if data:
                        hx = bytes(data).hex(" ")
                        if hx not in seen:
                            seen.append(hx)
                    time.sleep(0.02)
                h.close()
                L.append(f"{d.get('product_string')} ({len(seen)} reports):")
                L.extend("   " + s for s in seen)
            except Exception as e:
                L.append(f"{d.get('product_string')}: cannot open ({e})")
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return path


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

W, H = 420, 700
CX, CY, R = 210, 275, 100
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

        self.state = {"online": False, "link": None, "name": "--", "pct": None,
                      "source": "--", "charging": False}
        self.shown = 0.0
        self.msg, self.msg_until = "", 0
        self.diag_running = False
        self.t0 = time.time()

        self.draw_static()
        self.cv.tag_bind("btn", "<Button-1>", lambda e: self.start_diag())
        self.bind("<KeyPress-d>", lambda e: self.start_diag())
        self.bind("<KeyPress-D>", lambda e: self.start_diag())

        threading.Thread(target=self.worker, daemon=True).start()
        self.tick()

    # ----- background detection -----
    def worker(self):
        batts, last_bt = [], 0.0
        order = {"USB WIRED": 0, "2.4GHZ DONGLE": 1, "BLUETOOTH": 2}
        while True:
            try:
                xi = read_xinput()
                pads = [p for p in find_pads()
                        if p["link"] == "BLUETOOTH" or xinput is None or xi is not None]
                pads.sort(key=lambda p: order[p["link"]])
                st = {"online": False, "link": None, "name": "--", "pct": None,
                      "source": "--", "charging": False}
                if pads:
                    st.update(online=True, link=pads[0]["link"], name=pads[0]["name"])
                elif xi is not None:
                    st.update(online=True, link="XINPUT", name="XInput Controller")

                if st["online"]:
                    st["charging"] = st["link"] == "USB WIRED"
                    if st["link"] == "BLUETOOTH":
                        if time.time() - last_bt > 15:
                            batts, last_bt = bt_batteries(), time.time()
                        v = match_bt(batts, st["name"])
                        if v is not None:
                            st.update(pct=v, source="WINDOWS BLUETOOTH")
                        else:
                            st["source"] = "NOT REPORTED"
                    elif xi and xi["type"] in (2, 3):  # real wireless battery
                        st.update(pct=LEVEL_PERCENT.get(xi["level"], 0), source="XINPUT (4 LEVELS)")
                    else:
                        st["source"] = "NOT REPORTED"
                self.state = st
            except Exception:
                pass
            time.sleep(2)

    # ----- diagnostic -----
    def start_diag(self):
        if self.diag_running:
            return
        self.diag_running = True
        self.msg, self.msg_until = "SAVING... (3 sec)", time.time() + 60

        def run():
            try:
                p = diagnostic()
                self.msg = "SAVED: diagnostic.txt"
                self.msg_until = time.time() + 6
                self.saved_path = p
            except Exception as e:
                self.msg, self.msg_until = f"ERROR: {str(e)[:28]}", time.time() + 6
            self.diag_running = False

        threading.Thread(target=run, daemon=True).start()

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

        if self.logo:
            c.create_image(18, 14, image=self.logo, anchor="nw")
        c.create_text(112, 38, text="DARK", anchor="w", fill=RED, font=(MONO, 12, "bold"))
        c.create_text(113, 66, text="CONTROLLER", anchor="w", fill=RED, font=(MONO, 24, "bold"))
        c.create_text(111, 65, text="CONTROLLER", anchor="w", fill=ORANGE, font=(MONO, 24, "bold"))
        c.create_text(112, 92, text="DARKDEATH EVIL // BATTERY MONITOR", anchor="w",
                      fill=MUTED, font=(MONO, 8))
        c.create_line(18, 112, W - 18, 112, fill=RED, width=2)
        c.create_line(18, 116, 140, 116, fill=ORANGE, width=1)

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

        self.bracket(25, 435, W - 25, 505, RED)
        c.create_text(40, 447, text="// CELL STATUS", anchor="w", fill=MUTED, font=(MONO, 8))
        for i, name in enumerate(("0-25", "26-50", "51-75", "76-100")):
            c.create_text(38 + i * 87 + 38, 494, text=name, fill=MUTED, font=(MONO, 7))

        self.bracket(25, 520, W - 25, 605, RED)
        c.create_text(40, 532, text="// LINK STATUS", anchor="w", fill=MUTED, font=(MONO, 8))

        c.create_rectangle(100, 620, W - 100, 648, outline=ORANGE, fill=PANEL, tags="btn")

        c.create_line(18, 662, W - 18, 662, fill=DIM)
        c.create_text(W // 2, 678, text="DARKDEATH EVIL  //  DARK CONTROLLER v1.1",
                      fill=MUTED, font=(MONO, 8))

    # ----- dynamic layer -----
    def tick(self):
        c = self.cv
        c.delete("dyn")
        t = time.time() - self.t0
        st = self.state
        known = st["pct"] is not None
        target = st["pct"] if known else 0
        self.shown += (target - self.shown) * 0.12
        pct = self.shown
        col = level_color(target)
        pulse = (math.sin(t * 4) + 1) / 2

        if pct > 0.5:
            c.create_arc(CX - R, CY - R, CX + R, CY + R, start=225, extent=-270 * pct / 100,
                         style=tk.ARC, outline=col, width=14, tags="dyn")
        if st["charging"]:
            c.create_oval(CX - R - 32, CY - R - 32, CX + R + 32, CY + R + 32,
                          outline=lerp_color(DIM, ORANGE, pulse), width=2, tags="dyn")

        if not st["online"]:
            c.create_text(CX, CY - 8, text="--", fill=MUTED, font=(MONO, 34, "bold"), tags="dyn")
            c.create_text(CX, CY + 30, text="NO SIGNAL", fill=RED, font=(MONO, 10, "bold"), tags="dyn")
        elif known:
            tilde = "~" if st["source"].startswith("XINPUT") else ""
            c.create_text(CX, CY - 8, text=f"{tilde}{int(round(pct))}%", fill=TEXT,
                          font=(MONO, 34, "bold"), tags="dyn")
            c.create_text(CX, CY + 30, text="BATTERY", fill=MUTED, font=(MONO, 9), tags="dyn")
        else:
            c.create_text(CX, CY - 8, text="N/A", fill=MUTED, font=(MONO, 34, "bold"), tags="dyn")
            c.create_text(CX, CY + 30, text="NOT REPORTED", fill=ORANGE, font=(MONO, 9, "bold"),
                          tags="dyn")
        if st["charging"]:
            c.create_text(CX, CY + 56, text="\u26A1 CHARGING",
                          fill=lerp_color(RED, ORANGE, pulse), font=(MONO, 11, "bold"), tags="dyn")

        for i in range(4):
            x = 38 + i * 87
            on = known and target > i * 25
            fill = col if on else PANEL
            if on and st["charging"] and target <= (i + 1) * 25:
                fill = lerp_color(PANEL, col, 0.4 + 0.6 * pulse)
            c.create_rectangle(x, 462, x + 76, 480, fill=fill, outline=col if on else DIM, tags="dyn")

        rows = (("LINK  ", st["link"] or "OFFLINE"),
                ("DEVICE", st["name"][:26]),
                ("SOURCE", st["source"]))
        for i, (k, v) in enumerate(rows):
            y = 553 + i * 18
            c.create_text(45, y, text=k + " :", anchor="w", fill=MUTED, font=(MONO, 10), tags="dyn")
            c.create_text(135, y, text=v, anchor="w", fill=TEXT, font=(MONO, 10, "bold"), tags="dyn")

        dot = GOOD if st["online"] else (RED if pulse > 0.5 else DIM)
        c.create_oval(W - 48, 538, W - 38, 548, fill=dot, outline="", tags="dyn")

        label = self.msg if time.time() < self.msg_until else "[ D ]  SAVE DIAGNOSTIC"
        c.create_text(W // 2, 634, text=label, fill=ORANGE, font=(MONO, 9, "bold"), tags=("dyn", "btn"))

        self.after(FRAME_MS, self.tick)


if __name__ == "__main__":
    App().mainloop()
