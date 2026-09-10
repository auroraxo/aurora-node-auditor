import os
import tempfile
import unittest
from unittest.mock import patch

from auditor.host import (
    CpuSampler,
    collect_host_vitals,
    read_cpu_temperature_c,
    read_rpi_undervoltage_alarm,
    read_wireless,
)


class CpuSamplerTests(unittest.TestCase):
    def test_delta_is_non_blocking_and_first_value_is_not_fabricated(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as handle:
            path = handle.name
            handle.write("cpu  100 0 50 850 0 0 0 0 0 0\n")
        try:
            sampler = CpuSampler(path)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("cpu  120 0 60 920 0 0 0 0 0 0\n")
            # 30 busy jiffies out of 100 total.
            self.assertEqual(sampler.sample(), 30.0)
        finally:
            os.unlink(path)

    def test_bad_cpu_source_returns_none(self):
        sampler = CpuSampler("/definitely/not/here")
        self.assertIsNone(sampler.sample())


class WirelessTests(unittest.TestCase):
    def _wireless_file(self, body):
        handle = tempfile.NamedTemporaryFile(mode="w", delete=False)
        handle.write(body)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def test_trailing_period_and_unmeasured_noise_are_handled(self):
        path = self._wireless_file(
            "Inter-| sta-| Quality | Discarded packets | Missed | WE\n"
            " face | tus | link level noise | nwid crypt frag retry misc | beacon | 22\n"
            " wlan0: 0000   46.  -64.  -256        0 0 0 0 0 0\n"
        )
        self.assertEqual(
            read_wireless(path),
            {"interface": "wlan0", "link_quality": 46.0, "rssi_dbm": -64, "noise_dbm": None},
        )

    def test_header_only_means_no_associated_interface(self):
        path = self._wireless_file("Inter-| sta-| Quality\n face | tus | link level noise\n")
        self.assertIsNone(read_wireless(path))


class TemperatureTests(unittest.TestCase):
    def test_prefers_cpu_zone_and_reads_millidegrees(self):
        with tempfile.TemporaryDirectory() as root:
            for zone, kind, value in (
                ("thermal_zone0", "wifi", "39000"),
                ("thermal_zone1", "cpu-thermal", "47250"),
            ):
                os.mkdir(os.path.join(root, zone))
                with open(os.path.join(root, zone, "type"), "w", encoding="utf-8") as handle:
                    handle.write(kind)
                with open(os.path.join(root, zone, "temp"), "w", encoding="utf-8") as handle:
                    handle.write(value)
            self.assertEqual(read_cpu_temperature_c(root), 47.25)

    def test_missing_thermal_tree_returns_none(self):
        self.assertIsNone(read_cpu_temperature_c("/definitely/not/here"))


class RpiUndervoltageTests(unittest.TestCase):
    def _write_hwmon_file(self, root, device, filename, content):
        device_path = os.path.join(root, device)
        os.makedirs(device_path, exist_ok=True)
        with open(os.path.join(device_path, filename), "w", encoding="utf-8") as handle:
            handle.write(content)

    def test_reads_rpi_volt_alarm_and_ignores_other_hwmon_devices(self):
        with tempfile.TemporaryDirectory() as root:
            self._write_hwmon_file(root, "hwmon0", "name", "other_sensor\n")
            self._write_hwmon_file(root, "hwmon0", "in0_lcrit_alarm", "1\n")
            self._write_hwmon_file(root, "hwmon1", "name", "rpi_volt\n")
            self._write_hwmon_file(root, "hwmon1", "in0_lcrit_alarm", "1\n")
            self.assertIs(read_rpi_undervoltage_alarm(root), True)

    def test_clear_rpi_volt_alarm_is_false(self):
        with tempfile.TemporaryDirectory() as root:
            self._write_hwmon_file(root, "hwmon0", "name", "rpi_volt\n")
            self._write_hwmon_file(root, "hwmon0", "in0_lcrit_alarm", "0\n")
            self.assertIs(read_rpi_undervoltage_alarm(root), False)

    def test_missing_rpi_volt_or_alarm_file_is_none(self):
        with tempfile.TemporaryDirectory() as root:
            self._write_hwmon_file(root, "hwmon0", "name", "other_sensor\n")
            self.assertIsNone(read_rpi_undervoltage_alarm(root))
        with tempfile.TemporaryDirectory() as root:
            self._write_hwmon_file(root, "hwmon0", "name", "rpi_volt\n")
            self.assertIsNone(read_rpi_undervoltage_alarm(root))

    def test_malformed_rpi_volt_alarm_is_none(self):
        with tempfile.TemporaryDirectory() as root:
            self._write_hwmon_file(root, "hwmon0", "name", "rpi_volt\n")
            self._write_hwmon_file(root, "hwmon0", "in0_lcrit_alarm", "2\n")
            self.assertIsNone(read_rpi_undervoltage_alarm(root))


class HostVitalsTests(unittest.TestCase):
    def test_collect_host_vitals_includes_undervoltage_alarm(self):
        with (
            patch("auditor.host.time.time", return_value=123.45),
            patch("auditor.host.read_wireless", return_value=None),
            patch("auditor.host.read_cpu_temperature_c", return_value=47.25),
            patch("auditor.host.read_rpi_undervoltage_alarm", return_value=True),
        ):
            self.assertEqual(
                collect_host_vitals(),
                {
                    "timestamp": 123.45,
                    "cpu_pct": None,
                    "temp_c": 47.25,
                    "rssi_dbm": None,
                    "wireless": None,
                    "undervoltage_alarm": True,
                },
            )


if __name__ == "__main__":
    unittest.main()
