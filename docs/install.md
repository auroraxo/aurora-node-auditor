# Aurora Node Auditor — install in 5 minutes

This bundle ships a Grafana dashboard and a Kubernetes manifest set so ops
teams can run the auditor on a cluster without writing YAML from scratch.

## What ships

```
deploy/k8s/
├── 00-namespace.yaml          # Namespace: aurora-auditor
├── 10-serviceaccount.yaml     # ServiceAccount with automountToken=false
├── 20-deployment.yaml         # Deployment (readOnlyRootFilesystem, non-root)
├── 30-service.yaml            # ClusterIP service on :8787
├── 40-poddisruptionbudget.yaml # minAvailable: 1
├── 50-servicemonitor.yaml     # Prometheus Operator scrape every 30s
├── 60-networkpolicy.yaml      # Default-deny + allow prometheus only
└── kustomization.yaml         # ties them all together

dashboards/auditor-node-vitals.json
                               # Grafana 10+ dashboard, 12 panels, $instance var
```

The image is published as
`ghcr.io/auroraxo/aurora-node-auditor:0.1.8` (built by `.github/workflows/image.yml`).

## Install the manifests

```bash
# 1. apply everything via kustomize
kubectl apply -k deploy/k8s

# 2. wait for the pod, then sanity-check the endpoints
kubectl -n aurora-auditor rollout status deploy/aurora-auditor
kubectl -n aurora-auditor port-forward svc/aurora-auditor 8787:8787 &
curl -s http://127.0.0.1:8787/health  | jq .   # {"status":"healthy",...}
curl -s http://127.0.0.1:8787/ready   | jq .   # {"ready":true}
curl -s http://127.0.0.1:8787/metrics | head  # Prometheus text format
```

## Install the Grafana dashboard

The dashboard JSON uses Grafana's `__inputs` mechanism, so the standard
import flow works:

1. Grafana → Dashboards → Import → upload `dashboards/auditor-node-vitals.json`.
2. Pick the Prometheus datasource that scrapes the auditor (the `DS_PROMETHEUS`
   input) and confirm.
3. Drop the `instance` template variable onto a dashboard filter — leave it
   set to `All` for multi-node clusters or pin a single node for triage.

## What each k8s piece enforces

- **Deployment** — `runAsNonRoot: true`, `runAsUser: 65534`,
  `seccompProfile: RuntimeDefault`, `readOnlyRootFilesystem: true`,
  `allowPrivilegeEscalation: false`, all `capabilities` dropped.
- **ServiceAccount** — `automountServiceAccountToken: false` (the auditor
  does not call the Kubernetes API).
- **PodDisruptionBudget** — `minAvailable: 1`; voluntary evictions never
  drive the auditor to zero replicas.
- **ServiceMonitor** — scrapes `/metrics` every 30 s with a 10 s timeout.
  The `release: prometheus` label assumes a stock Prometheus Operator
  `kube-prometheus-stack` install; relabel if your stack uses a different
  selector.
- **NetworkPolicy** — default-deny + allow only intra-cluster traffic on
  port 8787. The auditor is read-only; there is no need for egress or
  external ingress.

## What the dashboard expects

The dashboard queries the following series, all of which the auditor
exposes on `/metrics`:

| Series                       | Source                                |
|------------------------------|---------------------------------------|
| `node_uptime_seconds`        | `get_uptime_seconds()` from `/proc`   |
| `node_cpu_count`             | `os.cpu_count()`                      |
| `node_cpu_used_percent`      | `CpuSampler` delta between scrapes    |
| `node_memory_total_bytes`    | `/proc/meminfo` total                 |
| `node_memory_available_bytes`| `/proc/meminfo` available             |
| `node_disk_used_percent`     | `shutil.disk_usage("/")`              |
| `node_load1/5/15`            | `os.getloadavg()` (empty on some OS)  |
| `process_rss_bytes`          | `VmRSS` from `/proc/<pid>/status`     |
| `process_threads`            | `threading.active_count()`            |

## Out of scope (deliberately)

- OpenTelemetry bridge.
- Multi-host fleet UI on top of Grafana.
- TLS / auth — keep this internal to the cluster and rely on NetworkPolicy.
- DaemonSet variant (use the Deployment as-is for control plane / VM hosts).
