"""Dependency-free Pi/edge host vitals: non-blocking CPU%, temperature, WiFi RSSI.

Every reader in this module is a single file read from /proc or /sys. Nothing
shells out, nothing blocks, and a field that cannot be read returns None rather
than a plausible-looking zero — a missing RSSI read and a signal of 0 dBm are
different facts and must not render the same.
"""

import os
import time
from typing import Any, Dict, Optional, Tuple

_PROC_STAT = "/proc/stat"
_PROC_WIRELESS = "/proc/net/wireless"
_THERMAL_GLOB = "/sys/class/thermal"

# "not measured" sentinel the wireless drivers write into the noise column.
_NOISE_UNMEASURED = -256


def _read_cpu_totals(path: str = _PROC_STAT) -> Optional[Tuple[int, int]]:
    """Return (busy_jiffies, total_jiffies) from the aggregate cpu line."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("cpu "):
                    fields = [int(value) for value in line.split()[1:]]
                    if len(fields) < 4:
                        return None
                    total = sum(fields)
                    idle = fields[3] + (fields[4] if len(fields) > 4 else 0)
                    return total - idle, total
    except (OSError, ValueError):
        return None
    return None


class CpuSampler:
    """Non-blocking CPU utilisation from successive /proc/stat deltas.

    psutil's ``cpu_percent(interval=2)`` blocks for two seconds, which cannot sit
    in a loop that publishes at 10 Hz; ``interval=None`` returns 0.0 on its first
    call, which is a lie rather than an absence. This sampler returns ``None``
    until it holds two samples, and never blocks.
    """

    def __init__(self, path: str = _PROC_STAT) -> None:
        self._path = path
        self._previous = _read_cpu_totals(path)

    def sample(self) -> Optional[float]:
        """Return CPU busy percentage since the previous call, or None."""
        current = _read_cpu_totals(self._path)
        if current is None:
            return None
        previous = self._previous
        self._previous = current
        if previous is None:
            return None
        busy_delta = current[0] - previous[0]
        total_delta = current[1] - previous[1]
        if total_delta <= 0:
            return None
        return round(100.0 * busy_delta / total_delta, 2)


def read_cpu_temperature_c(thermal_root: str = _THERMAL_GLOB) -> Optional[float]:
    """Read CPU temperature in degrees Celsius from sysfs, or None.

    Prefers a zone whose ``type`` looks like a CPU/SoC sensor, falling back to
    thermal_zone0. Values are millidegrees on every kernel that exposes them.
    """
    candidates = []
    try:
        zones = sorted(
            name for name in os.listdir(thermal_root) if name.startswith("thermal_zone")
        )
    except OSError:
        return None
    for zone in zones:
        zone_type = ""
        try:
            with open(os.path.join(thermal_root, zone, "type"), "r", encoding="utf-8") as handle:
                zone_type = handle.read().strip().lower()
        except OSError:
            pass
        score = 0 if any(tag in zone_type for tag in ("cpu", "soc", "x86_pkg", "package")) else 1
        candidates.append((score, zone))
    for _score, zone in sorted(candidates):
        try:
            with open(os.path.join(thermal_root, zone, "temp"), "r", encoding="utf-8") as handle:
                raw = int(handle.read().strip())
        except (OSError, ValueError):
            continue
        return round(raw / 1000.0, 2)
    return None


def read_wireless(path: str = _PROC_WIRELESS) -> Optional[Dict[str, Any]]:
    """Parse /proc/net/wireless for the first associated interface, or None.

    Needs nothing installed — ``iwconfig`` is deprecated and absent from Debian
    Bookworm Lite, and ``iw`` is not a default package either. Two traps are
    handled here: the quality and level columns carry a trailing period
    (``-64.``), which a naive ``int()`` raises on, and a ``noise`` column of
    -256 is the driver saying "not measured" rather than a noise floor, so it is
    returned as None.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return None
    for line in lines:
        if ":" not in line:
            continue
        name, _, rest = line.partition(":")
        interface = name.strip()
        fields = rest.split()
        if not interface or len(fields) < 4:
            continue

        def _number(token: str) -> Optional[float]:
            try:
                return float(token.rstrip("."))
            except ValueError:
                return None

        link = _number(fields[1])
        level = _number(fields[2])
        noise = _number(fields[3])
        if level is None:
            continue
        return {
            "interface": interface,
            "link_quality": link,
            "rssi_dbm": int(level),
            "noise_dbm": None if noise is None or int(noise) == _NOISE_UNMEASURED else int(noise),
        }
    return None


def collect_host_vitals(sampler: Optional[CpuSampler] = None) -> Dict[str, Any]:
    """One snapshot of the host-side fields an edge craft or node actually needs.

    Any field the machine cannot supply is present and None, so a consumer can
    render "not measured" rather than guessing from a missing key.
    """
    wireless = read_wireless()
    return {
        "timestamp": time.time(),
        "cpu_pct": sampler.sample() if sampler is not None else None,
        "temp_c": read_cpu_temperature_c(),
        "rssi_dbm": wireless["rssi_dbm"] if wireless else None,
        "wireless": wireless,
    }
