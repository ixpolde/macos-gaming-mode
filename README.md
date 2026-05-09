# macOS Gaming Mode

One-click max performance mode for macOS. Disables all power-saving features and keeps your MacBook running at full speed — no throttling, no sleep, no interruptions.

![Python](https://img.shields.io/badge/python-3.8+-blue) ![macOS](https://img.shields.io/badge/macOS-12%2B-lightgrey) ![License](https://img.shields.io/badge/license-MIT-green)

## What it does

When activated, it applies the following via `pmset` and `caffeinate`:

| Setting | Gaming Mode | Normal |
|---|---|---|
| Low Power Mode | Off | Off |
| System Sleep | Disabled | 10 min |
| Disk Sleep | Disabled | 10 min |
| Display Sleep | Disabled | 5 min |
| Power Nap | Off | On |
| App Nap | Off | On |
| caffeinate | Running | — |

When you close the app or click Disable, everything is restored to defaults automatically.

## Requirements

- macOS 12+
- Python 3.8+ (built-in `tkinter` — no pip installs needed)
- Admin password (required once to apply `pmset` changes)

## Usage

```bash
python3 power.py
```

Click **Enable Power Mode**, enter your password once, and you're good to go.

> Best results when plugged in to AC power — the app will warn you if you're on battery.

## Why

macOS aggressively throttles CPU and GPU when it thinks you don't need the power. This is great for battery life, bad for gaming or rendering. This app flips all the relevant knobs in one click and restores them when you're done.

## License

MIT
