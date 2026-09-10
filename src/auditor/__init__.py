"""Aurora Node Auditor package."""

__version__ = "0.1.5"

from auditor.audit import audit_resources, audit_system_security, run_node_audit
from auditor.client import AuditorClient, AuditorError
from auditor.host import (
    CpuSampler,
    collect_host_vitals,
    read_cpu_frequency,
    read_cpu_temperature_c,
    read_rpi_undervoltage_alarm,
    read_throttle_flags,
    read_wireless,
)

__all__ = [
    "AuditorClient",
    "AuditorError",
    "CpuSampler",
    "__version__",
    "audit_resources",
    "audit_system_security",
    "collect_host_vitals",
    "read_cpu_frequency",
    "read_cpu_temperature_c",
    "read_rpi_undervoltage_alarm",
    "read_throttle_flags",
    "read_wireless",
    "run_node_audit",
]
