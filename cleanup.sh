#!/usr/bin/env bash
# cleanup.sh — delete all resources in the ai-eo-explorer namespace, then drop it.
# Usage: ./cleanup.sh [--force]
#   --force  skip the confirmation prompt

set -euo pipefail

NAMESPACE="ai-eo-explorer"

# ── confirmation ──────────────────────────────────────────────────────────────
if [[ "${1:-}" != "--force" ]]; then
  echo "⚠️  This will permanently delete the '$NAMESPACE' namespace and everything in it."
  read -r -p "Type the namespace name to confirm: " CONFIRM
  if [[ "$CONFIRM" != "$NAMESPACE" ]]; then
    echo "Aborted."
    exit 1
  fi
fi

echo ""
echo "=== Cleaning up namespace: $NAMESPACE ==="
echo ""

# ── 1. Jobs ───────────────────────────────────────────────────────────────────
echo "[1/6] Deleting Jobs..."
kubectl delete jobs --all -n "$NAMESPACE" --ignore-not-found --grace-period=0 2>/dev/null || true
echo "      Done."

# ── 2. Deployments ────────────────────────────────────────────────────────────
echo "[2/6] Deleting Deployments..."
kubectl delete deployments --all -n "$NAMESPACE" --ignore-not-found 2>/dev/null || true
echo "      Done."

# ── 3. StatefulSets (Qdrant) ──────────────────────────────────────────────────
echo "[3/6] Deleting StatefulSets..."
kubectl delete statefulsets --all -n "$NAMESPACE" --ignore-not-found 2>/dev/null || true
echo "      Done."

# ── 4. Force-delete any stuck Pods ────────────────────────────────────────────
echo "[4/6] Force-deleting remaining Pods..."
kubectl delete pods --all -n "$NAMESPACE" --ignore-not-found --grace-period=0 --force 2>/dev/null || true
echo "      Done."

# ── 5. PersistentVolumeClaims (Qdrant data) ───────────────────────────────────
echo "[5/6] Deleting PersistentVolumeClaims..."
kubectl delete pvc --all -n "$NAMESPACE" --ignore-not-found 2>/dev/null || true
echo "      Done."

# ── 6. Drop the namespace (takes out everything else: Services, ConfigMaps,
#       Secrets, Ingress, ServiceAccounts, etc.) ────────────────────────────────
echo "[6/6] Deleting namespace '$NAMESPACE'..."
kubectl delete namespace "$NAMESPACE" --ignore-not-found

# Wait for it to disappear
echo "      Waiting for namespace to be fully removed..."
TIMEOUT=120
ELAPSED=0
while kubectl get namespace "$NAMESPACE" &>/dev/null; do
  if (( ELAPSED >= TIMEOUT )); then
    echo "      ⚠️  Namespace is taking longer than ${TIMEOUT}s to terminate."
    echo "      It may still be cleaning up — check with: kubectl get namespace $NAMESPACE"
    exit 0
  fi
  sleep 5
  ELAPSED=$(( ELAPSED + 5 ))
  echo "      Still terminating... (${ELAPSED}s elapsed)"
done

echo ""
echo "✅  Namespace '$NAMESPACE' has been fully removed."
echo "    Run './deploy.sh' to redeploy from scratch."
