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
import { IconGrid, IconUsers } from "@/components/icons";
import {
  LoadError,
  logSecondaryFailure,
  recoverWith,
} from "@/components/ui/LoadError";
import { useModal } from "@/components/ui/ModalProvider";
import { useToast } from "@/components/ui/ToastProvider";
import {
  ApiError,
  api,
  type Child,
  type Group,
  type StaffUser,
} from "@/lib/api";
import {
  ageInYears,
  ageRangeLabel,
  initials,
  isoDate,
  money,
  relationLabel,
} from "@/lib/format";

/** Bugungi davomat holatining rangi. Belgilanmagan — neytral kulrang. */
const STATUS_TONE: Record<string, "pos" | "neg" | "warn" | "mute"> = {
  PRESENT: "pos",
  LATE: "warn",
  ABSENT: "neg",
  SICK: "warn",
  EXCUSED: "mute",
};

function statusLabel(
  status: string | null,
  t: ReturnType<typeof useAppUI>["t"],
): string {
  switch (status) {
    case "PRESENT":
      return t.attendance.present;
    case "LATE":
      return t.attendance.late;
    case "ABSENT":
      return t.attendance.absent;
    case "SICK":
      return t.attendance.sick;
    case "EXCUSED":
      return t.attendance.excused;
    default:
      return t.groups.unmarked;
  }
}

export default function GroupsPage(): ReactNode {
  return (
    <Suspense fallback={null}>
      <GroupsContent />
    </Suspense>
  );
}

function GroupsContent(): ReactNode {
  const { t, branchId, setPageMeta, can } = useAppUI();

  useEffect(() => {
    setPageMeta({ title: t.groups.title, subtitle: t.groups.subtitle });
  }, [setPageMeta, t]);
  const modal = useModal();
  const toast = useToast();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [groups, setGroups] = useState<Group[]>([]);
  // Guruhdagi bolalar — mockupdagi kartochkada avatar tizmasi uchun kerak,
  // shu bilan birga to'ldirilganlik soni ham shundan olinadi. ID ham
  // saqlanadi: bir xil ismli ikki bola bo'lishi mumkin, ism React kalit
  // sifatida yaroqsiz.
  const [roster, setRoster] = useState<
    Record<string, { id: string; name: string; status: string | null }[]>
  >({});
  const [teachers, setTeachers] = useState<StaffUser[]>([]);
  // Guruh tarkibi oynasi uchun: yosh, tibbiy izoh va ota-ona ismi shu
  // ro'yxatdan olinadi (roster faqat ism va bugungi davomatni beradi).
  const [children, setChildren] = useState<Record<string, Child>>({});
  const [parentPhones, setParentPhones] = useState<Record<string, string>>({});
  const [ready, setReady] = useState(false);
  const [loadError, setLoadError] = useState<unknown>(null);

  function load(): void {
    if (!branchId) return;
    setReady(false);
    setLoadError(null);
    // Guruhlar va ularning bolalari bitta so'rovda. Ilgari har bir guruh
    // uchun alohida roster so'rovi yuborilardi.
    Promise.all([
      api.listGroups(branchId),
      api
        .branchAttendanceSummary(branchId, isoDate(new Date()))
        .catch(recoverWith("Guruh tarkibi", null)),
    ])
      .then(([branchGroups, attendance]) => {
        setGroups(branchGroups);
        const map: Record<
          string,
          { id: string; name: string; status: string | null }[]
        > = {};
        for (const group of attendance?.groups ?? []) {
          map[group.group_id] = group.rows.map((r) => ({
            id: r.child_id,
            name: r.child_name,
            // Bugungi davomat tarkib oynasida ko'rsatiladi.
            status: r.status,
          }));
        }
        setRoster(map);
      })
      .catch(setLoadError)
      .finally(() => setReady(true));

    // Guruhga faqat shu filialdagi tarbiyachi biriktiriladi.
    api
      .listStaff("TEACHER", branchId)
      .then(setTeachers)
      .catch(logSecondaryFailure("Tarbiyachilar ro'yxati"));

    // Tarkib oynasi uchun qo'shimcha ma'lumot. Kartochkalar bularsiz ham
    // chiziladi, shuning uchun xatosi sahifani yiqitmaydi.
    api
      .listChildren(branchId)
      .then((rows) => {
        const map: Record<string, Child> = {};
        for (const c of rows) map[c.id] = c;
        setChildren(map);
      })
      .catch(logSecondaryFailure("Bolalar ro'yxati"));

    // Telefon OWNER/MANAGER huquqini talab qiladi — tarbiyachiga so'rov
    // umuman yuborilmaydi (aks holda har ochilishda 403 tushardi).
    if (can("parents.message")) {
      api
        .listParents(branchId)
        .then((rows) => {
          const phones: Record<string, string> = {};
          for (const r of rows) if (r.phone) phones[r.id] = r.phone;
          setParentPhones(phones);
        })
        .catch(logSecondaryFailure("Ota-onalar telefonlari"));
    }
  }

  useEffect(load, [branchId, can]);

  useEffect(() => {
    if (searchParams.get("new") === "1") {
      openGroupForm(null);
      router.replace("/groups");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  function openGroupForm(existing: Group | null): void {
    let name = existing?.name ?? "";
    let minAge = existing?.min_age_months?.toString() ?? "";
    let maxAge = existing?.max_age_months?.toString() ?? "";
    let capacity = existing?.capacity?.toString() ?? "20";
    let monthlyFee = existing?.monthly_fee ?? "";
    let roomNumber = existing?.room_number ?? "";
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
              if (existing) {
                await api.updateGroup(existing.id, {
                  name,
                  min_age_months: minAge ? Number(minAge) : undefined,
                  max_age_months: maxAge ? Number(maxAge) : undefined,
                  capacity: Number(capacity),
                  monthly_fee: monthlyFee || undefined,
                  room_number: roomNumber || undefined,
                });
              } else {
                await api.createGroup({
                  branch_id: branchId,
                  name,
                  min_age_months: minAge ? Number(minAge) : undefined,
                  max_age_months: maxAge ? Number(maxAge) : undefined,
                  capacity: Number(capacity),
                  monthly_fee: monthlyFee || undefined,
                  room_number: roomNumber || undefined,
                });
              }
              modal.close();
              toast.show(t.groups.savedGroup);
              load();
            } catch (err) {
              error = err instanceof ApiError ? err.message : t.common.errTitle;
              saving = false;
              render();
            }
          }}
        >
          <div className="form-grid">
            <label className="field span-2">
              <span className="field__label">
                {t.groups.groupName}
                <span className="req">*</span>
              </span>
              <input
                className="input"
                defaultValue={name}
                required
                onChange={(e) => (name = e.target.value)}
              />
            </label>
            <label className="field">
              <span className="field__label">{t.groups.ageRange} — min</span>
              <input
                className="input"
                inputMode="numeric"
                defaultValue={minAge}
                onChange={(e) => (minAge = e.target.value)}
              />
            </label>
            <label className="field">
              <span className="field__label">{t.groups.ageRange} — max</span>
              <input
                className="input"
                inputMode="numeric"
                defaultValue={maxAge}
                onChange={(e) => (maxAge = e.target.value)}
              />
            </label>
            <label className="field">
              <span className="field__label">{t.groups.capacityField}</span>
              <input
                className="input"
                inputMode="numeric"
                defaultValue={capacity}
                required
                onChange={(e) => (capacity = e.target.value)}
              />
            </label>
            <label className="field">
              <span className="field__label">{t.groups.roomNumber}</span>
              <input
                className="input"
                defaultValue={roomNumber}
                onChange={(e) => (roomNumber = e.target.value)}
              />
            </label>
            <label className="field span-2">
              <span className="field__label">{t.groups.monthlyFee}</span>
              <input
                className="input"
                inputMode="decimal"
                defaultValue={monthlyFee}
                onChange={(e) => (monthlyFee = e.target.value)}
              />
            </label>
          </div>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <div className="modal-actions">
            <button className="btn" type="submit" disabled={saving}>
              {saving
                ? t.common.saving
                : existing
                  ? t.common.save
                  : t.common.create}
            </button>
          </div>
        </form>,
        {
          title: existing ? t.groups.editGroup : t.groups.addGroup,
          size: "default",
        },
      );
    }
    render();
  }

  /**
   * Guruh tarkibi oynasi.
   *
   * Ilgari kartochkada faqat 7 ta avatar turardi va kimligini bilishning
   * yagona yo'li sichqonchani ustiga olib borish edi — klaviatura bilan
   * umuman ko'rib bo'lmasdi. Endi to'liq ro'yxat: yosh, bugungi davomat,
   * ota-ona va tibbiy izoh.
   */
  function openRoster(group: Group): void {
    let query = "";

    function render(): void {
      const rows = (roster[group.id] ?? [])
        .map((kid) => ({ ...kid, child: children[kid.id] }))
        .sort((a, b) => a.name.localeCompare(b.name));
      const q = query.trim().toLowerCase();
      const shown = q
        ? rows.filter((r) => r.name.toLowerCase().includes(q))
        : rows;

      const leadId = (
        group.teachers.find((x) => x.is_primary) ?? group.teachers[0]
      )?.teacher_user_id;
      const lead =
        teachers.find((x) => x.id === leadId)?.full_name ?? t.groups.noTeacher;

      modal.open(
        <div className="roster">
          {rows.length > 3 && (
            <input
              className="input roster__search"
              placeholder={t.groups.searchChild}
              defaultValue={query}
              onChange={(e) => {
                query = e.target.value;
                render();
              }}
            />
          )}
          {shown.length === 0 ? (
            <div className="state">
              <div className="state__ico">
                <IconUsers size={24} />
              </div>
              <h4>
                {rows.length === 0 ? t.groups.noChildren : t.common.empty}
              </h4>
            </div>
          ) : (
            <ul className="roster__list">
              {shown.map((r) => {
                const child = r.child;
                const guardian =
                  child?.guardians.find((g) => g.is_primary) ??
                  child?.guardians[0];
                const phone = guardian
                  ? parentPhones[guardian.guardian_user_id]
                  : undefined;
                const tone = STATUS_TONE[r.status ?? ""] ?? "mute";
                return (
                  <li className="roster__row" key={r.id}>
                    <span className="avatar">{initials(r.name)}</span>
                    <div className="roster__main">
                      <b className="tr">{r.name}</b>
                      <span className="roster__meta tr">
                        {child
                          ? `${ageInYears(child.birth_date)} ${t.groups.ageYears}`
                          : ""}
                        {/* Vasiyning kimligi ham yoziladi: ilgari faqat ism
                            turardi va u onasimi, otasimi — bilib bo'lmasdi. */}
                        {guardian
                          ? ` · ${relationLabel(guardian.relationship_type, t.children)}: ${guardian.full_name}`
                          : ""}
                        {phone ? ` · ${phone}` : ""}
                      </span>
                      {child?.medical_notes && (
                        <span
                          className="roster__note"
                          title={t.groups.medicalNote}
                        >
                          {child.medical_notes}
                        </span>
                      )}
                    </div>
                    {/* Nishon faqat davomat belgilangan bo'lsa. Aks holda
                        har bir qatorda bir xil "Belgilanmagan" turib,
                        haqiqiy holatlarni ko'rinmas qilardi. */}
                    {r.status && (
                      <span className={`badge badge--${tone}`}>
                        {statusLabel(r.status, t)}
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>,
        {
          title: group.name,
          subtitle: `${lead} · ${rows.length} / ${group.capacity}`,
          size: "default",
          onClose: () => {
            query = "";
          },
        },
      );
    }

    render();
  }

  function openAssignTeacher(group: Group): void {
    if (teachers.length === 0) {
      toast.show(t.common.errTitle, { type: "neg" });
      return;
    }
    let teacherUserId = teachers[0]?.id ?? "";
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
              await api.assignTeacher(group.id, teacherUserId, true);
              modal.close();
              toast.show(t.groups.teacherAssigned);
              load();
            } catch (err) {
              error = err instanceof ApiError ? err.message : t.common.errTitle;
              saving = false;
              render();
            }
          }}
        >
          <label className="field">
            <span className="field__label">{t.groups.mainTeacher}</span>
            <select
              className="input"
              defaultValue={teacherUserId}
              onChange={(e) => (teacherUserId = e.target.value)}
            >
              {teachers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.full_name}
                </option>
              ))}
            </select>
          </label>
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
        { title: t.groups.assignTeacher, subtitle: group.name, size: "narrow" },
      );
    }
    render();
  }

  if (loadError) {
    return <LoadError error={loadError} onRetry={load} />;
  }

  if (!ready) {
    return (
      <div className="grid g-3">
        {[0, 1, 2].map((i) => (
          <div className="card" key={i}>
            <div className="card__body" style={{ paddingTop: "var(--s5)" }}>
              <div className="sk sk-line" style={{ width: "50%" }} />
              <div
                className="sk sk-block"
                style={{ height: 60, marginTop: 12 }}
              />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <>
      {/* Sarlavha topbarda turadi (mockupdagidek), bu yerda faqat amal. */}
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          marginBottom: 16,
        }}
      >
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => openGroupForm(null)}
        >
          + {t.groups.addGroup}
        </button>
      </div>

      {groups.length === 0 ? (
        <div className="card">
          <div className="state">
            <div className="state__ico">
              <IconGrid size={22} />
            </div>
            <h4>{t.common.empty}</h4>
          </div>
        </div>
      ) : (
        <div className="grid g-2">
          {groups.map((g) => {
            const kids = roster[g.id] ?? [];
            const count = kids.length;
            const pct = Math.min(100, Math.round((count / g.capacity) * 100));
            const leadTeacherId = (
              g.teachers.find((x) => x.is_primary) ?? g.teachers[0]
            )?.teacher_user_id;
            const leadTeacher =
              teachers.find((x) => x.id === leadTeacherId)?.full_name ??
              t.groups.noTeacher;
            const fee = Number(g.monthly_fee ?? 0);
            return (
              <div className="card" key={g.id}>
                <div className="card__head">
                  <span className="avatar avatar--lg">{g.name.charAt(0)}</span>
                  <div style={{ minWidth: 0 }}>
                    <h3 style={{ fontSize: 17, fontFamily: "var(--display)" }}>
                      {g.name}
                    </h3>
                    <p className="tr">
                      {ageRangeLabel(g.min_age_months, g.max_age_months)}{" "}
                      {t.groups.ageYears} · {leadTeacher}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="btn-ghost btn btn-sm"
                    style={{ marginLeft: "auto" }}
                    onClick={() => openGroupForm(g)}
                  >
                    {t.common.edit}
                  </button>
                </div>
                <div className="card__body">
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "baseline",
                      marginBottom: 8,
                    }}
                  >
                    <span style={{ fontSize: 13, color: "var(--ink-2)" }}>
                      {t.groups.occupancy}
                    </span>
                    <span className="num" style={{ fontWeight: 600 }}>
                      {count} / {g.capacity}
                    </span>
                  </div>
                  <div className="bar mb-4">
                    <i
                      style={{
                        width: `${pct}%`,
                        background: pct > 95 ? "var(--warn)" : "var(--brand-2)",
                      }}
                    />
                  </div>
                  {/* Avatar tizmasi butunlay bosiladigan: guruh tarkibini
                      ochadi. Ilgari bu shunchaki bezak edi va bolalarning
                      kimligini bilishning yagona yo'li sichqonchani ustiga
                      olib borish edi. */}
                  <button
                    type="button"
                    className="roster-strip"
                    onClick={() => openRoster(g)}
                    aria-label={`${g.name} — ${t.groups.viewRoster}`}
                  >
                    <span className="roster-strip__avatars">
                      {kids.slice(0, 7).map((kid) => (
                        <span className="avatar avatar--sm" key={kid.id}>
                          {initials(kid.name)}
                        </span>
                      ))}
                      {count > 7 && (
                        <span className="avatar avatar--sm roster-strip__more">
                          +{count - 7}
                        </span>
                      )}
                    </span>
                    <span className="roster-strip__cta">
                      {count === 0 ? t.groups.noChildren : t.groups.viewRoster}
                    </span>
                  </button>
                  <div style={{ display: "flex", gap: 32, flexWrap: "wrap" }}>
                    <div>
                      <small style={{ fontSize: 12, color: "var(--ink-3)" }}>
                        {t.groups.monthlyFee}
                      </small>
                      <div
                        className="num"
                        style={{ fontWeight: 600, fontSize: 16 }}
                      >
                        {fee ? money(fee) : "—"}
                      </div>
                    </div>
                    <div>
                      <small style={{ fontSize: 12, color: "var(--ink-3)" }}>
                        {t.groups.monthlyRevenue}
                      </small>
                      <div
                        className="num"
                        style={{
                          fontWeight: 600,
                          fontSize: 16,
                          color: "var(--pos)",
                        }}
                      >
                        {fee ? money(fee * count) : "—"}
                      </div>
                    </div>
                    {g.room_number && (
                      <div>
                        <small style={{ fontSize: 12, color: "var(--ink-3)" }}>
                          {t.groups.roomNumber}
                        </small>
                        <div
                          className="num"
                          style={{ fontWeight: 600, fontSize: 16 }}
                        >
                          {g.room_number}
                        </div>
                      </div>
                    )}
                    <button
                      type="button"
                      className="btn--quiet btn btn-sm"
                      style={{ marginLeft: "auto", alignSelf: "flex-end" }}
                      onClick={() => openAssignTeacher(g)}
                    >
                      {t.groups.assignTeacher}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
