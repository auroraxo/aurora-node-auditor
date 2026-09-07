"""Example CI / Pipeline script demonstrating automated edge node auditing."""

import sys
from auditor.client import AuditorClient
from auditor.audit import run_node_audit


def audit_local():
    print("Running local host audit...")
    report = run_node_audit()
    print(f"Audit Status: {report['status']}")
    if report["status"] == "critical":
        print("CRITICAL: Local node health check failed!")
        sys.exit(1)


def audit_remote(endpoint_url="https://codebyaurora.com"):
    print(f"Auditing remote endpoint: {endpoint_url}")
    client = AuditorClient(endpoint_url)
    audit = client.get_audit()
    print(f"Remote Node Status: {audit.get('status')}")
    print(f"Node Info: {audit.get('node', {}).get('hostname')} ({audit.get('node', {}).get('os')})")


if __name__ == "__main__":
    audit_local()
    # Uncomment to check live remote auditor
    # audit_remote()
