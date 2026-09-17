"use client";

import { useEffect, useState, type ReactNode } from "react";

import { useAppUI } from "@/components/AppShell";
import { Sparkline } from "@/components/charts/Sparkline";
import { useToast } from "@/components/ui/ToastProvider";
import { ListSkeleton } from "@/components/ui/ListSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { GroupPicker, groupPickerLabels } from "@/components/ui/GroupPicker";
import { ApiError, api, type AttendanceRosterRow, type Group } from "@/lib/api";
import { initials, isoDate } from "@/lib/format";

type Status = "PRESENT" | "LATE" | "SICK" | "ABSENT" | "EXCUSED";

export default function AttendancePage(): ReactNode {
  return <AttendanceContent />;
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
  const [trend, setTrend] = useState<
    { label: string; present: number; total: number }[]
  >([]);

  // Guruhlar tanlangan filialga tegishli bo'lishi shart — aks holda boshqa
  // filial guruhiga davomat belgilash mumkin bo'lib qolardi.
  useEffect(() => {
    if (!branchId) return;
    api
      .listGroups(branchId)
      .then((list) => {
        setGroups(list);
        setGroupId(list.length > 0 ? list[0].id : "");
      })
      .catch(() => {
        setGroups([]);
        setGroupId("");
      })
      // Guruh topilmasa `load()` erta qaytadi va `ready` hech qachon `true`
      // bo'lmasdi — sahifa abadiy "Yuklanmoqda..." holatida qolardi.
      .finally(() => setReady(true));
  }, [branchId]);

  // Qaytgan funksiya eskirgan javobni bekor qiladi: guruh yoki sana tez
  // almashtirilsa, oldingisining kechikkan javobi yangi ro'yxat va
  // belgilanmagan holatlar ustiga yozilmasin (saqlashda noto'g'ri bolalar
  // ketib qolardi).
  function load(): (() => void) | undefined {
    if (!groupId || !date) {
      setRoster([]);
      setPending({});
      return undefined;
    }
    let cancelled = false;
    setReady(false);
    api
      .attendanceRoster(groupId, date)
      .then((rows) => {
        if (cancelled) return;
        setRoster(rows);
        const initial: Record<string, Status> = {};
        rows.forEach((r) => {
          if (r.status) initial[r.child_id] = r.status as Status;
        });
        setPending(initial);
      })
      .catch(() => {
        if (!cancelled) setRoster([]);
      })
      .finally(() => {
        if (!cancelled) setReady(true);
      });

    api
      .attendanceTrend(groupId, 11)
      .then((res) => {
        if (cancelled) return;
        setTrend(
          res.points.map((p) => ({
            label: p.attendance_date.slice(5),
            present: p.present_count,
            total: p.total_count,
          })),
        );
      })
      .catch(() => {
        if (!cancelled) setTrend([]);
      });
    return () => {
      cancelled = true;
    };
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
        entries: Object.entries(pending).map(([child_id, status]) => ({
          child_id,
          status,
        })),
      });
      toast.show(t.attendance.saved);
      load();
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t.common.errTitle, {
        type: "neg",
      });
    } finally {
      setSaving(false);
    }
  }

  const presentCount = Object.values(pending).filter(
    (s) => s === "PRESENT" || s === "LATE",
  ).length;
  const sickCount = Object.values(pending).filter((s) => s === "SICK").length;
  const absentCount = Object.values(pending).filter(
    (s) => s === "ABSENT" || s === "EXCUSED",
  ).length;
  const rate = roster.length
    ? Math.round((presentCount / roster.length) * 100)
    : 0;

  // Telefonda tugma ikki joyda chiqadi: yuqorida (kompyuter) va ro'yxat
  // ostida ekranga yopishgan panelda — ko'rinishini CSS boshqaradi.
  function renderSave(extraClass = ""): ReactNode {
    return (
      <button
        type="button"
        className={`btn btn-sm${extraClass}`}
        onClick={save}
        /* Guruh tanlanmagan bo'lsa `group_id` bo'sh ketib backend 422
           qaytarardi; belgilanmagan ro'yxatni saqlashning ma'nosi ham
           yo'q. */
        disabled={saving || !groupId || roster.length === 0}
      >
        {saving ? t.common.saving : t.attendance.saveAndSend}
      </button>
    );
  }

  return (
    <>
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
          <div className="att__save-top">{renderSave()}</div>
        </div>
        {/* Guruh, sana va "hammasi keldi" bitta qatorda: guruhlar ko'p bo'lsa
            ham qator o'ralmaydi, gorizontal suriladi (GroupPicker). */}
        <div className="toolbar toolbar--picker">
          <GroupPicker
            groups={groups}
            value={groupId}
            onChange={setGroupId}
            labels={groupPickerLabels(t)}
          />
          {/* Ko'rinadigan yorlig'i yo'q — nomi yordamchi texnologiyalar va
              sichqoncha uchun shu yerda beriladi. */}
          <input
            className="input toolbar__date"
            type="date"
            aria-label={t.common.date}
            title={t.common.date}
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
          <button
            type="button"
            className="btn-ghost btn btn-sm att__markall"
            onClick={markAll}
            disabled={roster.length === 0}
          >
            {t.attendance.markAll}
          </button>
        </div>
        {!ready ? (
          /* Bitta qatorli "Yuklanmoqda" o'rniga ro'yxat qolipi: ma'lumot
             kelganda blok birdan o'sib, sahifani pastga surib yubormaydi. */
          <ListSkeleton rows={8} />
        ) : groups.length === 0 ? (
          <div className="panel-empty">{t.attendance.noGroups}</div>
        ) : roster.length === 0 ? (
          <EmptyState title={t.common.empty} />
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
                        onClick={() =>
                          setPending((p) => ({ ...p, [row.child_id]: s }))
                        }
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
        {ready && roster.length > 0 && (
          <div className="att__savebar">{renderSave(" btn--full")}</div>
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
