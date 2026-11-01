# Stream Deck Neo USB recovery for macOS

Reconnect an unresponsive Stream Deck Neo without physically unplugging its cable.
Includes an optional watchdog that checks the official app's log every 10 minutes.

## Build and reconnect

Requires macOS and Xcode Command Line Tools (`xcode-select --install`).
The watchdog also needs Python 3.9+. No third-party packages are needed.

```sh
clang -Wall -Wextra -Werror -Wno-deprecated-declarations neo-usb-reset.c -framework IOKit -framework CoreFoundation -o neo-usb-reset
./neo-usb-reset --list
./neo-usb-reset --reset YOUR_SERIAL
```

Only USB VID/PID `0FD9:009A` (Neo) and exactly one device with the requested serial
are accepted. The utility uses `USBDeviceReEnumerate` with options 0. It does not
reset the hub, cycle power, flash firmware, or change profiles. Run from a normal
Terminal; application sandboxes may block USB access.

## Automatic recovery

Keep this checkout in a permanent location, then install:

```sh
python3 install.py --serial YOUR_SERIAL
```

The installer builds the utility, writes a git-ignored `config.json`, and installs
user LaunchAgent `com.ruslan.streamdeck-watchdog`. It checks at login and every
600 seconds. No root privileges are required.

The watchdog detects explicit HID communication errors for the configured serial
in the last 30 minutes, unless a later successful connection was logged. Each
failure event is handled once, with at least 10 minutes between reset attempts.
Only the current `StreamDeck.log` is read (last 1 MiB). Silent freezes and errors
already rotated out of this log are not detected. Detection depends on the app's
log format. Activity is recorded in `watchdog.log` in this folder.

Inspect without resetting:

```sh
python3 watchdog.py --check
```

**Before firmware updates**, pause recovery by creating a `PAUSE` file here:

```sh
touch PAUSE
```

Remove that file after the update to resume. Recent firmware update mentions in
the app log also suppress recovery, but this is only a heuristic.

Uninstall the scheduled task (preserves files and configuration):

```sh
python3 install.py --uninstall
```

## Validation and limitations

On a physical Neo, USB re-enumeration recovered one occurrence of
`Read FW version: FAILED` / `Problem with connecting HID device`. The app then
reported `connected` and firmware `1.00.017`, without an app restart or cable
reconnection. This is not a diagnosis or a guarantee for every freeze.
The scheduled task was loaded successfully; recovery of a future freeze by the
scheduled task remains unverified.

```sh
python3 -m unittest discover -s tests
```

References: [Elgato Neo HID API](https://docs.elgato.com/streamdeck/hid/stream-deck-neo/)
and [Apple USBDeviceReEnumerate](https://developer.apple.com/documentation/iokit/iousbdeviceinterface187/1559027-usbdevicereenumerate).
