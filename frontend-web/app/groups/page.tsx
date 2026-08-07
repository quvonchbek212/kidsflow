"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent, type ReactNode } from "react";

import { AppShell, useAppUI } from "@/components/AppShell";
import { IconGrid } from "@/components/icons";
import { useModal } from "@/components/ui/ModalProvider";
import { useToast } from "@/components/ui/ToastProvider";
import { ApiError, api, type Group, type StaffUser } from "@/lib/api";
import { ageRangeLabel, initials, isoDate, money } from "@/lib/format";
import { useAuth } from "@/lib/useAuth";

export default function GroupsPage(): ReactNode {
  const { user, loading } = useAuth();
  if (loading || !user) return <div className="boot-screen">KIDSFLOW</div>;
  return (
    <AppShell user={user} active="groups">
      <Suspense fallback={null}>
        <GroupsContent />
      </Suspense>
    </AppShell>
  );
}

function GroupsContent(): ReactNode {
  const { t, branchId, setPageMeta } = useAppUI();

  useEffect(() => {
    setPageMeta({ title: t.groups.title, subtitle: t.groups.subtitle });
  }, [setPageMeta, t]);
  const modal = useModal();
  const toast = useToast();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [groups, setGroups] = useState<Group[]>([]);
  // Guruhdagi bolalar ismlari — mockupdagi kartochkada avatar tizmasi
  // uchun kerak, shu bilan birga to'ldirilganlik soni ham shundan olinadi.
  const [roster, setRoster] = useState<Record<string, string[]>>({});
  const [teachers, setTeachers] = useState<StaffUser[]>([]);
  const [ready, setReady] = useState(false);

  function load(): void {
    if (!branchId) return;
    setReady(false);
    api
      .listGroups(branchId)
      .then(async (branchGroups) => {
        setGroups(branchGroups);
        const rosters = await Promise.all(
          branchGroups.map((g) =>
            api
              .attendanceRoster(g.id, isoDate(new Date()))
              .then((rows) => rows.map((r) => r.child_name))
              .catch(() => [] as string[]),
          ),
        );
        const map: Record<string, string[]> = {};
        branchGroups.forEach((g, i) => (map[g.id] = rosters[i]));
        setRoster(map);
      })
      .catch(() => {})
      .finally(() => setReady(true));

    // Guruhga faqat shu filialdagi tarbiyachi biriktiriladi.
    api
      .listStaff("TEACHER", branchId)
      .then(setTeachers)
      .catch(() => setTeachers([]));
  }

  useEffect(load, [branchId]);

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
            <div className="field span-2">
              <label>
                {t.groups.groupName}
                <span className="req">*</span>
              </label>
              <input className="input" defaultValue={name} required onChange={(e) => (name = e.target.value)} />
            </div>
            <div className="field">
              <label>{t.groups.ageRange} — min</label>
              <input
                className="input"
                inputMode="numeric"
                defaultValue={minAge}
                onChange={(e) => (minAge = e.target.value)}
              />
            </div>
            <div className="field">
              <label>{t.groups.ageRange} — max</label>
              <input
                className="input"
                inputMode="numeric"
                defaultValue={maxAge}
                onChange={(e) => (maxAge = e.target.value)}
              />
            </div>
            <div className="field">
              <label>{t.groups.capacityField}</label>
              <input
                className="input"
                inputMode="numeric"
                defaultValue={capacity}
                required
                onChange={(e) => (capacity = e.target.value)}
              />
            </div>
            <div className="field">
              <label>{t.groups.roomNumber}</label>
              <input className="input" defaultValue={roomNumber} onChange={(e) => (roomNumber = e.target.value)} />
            </div>
            <div className="field span-2">
              <label>{t.groups.monthlyFee}</label>
              <input
                className="input"
                inputMode="decimal"
                defaultValue={monthlyFee}
                onChange={(e) => (monthlyFee = e.target.value)}
              />
            </div>
          </div>
          {error && <p className="error">{error}</p>}
          <button className="btn" type="submit" disabled={saving} style={{ marginTop: 8 }}>
            {saving ? t.common.saving : existing ? t.common.save : t.common.create}
          </button>
        </form>,
        { title: existing ? t.groups.editGroup : t.groups.addGroup, size: "default" },
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
          <div className="field">
            <label>{t.groups.mainTeacher}</label>
            <select className="input" defaultValue={teacherUserId} onChange={(e) => (teacherUserId = e.target.value)}>
              {teachers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.full_name}
                </option>
              ))}
            </select>
          </div>
          {error && <p className="error">{error}</p>}
          <button className="btn" type="submit" disabled={saving} style={{ marginTop: 8 }}>
            {saving ? t.common.saving : t.common.save}
          </button>
        </form>,
        { title: t.groups.assignTeacher, subtitle: group.name, size: "narrow" },
      );
    }
    render();
  }

  if (!ready) {
    return (
      <div className="grid g-3">
        {[0, 1, 2].map((i) => (
          <div className="card" key={i}>
            <div className="card__body" style={{ paddingTop: "var(--s5)" }}>
              <div className="sk sk-line" style={{ width: "50%" }} />
              <div className="sk sk-block" style={{ height: 60, marginTop: 12 }} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <>
      {/* Sarlavha topbarda turadi (mockupdagidek), bu yerda faqat amal. */}
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 16 }}>
        <button type="button" className="btn btn-sm" onClick={() => openGroupForm(null)}>
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
            const leadTeacherId = (g.teachers.find((x) => x.is_primary) ?? g.teachers[0])
              ?.teacher_user_id;
            const leadTeacher =
              teachers.find((x) => x.id === leadTeacherId)?.full_name ?? t.groups.noTeacher;
            const fee = Number(g.monthly_fee ?? 0);
            return (
              <div className="card" key={g.id}>
                <div className="card__head">
                  <span className="avatar avatar--lg">{g.name.charAt(0)}</span>
                  <div style={{ minWidth: 0 }}>
                    <h3 style={{ fontSize: 17, fontFamily: "var(--display)" }}>{g.name}</h3>
                    <p className="tr">
                      {ageRangeLabel(g.min_age_months, g.max_age_months)} {t.groups.ageYears} ·{" "}
                      {leadTeacher}
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
                    <span style={{ fontSize: 13, color: "var(--ink-2)" }}>{t.groups.occupancy}</span>
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
                  {/* Avatar tizmasi — mockupdagidek dastlabki 7 ta bola */}
                  <div style={{ display: "flex", gap: 4, marginBottom: 20, minHeight: 27 }}>
                    {kids.slice(0, 7).map((name) => (
                      <span className="avatar avatar--sm" key={name} title={name}>
                        {initials(name)}
                      </span>
                    ))}
                    {count > 7 && (
                      <span
                        className="avatar avatar--sm"
                        style={{ background: "var(--surface-2)", color: "var(--ink-3)" }}
                      >
                        +{count - 7}
                      </span>
                    )}
                  </div>
                  <div style={{ display: "flex", gap: 32, flexWrap: "wrap" }}>
                    <div>
                      <small style={{ fontSize: 12, color: "var(--ink-3)" }}>
                        {t.groups.monthlyFee}
                      </small>
                      <div className="num" style={{ fontWeight: 600, fontSize: 16 }}>
                        {fee ? money(fee) : "—"}
                      </div>
                    </div>
                    <div>
                      <small style={{ fontSize: 12, color: "var(--ink-3)" }}>
                        {t.groups.monthlyRevenue}
                      </small>
                      <div
                        className="num"
                        style={{ fontWeight: 600, fontSize: 16, color: "var(--pos)" }}
                      >
                        {fee ? money(fee * count) : "—"}
                      </div>
                    </div>
                    {g.room_number && (
                      <div>
                        <small style={{ fontSize: 12, color: "var(--ink-3)" }}>
                          {t.groups.roomNumber}
                        </small>
                        <div className="num" style={{ fontWeight: 600, fontSize: 16 }}>
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
