"""KIDSFLOW — namoyish uchun namuna ma'lumot to'ldirish.

Maqsad: saytni bog'cha egalariga ko'rsatganda u bir necha oydan beri ishlab
turganday ko'rinsin — diagrammalar to'lgan, to'lovlar va qarzlar bor, davomat
belgilangan, kunlik hisobotlar yozilgan.

Ma'lumot **API orqali** kiritiladi (to'g'ridan-to'g'ri SQL emas), shuning uchun
barcha biznes qoidalari ishlaydi: hisob-faktura summasi guruhning `monthly_fee`
sidan hisoblanadi, to'lov invoice'ga taqsimlanadi va holati (`PARTIALLY_PAID`,
`PAID`) o'zi yangilanadi, ovqat berilganda ombordan mahsulot yechiladi.

Skript **qayta ishga tushirilsa xavfsiz**: mavjud yozuvni ikkilantirmaydi
(hisob-faktura generatsiyasi idempotent, davomat esa `upsert`).

Hammasini o'chirish uchun: `python scripts/demo_reset.py`

Ishga tushirish:
    cd backend && .venv/Scripts/python.exe ../scripts/demo_seed.py
"""

from __future__ import annotations

import asyncio
import calendar
import os
import random
import sys
from datetime import date, datetime, time, timedelta

import httpx

BASE = os.environ.get("KIDSFLOW_API", "http://localhost:8000/api/v1")
LOGIN = os.environ.get("KIDSFLOW_LOGIN", "quvonchbek")
PASSWORD = os.environ.get("KIDSFLOW_PASSWORD", "KidsFlow2026!")

# Takrorlanadigan natija — skript qayta ishga tushirilsa bir xil "hikoya" chiqadi.
random.seed(20260910)

TODAY = date.today()


def working_days(start: date, end: date) -> list[date]:
    """Dam olish kunlarisiz sanalar (bog'cha shanba-yakshanba ishlamaydi)."""
    days = []
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            days.append(cur)
        cur += timedelta(days=1)
    return days


def month_start(d: date) -> date:
    return d.replace(day=1)


def add_months(d: date, months: int) -> date:
    """Oyni siljitish (kun 1 bo'lgani uchun oy oxiri muammosi yo'q)."""
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


class Api:
    def __init__(self, client: httpx.AsyncClient, token: str) -> None:
        self._c = client
        self._h = {"Authorization": f"Bearer {token}"}

    async def get(self, path: str) -> object:
        r = await self._c.get(path, headers=self._h)
        r.raise_for_status()
        return r.json()

    async def post(self, path: str, body: dict) -> httpx.Response:
        return await self._c.post(path, headers=self._h, json=body)


# Ikkinchi filial uchun guruh va bolalar — namoyishda filial almashtirilganda
# bo'sh sahifa chiqmasligi uchun. Ismlar o'zbekcha va takrorlanmaydigan.
FAMILIES = [
    ("Tursunov", "Jasur", "Nodira"),
    ("Qodirov", "Aziza", "Malika"),
    ("Yusupova", "Diyor", "Zilola"),
    ("Ergashev", "Sevinch", "Dilnoza"),
    ("Xolmatov", "Omina", "Gulnora"),
    ("Sattorov", "Bekzod", "Shahnoza"),
    ("Nazarova", "Laylo", "Munisa"),
    ("Rahimov", "Doston", "Feruza"),
    ("Islomova", "Robiya", "Nilufar"),
    ("Umarov", "Asadbek", "Ozoda"),
    ("Karimov", "Shohruh", "Kamola"),
    ("Mahmudov", "Iroda", "Sitora"),
]
GROUP_PLAN = [
    ("Bodomcha", 24, 42, 1_500_000),
    ("Lolajon", 42, 60, 1_700_000),
]


async def seed_branch_basics(api: Api, branch_id: str) -> tuple[int, int]:
    """Filialda guruh yoki bola bo'lmasa — asosini yaratadi.

    Faqat BO'SH filial uchun. To'ldirilgan filialga tegmaydi.
    """
    groups = await api.get(f"/groups?branch_id={branch_id}")
    if groups:  # type: ignore[union-attr]
        return 0, 0

    group_ids = []
    for name, min_m, max_m, fee in GROUP_PLAN:
        r = await api.post(
            "/groups",
            {
                "branch_id": branch_id,
                "name": name,
                "min_age_months": min_m,
                "max_age_months": max_m,
                "capacity": 18,
                "monthly_fee": str(fee),
            },
        )
        if r.status_code < 400:
            group_ids.append(r.json()["id"])
        else:
            print(f"    guruh '{name}' xatosi: {r.status_code} {r.text[:140]}")
    if not group_ids:
        return 0, 0

    made = 0
    for i, (surname, child_name, parent_name) in enumerate(FAMILIES):
        birth = date(
            TODAY.year - random.randint(3, 6),
            random.randint(1, 12),
            random.randint(1, 28),
        )
        r = await api.post(
            "/children",
            {"full_name": f"{surname} {child_name}", "birth_date": birth.isoformat()},
        )
        if r.status_code >= 400:
            continue
        child_id = r.json()["id"]
        await api.post(
            f"/children/{child_id}/enrollments",
            {
                "branch_id": branch_id,
                "group_id": group_ids[i % len(group_ids)],
                # Ro'yxatga olish sanasi — o'tgan oy boshidan, ya'ni bola
                # bir necha oydan beri qatnayotgandek ko'rinadi.
                "start_date": add_months(month_start(TODAY), -5).isoformat(),
                "status": "ACTIVE",
            },
        )
        await api.post(
            f"/children/{child_id}/guardians",
            {
                "full_name": f"{surname} {parent_name}",
                "phone": f"+9989{random.randint(10000000, 99999999)}",
                "relationship_type": "MOTHER",
                "receives_notifications": True,
            },
        )
        made += 1
    return len(group_ids), made


async def seed_invoices(api: Api, branch_id: str, period: date) -> int:
    """Oylik hisob-fakturalarni yaratadi (endpoint idempotent)."""
    r = await api.post(
        "/invoices/generate",
        {
            "branch_id": branch_id,
            "billing_period": period.isoformat(),
            "due_day": 10,
        },
    )
    if r.status_code >= 400:
        print(
            f"    hisob-faktura ({period:%Y-%m}) xato: {r.status_code} {r.text[:120]}"
        )
        return 0
    data = r.json()
    return int(data.get("created_count", data.get("created", 0)) or 0)


async def seed_payments(api: Api, branch_id: str, period: date) -> int:
    """To'lovlar — hammasi emas, realistik intizom bilan.

    ~65% to'liq to'laydi, ~20% qisman, ~15% umuman to'lamaydi. Shu tufayli
    Boshqaruv panelidagi "Qarz" va "To'lov kechikishi" bloklari bo'sh qolmaydi.
    """
    invoices = await api.get(
        f"/invoices?branch_id={branch_id}&billing_period={period.isoformat()}"
    )
    # Bu oy allaqachon to'ldirilganmi: bironta hisob-faktura OPEN dan boshqa
    # holatda bo'lsa, to'lovlar kiritilgan. Busiz skript har ishga tushganda
    # yana to'lov qo'shib, "qarzdorlar" hikoyasini yemirardi.
    if any(inv["status"] != "OPEN" for inv in invoices):  # type: ignore[union-attr]
        return -1
    count = 0
    for inv in invoices:  # type: ignore[union-attr]
        outstanding = float(inv["outstanding_amount"])
        # Faqat hali to'lov tegmagan hisob-fakturalar. Busiz skript qayta
        # ishga tushirilganda har safar yangi qisman to'lov qo'shilardi
        # (summa tasodifiy bo'lgani uchun idempotentlik kaliti ham har xil).
        if outstanding <= 0 or inv["status"] != "OPEN":
            continue
        roll = random.random()
        if roll < 0.15:
            continue  # to'lamagan — qarz bo'lib qoladi
        amount = (
            outstanding
            if roll < 0.80
            else round(outstanding * random.uniform(0.3, 0.7))
        )
        if amount <= 0:
            continue
        # To'lov sanasi — oy ichida tasodifiy ish kuni, lekin bugundan keyin emas.
        last = min(add_months(period, 1) - timedelta(days=1), TODAY)
        days = working_days(period, last)
        if not days:
            continue
        paid_on = random.choice(days)
        paid_at = datetime.combine(
            paid_on, time(random.randint(9, 17), random.choice((0, 15, 30, 45)))
        )
        r = await api.post(
            "/payments",
            {
                "child_id": inv["child_id"],
                "amount": str(amount),
                "payment_method": random.choice(["CASH", "CARD", "TERMINAL", "BANK"]),
                "paid_at": paid_at.isoformat(),
                # Idempotentlik: skript qayta ishlatilsa dublikat bo'lmaydi.
                "idempotency_key": f"demo-{inv['id']}-{int(amount)}",
            },
        )
        if r.status_code < 400:
            count += 1
        elif count == 0:
            # Birinchi xatoni ko'rsatamiz — jim qolib ketmasin.
            print(f"    to'lov xatosi: {r.status_code} {r.text[:160]}")
    return count


async def seed_attendance(api: Api, groups: list[dict], start: date, end: date) -> int:
    """Davomat — har ish kuni uchun guruh bo'yicha.

    ~88% keldi, qolgani kasal/kelmadi/kechikdi. Real bog'chada davomat 100%
    bo'lmaydi, shuning uchun diagramma tekis chiziq bo'lib qolmaydi.
    """
    marked = 0
    days = working_days(start, end)
    if not days:
        return 0
    for group in groups:
        # Qorovul OXIRGI ISH KUNI bo'yicha tekshiriladi: oy oxiri dam olish
        # kuniga to'g'ri kelsa u yerda hech qachon davomat bo'lmaydi va
        # qorovul har safar o'tib ketardi (holatlar qayta tasodifiylanardi).
        roster = await api.get(
            f"/attendance/roster?group_id={group['id']}&date={days[-1].isoformat()}"
        )
        child_ids = [row["child_id"] for row in roster]  # type: ignore[union-attr]
        if not child_ids:
            continue
        if any(row.get("status") for row in roster):  # type: ignore[union-attr]
            continue
        for day in days:
            entries = []
            for child_id in child_ids:
                roll = random.random()
                if roll < 0.88:
                    status = "PRESENT"
                elif roll < 0.93:
                    status = "SICK"
                elif roll < 0.97:
                    status = "ABSENT"
                else:
                    status = "LATE"
                entries.append({"child_id": child_id, "status": status})
            r = await api.post(
                "/attendance/bulk",
                {
                    "group_id": group["id"],
                    "attendance_date": day.isoformat(),
                    "entries": entries,
                },
            )
            if r.status_code < 400:
                marked += len(entries)
    return marked


# Oylik xarajatlar — mavjud oylardagi (mart–avgust) naqsh bilan bir xil:
# har kategoriyadan bittadan, taxminan o'sha summalarda. Shu tufayli
# "Daromad va xarajat" diagrammasidagi joriy oy ustuni boshqa oylardan
# keskin farq qilib turmaydi.
EXPENSE_TEMPLATE = [
    ("Ijara", 8_000_000, "Chilonzor Mulk", True),
    ("Oziq-ovqat", 8_000_000, "Anhor Savdo", False),
    ("Kommunal xizmat", 2_600_000, "Hududgaz", False),
    ("Soliq", 1_750_000, "Soliq qomitasi", False),
    ("Transport", 720_000, "Tez Yuk", False),
    ("Ta'mirlash", 470_000, "Usta Servis", False),
    ("Jihoz", 410_000, "Bolajon Savdo", False),
]


async def seed_expenses(api: Api, branch_id: str, period: date) -> int:
    """Joriy oy xarajatlari — kategoriya bo'yicha bittadan.

    Allaqachon kiritilgan kategoriya qayta yozilmaydi (skript qayta ishga
    tushirilsa dublikat bo'lmasin).
    """
    categories = {c["name"]: c["id"] for c in await api.get("/expense-categories")}  # type: ignore[union-attr]
    last = min(add_months(period, 1) - timedelta(days=1), TODAY)
    existing = await api.get(
        f"/expenses?branch_id={branch_id}"
        f"&period_start={period.isoformat()}&period_end={last.isoformat()}"
    )
    already = {e["category_id"] for e in existing}  # type: ignore[union-attr]

    created = 0
    for name, base, vendor, recurring in EXPENSE_TEMPLATE:
        if name not in categories or categories[name] in already:
            continue
        # ±8% tebranish — har oy bir xil raqam turmasin.
        amount = int(base * random.uniform(0.92, 1.08))
        days = working_days(period, last)
        if not days:
            continue
        r = await api.post(
            "/expenses",
            {
                "branch_id": branch_id,
                "category_id": categories[name],
                "amount": str(amount),
                "expense_date": random.choice(days).isoformat(),
                "vendor": vendor,
                "is_recurring": recurring,
            },
        )
        if r.status_code < 400:
            created += 1
        elif created == 0:
            print(f"    xarajat xatosi: {r.status_code} {r.text[:160]}")
    return created


ACTIVITIES = [
    "Ertalabki mashq, so'ng rasm chizdik.",
    "Harflar bilan tanishdik va qo'shiq aytdik.",
    "Konstruktordan uy qurdik, keyin hovlida o'ynadik.",
    "Sanoqni mashq qildik, plastilindan hayvonlar yasadik.",
    "Ertak tingladik va uni rollar bo'yicha o'ynadik.",
]
NOTES = [
    "Kayfiyati yaxshi, ishtaha joyida.",
    "Bugun juda faol edi.",
    "Tushlikdan keyin yaxshi uxladi.",
    "Do'stlari bilan yaxshi o'ynadi.",
    "Biroz charchagan, lekin xursand.",
]


async def seed_daily_reports(api: Api, groups: list[dict], days_back: int) -> int:
    """Kunlik hisobotlar — oxirgi N ish kuni uchun, e'lon qilingan holatda."""
    created = 0
    end = TODAY
    start = TODAY - timedelta(days=days_back)
    for group in groups:
        roster = await api.get(
            f"/attendance/roster?group_id={group['id']}&date={end.isoformat()}"
        )
        child_ids = [row["child_id"] for row in roster]  # type: ignore[union-attr]
        # Guruh uchun bu davr allaqachon to'ldirilganmi — oxirgi ish kunini
        # tekshirish kifoya (skript butun davrni birdan to'ldiradi).
        probe_days = working_days(start, end)
        if not probe_days:
            continue
        probe = await api.get(
            f"/daily-reports/roster?group_id={group['id']}"
            f"&date={probe_days[-1].isoformat()}"
        )
        if any(row.get("report") for row in probe):  # type: ignore[union-attr]
            continue

        for day in probe_days:
            for child_id in child_ids:
                # Har bolaga har kuni emas — real bog'chada ham shunday.
                if random.random() > 0.55:
                    continue
                r = await api.post(
                    "/daily-reports",
                    {
                        "child_id": child_id,
                        "report_date": day.isoformat(),
                        "meal_status": random.choice(
                            ["ATE_WELL", "ATE_WELL", "ATE_SOME"]
                        ),
                        "nap_minutes": random.choice([60, 75, 90, 105, 120]),
                        "mood": random.choice(["HAPPY", "HAPPY", "CALM", "TIRED"]),
                        "activities_text": random.choice(ACTIVITIES),
                        "teacher_note": random.choice(NOTES),
                    },
                )
                if r.status_code >= 400:
                    continue
                report_id = r.json()["id"]
                # E'lon qilingan hisobot ota-onaga ko'rinadi va Telegramga ketadi.
                await api.post(f"/daily-reports/{report_id}/publish", {})
                created += 1
    return created


PRODUCTS = [
    ("Guruch", "kg", 14000),
    ("Kartoshka", "kg", 6000),
    ("Sabzi", "kg", 5000),
    ("Piyoz", "kg", 4500),
    ("Go'sht (mol)", "kg", 95000),
    ("Tovuq go'shti", "kg", 42000),
    ("Sut", "l", 12000),
    ("Tuxum", "dona", 1400),
    ("Un", "kg", 8000),
    ("Yog'", "l", 24000),
    ("Makaron", "kg", 11000),
    ("Olma", "kg", 15000),
]

MEALS = [
    (
        "Palov",
        "Guruch, go'sht, sabzi va piyozdan tayyorlangan.",
        [("Guruch", 4), ("Go'sht (mol)", 2), ("Sabzi", 2), ("Piyoz", 1), ("Yog'", 1)],
    ),
    (
        "Mastava",
        "Guruchli sho'rva.",
        [("Guruch", 2), ("Go'sht (mol)", 1), ("Kartoshka", 2), ("Sabzi", 1)],
    ),
    (
        "Makaron va tovuq",
        "Tovuq go'shti bilan makaron.",
        [("Makaron", 3), ("Tovuq go'shti", 2), ("Yog'", 1)],
    ),
    ("Sutli bo'tqa", "Ertalabki bo'tqa.", [("Guruch", 2), ("Sut", 4), ("Yog'", 1)]),
    (
        "Kartoshkali qovurma",
        "Kartoshka va go'sht.",
        [("Kartoshka", 4), ("Go'sht (mol)", 1), ("Piyoz", 1), ("Yog'", 1)],
    ),
]


async def seed_food(api: Api, branch_id: str, days_back: int) -> tuple[int, int, int]:
    """Ombor mahsulotlari, retseptlar va ovqat berilgan kunlar."""
    existing = {p["name"] for p in await api.get(f"/food/products?branch_id={branch_id}")}  # type: ignore[union-attr]
    product_ids: dict[str, str] = {}
    for name, unit, cost in PRODUCTS:
        if name in existing:
            continue
        r = await api.post(
            "/food/products",
            {
                "branch_id": branch_id,
                "name": name,
                "unit": unit,
                "unit_cost": str(cost),
            },
        )
        if r.status_code < 400:
            product_ids[name] = r.json()["id"]
    # Mavjudlarini ham olamiz (skript qayta ishlatilgan bo'lsa)
    for p in await api.get(f"/food/products?branch_id={branch_id}"):  # type: ignore[union-attr]
        product_ids[p["name"]] = p["id"]

    # Ombor kirimi — ovqat berilganda qoldiq manfiy bo'lib qolmasin.
    stocked = 0
    for name, pid in product_ids.items():
        cost = next((c for n, _, c in PRODUCTS if n == name), 10000)
        r = await api.post(
            "/food/stock-movements",
            {
                "product_id": pid,
                "movement_type": "IN",
                "quantity": "400",
                "reason": "PURCHASE",
                "unit_cost": str(cost),
                "occurred_at": (TODAY - timedelta(days=days_back + 2)).isoformat(),
            },
        )
        if r.status_code < 400:
            stocked += 1

    existing_meals = {m["name"] for m in await api.get(f"/food/meals?branch_id={branch_id}")}  # type: ignore[union-attr]
    meal_ids: dict[str, str] = {}
    for name, desc, ingredients in MEALS:
        if name in existing_meals:
            continue
        r = await api.post(
            "/food/meals",
            {
                "branch_id": branch_id,
                "name": name,
                "description": desc,
                "ingredients": [
                    {"product_id": product_ids[n], "quantity_per_serving": str(q)}
                    for n, q in ingredients
                    if n in product_ids
                ],
            },
        )
        if r.status_code < 400:
            meal_ids[name] = r.json()["id"]
        else:
            print(f"    ovqat '{name}' xatosi: {r.status_code} {r.text[:160]}")
    for m in await api.get(f"/food/meals?branch_id={branch_id}"):  # type: ignore[union-attr]
        meal_ids[m["name"]] = m["id"]

    logged = 0
    if not meal_ids:
        return len(product_ids), 0, 0
    start = TODAY - timedelta(days=days_back)

    # Ovqat qaydlarini o'qiydigan endpoint yo'q, lekin ular ombordan mahsulot
    # yechadi — shuning uchun davr bo'yicha chiqim bo'lgan-bo'lmagani belgi
    # sifatida ishlatiladi. Chiqim bor bo'lsa, bu davr allaqachon to'ldirilgan.
    report = await api.get(
        f"/food/stock-report?branch_id={branch_id}"
        f"&period_start={start.isoformat()}&period_end={TODAY.isoformat()}"
    )
    already_served = any(
        float(row.get("stock_out") or 0) > 0
        for row in report.get("rows", [])  # type: ignore[union-attr]
    )
    if already_served:
        return len(product_ids), len(meal_ids), 0

    for day in working_days(start, TODAY):
        name = random.choice(list(meal_ids))
        r = await api.post(
            "/food/meal-logs",
            {
                "meal_id": meal_ids[name],
                "serving_date": day.isoformat(),
                "servings_count": random.randint(30, 40),
            },
        )
        if r.status_code < 400:
            logged += 1
    return len(product_ids), len(meal_ids), logged


QUESTIONS = [
    "Assalomu alaykum! Ertaga bog'cha ishlaydimi?",
    "Farzandim bugun biroz shamollagan, iltimos e'tibor bering.",
    "To'lovni karta orqali qilsam bo'ladimi?",
    "Ertaga tug'ilgan kun qilmoqchimiz, ruxsat bo'ladimi?",
]
ANSWERS = [
    "Va alaykum assalom! Ha, ertaga odatdagidek ishlaymiz.",
    "Albatta, tarbiyachiga aytdik. Xavotir olmang.",
    "Ha, karta orqali ham qabul qilamiz.",
    "Ruxsat, faqat oldindan tarbiyachi bilan kelishib oling.",
]


async def seed_messages(
    api: Api, client: httpx.AsyncClient, branch_id: str, bot_token: str
) -> int:
    """Bir nechta ota-onani Telegramga "ulab", savol-javob yozishmasi yaratadi.

    Yangi Xabarlar bo'limi ko'rsatilganda bo'sh turmasligi uchun.
    """
    # Allaqachon yozishma bor bo'lsa qayta yaratilmaydi.
    threads = await api.get(f"/messages/threads?branch_id={branch_id}")
    if threads:  # type: ignore[union-attr]
        return -1
    parents = await api.get(f"/children/parents?branch_id={branch_id}")
    if not parents:  # type: ignore[union-attr]
        return 0
    bh = {"X-Bot-Token": bot_token}
    made = 0
    for i, parent in enumerate(parents[:4]):  # type: ignore[index]
        tg_id = 900_100 + i
        code_res = await api.post("/telegram/invitations", {"user_id": parent["id"]})
        if code_res.status_code >= 400:
            continue
        link = await client.post(
            "/telegram/link",
            headers=bh,
            json={
                "code": code_res.json()["code"],
                "telegram_user_id": tg_id,
                "telegram_chat_id": tg_id,
            },
        )
        if link.status_code >= 400:
            continue
        session = await client.post(
            "/telegram/session", headers=bh, json={"telegram_user_id": tg_id}
        )
        parent_token = session.json()["access_token"]
        sent = await client.post(
            "/messages/from-parent",
            headers={"Authorization": f"Bearer {parent_token}"},
            json={"text": QUESTIONS[i % len(QUESTIONS)]},
        )
        if sent.status_code >= 400:
            continue
        made += 1
        # Bittasi javobsiz qoladi — qo'ng'iroqchada "yangi savol" ko'rinsin.
        if i < len(parents[:4]) - 1:  # type: ignore[index]
            await api.post(
                f"/messages/threads/{parent['id']}/reply?branch_id={branch_id}",
                {"text": ANSWERS[i % len(ANSWERS)]},
            )
    return made


async def main() -> None:
    bot_token = os.environ.get("BOT_API_TOKEN", "")
    async with httpx.AsyncClient(base_url=BASE, timeout=120.0) as client:
        login = await client.post(
            "/auth/login", json={"login": LOGIN, "password": PASSWORD}
        )
        if login.status_code >= 400:
            print(f"Kirish muvaffaqiyatsiz: {login.status_code} {login.text[:200]}")
            sys.exit(1)
        api = Api(client, login.json()["access_token"])

        branches = await api.get("/branches")
        print(f"Filiallar: {[b['name'] for b in branches]}")  # type: ignore[union-attr]

        for branch in branches:  # type: ignore[union-attr]
            bid = branch["id"]
            print(f"\n=== {branch['name']} ===")
            new_groups, new_children = await seed_branch_basics(api, bid)
            if new_groups:
                print(f"  asos: {new_groups} guruh, {new_children} bola yaratildi")

            groups = await api.get(f"/groups?branch_id={bid}")
            groups = [g for g in groups if g["is_active"]]  # type: ignore[union-attr]
            if not groups:
                print("  guruh yo'q — o'tkazib yuborildi")
                continue

            # 1-4) Oylik ma'lumot — oxirgi 6 oy. Har bosqichda "allaqachon
            # to'ldirilgan" qorovuli bor, shuning uchun to'la filialga
            # (masalan filial-1 ning mart-avgusti) qayta tegilmaydi.
            inv_total = pay_total = exp_total = att_total = 0
            for back in range(5, -1, -1):
                period = add_months(month_start(TODAY), -back)
                period_end = min(add_months(period, 1) - timedelta(days=1), TODAY)

                inv_total += await seed_invoices(api, bid, period)
                paid = await seed_payments(api, bid, period)
                pay_total += max(paid, 0)
                exp_total += await seed_expenses(api, bid, period)
                att_total += await seed_attendance(api, groups, period, period_end)

            print(f"  hisob-faktura: {inv_total} ta yaratildi")
            print(f"  to'lovlar: {pay_total} ta")
            print(f"  xarajatlar: {exp_total} ta")
            print(f"  davomat: {att_total} ta belgi")

            # 5) Kunlik hisobotlar (oxirgi 45 kun)
            reports = await seed_daily_reports(api, groups, days_back=45)
            print(f"  kunlik hisobot: {reports} ta e'lon qilindi")

            # 6) Oziq-ovqat
            products, meals, logs = await seed_food(api, bid, days_back=45)
            print(
                f"  oziq-ovqat: {products} mahsulot, {meals} ovqat, {logs} kunlik qayd"
            )

            # 7) Bot yozishmalari (faqat birinchi filialda)
            if bot_token and branch is branches[0]:  # type: ignore[index]
                msgs = await seed_messages(api, client, bid, bot_token)
                print(
                    "  bot yozishmalari: allaqachon bor"
                    if msgs < 0
                    else f"  bot yozishmalari: {msgs} ta suhbat"
                )
            elif not bot_token:
                print("  bot yozishmalari: BOT_API_TOKEN berilmadi — o'tkazildi")

    print("\nTayyor. O'chirish uchun: python scripts/demo_reset.py")


if __name__ == "__main__":
    asyncio.run(main())
