#!/usr/bin/env bash
#
# KIDSFLOW backupdan tiklash (12-bo'lim: tiklash jarayoni ishlashini tekshirish).
#
# Ishlatish:
#   BACKUP_PASSPHRASE=... ./scripts/restore.sh ./backups/kidsflow-backup-XXXX.tar.enc
#
# DIQQAT: bu joriy bazani almashtiradi. Avval staging'da sinab ko'ring.

set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
PG_SERVICE="${PG_SERVICE:-postgres}"
POSTGRES_USER="${POSTGRES_USER:-kidsflow}"
POSTGRES_DB="${POSTGRES_DB:-kidsflow}"
FILES_VOLUME="${FILES_VOLUME:-kidsflow_file_storage}"

if [[ $# -lt 1 ]]; then
  echo "Foydalanish: $0 <backup.tar.enc>" >&2
  exit 1
fi
encrypted="$1"

if [[ -z "${BACKUP_PASSPHRASE:-}" ]]; then
  echo "XATO: BACKUP_PASSPHRASE o'rnatilmagan." >&2
  exit 1
fi

work_dir="$(mktemp -d)"
trap 'rm -rf "${work_dir}"' EXIT

echo "[1/4] Deshifrlash..."
openssl enc -d -aes-256-cbc -pbkdf2 \
  -in "${encrypted}" -out "${work_dir}/backup.tar" -pass "pass:${BACKUP_PASSPHRASE}"
tar xf "${work_dir}/backup.tar" -C "${work_dir}"

echo "[2/4] Bazani tiklash (mavjud ma'lumot almashtiriladi)..."
docker compose -f "${COMPOSE_FILE}" exec -T "${PG_SERVICE}" \
  pg_restore -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --clean --if-exists --no-owner \
  < "${work_dir}/db.dump"

echo "[3/4] Fayllarni tiklash..."
if [[ -s "${work_dir}/files.tar.gz" ]]; then
  docker run --rm -v "${FILES_VOLUME}:/data" -v "${work_dir}:/backup:ro" \
    alpine sh -c "rm -rf /data/* && tar xzf /backup/files.tar.gz -C /data"
else
  echo "OGOHLANTIRISH: fayl arxivi bo'sh, o'tkazib yuborildi." >&2
fi

echo "[4/4] Migratsiyalarni tekshirish (alembic upgrade head)..."
docker compose -f "${COMPOSE_FILE}" exec -T backend alembic upgrade head

echo "Tiklash muvaffaqiyatli yakunlandi. Endi smoke testni ishga tushiring."
