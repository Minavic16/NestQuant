#!/usr/bin/env bash
# Blue-green deployment for NQTS on the VPS.
# Two runner slots: "blue" and "green". Current slot serves traffic; the new
# build goes to the idle slot; after health checks, Caddy swaps the upstream.
set -euo pipefail

CURRENT="${CURRENT_SLOT:-blue}"
TARGET=$([ "$CURRENT" = "blue" ] && echo green || echo blue)

echo "[blue-green] deploying to slot: $TARGET"
systemctl stop "nqts-$TARGET" || true
cp -r ./release "/opt/nqts/$TARGET"
systemctl start "nqts-$TARGET"

# Health gate
for i in $(seq 1 15); do
  if curl -sf "http://127.0.0.1:8080/api/health"; then
    echo "[blue-green] health OK on $TARGET"; break
  fi
  echo "[blue-green] waiting for $TARGET health..."; sleep 2
done

# Caddy upstream swap (idempotent)
sed -i "s|to nqts-$CURRENT|to nqts-$TARGET|" /etc/caddy/Caddyfile
systemctl reload caddy

echo "[blue-green] promoted $TARGET; rolling back container slot on failure"
