"""System and Kolonie node metrics collector."""

import os
import platform
import shutil
import threading
import time
from typing import Any, Dict


def get_process_stats() -> Dict[str, Any]:
    """Get process-level metrics for the auditor."""
    pid = os.getpid()
    threads_count = threading.active_count()
    rss_bytes = 0
    try:
        if os.path.exists(f"/proc/{pid}/status"):
            with open(f"/proc/{pid}/status", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        parts = line.split()
                        if len(parts) >= 2:
                            rss_bytes = int(parts[1]) * 1024
                        break
    except Exception:
        pass
    return {
        "pid": pid,
        "threads": threads_count,
        "rss_bytes": rss_bytes,
    }


def get_uptime_seconds() -> float:
    """Return system uptime in seconds from /proc/uptime if available, else clock monotonic."""
    try:
        if os.path.exists("/proc/uptime"):
            with open("/proc/uptime", "r", encoding="utf-8") as f:
                return float(f.readline().split()[0])
    except Exception:
        pass
    return time.monotonic()


def get_memory_stats() -> Dict[str, Any]:
    """Parse /proc/meminfo or provide estimates."""
    stats: Dict[str, Any] = {"total_bytes": 0, "available_bytes": 0, "used_percent": 0.0}
    try:
        if os.path.exists("/proc/meminfo"):
            mem_data = {}
            with open("/proc/meminfo", "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val_parts = parts[1].strip().split()
                        if val_parts:
                            val_kb = int(val_parts[0])
                            mem_data[key] = val_kb * 1024
            total = mem_data.get("MemTotal", 0)
            avail = mem_data.get("MemAvailable", mem_data.get("MemFree", 0))
            stats["total_bytes"] = total
            stats["available_bytes"] = avail
            if total > 0:
                stats["used_percent"] = round(100.0 * (1.0 - (avail / total)), 2)
    except Exception:
        pass
    return stats


def get_disk_stats(path: str = "/") -> Dict[str, Any]:
    """Get disk usage metrics for path."""
    try:
        usage = shutil.disk_usage(path)
        total = usage.total
        free = usage.free
        used = usage.used
        pct = round((used / total) * 100.0, 2) if total > 0 else 0.0
        return {
            "path": path,
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "used_percent": pct,
        }
    except Exception as exc:
        return {"path": path, "error": str(exc)}


def collect_node_telemetry() -> Dict[str, Any]:
    """Collect full snapshot of node telemetry."""
    try:
        from auditor import __version__
        pkg_version = __version__
    except Exception:
        pkg_version = "0.1.2"

    uptime = get_uptime_seconds()
    mem = get_memory_stats()
    disk = get_disk_stats("/")
    proc = get_process_stats()
    
    return {
        "timestamp": time.time(),
        "node": {
            "hostname": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
            "arch": platform.machine(),
            "python_version": platform.python_version(),
            "uptime_seconds": round(uptime, 2),
        },
        "resources": {
            "memory": mem,
            "disk": disk,
            "cpu_count": os.cpu_count() or 1,
            "load_avg": list(os.getloadavg()) if hasattr(os, "getloadavg") else [],
        },
        "process": proc,
        "service": {
            "name": "aurora-node-auditor",
            "version": pkg_version,
            "status": "healthy",
        }
    }
