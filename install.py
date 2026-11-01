#!/usr/bin/python3
"""Build and install the current user's watchdog, or uninstall it."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys

BASE = Path(__file__).resolve().parent
LABEL = "com.ruslan.streamdeck-watchdog"
PLIST = Path.home() / "Library/LaunchAgents" / (LABEL + ".plist")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial")
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    if args.uninstall:
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"], check=False)
        PLIST.unlink(missing_ok=True)
        print("LaunchAgent removed. Source and configuration preserved.")
        return
    if not args.serial or not args.serial.strip():
        parser.error("--serial is required for installation")
    subprocess.run(["clang", "-Wall", "-Wextra", "-Werror", "-Wno-deprecated-declarations",
                    str(BASE / "neo-usb-reset.c"), "-framework", "IOKit", "-framework",
                    "CoreFoundation", "-o", str(BASE / "neo-usb-reset")], check=True)
    (BASE / "config.json").write_text(json.dumps({"serial": args.serial}, indent=2) + "\n")
    definition = {
        "Label": LABEL,
        "ProgramArguments": [sys.executable, str(BASE / "watchdog.py")],
        "StartInterval": 600, "RunAtLoad": True, "ProcessType": "Background",
        "StandardOutPath": str(BASE / "watchdog.log"),
        "StandardErrorPath": str(BASE / "watchdog.log"),
    }
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    with PLIST.open("wb") as stream:
        plistlib.dump(definition, stream)
    subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(PLIST)], check=True)
    print("Installed: checks every 10 minutes and at login.")


if __name__ == "__main__":
    main()
