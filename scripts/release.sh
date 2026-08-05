#!/usr/bin/env bash
#
# KIDSFLOW release jarayoni (12-bo'lim: yangilash):
#   1. backup;  2. yangi image build;  3. migratsiya;  4. servisni ko'tarish;
#   5. healthcheck;  6. smoke test;  7. muammo bo'lsa rollback ko'rsatmasi.
#
# Ishlatish (staging'da sinab bo'lgach):
#   BACKUP_PASSPHRASE=... ./scripts/release.sh

set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== KIDSFLOW release ==="

echo "[1/6] Backup (rollback uchun xavfsizlik nusxasi)..."
"${SCRIPT_DIR}/backup.sh"

echo "[2/6] Yangi image build..."
# Frontend va bot ham build qilinadi: ilgari faqat backend/worker build qilinib,
# keyingi qadamda `up -d` bilan ko'tarilardi — frontend kodi o'zgargan release'da
# eski image o'z holicha qolib ketardi.
docker compose -f "${COMPOSE_FILE}" build backend worker frontend telegram-bot

echo "[3/6] Database migratsiya (alembic upgrade head)..."
docker compose -f "${COMPOSE_FILE}" run --rm backend alembic upgrade head

echo "[4/6] Servislarni yangilash..."
docker compose -f "${COMPOSE_FILE}" up -d backend worker telegram-bot frontend

# Nginx upstream IP'larni konfiguratsiya yuklanganda bir marta aniqlaydi. Yuqorida
# konteynerlar qayta yaratilgani uchun ularning IP'lari o'zgardi va nginx eski
# manzilga urinib 502 qaytaradi. Qayta ishga tushirish shuni tuzatadi — busiz
# sayt har bir release'dan keyin ishlamay qolardi.
echo "      nginx qayta ishga tushirilmoqda (upstream IP'lar yangilanishi uchun)..."
docker compose -f "${COMPOSE_FILE}" restart nginx

echo "[5/6] Healthcheck kutilmoqda..."
# Production'da backend porti host'ga ochilmaydi, shuning uchun tekshiruv nginx
# orqali boradi. Boshqa manzil kerak bo'lsa: HEALTH_URL=... ./scripts/release.sh
HEALTH_URL="${HEALTH_URL:-http://localhost/api/v1/health}"
for i in $(seq 1 30); do
  if curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; then
    echo "  backend sog'lom (${HEALTH_URL})."
    break
  fi
  sleep 2
  if [[ "${i}" -eq 30 ]]; then
    echo "XATO: backend healthcheck muvaffaqiyatsiz (${HEALTH_URL})." >&2
    echo "ROLLBACK: ./scripts/restore.sh <oxirgi-backup> va oldingi image'ni tiklang." >&2
    exit 1
  fi
done

echo "[6/6] Smoke test..."
BASE_URL="${BASE_URL:-http://localhost}" EXPECT_DOCS="${EXPECT_DOCS:-disabled}" \
  "${SCRIPT_DIR}/smoke_test.sh"

echo "=== Release muvaffaqiyatli yakunlandi ==="
