#!/usr/bin/env bash
#
# KIDSFLOW kundalik backup (12-bo'lim):
#   - PostgreSQL dump (custom format);
#   - fayllar (storage volume) arxivi;
#   - AES-256 bilan shifrlash;
#   - saqlash muddati (retention) bo'yicha eskilarini o'chirish.
#
# Ishlatish:
#   BACKUP_PASSPHRASE=... ./scripts/backup.sh
#
# Muhit o'zgaruvchilari (standart qiymatlar bilan):
#   COMPOSE_FILE        docker-compose.yml:docker-compose.prod.yml
#   PG_SERVICE          postgres
#   POSTGRES_USER       kidsflow
#   POSTGRES_DB         kidsflow
#   FILES_VOLUME        kidsflow_file_storage
#   BACKUP_DIR          ./backups
#   RETENTION_DAYS      14
#   BACKUP_PASSPHRASE   (majburiy) — shifrlash paroli
#   OFFSITE_TARGET      (ixtiyoriy) — rsync/scp manzili (serverdan tashqari nusxa)

set -euo pipefail

# Production'da IKKALA fayl birga kerak: prod override postgres/backend portlarini
# yopadi, TLS'li nginx konfiguratsiyasini va frontend uchun to'g'ri API manzilini
# beradi. Ilgari faqat docker-compose.yml ishlatilardi — release serverga dev
# sozlamasini chiqarardi (ochiq 5432/8000 portlar, frontend localhost:8000 ga
# murojaat qilardi). `docker compose` bu o'zgaruvchini ro'yxat sifatida o'zi o'qiydi.
export COMPOSE_PATH_SEPARATOR="${COMPOSE_PATH_SEPARATOR:-:}"
export COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml:docker-compose.prod.yml}"
PG_SERVICE="${PG_SERVICE:-postgres}"
POSTGRES_USER="${POSTGRES_USER:-kidsflow}"
POSTGRES_DB="${POSTGRES_DB:-kidsflow}"
FILES_VOLUME="${FILES_VOLUME:-kidsflow_file_storage}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

if [[ -z "${BACKUP_PASSPHRASE:-}" ]]; then
  echo "XATO: BACKUP_PASSPHRASE o'rnatilmagan (shifrlash paroli majburiy)." >&2
  exit 1
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
work_dir="${BACKUP_DIR}/${timestamp}"
mkdir -p "${work_dir}"

echo "[1/4] PostgreSQL dump..."
docker compose exec -T "${PG_SERVICE}" \
  pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc \
  > "${work_dir}/db.dump"

echo "[2/4] Fayllar arxivi..."
# Fayl volume'ini vaqtinchalik konteyner orqali arxivlash.
docker run --rm -v "${FILES_VOLUME}:/data:ro" -v "$(pwd)/${work_dir}:/backup" \
  alpine tar czf /backup/files.tar.gz -C /data . || {
    echo "OGOHLANTIRISH: fayl volume topilmadi yoki bo'sh." >&2
    touch "${work_dir}/files.tar.gz"
  }

echo "[3/4] Shifrlash (AES-256)..."
archive="${BACKUP_DIR}/kidsflow-backup-${timestamp}.tar"
tar cf "${archive}" -C "${work_dir}" db.dump files.tar.gz
openssl enc -aes-256-cbc -pbkdf2 -salt \
  -in "${archive}" -out "${archive}.enc" -pass "pass:${BACKUP_PASSPHRASE}"
rm -f "${archive}"
rm -rf "${work_dir}"
echo "Yaratildi: ${archive}.enc"

# Serverdan tashqari nusxa (ixtiyoriy).
if [[ -n "${OFFSITE_TARGET:-}" ]]; then
  echo "[offsite] ${OFFSITE_TARGET} ga nusxalash..."
  rsync -avz "${archive}.enc" "${OFFSITE_TARGET}/"
fi

echo "[4/4] Eski backuplarni tozalash (>${RETENTION_DAYS} kun)..."
find "${BACKUP_DIR}" -name 'kidsflow-backup-*.tar.enc' -type f \
  -mtime "+${RETENTION_DAYS}" -delete

echo "Backup muvaffaqiyatli yakunlandi."
