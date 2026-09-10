"""Automated node audit module for system health, resources, and security checks."""

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

from auditor.collector import collect_node_telemetry


def audit_resources(telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Audit system resource utilization against healthy operational thresholds."""
    if telemetry is None:
        telemetry = collect_node_telemetry()

    resources = telemetry.get("resources", {})
    memory = resources.get("memory", {})
    disk = resources.get("disk", {})
    load_avg = resources.get("load_avg", [])
    cpu_count = resources.get("cpu_count", 1) or 1

    checks: List[Dict[str, Any]] = []
    status = "healthy"

    mem_used_pct = memory.get("used_percent", 0.0)
    if mem_used_pct >= 95.0:
        mem_status = "critical"
        status = "critical"
    elif mem_used_pct >= 85.0:
        mem_status = "warning"
        if status != "critical":
            status = "warning"
    else:
        mem_status = "ok"

    checks.append({
        "name": "memory_usage",
        "status": mem_status,
        "value": mem_used_pct,
        "unit": "percent",
        "thresholds": {"warning": 85.0, "critical": 95.0},
    })

    disk_used_pct = disk.get("used_percent", 0.0)
    if disk_used_pct >= 90.0:
        disk_status = "critical"
        status = "critical"
    elif disk_used_pct >= 80.0:
        disk_status = "warning"
        if status != "critical":
            status = "warning"
    else:
        disk_status = "ok"

    checks.append({
        "name": "disk_usage",
        "status": disk_status,
        "value": disk_used_pct,
        "unit": "percent",
        "thresholds": {"warning": 80.0, "critical": 90.0},
    })

    load1 = load_avg[0] if load_avg else 0.0
    load_ratio = load1 / float(cpu_count) if cpu_count > 0 else 0.0
    if load_ratio >= 2.0:
        load_status = "critical"
        status = "critical"
    elif load_ratio >= 1.0:
        load_status = "warning"
        if status != "critical":
            status = "warning"
    else:
        load_status = "ok"

    checks.append({
        "name": "cpu_load",
        "status": load_status,
        "value": load1,
        "load_ratio": round(load_ratio, 2),
        "cpu_count": cpu_count,
        "thresholds": {"warning": round(float(cpu_count), 2), "critical": round(float(cpu_count) * 2.0, 2)},
    })

    return {
        "status": status,
        "checks": checks,
    }


def audit_system_security() -> Dict[str, Any]:
    """Perform baseline node security and environment posture checks."""
    checks: List[Dict[str, Any]] = []
    status = "healthy"

    is_root = (os.geteuid() == 0) if hasattr(os, "geteuid") else False
    checks.append({
        "name": "running_as_root",
        "status": "warning" if is_root else "ok",
        "passed": not is_root,
        "details": "Process runs as root user" if is_root else "Process runs as non-root user",
    })
    if is_root and status != "critical":
        status = "warning"

    world_writable_tmp = False
    tmp_path = "/tmp"
    if os.path.exists(tmp_path):
        tmp_stat = os.stat(tmp_path)
        world_writable_tmp = bool(tmp_stat.st_mode & 0o002)
        has_sticky = bool(tmp_stat.st_mode & 0o1000)
        tmp_ok = world_writable_tmp and has_sticky
        checks.append({
            "name": "tmp_permissions",
            "status": "ok" if tmp_ok else "warning",
            "passed": tmp_ok,
            "details": "/tmp has sticky bit set and is appropriately writable" if tmp_ok else "/tmp permissions may be irregular",
        })
        if not tmp_ok and status != "critical":
            status = "warning"

    return {
        "status": status,
        "checks": checks,
    }


def run_node_audit(telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute complete automated node audit."""
    try:
        from auditor import __version__
        pkg_version = __version__
    except Exception:
        pkg_version = "0.1.5"

    if telemetry is None:
        telemetry = collect_node_telemetry()

    resource_audit = audit_resources(telemetry)
    security_audit = audit_system_security()

    sub_statuses = [resource_audit["status"], security_audit["status"]]
    if "critical" in sub_statuses:
        overall_status = "critical"
    elif "warning" in sub_statuses:
        overall_status = "warning"
    else:
        overall_status = "healthy"

    return {
        "timestamp": time.time(),
        "status": overall_status,
        "node": telemetry.get("node", {}),
        "service": {
            "name": "aurora-node-auditor",
            "version": pkg_version,
        },
        "resources": resource_audit,
        "security": security_audit,
    }


def main() -> None:
    """CLI entry point for running a node audit from command line."""
    try:
        from auditor import __version__
        pkg_version = __version__
    except Exception:
        pkg_version = "0.1.5"

    parser = argparse.ArgumentParser(
        prog="node-audit",
        description="Autonomous Node Auditor - Host Health & Security Inspection CLI",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {pkg_version}",
    )
    parser.add_argument("--json", action="store_true", help="Output audit report as JSON")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero code if status is warning or critical",
    )
    args = parser.parse_args()

    audit_result = run_node_audit()
    status = audit_result.get("status", "healthy")

    if args.json:
        print(json.dumps(audit_result, indent=2))
    else:
        node = audit_result.get("node", {})
        hostname = node.get("hostname", "unknown")
        os_name = node.get("os", "unknown")
        print(f"=== Aurora Node Audit: {hostname} ({os_name}) ===")
        print(f"Overall Status: {status.upper()}")
        print("\n--- Resource Checks ---")
        for c in audit_result.get("resources", {}).get("checks", []):
            name = c.get("name")
            st = c.get("status", "ok")
            val = c.get("value")
            unit = c.get("unit", "")
            print(f"  [{st.upper():8s}] {name}: {val} {unit}")

        print("\n--- Security Checks ---")
        for c in audit_result.get("security", {}).get("checks", []):
            name = c.get("name")
            st = c.get("status", "ok")
            details = c.get("details", "")
            print(f"  [{st.upper():8s}] {name}: {details}")

    if args.strict and status != "healthy":
        sys.exit(1 if status == "warning" else 2)
    sys.exit(0)


if __name__ == "__main__":
    main()
