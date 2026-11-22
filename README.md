# DARK CONTROLLER

Sci-fi styled Windows app that shows your controller's battery level and a live charging indicator.
Made by **DarkDeath Evil**. Built with Python + Tkinter, battery read via Windows XInput.

## Run
```
python main.py
```
No extra packages needed (Python 3.9+ on Windows).

## Build .exe
```
pip install pyinstaller
pyinstaller --onefile --windowed --icon assets/icon.ico --add-data "assets;assets" --name DarkController main.py
```

## Diagnostic
Press **D** in the app (or click the button) to save `diagnostic.txt` next to the exe.
Run it once in each mode (wired, 2.4GHz dongle, Bluetooth) to find how your controller reports battery.

## Notes
- Battery is shown only when really reported (Windows Bluetooth battery or XInput wireless battery), else N/A.
- "Charging" shows only when the controller is connected by USB cable.
- Needs `hidapi` (`pip install hidapi`) when running from source.
- Budget controllers may not report battery over Bluetooth / 2.4GHz dongle.

## Roadmap
- [ ] Raw HID mode for exact battery %
- [ ] System tray icon
- [ ] Low battery alert

## Tested with
- Cosmic Byte Lumora (add your results)
