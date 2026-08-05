# KIDSFLOW — Production runbook

5-bosqich (production tayyorgarligi) operatsion qo'llanmasi. Har bir bog'cha
alohida deployment bo'lgani uchun (2.2-bo'lim) quyidagi amallar har bir deployment
uchun alohida bajariladi.

## 1. Deployment (birinchi ishga tushirish)

```bash
# 1. .env fayllarni tayyorlang (production secretlar bilan!)
cp .env.example .env
cp backend/.env.example backend/.env        # JWT_SECRET, ENCRYPTION_KEY, BOT_API_TOKEN, SETUP_TOKEN, TELEGRAM_BOT_TOKEN
cp telegram-bot/.env.example telegram-bot/.env
cp frontend-web/.env.example frontend-web/.env

# 2. Production stek (resurs limitlari bilan)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 3. Migratsiya
docker compose run --rm backend alembic upgrade head

# 4. Smoke test
BASE_URL=http://localhost:8000 ./scripts/smoke_test.sh

# 5. Tizimni sozlash (bir martalik)
curl -X POST http://localhost:8000/api/v1/setup -H "X-Setup-Token: $SETUP_TOKEN" ...
```

### Production secret ro'yxati (majburiy o'zgartiring!)

| O'zgaruvchi | Tavsif |
| --- | --- |
| `SETUP_TOKEN` | Bir martalik setup tokeni |
| `JWT_SECRET` | JWT imzo kaliti (uzun, tasodifiy) |
| `ENCRYPTION_KEY` | Tibbiy ma'lumot shifrlash paroli |
| `BOT_API_TOKEN` | Bot ↔ backend umumiy siri |
| `TELEGRAM_BOT_TOKEN` | BotFather tokeni (worker xabar yuborishi uchun) |
| `POSTGRES_PASSWORD` | DB paroli |
| `BACKUP_PASSPHRASE` | Backup shifrlash paroli (backup skripti uchun) |

## 2. Backup (kundalik)

```bash
BACKUP_PASSPHRASE='...' RETENTION_DAYS=14 OFFSITE_TARGET='user@host:/backups' \
  ./scripts/backup.sh
```

Cron misoli (har kuni 02:00):

```cron
0 2 * * * cd /opt/kidsflow && BACKUP_PASSPHRASE='...' ./scripts/backup.sh >> /var/log/kidsflow-backup.log 2>&1
```

Backup quyidagilarni o'z ichiga oladi: PostgreSQL dump + fayllar arxivi,
AES-256 bilan shifrlangan, retention bo'yicha eskilarini o'chiradi, ixtiyoriy
serverdan tashqari nusxa.

## 3. Restore va restore testi (12-bo'lim: tiklash jarayoni tekshiriladi)

> Backup mavjudligi yetarli emas — tiklash ishlashi muntazam sinaladi.

**Staging'da restore testi (tavsiya: oyda bir marta):**

```bash
BACKUP_PASSPHRASE='...' ./scripts/restore.sh ./backups/kidsflow-backup-XXXX.tar.enc
BASE_URL=http://staging:8000 ./scripts/smoke_test.sh
```

## 4. Release (yangilash)

Har bir release avval **staging**da sinaladi, so'ng production'da:

```bash
BACKUP_PASSPHRASE='...' ./scripts/release.sh
```

Bu ketma-ketlikda: backup → build → migratsiya → up → healthcheck → smoke test.

### Rollback (muammo bo'lsa)

```bash
# 1. Oldingi image tegiga qayting (yoki git checkout <oldingi-tag> && build)
# 2. Zarur bo'lsa bazani tiklang:
BACKUP_PASSPHRASE='...' ./scripts/restore.sh ./backups/<release-oldidan-backup>.tar.enc
# 3. Servisni ko'taring va smoke test:
docker compose up -d && ./scripts/smoke_test.sh
```

## 5. Monitoring va loglar

- **Health**: `GET /api/v1/health` (liveness), `GET /api/v1/health/ready` (DB readiness).
- **Strukturali loglar**: barcha loglar JSON formatda stdout'ga chiqadi
  (`docker compose logs -f backend`). Har bir so'rov `request_id`, `method`,
  `path`, `status_code`, `duration_ms` bilan loglanadi.
- Log yig'ish uchun `docker compose logs` ni Loki/ELK kabi tizimga yo'naltiring.

## 6. Xavfsizlik auditi (release oldidan checklist)

- [ ] Barcha production secretlar `.env.example`dagi standart qiymatlardan farq qiladi.
- [ ] `ENVIRONMENT=production`, `DEBUG=false`.
- [ ] TLS yoqilgan (nginx `certs/` + 443 server bloki).
- [ ] postgres/redis host portlari yopiq (prod override).
- [ ] Login/setup rate limit ishlayapti (`RATE_LIMIT_ENABLED=true`; bir nechta
      instans bo'lsa `RATE_LIMIT_BACKEND=redis`).
- [ ] `pytest` (unit + integration + security) yashil.
- [ ] Filial izolyatsiyasi va parent/teacher kirish testlari o'tgan.
- [ ] Backup ishlayapti va restore staging'da sinovdan o'tgan.
- [ ] Yuklama testi (`loadtest/`) qoniqarli natija bergan.

## 7. Yuklama testi

Batafsil: [loadtest/README.md](../loadtest/README.md).

```bash
locust -f loadtest/locustfile.py --host http://staging:8000 --headless -u 50 -r 5 -t 2m
```
