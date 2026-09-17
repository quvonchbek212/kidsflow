"""KIDSFLOW — namuna ma'lumotni tozalash (real bog'chaga topshirishdan oldin).

Namoyish uchun kiritilgan hamma narsani o'chiradi va tizimni yangi bog'cha
ma'lumotini kiritishga tayyor holatga keltiradi.

O'CHIRILADI: bolalar, vasiylar, ro'yxatga olishlar, davomat, kunlik hisobotlar,
hisob-fakturalar, to'lovlar, xarajatlar, ish haqi, oziq-ovqat (mahsulot, ovqat,
ombor), ota-ona yozishmalari, bildirishnomalar, egadan boshqa barcha
xodimlar va audit jurnali.

SAQLANADI: egasi (siz kirasiz), bog'cha sozlamalari, filiallar, guruhlar,
xarajat kategoriyalari va tarif rejalari — bular yangi bog'cha uchun ham
asos bo'ladi (nomlarini interfeysdan o'zgartirasiz).

Sukut bo'yicha HECH NARSA o'chirilmaydi — faqat nima o'chishi ko'rsatiladi.
Haqiqatan o'chirish uchun `--yes` bering:

    python scripts/demo_reset.py           # faqat ko'rsatadi
    python scripts/demo_reset.py --yes     # o'chiradi
"""

from __future__ import annotations

import subprocess
import sys

# Tartib muhim: chet kalitlar sababli avval bolalar (bog'liq) jadval o'chadi.
# Ko'pchiligida CASCADE bor, lekin tartib aniq bo'lgani ma'qul.
TABLES = [
    # Xabar yuborish
    "parent_messages",
    "notifications",
    "outbox_events",
    "daily_job_runs",
    "telegram_invitations",
    # Oziq-ovqat
    "meal_logs",
    "meal_ingredients",
    "meals",
    "food_stock_movements",
    "food_products",
    # Moliya
    "payment_allocations",
    "payment_transactions",
    "invoice_adjustments",
    "invoices",
    "expenses",
    "salary_advances",
    "payroll_runs",
    # Bog'cha kunlik faoliyati
    "daily_report_files",
    "daily_reports",
    "attendance",
    "enrollments",
    "child_guardians",
    "children",
    # Fayllar va jurnal
    "files",
    "audit_logs",
    "ai_usage_logs",
    "knowledge_documents",
]

# Egadan boshqa foydalanuvchilar. OWNER roli `user_role_assignments` da.
DELETE_NON_OWNER_USERS = """
DELETE FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM user_role_assignments r
     WHERE r.user_id = u.id AND r.role = 'OWNER'
)
"""


def psql(sql: str) -> str:
    """SQL ni backend konteyneridagi postgres orqali bajaradi."""
    result = subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "kidsflow",
            "-d",
            "kidsflow",
            "-A",
            "-t",
            "-c",
            sql,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"XATO: {result.stderr.strip()[:300]}")
        sys.exit(1)
    return result.stdout.strip()


def main() -> None:
    apply = "--yes" in sys.argv

    print("Hozirgi ma'lumot:\n")
    counts = {}
    for table in TABLES:
        raw = psql(f"SELECT count(*) FROM {table}")
        # Jadval mavjud bo'lmasa (eski baza) — o'tkazib yuboramiz.
        counts[table] = int(raw) if raw.isdigit() else 0
    non_owner = int(
        psql(
            f"SELECT count(*) FROM ({DELETE_NON_OWNER_USERS.replace('DELETE FROM users u', 'SELECT 1 FROM users u')}) x"
        )
    )

    total = 0
    for table, n in counts.items():
        if n:
            print(f"  {table:26} {n:>7}")
            total += n
    print(f"  {'egadan boshqa xodimlar':26} {non_owner:>7}")
    total += non_owner
    print(f"\n  JAMI: {total} yozuv")

    if not apply:
        print(
            "\nHech narsa o'chirilmadi (bu faqat ko'rsatish).\n"
            "Haqiqatan o'chirish uchun: python scripts/demo_reset.py --yes"
        )
        return

    print("\nO'chirilmoqda...")
    # Bitta tranzaksiyada — yarim o'chirilgan holat qolmasin.
    statements = [f"DELETE FROM {t}" for t in TABLES] + [DELETE_NON_OWNER_USERS]
    psql("BEGIN; " + "; ".join(statements) + "; COMMIT;")

    print("Tozalandi. Qolgani:")
    print(f"  filiallar:  {psql('SELECT count(*) FROM branches')}")
    print(f"  guruhlar:   {psql('SELECT count(*) FROM groups')}")
    print(f"  foydalanuvchilar: {psql('SELECT count(*) FROM users')}")
    print(f"  bog'cha nomi: {psql('SELECT name FROM kindergarten_settings')}")
    print(
        "\nEndi real bog'cha ma'lumotini kiritishingiz mumkin:\n"
        "  Sozlamalar → bog'cha nomi va filiallar\n"
        "  Guruhlar → guruh nomlari va tariflar\n"
        "  Xodimlar → xodim qo'shish\n"
        "  Bolalar → bola qo'shish (yoki Excel'dan import)"
    )


if __name__ == "__main__":
    main()
