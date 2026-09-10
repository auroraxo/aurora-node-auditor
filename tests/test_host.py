import os
import tempfile
import unittest
from unittest.mock import patch

from auditor.host import (
    CpuSampler,
    collect_host_vitals,
    read_cpu_frequency,
    read_cpu_temperature_c,
    read_rpi_undervoltage_alarm,
    read_throttle_flags,
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


class ThrottleFlagsTests(unittest.TestCase):
    def test_decode_real_throttled_value_0x20002(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as handle:
            handle.write("0x20002\n")
            path = handle.name
        self.addCleanup(os.unlink, path)
        self.assertEqual(
            read_throttle_flags(path),
            {
                "raw": "0x20002",
                "undervoltage_now": False,
                "arm_frequency_capped_now": True,
                "throttled_now": False,
                "soft_temp_limit_now": False,
                "undervoltage_occurred": False,
                "arm_frequency_capped_occurred": True,
                "throttled_occurred": False,
                "soft_temp_limit_occurred": False,
            },
        )

    def test_decode_all_clear_0x0(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as handle:
            handle.write("0x0\n")
            path = handle.name
        self.addCleanup(os.unlink, path)
        self.assertEqual(
            read_throttle_flags(path),
            {
                "raw": "0x0",
                "undervoltage_now": False,
                "arm_frequency_capped_now": False,
                "throttled_now": False,
                "soft_temp_limit_now": False,
                "undervoltage_occurred": False,
                "arm_frequency_capped_occurred": False,
                "throttled_occurred": False,
                "soft_temp_limit_occurred": False,
            },
        )

    def test_plain_decimal_looking_hex(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as handle:
            handle.write(" 20002 \n")
            path = handle.name
        self.addCleanup(os.unlink, path)
        res = read_throttle_flags(path)
        self.assertIsNotNone(res)
        self.assertEqual(res["raw"], "0x20002")
        self.assertTrue(res["arm_frequency_capped_now"])
        self.assertTrue(res["arm_frequency_capped_occurred"])
        self.assertFalse(res["undervoltage_now"])

    def test_malformed_value_returns_none(self):
        for bad_val in ("not_hex\n", "", "   \n", "-1\n", "0xG"):
            with tempfile.NamedTemporaryFile(mode="w", delete=False) as handle:
                handle.write(bad_val)
                path = handle.name
            self.addCleanup(os.unlink, path)
            self.assertIsNone(read_throttle_flags(path))

    def test_missing_directory_returns_none(self):
        self.assertIsNone(read_throttle_flags("/definitely/not/here/get_throttled"))


class CpuFrequencyTests(unittest.TestCase):
    def test_frequency_capped_computation(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "scaling_cur_freq"), "w", encoding="utf-8") as handle:
                handle.write("600000\n")
            with open(os.path.join(root, "cpuinfo_max_freq"), "w", encoding="utf-8") as handle:
                handle.write("1500000\n")
            self.assertEqual(
                read_cpu_frequency(root),
                {
                    "current_mhz": 600.0,
                    "max_mhz": 1500.0,
                    "capped_pct": 60.0,
                },
            )

    def test_frequency_uncapped_clamped_at_zero(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "scaling_cur_freq"), "w", encoding="utf-8") as handle:
                handle.write("1500000\n")
            with open(os.path.join(root, "cpuinfo_max_freq"), "w", encoding="utf-8") as handle:
                handle.write("1500000\n")
            self.assertEqual(
                read_cpu_frequency(root),
                {
                    "current_mhz": 1500.0,
                    "max_mhz": 1500.0,
                    "capped_pct": 0.0,
                },
            )

    def test_zero_max_frequency_returns_none(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "scaling_cur_freq"), "w", encoding="utf-8") as handle:
                handle.write("600000\n")
            with open(os.path.join(root, "cpuinfo_max_freq"), "w", encoding="utf-8") as handle:
                handle.write("0\n")
            self.assertIsNone(read_cpu_frequency(root))

    def test_missing_directory_returns_none(self):
        self.assertIsNone(read_cpu_frequency("/definitely/not/here"))

    def test_missing_file_or_malformed_returns_none(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "scaling_cur_freq"), "w", encoding="utf-8") as handle:
                handle.write("600000\n")
            self.assertIsNone(read_cpu_frequency(root))

        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "scaling_cur_freq"), "w", encoding="utf-8") as handle:
                handle.write("bad_val\n")
            with open(os.path.join(root, "cpuinfo_max_freq"), "w", encoding="utf-8") as handle:
                handle.write("1500000\n")
            self.assertIsNone(read_cpu_frequency(root))


class HostVitalsTests(unittest.TestCase):
    def test_collect_host_vitals_includes_undervoltage_alarm(self):
        mock_throttle = {
            "raw": "0x20002",
            "undervoltage_now": False,
            "arm_frequency_capped_now": True,
            "throttled_now": False,
            "soft_temp_limit_now": False,
            "undervoltage_occurred": False,
            "arm_frequency_capped_occurred": True,
            "throttled_occurred": False,
            "soft_temp_limit_occurred": False,
        }
        mock_cpufreq = {
            "current_mhz": 600.0,
            "max_mhz": 1500.0,
            "capped_pct": 60.0,
        }
        with (
            patch("auditor.host.time.time", return_value=123.45),
            patch("auditor.host.read_wireless", return_value=None),
            patch("auditor.host.read_cpu_temperature_c", return_value=47.25),
            patch("auditor.host.read_rpi_undervoltage_alarm", return_value=True),
            patch("auditor.host.read_throttle_flags", return_value=mock_throttle),
            patch("auditor.host.read_cpu_frequency", return_value=mock_cpufreq),
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
                    "throttle": mock_throttle,
                    "cpu_frequency": mock_cpufreq,
                },
            )

    def test_collect_host_vitals_defaults_to_none_when_unavailable(self):
        with (
            patch("auditor.host.time.time", return_value=123.45),
            patch("auditor.host.read_wireless", return_value=None),
            patch("auditor.host.read_cpu_temperature_c", return_value=None),
            patch("auditor.host.read_rpi_undervoltage_alarm", return_value=None),
            patch("auditor.host.read_throttle_flags", return_value=None),
            patch("auditor.host.read_cpu_frequency", return_value=None),
        ):
            self.assertEqual(
                collect_host_vitals(),
                {
                    "timestamp": 123.45,
                    "cpu_pct": None,
                    "temp_c": None,
                    "rssi_dbm": None,
                    "wireless": None,
                    "undervoltage_alarm": None,
                    "throttle": None,
                    "cpu_frequency": None,
                },
            )


if __name__ == "__main__":
    unittest.main()
