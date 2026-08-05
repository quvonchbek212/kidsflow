"""Excel/CSV orqali bolalarni ommaviy import qilish (7-bosqich B).

Ustun sarlavhalari qattiq belgilanmagan — moslashuvchan (fuzzy) tarzda uz/ru/en
variantlarini tanib oladi. Har bir qator alohida baholanadi: bitta qatordagi
xato boshqa qatorlarni to'xtatmaydi (`dry_run=True` bilan avval ko'rib chiqish
mumkin, keyin `dry_run=False` bilan haqiqiy import bajariladi).
"""

from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import date, datetime

import openpyxl
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PermissionDeniedError
from app.core.permissions import CurrentUser
from app.models.enums import EnrollmentStatus, GuardianRelationship
from app.schemas.child import (
    ChildCreateRequest,
    GuardianCreateRequest,
    ImportPreviewRow,
    ImportResultResponse,
)
from app.schemas.enrollment import EnrollmentCreateRequest
from app.services.access_service import AccessService
from app.services.child_service import ChildService
from app.services.enrollment_service import EnrollmentService
from app.utils.phone import InvalidPhoneError, normalize_phone

_DATE_FORMATS = ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y")

_BIRTH_DATE_KEYWORDS = ("tugilgan", "birth", "рожд", "dob")
_PHONE_KEYWORDS = ("phone", "tel", "тел")
_GUARDIAN_KEYWORDS = ("ota", "ona", "vasiy", "parent", "guardian", "родит")
_NAME_KEYWORDS = ("fio", "ism", "name", "имя", "фио")


def _normalize_header(raw: str) -> str:
    return re.sub(r"[^a-z0-9а-яё]", "", raw.strip().lower())


def _classify_header(raw: str) -> str | None:
    """Ustun sarlavhasini kanonik maydonga moslaydi (fuzzy heuristika)."""
    norm = _normalize_header(raw)
    if any(keyword in norm for keyword in _BIRTH_DATE_KEYWORDS):
        return "birth_date"
    if any(keyword in norm for keyword in _PHONE_KEYWORDS):
        return "guardian_phone"
    if any(keyword in norm for keyword in _GUARDIAN_KEYWORDS):
        return "guardian_name"
    if any(keyword in norm for keyword in _NAME_KEYWORDS):
        return "full_name"
    return None


def _parse_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
    return None


def _read_rows(content: bytes, filename: str) -> tuple[list[str], list[list[object]]]:
    if filename.lower().endswith((".xlsx", ".xlsm")):
        workbook = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        sheet = workbook.active
        raw_rows = list(sheet.iter_rows(values_only=True)) if sheet else []
    else:
        text = content.decode("utf-8-sig")
        raw_rows = list(csv.reader(io.StringIO(text)))

    if not raw_rows:
        return [], []

    header = [str(cell) if cell is not None else "" for cell in raw_rows[0]]
    data_rows = [
        list(row) for row in raw_rows[1:] if any(cell not in (None, "") for cell in row)
    ]
    return header, data_rows


class ImportService:
    def __init__(self, session: AsyncSession) -> None:
        self._access = AccessService(session)
        self._children = ChildService(session)
        self._enrollments = EnrollmentService(session)

    def _build_rows(self, content: bytes, filename: str) -> list[ImportPreviewRow]:
        header, data_rows = _read_rows(content, filename)
        column_map: dict[int, str] = {}
        for idx, raw in enumerate(header):
            kind = _classify_header(raw)
            if kind:
                column_map[idx] = kind

        rows: list[ImportPreviewRow] = []
        for row_number, raw_row in enumerate(data_rows, start=2):
            values: dict[str, object] = {}
            for idx, kind in column_map.items():
                if idx < len(raw_row):
                    values[kind] = raw_row[idx]

            errors: list[str] = []

            full_name = str(values.get("full_name") or "").strip() or None
            if not full_name:
                errors.append("Ism ko'rsatilmagan.")

            raw_birth = values.get("birth_date")
            birth_date = _parse_date(raw_birth) if raw_birth not in (None, "") else None
            if raw_birth not in (None, "") and birth_date is None:
                errors.append("Tug'ilgan sana formatini aniqlab bo'lmadi.")
            elif birth_date is None:
                errors.append("Tug'ilgan sana ko'rsatilmagan.")
            elif birth_date > date.today():
                errors.append("Tug'ilgan sana kelajakda bo'lishi mumkin emas.")
                birth_date = None

            guardian_name = str(values.get("guardian_name") or "").strip() or None
            raw_phone = values.get("guardian_phone")
            guardian_phone: str | None = None
            if raw_phone not in (None, ""):
                try:
                    guardian_phone = normalize_phone(str(raw_phone).strip())
                except InvalidPhoneError:
                    guardian_phone = None  # noto'g'ri format — vasiy import qilinmaydi

            rows.append(
                ImportPreviewRow(
                    row_number=row_number,
                    full_name=full_name,
                    birth_date=birth_date.isoformat() if birth_date else None,
                    guardian_name=guardian_name,
                    guardian_phone=guardian_phone,
                    errors=errors,
                    valid=len(errors) == 0,
                )
            )
        return rows

    async def run(
        self,
        content: bytes,
        filename: str,
        branch_id: uuid.UUID,
        group_id: uuid.UUID,
        dry_run: bool,
        current_user: CurrentUser,
    ) -> ImportResultResponse:
        if not self._access.can_manage_branch(current_user, branch_id):
            raise PermissionDeniedError("Bu filialga bola import qilish huquqi yo'q.")

        rows = self._build_rows(content, filename)
        valid_rows = [row for row in rows if row.valid]
        imported = 0

        if not dry_run:
            for row in valid_rows:
                assert row.full_name is not None
                assert row.birth_date is not None
                child = await self._children.create(
                    ChildCreateRequest(
                        full_name=row.full_name,
                        birth_date=date.fromisoformat(row.birth_date),
                    ),
                    current_user,
                )
                await self._enrollments.create(
                    child.id,
                    EnrollmentCreateRequest(
                        branch_id=branch_id,
                        group_id=group_id,
                        start_date=date.today(),
                        status=EnrollmentStatus.ACTIVE,
                    ),
                    current_user,
                )
                if row.guardian_name and row.guardian_phone:
                    await self._children.add_guardian(
                        child.id,
                        GuardianCreateRequest(
                            full_name=row.guardian_name,
                            phone=row.guardian_phone,
                            relationship_type=GuardianRelationship.OTHER,
                        ),
                        current_user,
                    )
                imported += 1

        return ImportResultResponse(
            dry_run=dry_run,
            total_rows=len(rows),
            valid_rows=len(valid_rows),
            imported=imported,
            rows=rows,
        )
