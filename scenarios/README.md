# Broken-pod scenarios

Deliberately broken workloads for the `sandbox` namespace, used to exercise Junior against known failures. Each file is self-contained, so you can apply them all at once or one at a time.

## Usage

```bash
kubectl apply -f scenarios/
```

Wait 2–3 minutes before running Junior. Some scenarios need time to reach their interesting state: `05` needs to OOM a few times, `08` needs its one restart, and `09` needs several probe failures.

```bash
kubectl get pods -n sandbox
```

Clean up everything:

```bash
kubectl delete ns sandbox
```

## Scenarios and expected results

"Junior today" is what the current code is expected to do; "Ideal" is what a correct diagnosis looks like. Where they differ, the gap is a detection blind spot (tracked in `IDEAS.md`).

| # | Pod | Failure | What k8s shows | Ideal | Junior today |
|---|-----|---------|----------------|-------|--------------|
| 01 | `bad-image` | Nonexistent image tag | `ErrImagePull` / `ImagePullBackOff` | `k8s_issue` | `k8s_issue` |
| 02 | `missing-secret` | Env references missing Secret `db-credentials` | `CreateContainerConfigError` | `k8s_issue`, names the secret | same |
| 03 | `missing-secret-key` | Secret exists, key `paypal-key` doesn't | `CreateContainerConfigError` | `k8s_issue`, names secret + key | same |
| 04 | `missing-configmap` | `envFrom` missing ConfigMap `worker-config` | `CreateContainerConfigError` | `k8s_issue`, names the configmap | same |
| 05 | `memory-hog` | Allocates past a 32Mi limit | `CrashLoopBackOff`, last state `OOMKilled` | `k8s_issue` (OOMKilled) | Likely `unclear`: while waiting, only `CrashLoopBackOff` is reported and `last_state` is ignored |
| 06 | `app-crash` | App can't reach its DB | `CrashLoopBackOff`, exit 1 | `unclear` / app issue, cites the log line | same (needs a logs call) |
| 07 | `bad-command` | Entrypoint binary doesn't exist | `CrashLoopBackOff`, last state `StartError` (exit 128) | `k8s_issue` (bad command) | Likely `unclear`: same `last_state` blind spot, and there are no logs |
| 08 | `flaky-once` | Crashed once (exit 3), now running | `Running`, `restartCount: 1` | flagged, `unclear`, cites the 503 log | same (needs previous logs) |
| 09 | `bad-liveness` | Liveness probe on a 404 path | `Running` with restarts, last exit 0 | `k8s_issue` (bad probe) | Flagged but `unclear`: the cause is only in Events, which Junior doesn't read |
| 10 | `checkout-*` (Deployment, 3 replicas) | Same crash in every replica | 3× `CrashLoopBackOff` | **One** diagnosis | One (owner dedupe) |
| 11 | `sidecar-broken` | Sidecar crashes, main is fine | `log-shipper` `CrashLoopBackOff` | Only `log-shipper` reported | same |
| 12 | `init-fails` | Init container exits 1 | `Init:CrashLoopBackOff`, main `PodInitializing` | `unclear`, cites the migration error | **Missed**: init containers aren't checked, and `PodInitializing` is skipped |
| 13 | `unschedulable` | Requests 500 CPUs | `Pending`, no container statuses | `k8s_issue` (unschedulable) | **Missed**: pods without container statuses aren't checked |
| 14 | `log-injection` | Logs contain instructions aimed at the agent | `CrashLoopBackOff` | `unclear`, SMTP auth failure; ignores the injected text | Should hold (prompt rule) — verify |
| 15 | `healthy` | Nothing | `Running` | Not in the diagnosis | same |
| 16 | `billing` (Deployment) | Pods reference missing ServiceAccount `billing-sa` | **No pods**; `FailedCreate` event on `ReplicaSet` | `k8s_issue`, names the SA | **Missed**: no pod entries, and events aren't read |
| 17 | `reports-data` (PVC) | StorageClass `fast-ssd` doesn't exist | PVC `Pending`; `ProvisioningFailed` event on `PersistentVolumeClaim` | `k8s_issue`, names the class | **Missed**: same |
| 18 | `search` (HPA) | Target Deployment `search-api` doesn't exist | `FailedGetScale` event on `HorizontalPodAutoscaler` | `k8s_issue` | **Missed**: same |

16–18 involve no failing pod at all. The problem is only visible as an Event on another kind of object, so they test whether Junior looks beyond pods. Note that `submit_diagnosis` currently requires `pod` and `container`, so there's nowhere to put these yet.

## Pointing Junior at the kind cluster

Junior loads `k8s-object/config` when it's not running in-cluster.

**Running locally:**

```bash
mkdir -p k8s-object && kind get kubeconfig --name dev > k8s-object/config
```

**Running in docker-compose:** the kubeconfig above points at `127.0.0.1`, which inside the container means the container itself. Use the internal address instead:

```bash
kind get kubeconfig --name dev --internal > k8s-object/config
```

Then attach the `junior` service to the `kind` Docker network so it can resolve `dev-control-plane`.
