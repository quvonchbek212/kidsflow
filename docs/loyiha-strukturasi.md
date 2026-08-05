# KIDSFLOW — xususiy bog‘chalar uchun boshqaruv platformasi

> Versiya: 2.0  
> Holat: ishlab chiqishni boshlash uchun texnik spetsifikatsiya  
> Asosiy bozor: O‘zbekiston xususiy bog‘chalari

---

## 1. Mahsulot g‘oyasi

KIDSFLOW — xususiy bog‘chaning kundalik ishlarini boshqaradigan platforma:

- egasi uchun moliya va filiallar nazorati;
- menejer uchun bolalar, guruhlar, to‘lovlar va xarajatlar;
- tarbiyachi uchun davomat va kunlik hisobot;
- ota-ona uchun Telegram bot orqali farzandi haqidagi ma’lumotlar.

Platformaning asosiy maqsadi — bog‘cha xodimlarining qo‘lda qiladigan ishlarini kamaytirish, ota-onalar bilan aloqani yaxshilash va egasiga aniq moliyaviy ko‘rsatkichlarni taqdim etish.

---

## 2. Arxitektura modeli

### 2.1 To‘g‘ri arxitektura nomi

KIDSFLOW dastlabki versiyada:

> **Single-tenant per deployment, multi-branch SaaS**

Bu quyidagini anglatadi:

- har bir bog‘cha uchun alohida ilova nusxasi ishga tushiriladi;
- har bir bog‘chaning alohida PostgreSQL bazasi bo‘ladi;
- har bir bog‘chaning alohida Telegram boti va sozlamalari bo‘ladi;
- bitta bog‘chada bir nechta filial bo‘lishi mumkin;
- filiallar `branch_id` orqali ajratiladi;
- umumiy `tenant_id`, tenant jadvali va superadmin panel mavjud emas.

### 2.2 Server modeli

Har bir bog‘cha uchun alohida fizik server olish shart emas. Bitta VPS ichida bir nechta bog‘cha alohida Docker loyihalari sifatida ishlashi mumkin:

```text
VPS-1
├── kidsflow_bogcha_a
│   ├── backend
│   ├── worker
│   ├── telegram_bot
│   ├── postgres
│   └── redis
├── kidsflow_bogcha_b
│   ├── backend
│   ├── worker
│   ├── telegram_bot
│   ├── postgres
│   └── redis
└── nginx
```

Har bir deployment uchun quyidagilar alohida bo‘ladi:

- `.env`;
- database va database user;
- Docker network;
- volume;
- Telegram bot token;
- domen yoki subdomen;
- fayl saqlash prefiksi/bucket;
- log va backup.

Server resurslari yetmay boshlaganda yangi VPS qo‘shiladi. Katta yoki maxsus xavfsizlik talab qiladigan mijoz alohida VPS’da joylashtirilishi mumkin.

### 2.3 Filiallar izolyatsiyasi

OWNER barcha filiallarni ko‘rishi mumkin. Boshqa rollar faqat ruxsat berilgan filial ma’lumotlariga kira oladi.

Har bir himoyalangan so‘rov quyidagi tekshiruvlardan o‘tadi:

```text
get_current_user
→ check_user_is_active
→ resolve_branch
→ check_branch_membership
→ check_role_permission
→ execute_business_rule
```

Frontenddagi yashirish xavfsizlik hisoblanmaydi. Ruxsatlar doimo backend darajasida tekshiriladi.

---

## 3. Foydalanuvchi rollari

### OWNER

- barcha filiallarni ko‘radi;
- filial yaratadi va tahrirlaydi;
- menejer va boshqa xodimlarni boshqaradi;
- barcha moliyaviy hisobotlarni ko‘radi;
- tizim sozlamalarini o‘zgartiradi;
- audit jurnalini ko‘radi.

### MANAGER

- bir yoki bir nechta biriktirilgan filialni boshqaradi;
- bola, vasiy va guruh ma’lumotlarini yuritadi;
- to‘lovni tasdiqlaydi;
- xarajat kiritadi;
- qarzdorlar va filial hisobotlarini ko‘radi;
- Telegram taklif kodlarini yaratadi.

### TEACHER

- faqat biriktirilgan guruhlarni ko‘radi;
- davomat belgilaydi;
- kunlik hisobot kiritadi;
- tegishli ota-onalar bilan muloqot qiladi;
- moliyaviy ma’lumotlarni ko‘rmaydi.

### PARENT

- faqat vasiy sifatida biriktirilgan bolalarni ko‘radi;
- davomat va kunlik hisobotlarni ko‘radi;
- o‘ziga tegishli to‘lov holatini ko‘radi;
- tegishli tarbiyachi yoki filial menejeriga yozadi;
- boshqa bolalar haqidagi ma’lumotlarni ko‘rmaydi.

### Rol modeli

Foydalanuvchining shaxsi va filialdagi roli alohida saqlanadi:

```text
users
user_role_assignments
```

Bu bitta tarbiyachini bir nechta filial yoki guruhga xavfsiz biriktirish imkonini beradi.

---

## 4. Asosiy biznes jarayonlari

### 4.1 Dastlabki sozlash

Yangi deployment birinchi marta ishga tushganda `/setup` orqali:

1. bog‘cha ma’lumotlari;
2. birinchi filial;
3. OWNER hisobi;
4. timezone, til va valyuta

yaratiladi.

Xavfsizlik qoidalari:

- `/setup` faqat baza hali sozlanmagan bo‘lsa ishlaydi;
- so‘rov `.env` dagi bir martalik `SETUP_TOKEN` ni talab qiladi;
- yaratish bitta database transaction ichida bajariladi;
- parallel setup so‘rovlari DB lock bilan to‘xtatiladi;
- muvaffaqiyatli setupdan keyin endpoint bloklanadi;
- oddiy `/register` orqali OWNER yaratib bo‘lmaydi.

### 4.2 Bola va vasiylarni ro‘yxatdan o‘tkazish

Menejer:

1. bolaning profilini yaratadi;
2. bir yoki bir nechta vasiyni biriktiradi;
3. vasiy turini belgilaydi: ota, ona, qarindosh yoki boshqa;
4. asosiy aloqa shaxsini belgilaydi;
5. bolani filial va guruhga enrollment orqali qabul qiladi;
6. ota-onaga bir martalik Telegram taklif kodini beradi.

Bola modeli ichida bitta `parent_id` va doimiy `group_id` saqlanmaydi. Aloqalar tarixni saqlaydigan jadvallar orqali yuritiladi.

### 4.3 Davomat

Tarbiyachi yoki menejer bolaning holatini belgilaydi:

- `PRESENT`;
- `ABSENT`;
- `LATE`;
- `EXCUSED`;
- `SICK`.

Har bir bola uchun bir sanada faqat bitta davomat yozuvi bo‘lishi mumkin.

Qo‘shimcha ma’lumotlar:

- kelgan vaqt;
- ketgan vaqt;
- izoh;
- kim belgilagani;
- qachon o‘zgartirilgani.

### 4.4 Kunlik hisobot

Tarbiyachi quyidagilarni kiritadi:

- ovqatlanish holati;
- uyqu davomiyligi;
- kayfiyat;
- faoliyatlar;
- qisqa izoh;
- foto yoki fayllar.

AI kiritilgan faktlarni o‘zgartirmasdan, ota-onaga yuboriladigan tabiiy matnni tayyorlashi mumkin. Tarbiyachi tasdiqlamaguncha AI matni ota-onaga yuborilmaydi.

### 4.5 To‘lov

MVP’da Payme yoki Click integratsiyasi mavjud emas.

Jarayon:

1. tizim har oy bola uchun invoice yaratadi;
2. ota-ona bog‘chaga naqd yoki terminal/karta orqali to‘laydi;
3. menejer real to‘lov tranzaksiyasini kiritadi;
4. ixtiyoriy chek yoki tasdiqlovchi fayl yuklanadi;
5. to‘lov invoice bilan bog‘lanadi;
6. qarz qoldig‘i qayta hisoblanadi;
7. transaction commit bo‘lgach, ota-onaga Telegram xabari navbatga qo‘yiladi.

Qo‘llab-quvvatlanadigan holatlar:

- to‘liq to‘lov;
- qisman to‘lov;
- oldindan to‘lov;
- chegirma;
- qarzni tuzatish;
- bekor qilish;
- pul qaytarish.

Moliyaviy yozuvlar bazadan o‘chirib yuborilmaydi. Noto‘g‘ri yozuv reversal yoki adjustment bilan tuzatiladi va audit jurnalida qoladi.

### 4.6 Xarajat

Xarajat kategoriyalari:

- ish haqi;
- ijara;
- oziq-ovqat;
- kommunal xizmat;
- ta’mirlash va jihoz;
- transport;
- soliq;
- boshqa.

Har bir xarajatda:

- filial;
- kategoriya;
- summa;
- valyuta;
- xarajat sanasi;
- izoh;
- ta’minotchi;
- ixtiyoriy chek;
- kiritgan foydalanuvchi;
- yaratilgan va tahrirlangan vaqt

saqlanadi.

### 4.7 Moliyaviy dashboard

Hisob-kitoblar birinchi navbatda SQL va aniq formulalar orqali bajariladi:

- tushgan real pul;
- invoice bo‘yicha hisoblangan daromad;
- qarzdorlik;
- xarajatlar;
- cash-flow;
- sof natija;
- filiallar taqqoslanishi;
- guruh to‘ldirilganligi;
- bir bolaga to‘g‘ri keladigan tushum va xarajat.

Dashboardda “kirim” tushunchasi aniq ajratiladi:

- **accrual revenue** — invoice orqali hisoblangan summa;
- **cash collected** — real kelib tushgan pul.

AI faqat tayyor raqamlarni tushuntiradi. AI mustaqil ravishda moliyaviy sabab yoki fakt o‘ylab topmasligi kerak.

---

## 5. Ma’lumotlar bazasi modeli

Barcha asosiy jadvallarda quyidagilar bo‘lishi kerak:

```text
id: UUID
created_at: timestamptz
updated_at: timestamptz
```

Pul qiymatlari `NUMERIC(18, 2)` bilan, vaqtlar UTC formatda saqlanadi. Interfeysda `Asia/Tashkent` timezone ishlatiladi.

### 5.1 Tizim va filiallar

```text
kindergarten_settings
  id, name, legal_name, address, phone, logo_file_id,
  timezone, default_language, currency, setup_completed_at

branches
  id, name, address, phone, capacity, is_active
```

`kindergarten_settings` jadvalida faqat bitta faol yozuv bo‘lishi kerak.

### 5.2 Foydalanuvchilar va rollar

```text
users
  id, full_name, phone, email, password_hash,
  telegram_user_id, telegram_chat_id,
  preferred_language, is_active, last_login_at

user_role_assignments
  id, user_id, role, branch_id nullable,
  valid_from, valid_until, assigned_by
```

Qoidalar:

- OWNER uchun `branch_id` bo‘sh bo‘lishi mumkin;
- boshqa xodim rollari uchun `branch_id` talab qilinadi;
- email va telefon normalizatsiya qilinadi;
- mavjud bo‘lsa, telefon va email uchun unique constraint qo‘yiladi;
- `telegram_user_id` unique bo‘ladi.

### 5.3 Bolalar, vasiylar va enrollment

```text
children
  id, full_name, birth_date, gender nullable,
  medical_notes_encrypted nullable, photo_file_id nullable,
  is_active

child_guardians
  id, child_id, guardian_user_id, relationship,
  is_primary, can_pick_up, receives_notifications

groups
  id, branch_id, name, min_age_months, max_age_months,
  capacity, is_active

group_teachers
  id, group_id, teacher_user_id, is_primary,
  valid_from, valid_until

enrollments
  id, child_id, branch_id, group_id,
  start_date, end_date nullable, status,
  fee_plan_id nullable, notes nullable
```

Enrollment holatlari:

- `PLANNED`;
- `ACTIVE`;
- `PAUSED`;
- `COMPLETED`;
- `CANCELLED`.

Bitta bolada bir vaqtda faqat bitta faol enrollment bo‘lishi kerak.

### 5.4 Davomat va hisobot

```text
attendance
  id, branch_id, child_id, attendance_date, status,
  check_in_at nullable, check_out_at nullable,
  note nullable, marked_by

daily_reports
  id, branch_id, child_id, report_date,
  meal_status, nap_minutes nullable, mood,
  activities_text, teacher_note nullable,
  ai_draft nullable, final_summary nullable,
  created_by, published_at nullable

daily_report_files
  id, daily_report_id, file_id, sort_order
```

Unique constraintlar:

```text
attendance(child_id, attendance_date)
daily_reports(child_id, report_date)
```

### 5.5 Tarif, invoice va to‘lovlar

```text
fee_plans
  id, branch_id, name, monthly_amount,
  currency, is_active

invoices
  id, branch_id, child_id, enrollment_id,
  billing_period, due_date,
  original_amount, discount_amount, adjusted_amount,
  paid_amount, outstanding_amount, status

payment_transactions
  id, branch_id, child_id, amount, currency,
  payment_method, paid_at, reference nullable,
  receipt_file_id nullable, status,
  recorded_by, reversed_transaction_id nullable

payment_allocations
  id, payment_transaction_id, invoice_id, amount

invoice_adjustments
  id, invoice_id, adjustment_type, amount,
  reason, created_by
```

Invoice holatlari:

- `DRAFT`;
- `OPEN`;
- `PARTIALLY_PAID`;
- `PAID`;
- `OVERDUE`;
- `CANCELLED`.

Payment holatlari:

- `RECORDED`;
- `CONFIRMED`;
- `REVERSED`;
- `REFUNDED`.

`billing_period` oyning birinchi sanasi sifatida `DATE` formatida saqlanadi. Matn ko‘rinishidagi “Iyul 2026” baza qiymati sifatida ishlatilmaydi.

### 5.6 Xarajatlar

```text
expense_categories
  id, name, is_system, is_active

expenses
  id, branch_id, category_id, amount, currency,
  expense_date, vendor nullable, description nullable,
  receipt_file_id nullable, status,
  recorded_by, reversed_expense_id nullable
```

### 5.7 Xabarlar

```text
conversations
  id, branch_id, child_id nullable, conversation_type,
  created_by

conversation_participants
  id, conversation_id, user_id, joined_at, left_at nullable

messages
  id, conversation_id, sender_id,
  text, sent_at, edited_at nullable, deleted_at nullable

message_files
  id, message_id, file_id
```

Foydalanuvchi xabar yuborishdan oldin conversation ishtirokchisi ekanligi backendda tekshiriladi.

### 5.8 Boshqa modullar

```text
events
  id, branch_id, title, description,
  starts_at, ends_at nullable, target_type,
  target_group_id nullable, created_by

health_records
  id, branch_id, child_id, record_type,
  description_encrypted, recorded_at, recorded_by

staff_schedules
  id, branch_id, user_id, shift_date,
  start_time, end_time, note nullable

files
  id, storage_key, original_name, content_type,
  size_bytes, checksum, uploaded_by,
  scan_status, created_at

notifications
  id, user_id, channel, notification_type,
  payload, status, scheduled_at,
  sent_at nullable, retry_count

outbox_events
  id, event_type, payload, status,
  available_at, processed_at nullable, retry_count

audit_logs
  id, actor_user_id nullable, branch_id nullable,
  action, entity_type, entity_id,
  before_data nullable, after_data nullable,
  ip_address nullable, user_agent nullable, created_at
```

### 5.9 Muhim indeks va constraintlar

- barcha foreign key ustunlariga indeks;
- `branch_id` ishlatiladigan qidiruvlarda composite indeks;
- pul qiymatlari manfiy bo‘lishiga faqat adjustment/reversal qoidalari orqali ruxsat;
- guruh sig‘imi noldan katta;
- `check_out_at >= check_in_at`;
- `end_date >= start_date`;
- bir bola uchun bir vaqtning o‘zida ikkita faol enrollment yo‘q;
- turli filialga tegishli bola, guruh va invoice noto‘g‘ri bog‘lanmasligi tekshiriladi.

---

## 6. Backend strukturasi

```text
backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   ├── api/
│   │   └── v1/
│   │       ├── router.py
│   │       └── endpoints/
│   │           ├── auth.py
│   │           ├── setup.py
│   │           ├── branches.py
│   │           ├── users.py
│   │           ├── children.py
│   │           ├── guardians.py
│   │           ├── groups.py
│   │           ├── enrollments.py
│   │           ├── attendance.py
│   │           ├── daily_reports.py
│   │           ├── invoices.py
│   │           ├── payments.py
│   │           ├── expenses.py
│   │           ├── conversations.py
│   │           ├── events.py
│   │           ├── analytics.py
│   │           └── ai.py
│   ├── core/
│   │   ├── security.py
│   │   ├── permissions.py
│   │   ├── exceptions.py
│   │   ├── logging.py
│   │   └── rate_limit.py
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── enrollment_service.py
│   │   ├── attendance_service.py
│   │   ├── billing_service.py
│   │   ├── expense_service.py
│   │   ├── notification_service.py
│   │   ├── analytics_service.py
│   │   └── ai/
│   │       ├── report_generator.py
│   │       ├── finance_narrator.py
│   │       ├── parent_assistant.py
│   │       ├── document_ocr.py
│   │       └── translation.py
│   ├── workers/
│   │   ├── notification_worker.py
│   │   ├── invoice_worker.py
│   │   └── reminder_worker.py
│   └── utils/
│       ├── file_storage.py
│       ├── validators.py
│       └── phone.py
├── alembic/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   └── factories/
├── requirements.txt
└── .env.example
```

Router faqat HTTP qatlamini boshqaradi. Biznes qoidalari service qatlamida, database so‘rovlari repository qatlamida joylashadi.

API versiyasi boshidan `/api/v1` bilan boshlanadi.

---

## 7. Telegram bot

```text
telegram-bot/
├── bot.py
├── config.py
├── api_client.py
├── handlers/
│   ├── start.py
│   ├── link_account.py
│   ├── children.py
│   ├── attendance.py
│   ├── daily_reports.py
│   ├── payments.py
│   ├── messages.py
│   └── ai_assistant.py
├── keyboards/
├── middlewares/
├── locales/
└── tests/
```

### Hisobni bog‘lash

Telefon raqamining o‘zi autentifikatsiya vositasi emas.

Xavfsiz jarayon:

1. menejer parent profilini yaratadi;
2. backend qisqa muddatli, bir martalik invitation code yaratadi;
3. ota-ona botda kodni yuboradi;
4. backend kod, foydalanuvchi va amal qilish muddatini tekshiradi;
5. Telegram user ID parent profiliga bog‘lanadi;
6. invitation code ishlatilgan deb belgilanadi.

Bot faqat backend API bilan ishlaydi. Botga database paroli berilmaydi.

---

## 8. Frontend

```text
frontend-web/
├── app/
│   ├── (auth)/
│   ├── setup/
│   ├── dashboard/
│   ├── branches/
│   ├── staff/
│   ├── children/
│   ├── groups/
│   ├── attendance/
│   ├── reports/
│   ├── billing/
│   ├── expenses/
│   ├── messages/
│   ├── analytics/
│   └── settings/
├── components/
├── features/
├── lib/
│   ├── api.ts
│   ├── auth.ts
│   └── permissions.ts
├── locales/
└── tests/
```

Frontend backendning OpenAPI sxemasidan yaratilgan typed API client ishlatishi tavsiya etiladi.

Interfeys:

- o‘zbek va rus tillarini;
- mobil ekranlarni;
- klaviatura orqali boshqarishni;
- tushunarli xato xabarlarini;
- loading va empty state’larni

qo‘llab-quvvatlashi kerak.

---

## 9. Bildirishnomalar va background tasklar

Muhim bildirishnoma HTTP so‘rovi ichida to‘g‘ridan-to‘g‘ri Telegram’ga yuborilmaydi.

Jarayon:

```text
Database transaction
├── payment saqlanadi
├── invoice yangilanadi
└── outbox_event yaratiladi

Worker
└── outbox_event → Telegram xabar → notification status
```

Bu Telegram vaqtincha ishlamasa ham to‘lov yozuvi yo‘qolmasligini va xabarni qayta yuborish mumkinligini ta’minlaydi.

Background tasklar:

- oylik invoice yaratish;
- muddati o‘tgan invoice’larni belgilash;
- qarzdorlik eslatmalari;
- Telegram bildirishnomalari;
- fayl tekshiruvi;
- rejalashtirilgan hisobotlar.

---

## 10. AI integratsiyasi

AI mahsulotning asosiy hisob-kitoblarini bajarmaydi. U tayyor ma’lumotni tushuntirish va matn yaratish uchun ishlatiladi.

### 10.1 Kunlik hisobot

Tarbiyachi kiritgan faktlardan tabiiy matn tayyorlaydi. AI:

- yangi fakt qo‘shmasligi;
- bolaning sog‘lig‘i bo‘yicha tashxis bermasligi;
- tarbiyachi tasdig‘isiz xabar yubormasligi kerak.

### 10.2 Parent yordamchi

RAG manbalari:

- bog‘cha qoidalari;
- ish vaqti;
- ovqatlanish jadvali;
- narx va tariflar;
- tadbirlar.

Javobda foydalanilgan ichki manba ko‘rsatiladi. Tibbiy, huquqiy yoki moliyaviy qarorlar bo‘yicha cheklov qo‘yiladi.

### 10.3 Moliyaviy izoh

SQL orqali hisoblangan ko‘rsatkichlarni oddiy tilda sharhlaydi. AI “xarajat oshishining sababi”ni ma’lumot bo‘lmasa taxmin qilmaydi.

### 10.4 OCR

Chekdan summa, sana va boshqa maydonlarni taklif sifatida ajratadi. Menejer tasdiqlamaguncha qiymatlar moliyaviy yozuvga aylanmaydi.

### 10.5 Tarjima

O‘zbek, rus va ingliz tillari orasida tarjima qiladi. Asl matn ham bazada saqlanadi.

### 10.6 Gemini API xarajatlari

Barcha deploymentlar bitta Gemini hisobidan foydalanishi mumkin. Har bir bog‘cha uchun alohida Gemini obunasi shart emas.

Har bir deployment uchun:

- alohida API key yoki markaziy AI gateway;
- oylik token limiti;
- request va token hisoboti;
- rate limit;
- model tanlovi;
- AI’ni o‘chirish sozlamasi

bo‘lishi kerak.

AI ishlatilishi quyidagi jadvalda hisoblanadi:

```text
ai_usage_logs
  id, feature, model, input_tokens, output_tokens,
  estimated_cost, user_id nullable, created_at
```

API key frontend yoki Telegram botga berilmaydi. Gemini bilan faqat backend yoki maxsus AI gateway ishlaydi.

---

## 11. Xavfsizlik

### Autentifikatsiya

- Argon2id orqali parol hash;
- qisqa muddatli access token;
- rotation qilinadigan refresh token;
- refresh tokenni bekor qilish;
- login va setup endpointlariga rate limit;
- muvaffaqiyatsiz loginlar auditi;
- muhim amallar uchun qayta autentifikatsiya.

### Ruxsatlar

- backend darajasida RBAC;
- har bir branch-scoped so‘rovda `branch_id` tekshiruvi;
- parent uchun `child_guardians` aloqasi tekshiruvi;
- teacher uchun faol `group_teachers` aloqasi tekshiruvi;
- ID almashtirib boshqa filial ma’lumotiga kirish testlari.

### Bolalar ma’lumotlari

- tibbiy ma’lumotlarni shifrlash;
- private fayl saqlash;
- vaqtinchalik signed URL;
- surat va ma’lumotlarni saqlash muddati;
- ota-ona roziligi;
- kim ko‘rganini audit qilish;
- eksport va o‘chirish jarayoni.

### Fayllar

- ruxsat etilgan formatlar ro‘yxati;
- maksimal fayl hajmi;
- MIME va real file signature tekshiruvi;
- tasodifiy storage key;
- zararli fayl tekshiruvi;
- original fayl nomini storage path sifatida ishlatmaslik.

### Moliyaviy xavfsizlik

- `DELETE` o‘rniga reversal;
- barcha o‘zgarishlar audit log’da;
- idempotency key bilan takroriy to‘lov yozuvining oldini olish;
- database transaction;
- foydalanuvchi va vaqtni majburiy saqlash.

---

## 12. Infrastruktura va deploy

```text
docker-compose.yml
├── postgres
├── redis
├── backend
├── worker
├── telegram-bot
├── minio (ixtiyoriy)
└── frontend

nginx/
├── TLS
├── reverse proxy
├── upload limit
└── security headers
```

Har bir servisda:

- healthcheck;
- restart policy;
- CPU va memory limit;
- strukturali log;
- production secret;
- aniq image version

bo‘lishi kerak.

### Backup

- PostgreSQL kundalik backup;
- fayllar backup’i;
- backup shifrlanishi;
- serverdan tashqarida nusxa;
- saqlash muddati;
- muntazam restore testi.

Backup mavjudligi yetarli emas — tiklash jarayoni ishlashi tekshirilishi kerak.

### Yangilash

Har bir release uchun:

1. staging muhitida test;
2. database backup;
3. Alembic migration;
4. yangi Docker image;
5. healthcheck;
6. smoke test;
7. muammo bo‘lsa rollback

bajariladi.

---

## 13. Test strategiyasi

Testlar oxirgi bosqichga qoldirilmaydi.

### Unit test

- ruxsat qoidalari;
- invoice hisoblash;
- qisman to‘lov;
- adjustment va reversal;
- davomat qoidalari;
- telefon normalizatsiyasi.

### Integration test

- setup;
- login va refresh;
- filial izolyatsiyasi;
- bola–vasiy bog‘lanishi;
- enrollment;
- to‘lov transaction’i;
- outbox va notification;
- fayl yuklash.

### Security test

- boshqa filial ID’sini yuborish;
- parent boshqa bolaning ma’lumotini so‘rashi;
- teacher boshqa guruhga kirishi;
- expired/revoked token;
- setupni qayta ishga tushirish;
- zararli yoki soxta fayl yuklash.

### End-to-end test

- OWNER setup;
- menejer bola va parent yaratishi;
- parent Telegram’ni bog‘lashi;
- teacher davomat va hisobot kiritishi;
- menejer to‘lovni tasdiqlashi;
- parent Telegram xabarini olishi.

---

## 14. Ishlab chiqish roadmap’i

Muddat jamoa hajmi va tajribasiga bog‘liq. Quyidagi tartib funksiyalarning bog‘liqligiga asoslangan.

### 0-bosqich — Qarorlar va skelet

- repository va papkalar;
- Docker development muhiti;
- FastAPI va PostgreSQL;
- Next.js;
- bot skeleton;
- lint, format va test konfiguratsiyasi;
- CI pipeline;
- `.env.example`.

### 1-bosqich — Xavfsiz poydevor

- settings va branch;
- setup;
- users va role assignments;
- JWT access/refresh;
- RBAC va branch isolation;
- audit log;
- auth/security testlari.

### 2-bosqich — Bog‘cha asosiy operatsiyalari

- children;
- guardians;
- groups;
- group teachers;
- enrollments;
- attendance;
- Telegram invitation code;
- parent uchun bola va davomatni ko‘rish.

### 3-bosqich — Hisobot va bildirishnoma

- daily reports;
- private fayllar;
- outbox;
- worker;
- Telegram bildirishnomalari;
- oddiy, AI’siz hisobot matni.

### 4-bosqich — Moliya

- fee plans;
- invoices;
- payment transactions;
- allocations;
- adjustments/reversals;
- expenses;
- qarzdorlik;
- moliyaviy dashboard;
- audit va integration testlar.

### 5-bosqich — Production tayyorgarligi

- backup va restore;
- monitoring;
- loglar;
- rate limit;
- xavfsizlik auditi;
- yuklama testi;
- staging va release jarayoni.

### 6-bosqich — AI va qo‘shimcha imkoniyatlar

- AI daily report;
- OCR;
- parent RAG yordamchi;
- moliyaviy izoh;
- tarjima;
- AI usage va limitlar.

AI, WebSocket chat va murakkab prognozlar asosiy MVP ishlagandan keyin qo‘shiladi.

---

## 15. MVP tarkibi

MVP uchun majburiy:

- setup va OWNER;
- filiallar;
- xodimlar va rollar;
- bolalar, vasiylar, guruhlar va enrollment;
- davomat;
- oddiy kunlik hisobot;
- Telegram orqali parent hisobini xavfsiz bog‘lash;
- invoice va qo‘lda to‘lov tasdiqlash;
- xarajatlar;
- asosiy moliyaviy dashboard;
- audit, backup va xavfsizlik testlari.

MVP’dan keyin:

- ichki real-time chat;
- AI chatbot;
- OCR;
- moliyaviy prognoz;
- avtomatik tarjima;
- Payme/Click;
- mobil ilova.

---

## 16. Kodlash yordamchisi uchun doimiy qoidalar

Har bir yangi vazifada quyidagi qoidalar saqlanadi:

1. Tizim markazlashgan multi-tenant emas.
2. Har bir bog‘cha alohida deployment va bazaga ega.
3. Bitta deployment ichida filiallar `branch_id` bilan ajratiladi.
4. Umumiy `tenant_id` va superadmin yo‘q.
5. MVP’da Payme/Click yo‘q.
6. To‘lov invoice va payment transaction sifatida alohida yuritiladi.
7. Moliyaviy yozuvlar o‘chirilmaydi, reversal qilinadi.
8. Bola–vasiy va guruh–teacher aloqalari many-to-many.
9. Bola guruh tarixi enrollment orqali saqlanadi.
10. Telefon raqamining o‘zi Telegram autentifikatsiyasi emas.
11. AI fakt va moliyaviy raqamlarni o‘ylab topmaydi.
12. Routerda biznes logika yozilmaydi.
13. Har bir modul test bilan birga yoziladi.
14. Har bir branch-scoped endpoint boshqa filial ID’si bilan sinovdan o‘tkaziladi.
15. Migratsiya, backup va rollback rejasi bo‘lmasdan production deploy qilinmaydi.

---

## 17. Ishni boshlash uchun birinchi topshiriq

```text
docs/loyiha-strukturasi.md faylini to‘liq o‘qib chiq.

Faqat 0-bosqichni bajar:
- backend, frontend-web va telegram-bot skeletini yarat;
- Docker development muhitini tayyorla;
- FastAPI health endpoint yoz;
- PostgreSQL ulanishini sozla;
- lint, format va test konfiguratsiyasini qo‘sh;
- .env.example yarat;
- kamida bitta backend smoke test yoz.

Hozircha biznes modellar va AI funksiyalarini yozma.
Natijada ishga tushirish va test buyruqlarini ko‘rsat.
```
