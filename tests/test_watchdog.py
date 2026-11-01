import datetime as dt
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("watchdog", Path(__file__).resolve().parents[1] / "watchdog.py")
watchdog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watchdog)


class DetectionTests(unittest.TestCase):
    now = 1804289760
    serial = "TEST_NEO"

    def line(self, offset, message):
        stamp = dt.datetime.fromtimestamp(self.now + offset, dt.timezone.utc).isoformat()
        return stamp + " " + message

    def failure(self, offset=-30, serial=None):
        return self.line(offset, "DeviceComm [" + (serial or self.serial) + "]: Preheat Read FW version: FAILED")

    def test_hid_failure(self):
        self.assertGreater(watchdog.failure_time([self.failure()], self.now, self.serial), 0)

    def test_recovered(self):
        connected = self.line(-10, "DeviceManager device status changed [" + self.serial + "]: connected")
        self.assertEqual(watchdog.failure_time([self.failure(), connected], self.now, self.serial), 0)

    def test_other_device_and_empty_serial(self):
        self.assertEqual(watchdog.failure_time([self.failure(serial="OTHER")], self.now, self.serial), 0)
        self.assertEqual(watchdog.failure_time([self.failure()], self.now, ""), 0)

    def test_time_window(self):
        self.assertEqual(watchdog.failure_time([self.failure(-1801)], self.now, self.serial), 0)
        self.assertGreater(watchdog.failure_time([self.failure(-601)], self.now, self.serial), 0)
        self.assertEqual(watchdog.failure_time([self.failure(60)], self.now, self.serial), 0)

    def test_firmware_update_suppresses_reset(self):
        lines = [self.failure(), self.line(-5, "Starting firmware update")]
        self.assertEqual(watchdog.failure_time(lines, self.now, self.serial), 0)

    def test_image_failure(self):
        line = self.line(-5, "DeviceComm [" + self.serial + "]: Upload Image Ignore error: FAILED")
        self.assertGreater(watchdog.failure_time([line], self.now, self.serial), 0)

    def test_malformed_lines(self):
        self.assertEqual(watchdog.failure_time(["", "invalid timestamp"], self.now, self.serial), 0)
