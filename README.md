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

## Notes
- XInput gives 4 levels (Empty / Low / Medium / Full), so the percentage is approximate.
- "Charging" shows when the controller is connected by USB cable.
- Budget controllers may not report battery over Bluetooth / 2.4GHz dongle.

## Roadmap
- [ ] Raw HID mode for exact battery %
- [ ] System tray icon
- [ ] Low battery alert

## Tested with
- Cosmic Byte Lumora (add your results)
