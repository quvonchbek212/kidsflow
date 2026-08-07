"use client";

import { useEffect, useState, type ReactNode } from "react";

import { AppShell, useAppUI } from "@/components/AppShell";
import { Sparkline } from "@/components/charts/Sparkline";
import { useToast } from "@/components/ui/ToastProvider";
import { ApiError, api, type AttendanceRosterRow, type Group } from "@/lib/api";
import { initials, isoDate } from "@/lib/format";
import { useAuth } from "@/lib/useAuth";

type Status = "PRESENT" | "LATE" | "SICK" | "ABSENT" | "EXCUSED";

export default function AttendancePage(): ReactNode {
  const { user, loading } = useAuth();
  if (loading || !user) return <div className="boot-screen">KIDSFLOW</div>;
  return (
    <AppShell user={user} active="attendance">
      <AttendanceContent />
    </AppShell>
  );
}

function AttendanceContent(): ReactNode {
  const { t, branchId, setPageMeta } = useAppUI();

  useEffect(() => {
    setPageMeta({ title: t.attendance.title, subtitle: t.attendance.subtitle });
  }, [setPageMeta, t]);
  const toast = useToast();
  const [groups, setGroups] = useState<Group[]>([]);
  const [groupId, setGroupId] = useState("");
  const [date, setDate] = useState(isoDate(new Date()));
  const [roster, setRoster] = useState<AttendanceRosterRow[]>([]);
  const [pending, setPending] = useState<Record<string, Status>>({});
  const [ready, setReady] = useState(false);
  const [saving, setSaving] = useState(false);
  const [trend, setTrend] = useState<{ label: string; present: number; total: number }[]>([]);

  // Guruhlar tanlangan filialga tegishli bo'lishi shart — aks holda boshqa
  // filial guruhiga davomat belgilash mumkin bo'lib qolardi.
  useEffect(() => {
    if (!branchId) return;
    api.listGroups(branchId).then((list) => {
      setGroups(list);
      setGroupId(list.length > 0 ? list[0].id : "");
    });
  }, [branchId]);

  function load(): void {
    if (!groupId || !date) return;
    setReady(false);
    api
      .attendanceRoster(groupId, date)
      .then((rows) => {
        setRoster(rows);
        const initial: Record<string, Status> = {};
        rows.forEach((r) => {
          if (r.status) initial[r.child_id] = r.status as Status;
        });
        setPending(initial);
      })
      .catch(() => setRoster([]))
      .finally(() => setReady(true));

    api
      .attendanceTrend(groupId, 11)
      .then((res) =>
        setTrend(
          res.points.map((p) => ({
            label: p.attendance_date.slice(5),
            present: p.present_count,
            total: p.total_count,
          })),
        ),
      )
      .catch(() => setTrend([]));
  }

  useEffect(load, [groupId, date]);

  function statusLabel(s: Status): string {
    if (s === "PRESENT") return t.attendance.present;
    if (s === "ABSENT") return t.attendance.absent;
    if (s === "LATE") return t.attendance.late;
    if (s === "EXCUSED") return t.attendance.excused;
    return t.attendance.sick;
  }

  function markAll(): void {
    const next: Record<string, Status> = {};
    roster.forEach((r) => (next[r.child_id] = "PRESENT"));
    setPending(next);
  }

  async function save(): Promise<void> {
    setSaving(true);
    try {
      await api.markAttendanceBulk({
        group_id: groupId,
        attendance_date: date,
        entries: Object.entries(pending).map(([child_id, status]) => ({ child_id, status })),
      });
      toast.show(t.attendance.saved);
      load();
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t.common.errTitle, { type: "neg" });
    } finally {
      setSaving(false);
    }
  }

  const presentCount = Object.values(pending).filter((s) => s === "PRESENT" || s === "LATE").length;
  const sickCount = Object.values(pending).filter((s) => s === "SICK").length;
  const absentCount = Object.values(pending).filter(
    (s) => s === "ABSENT" || s === "EXCUSED",
  ).length;
  const rate = roster.length ? Math.round((presentCount / roster.length) * 100) : 0;

  return (
    <>
      {/* Sana tanlagich; guruh esa mockupdagidek chip qatorida. */}
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 16 }}>
        <input
          className="input"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          style={{ marginTop: 0, width: "auto" }}
        />
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="att__sum">
          <div>
            {t.attendance.present}
            <b style={{ color: "var(--pos)" }}>{presentCount}</b>
          </div>
          <div>
            {t.attendance.sick}
            <b style={{ color: "var(--warn)" }}>{sickCount}</b>
          </div>
          <div>
            {t.attendance.absent}
            <b style={{ color: "var(--neg)" }}>{absentCount}</b>
          </div>
          <div>
            {t.attendance.rate}
            <b>{rate}%</b>
          </div>
          <div style={{ marginLeft: "auto", alignSelf: "center" }}>
            <button type="button" className="btn btn-sm" onClick={save} disabled={saving}>
              {saving ? t.common.saving : t.attendance.saveAndSend}
            </button>
          </div>
        </div>
        {/* Guruh tanlash — mockupdagi chip qatori */}
        <div className="toolbar">
          {groups.map((g) => (
            <button
              key={g.id}
              type="button"
              className={`chip${g.id === groupId ? " on" : ""}`}
              onClick={() => setGroupId(g.id)}
            >
              {g.name}
            </button>
          ))}
          <button
            type="button"
            className="btn-ghost btn btn-sm"
            style={{ marginLeft: "auto" }}
            onClick={markAll}
          >
            {t.attendance.markAll}
          </button>
        </div>
        {!ready ? (
          <div className="panel-empty">{t.common.loading}</div>
        ) : roster.length === 0 ? (
          <div className="panel-empty">{t.common.empty}</div>
        ) : (
          <div>
            {roster.map((row) => {
              const current = pending[row.child_id];
              return (
                <div className="att__row" key={row.child_id}>
                  <div className="att__who">
                    <span className="avatar">{initials(row.child_name)}</span>
                    <b className="tr">{row.child_name}</b>
                  </div>
                  <div className="att__opts">
                    {(["PRESENT", "ABSENT", "SICK"] as Status[]).map((s) => (
                      <button
                        key={s}
                        type="button"
                        className={`att__btn${current === s ? " on" : ""}`}
                        data-v={s}
                        onClick={() => setPending((p) => ({ ...p, [row.child_id]: s }))}
                      >
                        {statusLabel(s)}
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {trend.length > 0 && (
        <div className="card">
          <div className="card__head">
            <div>
              <h3>{t.attendance.trend}</h3>
              <p>{t.attendance.trendSub}</p>
            </div>
          </div>
          <div className="card__body">
            {/* SVG viewBox qat'iy (560×150) — cheklamasak keng kartochkada
                o'lchamlar bilan birga o'q yozuvlari ham kattalashib ketadi. */}
            <div style={{ maxWidth: 680 }}>
              <Sparkline points={trend} />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
