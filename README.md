# KIDSFLOW

Xususiy bog'chalar uchun boshqaruv platformasi.

Bajarilgan bosqichlar (roadmap, 14-bo'lim):

- **0-bosqich** — skelet, Docker muhiti, health endpoint, lint/format/test.
- **1-bosqich** — xavfsiz poydevor: settings/branches, setup, users/roles, JWT
  (Argon2id + refresh rotation), RBAC + filial izolyatsiyasi, audit log.
- **2-bosqich** — bog'cha operatsiyalari: children, guardians, groups, group
  teachers, enrollments, attendance, Telegram taklif kodi va parent/teacher
  ko'rish huquqlari.
- **3-bosqich** — hisobot va bildirishnoma: kunlik hisobotlar (draft → publish),
  private fayllar (MIME/imzo validatsiyasi + kirish nazorati), outbox + worker,
  Telegram bildirishnomalari (transactional outbox pattern).
- **4-bosqich** — moliya: tarif rejalari, invoice generatsiyasi, to'lovlar
  (allocation + idempotency + reversal), invoice tuzatmalari (chegirma/qo'shimcha/
  qarz kechirish), xarajatlar (+reversal), moliyaviy dashboard (accrual vs cash).
- **5-bosqich** — production tayyorgarligi: rate limiting (login/setup),
  xavfsizlik sarlavhalari + so'rov logging (request ID), backup/restore/release
  skriptlari, prod docker override (resurs limitlari), nginx TLS/rate-limit,
  yuklama testi (locust), operatsion runbook.
- **6-bosqich** — AI: kunlik hisobot matni, moliyaviy izoh, parent RAG yordamchi,
  chek OCR, tarjima, AI usage/limitlar (Gemini, pluggable provayder). AI faqat
  tayyor ma'lumotni tushuntiradi — fakt/raqam o'ylab topmaydi (10-bo'lim).

To'liq texnik spetsifikatsiya: [docs/loyiha-strukturasi.md](docs/loyiha-strukturasi.md).

> AI funksiyalari va moliya (invoice/to'lov) hozircha yozilmagan — ular keyingi
> bosqichlarda qo'shiladi.

## Tarkib

```text
kidsflow/
├── backend/        FastAPI + SQLAlchemy (async) + Alembic
├── frontend-web/   Next.js (App Router, TS) — login, dashboard, bolalar, to'lovlar
├── telegram-bot/   aiogram 3 — hisob bog'lash, davomat/hisobot/to'lov ko'rish, AI
├── nginx/          reverse proxy
├── docker-compose.yml
└── docs/
```

## Talablar

- Docker + Docker Compose (butun stekni ishga tushirish uchun)
- Yoki lokal ishlab chiqish uchun: Python 3.12+, Node.js 22+

---

## 1-variant — Docker orqali to'liq stek

```bash
# .env fayllarni namunalardan yarating
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend-web/.env.example frontend-web/.env
cp telegram-bot/.env.example telegram-bot/.env   # BOT_TOKEN ni to'ldiring

# Barcha servislarni ko'taring
docker compose up -d --build

# Health tekshiruvi
curl http://localhost:8000/api/v1/health
```

Ochiladigan manzillar:

| Servis        | Manzil                                   |
| ------------- | ---------------------------------------- |
| Backend API   | http://localhost:8000/api/v1/health      |
| API hujjatlar | http://localhost:8000/docs               |
| Frontend      | http://localhost:3000                    |
| Nginx (proxy) | http://localhost/                        |

To'xtatish: `docker compose down` (ma'lumot bilan: `docker compose down -v`).

---

## 2-variant — Backendni lokal ishga tushirish

Windows (PowerShell):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env

# Faqat DB ni Docker'da ko'tarish yetarli
docker compose up -d postgres redis

uvicorn app.main:app --reload
```

Linux/macOS (bash):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

---

## Test va sifat tekshiruvi (backend)

Virtual muhit faollashtirilgan holda `backend/` ichida:

```bash
pytest            # testlar (smoke test shu yerda)
ruff check .      # lint
black --check .   # format tekshiruvi
mypy app          # tip tekshiruvi
```

Smoke test tashqi PostgreSQL'siz ham ishlaydi — health endpointi soxta DB
sessiyasi bilan sinaladi (`tests/integration/test_health.py`).

## Migratsiya (Alembic)

1-bosqich uchun boshlang'ich migratsiya tayyor (`alembic/versions/0001_initial_foundation.py`).
Bazani sxema bilan to'ldirish:

```bash
cd backend
alembic upgrade head
```

Keyingi bosqichlarda modellar qo'shilgach:

```bash
alembic revision --autogenerate -m "izoh"
alembic upgrade head
```

## 1-bosqich API oqimi (xavfsiz poydevor)

| Endpoint | Rol | Tavsif |
| --- | --- | --- |
| `POST /api/v1/setup` | — (X-Setup-Token) | OWNER + birinchi filialni bir transaction'da yaratadi |
| `POST /api/v1/auth/login` | hamma | Telefon/email + parol → access/refresh token |
| `POST /api/v1/auth/refresh` | hamma | Refresh token rotation (eski token bekor qilinadi) |
| `POST /api/v1/auth/logout` | hamma | Refresh tokenni bekor qiladi |
| `GET /api/v1/auth/me` | autentifikatsiya | Joriy foydalanuvchi va rollari |
| `GET /api/v1/branches` | OWNER: hammasi; boshqalar: biriktirilgan | Filiallar ro'yxati |
| `POST /api/v1/branches` | OWNER | Filial yaratish |
| `GET/PATCH /api/v1/branches/{id}` | kirish huquqi bor rol | Filial ko'rish/tahrirlash |
| `POST /api/v1/users` | OWNER | Xodim (MANAGER/TEACHER/PARENT) yaratish |

Namuna (setup → login → me):

```bash
# 1. Setup
curl -X POST http://localhost:8000/api/v1/setup \
  -H "X-Setup-Token: change-me-setup-token" \
  -H "Content-Type: application/json" \
  -d '{"kindergarten":{"name":"Bog cha"},"branch":{"name":"Markaz"},
       "owner":{"full_name":"Egasi","phone":"+998901112233","password":"parol1234"}}'

# 2. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"+998901112233","password":"parol1234"}'

# 3. Me (yuqoridagi access_token bilan)
curl http://localhost:8000/api/v1/auth/me -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Xavfsizlik xususiyatlari: Argon2id parol hash, JWT access (15 daqiqa) + rotation
qilinadigan refresh token, backend darajasidagi RBAC va filial izolyatsiyasi,
barcha muhim amallar audit jurnaliga yoziladi.

## 2-bosqich API (bog'cha operatsiyalari)

| Endpoint | Rol | Tavsif |
| --- | --- | --- |
| `POST/GET /api/v1/children` | MANAGER/OWNER yaratadi; PARENT o'z bolasini, TEACHER guruhidagi bolalarni ko'radi | Bolalar |
| `POST /api/v1/children/{id}/guardians` | MANAGER/OWNER | Vasiy biriktirish (yangi PARENT yaratadi) |
| `POST /api/v1/children/{id}/enrollments` | MANAGER (o'z filiali) | Filial+guruhga qabul (bitta faol enrollment) |
| `PATCH /api/v1/enrollments/{id}` | MANAGER (o'z filiali) | Holat/guruh o'zgartirish |
| `POST/GET /api/v1/groups` | MANAGER (o'z filiali) yaratadi; TEACHER o'z guruhini ko'radi | Guruhlar |
| `POST /api/v1/groups/{id}/teachers` | MANAGER (o'z filiali) | Tarbiyachi biriktirish |
| `POST /api/v1/attendance` | TEACHER (guruhi) / MANAGER (filiali) | Davomat belgilash (bir bola/sana = bitta yozuv) |
| `GET /api/v1/attendance/child/{id}` | kirish huquqiga ega rollar | Davomat tarixi |
| `POST /api/v1/telegram/invitations` | MANAGER/OWNER | Ota-ona uchun bir martalik kod |
| `POST /api/v1/telegram/link` | bot (X-Bot-Token) | Telegram hisobini kod orqali bog'lash |
| `POST /api/v1/telegram/session` | bot (X-Bot-Token) | Bog'langan ota-ona uchun token |

Tibbiy izohlar bazada shifrlanadi (Fernet) va faqat OWNER/MANAGER'ga ochiladi.
Ota-onalar parol bilan emas, Telegram orqali kiradi: bot taklif kodi bilan
hisobni bog'laydi, so'ng `/telegram/session` orqali ota-ona nomidan token oladi.

## 3-bosqich API (hisobot va bildirishnoma)

| Endpoint | Rol | Tavsif |
| --- | --- | --- |
| `POST /api/v1/daily-reports` | TEACHER (guruhi) / MANAGER | Kunlik hisobot yaratish (draft) |
| `PATCH /api/v1/daily-reports/{id}` | TEACHER/MANAGER | Qoralamani tahrirlash (e'lon qilingandan keyin mumkin emas) |
| `POST /api/v1/daily-reports/{id}/publish` | TEACHER/MANAGER | E'lon qilish → outbox → ota-onaga Telegram bildirishnoma |
| `GET /api/v1/daily-reports/{id}` | kirish huquqiga ega rollar | Hisobot (ota-ona faqat e'lon qilinganini) |
| `GET /api/v1/children/{id}/daily-reports` | kirish huquqiga ega rollar | Bola hisobotlari tarixi |
| `POST /api/v1/files` | xodimlar (OWNER/MANAGER/TEACHER) | Fayl yuklash (MIME + imzo tekshiruvi) |
| `GET /api/v1/files/{id}` | kirish huquqiga ega rollar | Faylni yuklab olish (maxfiy, backend orqali) |

**Bildirishnoma oqimi (9-bo'lim):** hisobot e'lon qilinganda bitta transaction
ichida `published_at` belgilanadi va `outbox_event` yaratiladi. Alohida **worker**
(`python -m app.workers.main`) outbox'ni muntazam qayta ishlaydi: hodisadan
bildirishnoma yozuvlari yaratadi, so'ng Telegram orqali yuboradi va holatini
yangilaydi. Bu Telegram vaqtincha ishlamasa ham yozuv yo'qolmasligini ta'minlaydi.

**Fayllar (11-bo'lim):** tasodifiy storage key (original nom path sifatida
ishlatilmaydi), MIME va real magic-byte imzosi mosligi tekshiriladi, hajm limiti,
va faqat vakolatli foydalanuvchi (yuklovchi yoki bola vasiysi/xodimi) yuklab oladi.

## 4-bosqich API (moliya)

| Endpoint | Rol | Tavsif |
| --- | --- | --- |
| `POST/GET /api/v1/fee-plans` | MANAGER/OWNER | Oylik tarif rejalari |
| `POST /api/v1/invoices/generate` | MANAGER/OWNER | Filial bo'yicha oylik invoice'lar |
| `GET /api/v1/children/{id}/invoices` | kirish huquqiga ega rollar | Bola invoice'lari |
| `POST /api/v1/invoices/{id}/adjustments` | MANAGER/OWNER | Chegirma/qo'shimcha/qarz kechirish |
| `POST /api/v1/invoices/{id}/cancel` | MANAGER/OWNER | Invoice'ni bekor qilish (to'lovsiz) |
| `POST /api/v1/payments` | MANAGER/OWNER | To'lov kiritish (idempotent, avto-allocation) |
| `POST /api/v1/payments/{id}/reverse` | MANAGER/OWNER | To'lovni bekor qilish (reversal) |
| `GET/POST /api/v1/expenses` | MANAGER/OWNER | Xarajatlar (+`/reverse`) |
| `GET /api/v1/expense-categories` | MANAGER/OWNER | Xarajat kategoriyalari |
| `GET /api/v1/analytics/dashboard` | MANAGER/OWNER | Moliyaviy dashboard |

**Moliyaviy xavfsizlik (11-bo'lim):** yozuvlar hech qachon `DELETE` qilinmaydi —
noto'g'ri to'lov/xarajat **reversal** bilan, invoice esa **adjustment** bilan
tuzatiladi va audit jurnalida qoladi. Takroriy to'lovning oldi **idempotency_key**
bilan olinadi. Pul `Decimal` (NUMERIC(18,2)) sifatida hisoblanadi. Dashboard
**accrual revenue** (invoice bo'yicha) va **cash collected** (real pul)ni aniq
ajratadi (4.7-bo'lim). To'lov qabul qilinganda ota-onaga outbox orqali Telegram
xabari yuboriladi.

## Production (5-bosqich)

Deployment, backup/restore, release/rollback va monitoring bo'yicha to'liq
operatsion qo'llanma: [docs/runbook.md](docs/runbook.md).

```bash
# Production stek (resurs limitlari, hardening bilan)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Backup (shifrlangan, retention bilan)
BACKUP_PASSPHRASE='...' ./scripts/backup.sh

# Release (backup → migratsiya → build → healthcheck → smoke test)
BACKUP_PASSPHRASE='...' ./scripts/release.sh

# Smoke test
BASE_URL=http://localhost:8000 ./scripts/smoke_test.sh
```

Xususiyatlar: login/setup endpointlariga **rate limit** (in-memory yoki Redis),
har bir javobda **xavfsizlik sarlavhalari** va **X-Request-ID**, JSON strukturali
so'rov loglari (`request_id`, `duration_ms`), nginx TLS + auth rate-limit zonasi,
va [loadtest/](loadtest/) locust yuklama testi.

## 6-bosqich API (AI)

| Endpoint | Rol | Tavsif |
| --- | --- | --- |
| `POST /api/v1/daily-reports/{id}/ai-draft` | TEACHER/MANAGER | Faktlardan AI matn (`ai_draft`, e'lon qilinmaydi) |
| `POST /api/v1/ai/finance-narrative` | OWNER/MANAGER | Dashboard raqamlarini AI sharhi |
| `POST /api/v1/ai/assistant` | autentifikatsiya | Parent RAG yordamchi (manba ko'rsatiladi) |
| `POST /api/v1/ai/ocr` | MANAGER/OWNER | Chekdan summa/sana/vendor (taklif) |
| `POST /api/v1/ai/translate` | autentifikatsiya | uz/ru/en tarjima |
| `POST/GET /api/v1/knowledge-documents` | MANAGER/OWNER | RAG bilim bazasi |
| `GET /api/v1/ai/usage` | OWNER | AI token/xarajat jurnali |

**AI guardraillari (10-bo'lim):** AI hisob-kitob qilmaydi — moliyaviy raqamlar SQL
orqali hisoblanadi, AI ularni faqat **tushuntiradi**. Kunlik hisobot AI matni faqat
tarbiyachi kiritgan **faktlardan** yaratiladi (yangi fakt/tashxis yo'q) va `ai_draft`
sifatida saqlanadi — tarbiyachi tasdiqlamaguncha ota-onaga yuborilmaydi. OCR faqat
**taklif** beradi — menejer tasdiqlamaguncha moliyaviy yozuvga aylanmaydi. Parent
yordamchi faqat ichki bilim bazasidan javob beradi va manbani ko'rsatadi. Har bir
AI so'rovi `ai_usage_logs` ga (token + xarajat) yoziladi; oylik token limiti bor.

AI **standart o'chirilgan** (`AI_ENABLED=false`) — MVP AI'siz to'liq ishlaydi.
Gemini API kaliti faqat backendda; frontend/botga berilmaydi. Provayder pluggable —
markaziy AI gateway (`AI_GATEWAY_URL`) ham qo'llab-quvvatlanadi.

## Frontend

```bash
cd frontend-web
npm install
npm run dev        # http://localhost:3000
npm run lint
npm run typecheck
```

## Telegram bot

`telegram-bot/.env` ichida `BOT_TOKEN` to'ldirilgach:

```bash
cd telegram-bot
pip install -r requirements.txt
python bot.py
```
