"""Validated MT7981 board profiles shared by import and image verification."""
import json
from pathlib import Path

def load_device(name):
    devices = json.loads((Path(__file__).resolve().parents[1] / 'configs/devices.json').read_text())
    if name not in devices:
        raise SystemExit('Unsupported device profile: ' + name)
    return devices[name]
