#!/usr/bin/python3
"""Recover this Neo only when the official app reports a fresh HID failure."""
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
LOG = Path.home() / "Library/Logs/ElgatoStreamDeck/StreamDeck.log"
STATE = BASE / "watchdog-state.json"


def failure_time(lines, now, serial):
    failure = 0
    recovered = 0
    updating = False
    for line in lines:
        try:
            stamp = dt.datetime.fromisoformat(line.split()[0]).timestamp()
        except (ValueError, IndexError):
            continue
        if stamp > now + 5 or now - stamp > 1800:
            continue
        if re.search(r"firmware.*(updat|upgrad|flash)|(?:updat|upgrad|flash).*firmware", line, re.I):
            updating = True
        if not serial or serial not in line:
            continue
        if "device status changed" in line and "]: connected" in line:
            recovered = max(recovered, stamp)
        if any(message in line for message in (
            "Read FW version: FAILED", "Problem with connecting HID device",
            "SetRGB                           Ignore error: FAILED",
            "Upload Image                     Ignore error: FAILED",
        )) or ("DeviceComm" in line and "Ignore error: FAILED" in line):
            failure = max(failure, stamp)
    return failure if not updating and failure > recovered else 0


def main():
    if (BASE / "PAUSE").exists() or not LOG.exists():
        return
    serial = json.loads((BASE / "config.json").read_text())["serial"]
    if not isinstance(serial, str) or not serial.strip():
        raise ValueError("Configure a nonempty serial in config.json")
    # Only read a bounded tail; the app rotates its logs itself.
    with LOG.open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        stream.seek(max(0, stream.tell() - 1024 * 1024))
        lines = stream.read().decode("utf-8", errors="replace").splitlines()
    now = time.time()
    failure = failure_time(lines, now, serial)
    if "--check" in sys.argv:
        print(json.dumps({"failure_pending": bool(failure), "failure_timestamp": failure}))
        return
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    if not failure or failure <= state.get("handled_failure", 0):
        return
    if now - state.get("last_attempt", 0) < 600:
        return
    # Persist before running: a timeout must also be subject to the cooldown.
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(json.dumps({"last_attempt": now, "handled_failure": failure}))
    temporary.replace(STATE)
    print(dt.datetime.now().astimezone().isoformat(), "HID failure detected; reconnecting Neo", flush=True)
    try:
        result = subprocess.run([str(BASE / "neo-usb-reset"), "--reset", serial],
                                capture_output=True, text=True, timeout=20)
        print(result.stdout + result.stderr, end="", flush=True)
        print("exit:", result.returncode, flush=True)
    except subprocess.TimeoutExpired:
        print("USB reset timed out", flush=True)


if __name__ == "__main__":
    main()
