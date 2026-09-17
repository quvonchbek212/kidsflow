"use client";

import { useRouter, useSearchParams } from "next/navigation";
import {
  Suspense,
  useEffect,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";

import { useAppUI } from "@/components/AppShell";
import { IconUpload, IconUsers } from "@/components/icons";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import {
  LoadError,
  logSecondaryFailure,
} from "@/components/ui/LoadError";
import { useConfirm } from "@/components/ui/useConfirm";
import { useModal } from "@/components/ui/ModalProvider";
import { useToast } from "@/components/ui/ToastProvider";
import {
  ApiError,
  api,
  type Child,
  type ChildStatus,
  type DiscountType,
  type Group,
  type ImportResult,
} from "@/lib/api";
import type { AppStrings } from "@/lib/app-i18n";
import {
  initials,
  isoDate,
  moneyPlain,
  monthRange,
  relationLabel,
} from "@/lib/format";

export default function ChildrenPage(): ReactNode {
  return (
    <Suspense fallback={null}>
      <ChildrenContent />
    </Suspense>
  );
}

function ChildrenContent(): ReactNode {
  const { t, branchId, setPageMeta, can } = useAppUI();
  // Tarbiyachi o'z guruhidagi bolalarni ko'radi, lekin yangi bola qo'shmaydi
  // va ro'yxat import qilmaydi — bu menejer/egasining ishi.
  const canManage = can("children.manage");

  useEffect(() => {
    setPageMeta({ title: t.children.title, subtitle: t.children.subtitle });
  }, [setPageMeta, t]);
  const modal = useModal();
  const toast = useToast();
  const confirm = useConfirm();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [children, setChildren] = useState<Child[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  // Mockupdagi "Telefon" va "Qarz" ustunlari uchun: telefon ota-onalar
  // ro'yxatidan, qarz esa joriy oy hisob-fakturalaridan yig'iladi.
  const [parentPhones, setParentPhones] = useState<Record<string, string>>({});
  const [childDebt, setChildDebt] = useState<Record<string, number>>({});
  const [ready, setReady] = useState(false);
  const [loadError, setLoadError] = useState<unknown>(null);

  // Faol yoki navbatdagi bolaning guruhi. Ketgan bolaning oxirgi guruhi
  // ko'rsatilmaydi — u endi o'sha guruhda emas.
  function groupOf(child: Child): Group | undefined {
    if (child.status === "left" || !child.enrollment) return undefined;
    return groups.find((g) => g.id === child.enrollment?.group_id);
  }

  // Guruhdagi faol bolalar va navbatdagilar soni (formadagi "12/15" uchun).
  function seatsOf(groupId: string): { taken: number; waiting: number } {
    let taken = 0;
    let waiting = 0;
    for (const c of children) {
      if (c.enrollment?.group_id !== groupId) continue;
      if (c.status === "active") taken += 1;
      else if (c.status === "waiting") waiting += 1;
    }
    return { taken, waiting };
  }

  function load(): void {
    // Filial aniqlanmaguncha so'rov yuborilmaydi — aks holda server filtrsiz
    // javob qaytarib, barcha filiallar aralashib ketardi.
    if (!branchId) return;
    setReady(false);
    setLoadError(null);
    Promise.all([api.listChildren(branchId), api.listGroups(branchId)])
      .then(([childList, groupList]) => {
        setChildren(childList);

        // Bu ikki so'rov jadvalning "Ota-ona/Telefon" va "Qarz" ustunlarini
        // to'ldiradi, ikkalasi ham OWNER/MANAGER huquqini talab qiladi.
        // Tarbiyachiga ular baribir 403 qaytarardi — javobi ushlanardi, lekin
        // har ochilishda ikkita keraksiz so'rov ketib, brauzer konsolida xato
        // ko'rinardi. Endi huquq bo'lmasa so'rov umuman yuborilmaydi.
        if (can("parents.message")) {
          api
            .listParents(branchId)
            .then((rows) => {
              const phones: Record<string, string> = {};
              for (const p of rows) if (p.phone) phones[p.id] = p.phone;
              setParentPhones(phones);
            })
            .catch(logSecondaryFailure("Ota-onalar telefonlari"));
        }

        if (can("finance.view")) {
          api
            .branchInvoices(branchId, monthRange().start)
            .then((invoices) => {
              const debts: Record<string, number> = {};
              for (const inv of invoices) {
                debts[inv.child_id] =
                  (debts[inv.child_id] ?? 0) + Number(inv.outstanding_amount);
              }
              setChildDebt(debts);
            })
            .catch(logSecondaryFailure("Qarzdorlik"));
        }

        // Filial kesimini server bajaradi; bu yerda faqat faollari qoladi.
        // Bola→guruh bog'lanishi bola javobining o'zida keladi (navbatdagi
        // bolalar ham) — alohida davomat so'rovi kerak emas.
        setGroups(groupList.filter((g) => g.is_active));
      })
      .catch(setLoadError)
      .finally(() => setReady(true));
  }

  useEffect(load, [branchId, can]);

  useEffect(() => {
    if (canManage && searchParams.get("new") === "1" && groups.length >= 0) {
      openAddChild();
      router.replace("/children");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  function statusBadge(status: ChildStatus): ReactNode {
    if (status === "active")
      return <span className="badge badge--pos">{t.children.active}</span>;
    if (status === "waiting")
      return <span className="badge badge--warn">{t.children.waiting}</span>;
    return <span className="badge badge--mute">{t.children.left}</span>;
  }

  const columns: DataTableColumn<Child>[] = [
    {
      key: "name",
      label: t.common.name,
      sortValue: (c) => c.full_name,
      render: (c) => (
        <div className="cell-name">
          <span className="avatar">{initials(c.full_name)}</span>
          <span>
            <b className="tr">{c.full_name}</b>
            {c.medical_notes && <small className="tr">{c.medical_notes}</small>}
          </span>
        </div>
      ),
    },
    {
      key: "group",
      label: t.children.group,
      sortValue: (c) => groupOf(c)?.name ?? "",
      render: (c) => (
        <span style={{ color: "var(--ink-2)" }}>{groupOf(c)?.name ?? "—"}</span>
      ),
    },
    {
      key: "birth",
      label: t.common.birthDate,
      sortValue: (c) => c.birth_date,
      render: (c) => (
        <span className="num" style={{ color: "var(--ink-2)", fontSize: 13 }}>
          {c.birth_date}
        </span>
      ),
    },
    {
      key: "guardians",
      label: t.children.parent,
      render: (c) => (
        <span className="tr" style={{ color: "var(--ink-2)" }}>
          {(c.guardians.find((g) => g.is_primary) ?? c.guardians[0])
            ?.full_name ?? "—"}
        </span>
      ),
    },
    {
      key: "phone",
      label: t.common.phone,
      render: (c) => {
        const guardian =
          c.guardians.find((g) => g.is_primary) ?? c.guardians[0];
        const phone = guardian
          ? parentPhones[guardian.guardian_user_id]
          : undefined;
        return (
          /* Telefonlar alohida so'rov bilan keladi. `min-width` bo'lmasa
             ustun ma'lumot kelganda kengayib, jadval qimirlaydi (CLS). */
          <span
            className="num"
            style={{
              fontSize: 13,
              color: "var(--ink-2)",
              display: "inline-block",
              minWidth: 118,
            }}
          >
            {phone ?? "—"}
          </span>
        );
      },
    },
    {
      key: "debt",
      label: t.dashboard.debt,
      align: "right",
      sortValue: (c) => childDebt[c.id] ?? 0,
      render: (c) => {
        const debt = childDebt[c.id] ?? 0;
        return (
          <span
            className="num"
            style={{
              display: "inline-block",
              minWidth: 84,
              ...(debt > 0
                ? { color: "var(--neg)", fontWeight: 600 }
                : { color: "var(--ink-3)" }),
            }}
          >
            {debt > 0 ? moneyPlain(debt) : "—"}
          </span>
        );
      },
    },
    {
      key: "status",
      label: t.common.status,
      align: "right",
      sortValue: (c) => c.status,
      render: (c) => statusBadge(c.status),
    },
  ];

  function openDetail(child: Child): void {
    const group = groupOf(child);
    const waiting = child.status === "waiting" && child.enrollment !== null;
    modal.open(
      <div>
        <dl className="deflist">
          <div>
            <dt>{t.common.birthDate}</dt>
            <dd>{child.birth_date}</dd>
          </div>
          <div>
            <dt>{t.children.group}</dt>
            <dd>{group?.name ?? "—"}</dd>
          </div>
          <div>
            <dt>{t.common.status}</dt>
            <dd>{statusBadge(child.status)}</dd>
          </div>
          {waiting && (
            <div>
              <dt>{t.children.desiredDate}</dt>
              <dd>{child.enrollment?.start_date}</dd>
            </div>
          )}
          <div>
            <dt>{t.children.medicalNotes}</dt>
            <dd>{child.medical_notes ?? "—"}</dd>
          </div>
        </dl>
        <div className="subhead">{t.common.guardians}</div>
        {child.guardians.length === 0 ? (
          <p className="muted">{t.common.empty}</p>
        ) : (
          child.guardians.map((g) => (
            <div key={g.guardian_user_id} style={{ marginBottom: 8 }}>
              <b>{g.full_name}</b>{" "}
              <span className="muted">
                ({relationLabel(g.relationship_type, t.children)})
              </span>
            </div>
          ))
        )}
        {/* Ketgan (faolsizlantirilgan yoki navbatdan chiqarilgan) bola —
            guruhga qayta yozish orqali qaytariladi. */}
        {canManage && child.status === "left" && groups.length > 0 && (
          <button
            type="button"
            className="btn"
            style={{ width: "100%", marginTop: 24 }}
            onClick={() => {
              modal.close();
              openReenroll(child);
            }}
          >
            {t.children.reenroll}
          </button>
        )}
        {canManage && waiting && (
          <div style={{ display: "flex", gap: 8, marginTop: 24 }}>
            <button
              type="button"
              className="btn"
              style={{ flex: 1 }}
              onClick={() => {
                modal.close();
                openAdmit(child);
              }}
            >
              {t.children.admit}
            </button>
            <button
              type="button"
              className="btn-ghost btn"
              style={{ flex: 1 }}
              onClick={() => void removeFromWaitlist(child)}
            >
              {t.children.unwaitlist}
            </button>
          </div>
        )}
        {canManage && (
          <div
            style={{
              display: "flex",
              gap: 8,
              marginTop:
                waiting || (child.status === "left" && groups.length > 0)
                  ? 8
                  : 24,
            }}
          >
            <button
              type="button"
              className={
                waiting || child.status === "left" ? "btn-ghost btn" : "btn"
              }
              style={{ flex: 1 }}
              onClick={() => {
                modal.close();
                openEditChild(child);
              }}
            >
              {t.common.edit}
            </button>
            {/* Guruh almashtirish faqat faol bolaga: backend faol
                enrollmentni yopib, yangisini ochadi. */}
            {child.status === "active" && (
              <button
                type="button"
                className="btn-ghost btn"
                style={{ flex: 1 }}
                onClick={() => {
                  modal.close();
                  openTransfer(child);
                }}
              >
                {t.children.transferGroup}
              </button>
            )}
          </div>
        )}
        {canManage && child.is_active && (
          <button
            type="button"
            className="btn--quiet btn"
            style={{
              width: "100%",
              marginTop: 8,
              color: "var(--neg)",
              justifyContent: "center",
            }}
            onClick={async () => {
              const ok = await confirm({
                title: t.common.deactivateTitle,
                body: t.children.deactivateBody,
                confirmLabel: t.common.deactivate,
                cancelLabel: t.common.cancel,
                danger: true,
              });
              if (!ok) return;
              try {
                await api.updateChild(child.id, { is_active: false });
                modal.close();
                toast.show(t.common.saved);
                load();
              } catch (err) {
                toast.show(
                  err instanceof ApiError ? err.message : t.common.errTitle,
                  { type: "neg" },
                );
              }
            }}
          >
            {t.common.deactivate}
          </button>
        )}
      </div>,
      { title: child.full_name, size: "default" },
    );
  }

  function openAdmit(child: Child): void {
    if (!child.enrollment) return;
    const enrollmentId = child.enrollment.id;
    const plannedGroupId = child.enrollment.group_id;
    let groupId = plannedGroupId;
    let startDate = isoDate(new Date());
    let saving = false;
    let error = "";

    function render(): void {
      const seats = seatsOf(groupId);
      const capacity = groups.find((g) => g.id === groupId)?.capacity ?? 0;
      const full = capacity > 0 && seats.taken >= capacity;
      modal.open(
        <form
          onSubmit={async (e: FormEvent) => {
            e.preventDefault();
            saving = true;
            error = "";
            render();
            try {
              await api.updateEnrollment(enrollmentId, {
                status: "ACTIVE",
                start_date: startDate,
                ...(groupId !== plannedGroupId ? { group_id: groupId } : {}),
              });
              modal.close();
              toast.show(t.children.admitted);
              load();
            } catch (err) {
              error = err instanceof ApiError ? err.message : t.common.errTitle;
              saving = false;
              render();
            }
          }}
        >
          <p className="info-box" style={{ marginBottom: 16 }}>
            {t.children.admitHint}
          </p>
          <label className="field">
            <span className="field__label">{t.children.group}</span>
            <select
              className="input"
              value={groupId}
              onChange={(e) => {
                groupId = e.target.value;
                render();
              }}
            >
              {groups.map((g) => (
                <option key={g.id} value={g.id}>
                  {groupOptionLabel(g)}
                </option>
              ))}
            </select>
            {full && (
              <p className="hint hint--warn">{t.children.groupFullHint}</p>
            )}
          </label>
          <label className="field">
            <span className="field__label">{t.children.admitDate}</span>
            <input
              className="input"
              type="date"
              required
              defaultValue={startDate}
              onChange={(e) => (startDate = e.target.value)}
            />
          </label>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <div className="modal-actions">
            <button className="btn" type="submit" disabled={saving}>
              {saving ? t.common.saving : t.children.admit}
            </button>
          </div>
        </form>,
        {
          title: t.children.admitTitle,
          subtitle: child.full_name,
          size: "narrow",
        },
      );
    }
    render();
  }

  function openReenroll(child: Child): void {
    // Oldingi guruhi hali mavjud bo'lsa — sukut bo'yicha o'sha.
    const previous = groups.find((g) => g.id === child.enrollment?.group_id);
    let groupId = previous?.id ?? groups[0]?.id ?? "";
    let mode: EnrollMode = "active";
    let startDate = isoDate(new Date());
    let saving = false;
    let error = "";

    function render(): void {
      const selected = groups.find((g) => g.id === groupId);
      const full =
        !!selected &&
        selected.capacity > 0 &&
        seatsOf(selected.id).taken >= selected.capacity;
      modal.open(
        <form
          onSubmit={async (e: FormEvent) => {
            e.preventDefault();
            if (!groupId) return;
            saving = true;
            error = "";
            render();
            try {
              // Bitta so'rov: backend nofaol bolani shu yerning o'zida
              // faollashtiradi.
              await api.createEnrollment(child.id, {
                branch_id: branchId,
                group_id: groupId,
                start_date: startDate,
                status: mode === "waiting" ? "PLANNED" : "ACTIVE",
              });
              modal.close();
              toast.show(
                mode === "waiting"
                  ? t.children.reenrollWaitlisted
                  : t.children.reenrolled,
              );
              load();
            } catch (err) {
              error = err instanceof ApiError ? err.message : t.common.errTitle;
              saving = false;
              render();
            }
          }}
        >
          <p className="info-box" style={{ marginBottom: 16 }}>
            {t.children.reenrollHint}
          </p>
          <EnrollModeField
            id="reenroll-mode"
            mode={mode}
            groupFull={full}
            t={t}
            onChange={(m) => {
              mode = m;
              render();
            }}
          />
          <label className="field">
            <span className="field__label">{t.children.group}</span>
            <select
              className="input"
              value={groupId}
              onChange={(e) => {
                groupId = e.target.value;
                render();
              }}
            >
              {groups.map((g) => (
                <option key={g.id} value={g.id}>
                  {groupOptionLabel(g)}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span className="field__label">
              {mode === "waiting"
                ? t.children.desiredDate
                : t.children.admitDate}
            </span>
            <input
              className="input"
              type="date"
              required
              defaultValue={startDate}
              onChange={(e) => (startDate = e.target.value)}
            />
          </label>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <div className="modal-actions">
            <button className="btn" type="submit" disabled={saving}>
              {saving
                ? t.common.saving
                : mode === "waiting"
                  ? t.children.enrollWaitlist
                  : t.children.reenroll}
            </button>
          </div>
        </form>,
        {
          title: t.children.reenroll,
          subtitle: child.full_name,
          size: "narrow",
        },
      );
    }
    render();
  }

  async function removeFromWaitlist(child: Child): Promise<void> {
    if (!child.enrollment) return;
    const ok = await confirm({
      title: t.children.unwaitlist,
      body: t.children.unwaitlistBody,
      confirmLabel: t.children.unwaitlist,
      cancelLabel: t.common.cancel,
      danger: true,
    });
    if (!ok) return;
    try {
      await api.updateEnrollment(child.enrollment.id, { status: "CANCELLED" });
      modal.close();
      toast.show(t.children.unwaitlisted);
      load();
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t.common.errTitle, {
        type: "neg",
      });
    }
  }

  // "Quyoshcha — 12/15" yoki "Quyoshcha — 15/15 (to'la) · 3 navbatda".
  function groupOptionLabel(g: Group): string {
    const { taken, waiting } = seatsOf(g.id);
    let label = g.capacity > 0 ? `${g.name} — ${taken}/${g.capacity}` : g.name;
    if (g.capacity > 0 && taken >= g.capacity) {
      label += ` (${t.children.groupFull})`;
    }
    if (waiting > 0) label += ` · ${waiting} ${t.children.waitingCount}`;
    return label;
  }

  function openAddChild(): void {
    openChildForm(null);
  }

  function openEditChild(child: Child): void {
    openChildForm(child);
  }

  function openChildForm(existing: Child | null): void {
    let fullName = existing?.full_name ?? "";
    let birthDate = existing?.birth_date ?? "";
    let gender = existing?.gender ?? "";
    let medicalNotes = existing?.medical_notes ?? "";
    let groupId = groups[0]?.id ?? "";
    // "active" — hozir qabul qilinadi; "waiting" — navbatga qo'yiladi
    // (PLANNED enrollment: davomat va to'lov hisoblanmaydi).
    let mode: EnrollMode = "active";
    let startDate = isoDate(new Date());
    let discountType: DiscountType = "NONE";
    let discountPercent = "";
    let guardianName = "";
    let guardianPhone = "";
    let relation = "MOTHER";
    let saving = false;
    let error = "";

    function render(): void {
      const selectedGroup = groups.find((g) => g.id === groupId);
      const groupFull =
        !!selectedGroup &&
        selectedGroup.capacity > 0 &&
        seatsOf(selectedGroup.id).taken >= selectedGroup.capacity;
      modal.open(
        <form
          onSubmit={async (e: FormEvent) => {
            e.preventDefault();
            error = "";
            // Ota-ona bloki ixtiyoriy, lekin yarim to'ldirilgan bo'lsa
            // vasiy yaratilmaydi. Ilgari bu jimgina sodir bo'lardi: bola
            // saqlanar, "saqlandi" yozuvi chiqar, ota-ona esa yo'qolardi.
            if (
              Boolean(guardianName.trim()) !== Boolean(guardianPhone.trim())
            ) {
              error = t.children.guardianBothRequired;
              render();
              return;
            }
            saving = true;
            render();
            try {
              if (existing) {
                await api.updateChild(existing.id, {
                  full_name: fullName,
                  birth_date: birthDate,
                  gender: gender || null,
                  medical_notes: medicalNotes || null,
                });
              } else {
                const created = await api.createChild({
                  full_name: fullName,
                  birth_date: birthDate,
                  gender: gender || undefined,
                  medical_notes: medicalNotes || undefined,
                });
                if (groupId) {
                  await api.createEnrollment(created.id, {
                    branch_id: branchId,
                    group_id: groupId,
                    start_date: startDate,
                    status: mode === "waiting" ? "PLANNED" : "ACTIVE",
                    discount_type:
                      discountType !== "NONE" ? discountType : undefined,
                    // Chegirma turi tanlanmagan bo'lsa foiz ham ketmasligi
                    // kerak — aks holda turi yo'q, foizi bor yozuv qolardi.
                    discount_percent:
                      discountType !== "NONE"
                        ? discountPercent || undefined
                        : undefined,
                  });
                }
                if (guardianName.trim() && guardianPhone.trim()) {
                  await api.addGuardian(created.id, {
                    full_name: guardianName,
                    phone: guardianPhone,
                    relationship_type: relation,
                    is_primary: true,
                  });
                }
              }
              modal.close();
              toast.show(t.children.savedChild);
              load();
            } catch (err) {
              error = err instanceof ApiError ? err.message : t.common.errTitle;
              saving = false;
              render();
            }
          }}
        >
          <div className="form-sec">{t.children.aboutChild}</div>
          <div className="form-grid">
            <label className="field">
              <span className="field__label">
                {t.common.fullName}
                <span className="req">*</span>
              </span>
              <input
                className="input"
                defaultValue={fullName}
                required
                onChange={(e) => (fullName = e.target.value)}
              />
            </label>
            <label className="field">
              <span className="field__label">
                {t.common.birthDate}
                <span className="req">*</span>
              </span>
              <input
                className="input"
                type="date"
                defaultValue={birthDate}
                required
                onChange={(e) => (birthDate = e.target.value)}
              />
            </label>
            <label className="field">
              <span className="field__label">{t.children.gender}</span>
              <select
                className="input"
                defaultValue={gender}
                onChange={(e) => (gender = e.target.value)}
              >
                <option value="">—</option>
                <option value="MALE">{t.children.boy}</option>
                <option value="FEMALE">{t.children.girl}</option>
              </select>
            </label>
          </div>
          <label className="field">
            <span className="field__label">{t.children.medicalNotes}</span>
            <textarea
              className="input"
              defaultValue={medicalNotes}
              placeholder={t.children.medicalHint}
              onChange={(e) => (medicalNotes = e.target.value)}
            />
          </label>

          {!existing && (
            <>
              <div className="form-sec">{t.children.group}</div>
              {groups.length > 0 && (
                <EnrollModeField
                  id="child-enroll-mode"
                  mode={mode}
                  groupFull={groupFull}
                  t={t}
                  onChange={(m) => {
                    mode = m;
                    render();
                  }}
                />
              )}
              <div className="form-grid">
                <label className="field">
                  <span className="field__label">{t.children.group}</span>
                  <select
                    className="input"
                    value={groupId}
                    onChange={(e) => {
                      groupId = e.target.value;
                      render();
                    }}
                  >
                    {groups.map((g) => (
                      <option key={g.id} value={g.id}>
                        {groupOptionLabel(g)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span className="field__label">
                    {mode === "waiting"
                      ? t.children.desiredDate
                      : t.children.startDate}
                  </span>
                  <input
                    className="input"
                    type="date"
                    defaultValue={startDate}
                    onChange={(e) => (startDate = e.target.value)}
                  />
                </label>
                <label className="field">
                  <span className="field__label">{t.children.discount}</span>
                  <select
                    className="input"
                    defaultValue={discountType}
                    onChange={(e) =>
                      (discountType = e.target.value as DiscountType)
                    }
                  >
                    <option value="NONE">{t.children.discountNone}</option>
                    <option value="SIBLING">
                      {t.children.discountSibling}
                    </option>
                    <option value="STAFF_CHILD">
                      {t.children.discountStaffChild}
                    </option>
                    <option value="SOCIAL">{t.children.discountSocial}</option>
                    <option value="OTHER">{t.children.discountOther}</option>
                  </select>
                </label>
                <label className="field">
                  <span className="field__label">
                    {t.children.discountPercent}
                  </span>
                  <input
                    className="input"
                    inputMode="decimal"
                    defaultValue={discountPercent}
                    onChange={(e) => (discountPercent = e.target.value)}
                  />
                </label>
              </div>

              <div className="form-sec">
                {t.children.guardianSection} ({t.common.optional})
              </div>
              <div className="form-grid">
                <label className="field">
                  <span className="field__label">{t.common.fullName}</span>
                  <input
                    className="input"
                    onChange={(e) => (guardianName = e.target.value)}
                  />
                </label>
                <label className="field">
                  <span className="field__label">{t.common.phone}</span>
                  <input
                    className="input"
                    placeholder="+998901234567"
                    onChange={(e) => (guardianPhone = e.target.value)}
                  />
                </label>
                <label className="field">
                  <span className="field__label">{t.children.relation}</span>
                  <select
                    className="input"
                    defaultValue={relation}
                    onChange={(e) => (relation = e.target.value)}
                  >
                    <option value="MOTHER">{t.children.rMother}</option>
                    <option value="FATHER">{t.children.rFather}</option>
                    <option value="RELATIVE">{t.children.rRelative}</option>
                    <option value="OTHER">{t.children.rOther}</option>
                  </select>
                </label>
              </div>
            </>
          )}

          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <div className="modal-actions">
            <button className="btn" type="submit" disabled={saving}>
              {saving ? t.common.saving : t.common.save}
            </button>
          </div>
        </form>,
        {
          title: existing ? t.children.editChild : t.children.addChild,
          size: "wide",
        },
      );
    }

    render();
  }

  function openTransfer(child: Child): void {
    let newGroupId = groups[0]?.id ?? "";
    let effectiveDate = isoDate(new Date());
    let reason = "";
    let saving = false;
    let error = "";

    function render(): void {
      modal.open(
        <form
          onSubmit={async (e: FormEvent) => {
            e.preventDefault();
            saving = true;
            error = "";
            render();
            try {
              await api.transferChild(child.id, {
                new_group_id: newGroupId,
                effective_date: effectiveDate,
                reason: reason || undefined,
              });
              modal.close();
              toast.show(t.children.transferDone);
              load();
            } catch (err) {
              error = err instanceof ApiError ? err.message : t.common.errTitle;
              saving = false;
              render();
            }
          }}
        >
          <p className="info-box" style={{ marginBottom: 16 }}>
            {t.children.transferHint}
          </p>
          <label className="field">
            <span className="field__label">{t.children.newGroup}</span>
            <select
              className="input"
              defaultValue={newGroupId}
              onChange={(e) => (newGroupId = e.target.value)}
            >
              {groups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span className="field__label">{t.children.effectiveDate}</span>
            <input
              className="input"
              type="date"
              defaultValue={effectiveDate}
              onChange={(e) => (effectiveDate = e.target.value)}
            />
          </label>
          <label className="field">
            <span className="field__label">
              {t.common.reason} ({t.common.optional})
            </span>
            <input
              className="input"
              onChange={(e) => (reason = e.target.value)}
            />
          </label>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <div className="modal-actions">
            <button className="btn" type="submit" disabled={saving}>
              {saving ? t.common.saving : t.children.transfer}
            </button>
          </div>
        </form>,
        {
          title: t.children.transferGroup,
          subtitle: child.full_name,
          size: "narrow",
        },
      );
    }
    render();
  }

  function openImportWizard(): void {
    // 3 bosqichli sehrgar: 1) fayl tanlash → 2) dry-run ko'rib chiqish →
    // 3) tasdiqlab haqiqiy import. Har bosqich bir xil modalda qayta chiziladi.
    let step: 1 | 2 | 3 = 1;
    let file: File | null = null;
    let importGroupId = groups[0]?.id ?? "";
    let preview: ImportResult | null = null;
    let busy = false;
    let error = "";

    async function runImport(dryRun: boolean): Promise<void> {
      if (!file) return;
      busy = true;
      error = "";
      render();
      try {
        const result = await api.importChildren(
          branchId,
          importGroupId,
          dryRun,
          file,
        );
        if (dryRun) {
          preview = result;
          step = 2;
        } else {
          modal.close();
          toast.show(`${result.imported} ${t.children.importDone}`);
          load();
          return;
        }
      } catch (err) {
        error = err instanceof ApiError ? err.message : t.common.errTitle;
      } finally {
        busy = false;
        render();
      }
    }

    function render(): void {
      modal.open(
        <div>
          <div
            className="steps"
            style={{ display: "flex", gap: 8, marginBottom: 16 }}
          >
            {[
              t.children.importUploadStep,
              t.children.importPreviewStep,
              t.children.importConfirmStep,
            ].map((label, i) => (
              <span
                key={label}
                className={`chip${step === i + 1 ? " on" : ""}`}
              >
                {i + 1}. {label}
              </span>
            ))}
          </div>

          {step === 1 && (
            <>
              <label className="field">
                <span className="field__label">{t.children.importGroup}</span>
                <select
                  className="input"
                  defaultValue={importGroupId}
                  onChange={(e) => (importGroupId = e.target.value)}
                >
                  {groups.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span className="field__label">
                  {t.children.importChooseFile}
                </span>
                <input
                  className="input"
                  type="file"
                  accept=".xlsx,.xlsm,.csv"
                  onChange={(e) => {
                    file = e.target.files?.[0] ?? null;
                    render();
                  }}
                />
              </label>
              <p className="field__hint">{t.children.importDryRunHint}</p>
              {error && (
                <p className="error" role="alert">
                  {error}
                </p>
              )}
              <button
                type="button"
                className="btn"
                disabled={busy || !file || !importGroupId}
                onClick={() => runImport(true)}
                style={{ marginTop: 8 }}
              >
                {busy ? t.common.loading : t.common.next}
              </button>
            </>
          )}

          {step === 2 && preview && (
            <>
              <div
                style={{
                  display: "flex",
                  gap: 16,
                  marginBottom: 16,
                  flexWrap: "wrap",
                }}
              >
                <div className="kpi" style={{ flex: 1, minWidth: 150 }}>
                  <div className="kpi__top">
                    <span className="kpi__label">
                      {t.children.importTotalRows}
                    </span>
                  </div>
                  <div className="kpi__value">{preview.total_rows}</div>
                </div>
                <div className="kpi" style={{ flex: 1, minWidth: 150 }}>
                  <div className="kpi__top">
                    <span className="kpi__label">
                      {t.children.importValidRows}
                    </span>
                  </div>
                  <div className="kpi__value">{preview.valid_rows}</div>
                </div>
              </div>
              <div
                className="tbl-wrap"
                style={{ maxHeight: 320, overflowY: "auto" }}
              >
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>{t.children.importRowNumber}</th>
                      <th>{t.common.fullName}</th>
                      <th>{t.common.birthDate}</th>
                      <th>{t.children.parent}</th>
                      <th>{t.children.importErrors}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((r) => (
                      <tr key={r.row_number}>
                        <td>{r.row_number}</td>
                        <td>{r.full_name ?? "—"}</td>
                        <td>{r.birth_date ?? "—"}</td>
                        <td>{r.guardian_name ?? "—"}</td>
                        <td>
                          {r.valid ? (
                            <span className="muted">—</span>
                          ) : (
                            <span style={{ color: "var(--neg)" }}>
                              {r.errors.join("; ")}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {error && (
                <p className="error" role="alert">
                  {error}
                </p>
              )}
              <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
                <button
                  type="button"
                  className="btn-ghost btn"
                  onClick={() => {
                    step = 1;
                    render();
                  }}
                >
                  {t.common.back}
                </button>
                <button
                  type="button"
                  className="btn"
                  style={{ flex: 1 }}
                  disabled={busy || preview.valid_rows === 0}
                  onClick={() => {
                    step = 3;
                    render();
                  }}
                >
                  {t.common.next}
                </button>
              </div>
            </>
          )}

          {step === 3 && preview && (
            <>
              <p className="info-box" style={{ marginBottom: 16 }}>
                {preview.valid_rows} / {preview.total_rows} —{" "}
                {t.children.importValidRows}
              </p>
              {error && (
                <p className="error" role="alert">
                  {error}
                </p>
              )}
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  type="button"
                  className="btn-ghost btn"
                  onClick={() => {
                    step = 2;
                    render();
                  }}
                >
                  {t.common.back}
                </button>
                <button
                  type="button"
                  className="btn"
                  style={{ flex: 1 }}
                  disabled={busy}
                  onClick={() => runImport(false)}
                >
                  {busy ? t.common.saving : t.children.importConfirmButton}
                </button>
              </div>
            </>
          )}
        </div>,
        { title: t.children.importTitle, size: "wide" },
      );
    }
    render();
  }

  return (
    <>
      {loadError ? (
        <LoadError error={loadError} onRetry={load} />
      ) : !ready ? (
        <div className="card">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <div className="sk-row" key={i}>
              <div
                className="sk"
                style={{ width: 34, height: 34, borderRadius: 10 }}
              />
              <div style={{ flex: 1 }}>
                <div className="sk sk-line" style={{ width: "38%" }} />
                <div className="sk sk-line" style={{ width: "22%" }} />
              </div>
              <div className="sk sk-line" style={{ width: 80 }} />
            </div>
          ))}
        </div>
      ) : (
        <DataTable
          columns={columns}
          rows={children}
          rowKey={(c) => c.id}
          searchText={(c) =>
            [
              c.full_name,
              ...c.guardians.map((g) => g.full_name),
              ...c.guardians.map((g) => parentPhones[g.guardian_user_id] ?? ""),
              groupOf(c)?.name ?? "",
            ].join(" ")
          }
          searchPlaceholder={t.common.search}
          filters={[
            { key: "all", label: t.common.all },
            { key: "active", label: t.children.filterActive },
            { key: "debt", label: t.children.filterDebt },
            { key: "waiting", label: t.children.filterWaiting },
            { key: "left", label: t.children.filterLeft },
          ]}
          filterFn={(c, f) =>
            f === "debt" ? (childDebt[c.id] ?? 0) > 0 : c.status === f
          }
          onRowClick={openDetail}
          emptyTitle={t.common.nothingFound}
          emptySub={t.common.nothingFoundSub}
          clearFiltersLabel={t.common.clearFilters}
          showingLabel={t.common.showing}
          ofLabel={t.common.of}
          actions={
            canManage ? (
              <>
                <button
                  type="button"
                  className="btn-ghost btn btn-sm"
                  onClick={openImportWizard}
                >
                  <IconUpload size={14} /> {t.children.importTitle}
                </button>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={openAddChild}
                >
                  <IconUsers size={14} /> {t.children.addChild}
                </button>
              </>
            ) : null
          }
        />
      )}
    </>
  );
}

type EnrollMode = "active" | "waiting";

/**
 * "Hozir qabul qilish / Navbatga qo'yish" tanlovi.
 *
 * Bola qo'shish formasi va qayta qabul oynasida bir xil — ilgari ikkala joyda
 * aynan bir xil JSX nusxalangan edi.
 */
function EnrollModeField({
  id,
  mode,
  groupFull,
  t,
  onChange,
}: {
  id: string;
  mode: EnrollMode;
  groupFull: boolean;
  t: AppStrings;
  onChange: (mode: EnrollMode) => void;
}): ReactNode {
  return (
    <div className="field" role="group" aria-labelledby={id}>
      <span className="field__label" id={id}>
        {t.children.enrollMode}
      </span>
      <div className="segmented">
        {(["active", "waiting"] as const).map((m) => (
          <button
            key={m}
            type="button"
            className={mode === m ? "on" : ""}
            aria-pressed={mode === m}
            onClick={() => onChange(m)}
          >
            {m === "active" ? t.children.enrollNow : t.children.enrollWaitlist}
          </button>
        ))}
      </div>
      {mode === "waiting" ? (
        <p className="hint hint--left">{t.children.waitlistHint}</p>
      ) : (
        groupFull && <p className="hint hint--warn">{t.children.groupFullHint}</p>
      )}
    </div>
  );
}
