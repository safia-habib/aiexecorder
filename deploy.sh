#!/usr/bin/env bash
# deploy.sh — Deploy the State AI EO Explorer stack to Kubernetes.
#
# Usage:
#   ./deploy.sh                  # deploy everything
#   ./deploy.sh --namespace foo  # override namespace (default: ai-eo-explorer)
#
# Requirements: kubectl configured and pointing at the target cluster.
# Before running: set AZURE_OPENAI_API_KEY in k8s/secret-stub.yaml.

set -euo pipefail

# ── Defaults ────────────────────────────────────────────────────────────────
NS="ai-eo-explorer"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="${SCRIPT_DIR}/k8s"

# ── Arg parsing ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
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
  local timeout="${2:-300}"
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
log "=== Step 1/8: Namespace ==="
apply "${K8S_DIR}/namespace.yaml"
kubectl wait namespace/"$NS" --for=jsonpath='{.status.phase}'=Active --timeout=30s
ok "Namespace $NS is Active."

# ── 2. Config & Secrets ──────────────────────────────────────────────────────
log "=== Step 2/8: ConfigMap and Secret ==="
apply "${K8S_DIR}/configmap.yaml"
apply "${K8S_DIR}/secret-stub.yaml"

# ── 3. Qdrant ────────────────────────────────────────────────────────────────
log "=== Step 3/8: Qdrant (PVC + StatefulSet + Service) ==="
apply "${K8S_DIR}/qdrant/pvc.yaml"
apply "${K8S_DIR}/qdrant/statefulset.yaml"
apply "${K8S_DIR}/qdrant/service.yaml"

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

# ── 4. Backend ────────────────────────────────────────────────────────────────
log "=== Step 4/8: Backend (Deployment + Service) ==="
apply "${K8S_DIR}/backend/deployment.yaml"
apply "${K8S_DIR}/backend/service.yaml"
wait_for_deployment_ready "backend" 180

# ── 5. Ingestion ─────────────────────────────────────────────────────────────
log "=== Step 5/8: Data ingestion job ==="
if kubectl get job/run-ingestion --namespace "$NS" > /dev/null 2>&1; then
  log "Found existing run-ingestion job — deleting before re-apply..."
  kubectl delete job/run-ingestion --namespace "$NS"
  sleep 3
fi
apply "${K8S_DIR}/jobs/ingest.yaml"
log "Waiting for ingestion job to complete (calls Azure OpenAI to embed all EO records)..."
wait_for_job_complete "run-ingestion" 300
log "Ingestion logs:"
kubectl logs --namespace "$NS" \
  "$(kubectl get pods --namespace "$NS" \
       --selector=job-name=run-ingestion \
       -o jsonpath='{.items[-1:].metadata.name}')" \
  --tail=20 || true

# ── 6. Frontend ───────────────────────────────────────────────────────────────
log "=== Step 6/8: Frontend (Deployment + Service) ==="
apply "${K8S_DIR}/frontend/deployment.yaml"
apply "${K8S_DIR}/frontend/service.yaml"
wait_for_deployment_ready "frontend" 120

# Wait for the cloud load balancer to assign a public IP / hostname.
log "Waiting for frontend LoadBalancer external IP (may take 1–3 min)..."
EXTERNAL_IP=""
for i in $(seq 1 36); do   # 36 × 5 s = 3 min ceiling
  EXTERNAL_IP=$(kubectl get svc frontend \
      --namespace "$NS" \
      -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
  # Some clouds (EKS) assign a hostname rather than an IP
  if [ -z "$EXTERNAL_IP" ]; then
    EXTERNAL_IP=$(kubectl get svc frontend \
        --namespace "$NS" \
        -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
  fi
  if [ -n "$EXTERNAL_IP" ]; then
    ok "Frontend is publicly reachable at: http://${EXTERNAL_IP}"
    break
  fi
  log "  Still waiting for external IP... (${i}/36)"
  sleep 5
done

if [ -z "$EXTERNAL_IP" ]; then
  log "WARNING: LoadBalancer external IP not yet assigned after 3 min."
  log "  Run this to check later:  kubectl get svc frontend -n $NS"
fi

# ── 7. Ingress ────────────────────────────────────────────────────────────────
log "=== Step 7/8: Ingress ==="
apply "${K8S_DIR}/ingress.yaml"
ok "Ingress applied. Edit k8s/ingress.yaml to set your actual hostname and Ingress class."

# ── 8. Summary ────────────────────────────────────────────────────────────────
log "=== Step 8/8: Deployment summary ==="
echo ""
kubectl get all --namespace "$NS"
echo ""
log "Next steps:"
log "  1. To re-run ingestion (e.g. after a data update):"
log "       kubectl delete job run-ingestion -n $NS"
log "       kubectl apply -f k8s/jobs/ingest.yaml"
if [ -n "$EXTERNAL_IP" ]; then
  log "  2. Open the app:           http://${EXTERNAL_IP}"
  log "  3. Health check:           curl http://${EXTERNAL_IP}/api/health"
else
  log "  2. Get the public IP:      kubectl get svc frontend -n $NS"
  log "  3. Health check:           curl http://<EXTERNAL-IP>/api/health"
fi
log ""
ok "All resources deployed successfully."
