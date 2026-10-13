#!/usr/bin/env bash
# deploy.sh — Deploy the State AI EO Explorer stack to Kubernetes.
#
# Usage:
#   ./deploy.sh                  # deploy everything
#   ./deploy.sh --skip-models    # skip the model-pull job (models already cached)
#   ./deploy.sh --namespace foo  # override namespace (default: ai-eo-explorer)
#
# Requirements: kubectl configured and pointing at the target cluster.

set -euo pipefail

# ── Defaults ────────────────────────────────────────────────────────────────
NS="ai-eo-explorer"
SKIP_MODELS=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="${SCRIPT_DIR}/k8s"

# ── Arg parsing ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-models)  SKIP_MODELS=true ;;
    --namespace)    NS="$2"; shift ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
  shift
done

# ── Helpers ──────────────────────────────────────────────────────────────────
log()  { echo "[$(date '+%H:%M:%S')] $*"; }
ok()   { echo "[$(date '+%H:%M:%S')] ✓ $*"; }
fail() { echo "[$(date '+%H:%M:%S')] ✗ $*" >&2; exit 1; }

wait_for_pod_ready() {
  local label="$1"
  local timeout="${2:-300}"
  log "Waiting for pod ($label) to be Ready (timeout ${timeout}s)..."
  if ! kubectl wait pod \
      --namespace "$NS" \
      --selector "$label" \
      --for=condition=Ready \
      --timeout="${timeout}s"; then
    fail "Pod ($label) did not become Ready within ${timeout}s."
  fi
  ok "Pod ($label) is Ready."
}

wait_for_deployment_ready() {
  local name="$1"
  local timeout="${2:-180}"
  log "Waiting for deployment/$name to roll out (timeout ${timeout}s)..."
  if ! kubectl rollout status deployment/"$name" \
      --namespace "$NS" \
      --timeout="${timeout}s"; then
    fail "Deployment/$name did not roll out within ${timeout}s."
  fi
  ok "Deployment/$name is Ready."
}

wait_for_job_complete() {
  local name="$1"
  local timeout="${2:-1800}"   # model pull can take 20–30 min on a slow link
  log "Waiting for job/$name to complete (timeout ${timeout}s)..."
  if ! kubectl wait job/"$name" \
      --namespace "$NS" \
      --for=condition=Complete \
      --timeout="${timeout}s"; then
    log "Job did not complete — showing last 40 lines of pod logs:"
    kubectl logs --namespace "$NS" \
      "$(kubectl get pods --namespace "$NS" \
           --selector=job-name="$name" \
           -o jsonpath='{.items[-1:].metadata.name}')" \
      --tail=40 || true
    fail "Job/$name did not complete within ${timeout}s."
  fi
  ok "Job/$name completed."
}

apply() {
  local file="$1"
  log "Applying $file ..."
  kubectl apply -f "$file"
}

# ── Preflight ────────────────────────────────────────────────────────────────
log "Checking kubectl connectivity..."
kubectl cluster-info --request-timeout=10s > /dev/null \
  || fail "kubectl cannot reach the cluster. Check your kubeconfig."
ok "Cluster reachable."

# ── 1. Namespace ─────────────────────────────────────────────────────────────
log "=== Step 1/9: Namespace ==="
apply "${K8S_DIR}/namespace.yaml"
kubectl wait namespace/"$NS" --for=jsonpath='{.status.phase}'=Active --timeout=30s
ok "Namespace $NS is Active."

# ── 2. Config & Secrets ──────────────────────────────────────────────────────
log "=== Step 2/9: ConfigMap and Secret ==="
apply "${K8S_DIR}/configmap.yaml"
apply "${K8S_DIR}/secret-stub.yaml"

# ── 3. Qdrant ────────────────────────────────────────────────────────────────
log "=== Step 3/9: Qdrant (PVC + StatefulSet + Service) ==="
apply "${K8S_DIR}/qdrant/pvc.yaml"
apply "${K8S_DIR}/qdrant/statefulset.yaml"
apply "${K8S_DIR}/qdrant/service.yaml"

# Qdrant is lightweight — 2 min is generous
wait_for_pod_ready "app=qdrant" 120

# Quick functional check: Qdrant /readyz
log "Verifying Qdrant /readyz via port-forward..."
kubectl port-forward --namespace "$NS" svc/qdrant 6333:6333 &
PF_PID=$!
sleep 3
QDRANT_OK=false
for i in $(seq 1 10); do
  if curl -sf http://localhost:6333/readyz > /dev/null 2>&1; then
    QDRANT_OK=true; break
  fi
  sleep 2
done
kill "$PF_PID" 2>/dev/null || true
$QDRANT_OK && ok "Qdrant /readyz responded." || log "Warning: Qdrant /readyz check skipped (port-forward may not be available in this environment)."

# ── 4. Ollama ────────────────────────────────────────────────────────────────
log "=== Step 4/9: Ollama (PVC + StatefulSet + Service) ==="
apply "${K8S_DIR}/ollama/pvc.yaml"
apply "${K8S_DIR}/ollama/statefulset.yaml"
apply "${K8S_DIR}/ollama/service.yaml"

# Ollama needs time to start the server process (no model download yet — that's the job)
wait_for_pod_ready "app=ollama" 300

# ── 5. Pull models ────────────────────────────────────────────────────────────
if [ "$SKIP_MODELS" = true ]; then
  log "=== Step 5/9: Skipping model-pull job (--skip-models) ==="
else
  log "=== Step 5/9: Model-pull Job (nomic-embed-text + llama3.1:8b) ==="
  log "NOTE: llama3.1:8b is ~4.7 GB. This step can take 20–30 min on a slow link."

  # Delete stale job if it exists (Jobs are immutable once created)
  if kubectl get job/ollama-pull-models --namespace "$NS" > /dev/null 2>&1; then
    log "Found existing ollama-pull-models job — deleting before re-apply..."
    kubectl delete job/ollama-pull-models --namespace "$NS"
    # Wait for pods to terminate
    sleep 5
  fi

  apply "${K8S_DIR}/jobs/pull-models.yaml"
  wait_for_job_complete "ollama-pull-models" 2400  # 40-min ceiling

  log "Model pull logs:"
  kubectl logs --namespace "$NS" \
    "$(kubectl get pods --namespace "$NS" \
         --selector=job-name=ollama-pull-models \
         -o jsonpath='{.items[-1:].metadata.name}')" \
    --tail=20 || true
fi

# ── 6. Backend ────────────────────────────────────────────────────────────────
log "=== Step 6/9: Backend (Deployment + Service) ==="
apply "${K8S_DIR}/backend/deployment.yaml"
apply "${K8S_DIR}/backend/service.yaml"

# Backend has an init container that waits for Qdrant + Ollama, so give it extra time
wait_for_deployment_ready "backend" 300

# ── 7. Frontend ───────────────────────────────────────────────────────────────
log "=== Step 7/9: Frontend (Deployment + Service) ==="
apply "${K8S_DIR}/frontend/deployment.yaml"
apply "${K8S_DIR}/frontend/service.yaml"
wait_for_deployment_ready "frontend" 120

# ── 8. Ingress ────────────────────────────────────────────────────────────────
log "=== Step 8/9: Ingress ==="
apply "${K8S_DIR}/ingress.yaml"
ok "Ingress applied. Edit k8s/ingress.yaml to set your actual hostname and Ingress class."

# ── 9. Summary ────────────────────────────────────────────────────────────────
log "=== Step 9/9: Deployment summary ==="
echo ""
kubectl get all --namespace "$NS"
echo ""
log "Next steps:"
log "  1. Run the ingestion job to load EO data into Qdrant:"
log "       kubectl exec -n $NS deploy/backend -- python ingestion/ingest.py --data-path /data/State_AI_Executive_Orders_Dynatrace_Report.xlsx"
log "  2. Check ingress address:  kubectl get ingress -n $NS"
log "  3. Health check:           kubectl port-forward -n $NS svc/backend 8000:8000 &"
log "                             curl http://localhost:8000/api/health"
log ""
ok "All resources deployed successfully."
