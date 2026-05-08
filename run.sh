#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "=========================================="
echo " Nomeda-MSTE v3 Backend"
echo " Root: $ROOT_DIR"
echo "=========================================="

[ -f .env ] && echo "[OK] .env found" || { echo "[WARN] .env not found"; cp .env.example .env; }

if [ -f models/ser/wavlm_hubert_optimized_seed42.pth ]; then
    echo "[OK] SER model found"
elif [ -f models/ser/wavlm_hubert_optimized_seed456.pth ]; then
    cp models/ser/wavlm_hubert_optimized_seed456.pth models/ser/wavlm_hubert_optimized_seed42.pth
    echo "[OK] SER model linked"
else
    echo "[WARN] SER model not found"
fi

mkdir -p data/sessions data/tts data/processed/chroma_db

systemctl --user stop nomeda-backend.service 2>/dev/null || true
systemctl --user reset-failed nomeda-backend.service 2>/dev/null || true
fuser -k 8000/tcp 2>/dev/null || true
sleep 1

systemd-run --user --unit=nomeda-backend \
    --working-directory="$ROOT_DIR" \
    --description="Nomeda-MSTE v3 Backend" \
    /home/abdallah/.local/bin/uvicorn backend.main:app \
        --host 0.0.0.0 --port 8000 \
        --log-level info --no-access-log 2>&1

echo ""
echo "=========================================="
echo " Dashboard:  http://localhost:8000/"
echo " Admin:      http://localhost:8000/static/admin/"
echo " Status:     systemctl --user status nomeda-backend.service"
echo " Logs:       journalctl --user -u nomeda-backend.service -f"
echo " Stop:       systemctl --user stop nomeda-backend.service"
echo "=========================================="
