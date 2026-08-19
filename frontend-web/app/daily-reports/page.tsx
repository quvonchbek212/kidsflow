"use client";

// Kunlik hisobot (4.4-bo'lim): tarbiyachi guruhdagi har bir bola uchun hisobot
// yozadi → qoralama saqlanadi → e'lon qilinadi. E'lon qilingach hisobot
// o'zgarmas bo'ladi va outbox orqali ota-onaga Telegram xabari yuboriladi.

import { useCallback, useEffect, useState, type ReactNode } from "react";

import { AppShell, useAppUI } from "@/components/AppShell";
import { useModal } from "@/components/ui/ModalProvider";
import { useToast } from "@/components/ui/ToastProvider";
import { useConfirm } from "@/components/ui/useConfirm";
import {
  ApiError,
  api,
  type DailyReport,
  type DailyReportInput,
  type DailyReportRosterRow,
  type Group,
  type MealStatus,
  type Mood,
} from "@/lib/api";
import { initials, isoDate } from "@/lib/format";
import { useAuth } from "@/lib/useAuth";

export default function DailyReportsPage(): ReactNode {
  const { user, loading } = useAuth();
  if (loading || !user) return <div className="boot-screen">KIDSFLOW</div>;
  return (
    <AppShell user={user} active="dailyReports">
      <DailyReportsContent />
    </AppShell>
  );
}

function DailyReportsContent(): ReactNode {
  const { t, branchId, setPageMeta } = useAppUI();
  const toast = useToast();
  const modal = useModal();
  const confirm = useConfirm();

  const [groups, setGroups] = useState<Group[]>([]);
  const [groupId, setGroupId] = useState("");
  const [date, setDate] = useState(isoDate(new Date()));
  const [roster, setRoster] = useState<DailyReportRosterRow[]>([]);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState("");

  useEffect(() => {
    setPageMeta({
      title: t.dailyReports.title,
      subtitle: t.dailyReports.subtitle,
    });
  }, [setPageMeta, t]);

  // Guruhlar tanlangan filial bo'yicha — filial almashsa tanlov ham qayta quriladi.
  useEffect(() => {
    if (!branchId) return;
    api
      .listGroups(branchId)
      .then((list) => {
        setGroups(list);
        setGroupId(list.length > 0 ? list[0].id : "");
      })
      .catch(() => {});
  }, [branchId]);

  const load = useCallback((): void => {
    if (!groupId || !date) {
      setRoster([]);
      setReady(true);
      return;
    }
    setReady(false);
    api
      .dailyReportRoster(groupId, date)
      .then(setRoster)
      .catch(() => setRoster([]))
      .finally(() => setReady(true));
  }, [groupId, date]);

  useEffect(load, [load]);

  const MEALS: { value: MealStatus; label: string }[] = [
    { value: "ATE_WELL", label: t.dailyReports.mealAteWell },
    { value: "ATE_SOME", label: t.dailyReports.mealAteSome },
    { value: "REFUSED", label: t.dailyReports.mealRefused },
  ];
  const MOODS: { value: Mood; label: string }[] = [
    { value: "HAPPY", label: t.dailyReports.moodHappy },
    { value: "CALM", label: t.dailyReports.moodCalm },
    { value: "TIRED", label: t.dailyReports.moodTired },
    { value: "SAD", label: t.dailyReports.moodSad },
    { value: "SICK", label: t.dailyReports.moodSick },
  ];

  // Forma modal ichida yashaydi va ModalProvider bitta `ReactNode` saqlaydi,
  // shuning uchun holat local o'zgaruvchilarda turadi va har o'zgarishda
  // qaytadan render qilinadi (children sahifasidagi forma bilan bir xil usul).
  function openForm(row: DailyReportRosterRow): void {
    const existing = row.report;
    const readOnly = existing?.is_published ?? false;

    let meal: MealStatus | "" = existing?.meal_status ?? "";
    let mood: Mood | "" = existing?.mood ?? "";
    let nap = existing?.nap_minutes != null ? String(existing.nap_minutes) : "";
    let activities = existing?.activities_text ?? "";
    let note = existing?.teacher_note ?? "";
    let summary = existing?.final_summary ?? "";
    let saving = false;
    let error = "";

    function payload(): DailyReportInput {
      return {
        meal_status: meal || null,
        mood: mood || null,
        nap_minutes: nap.trim() === "" ? null : Number(nap),
        activities_text: activities.trim() || null,
        teacher_note: note.trim() || null,
        final_summary: summary.trim() || null,
      };
    }

    async function save(): Promise<void> {
      saving = true;
      error = "";
      render();
      try {
        if (existing) {
          await api.updateDailyReport(existing.id, payload());
        } else {
          await api.createDailyReport(row.child_id, date, payload());
        }
        modal.close();
        toast.show(t.dailyReports.savedDraft);
        load();
      } catch (err) {
        error = err instanceof ApiError ? err.message : t.common.errTitle;
        saving = false;
        render();
      }
    }

    function render(): void {
      modal.open(
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!readOnly && !saving) void save();
          }}
        >
          {readOnly && <p className="hint">{t.dailyReports.publishedLocked}</p>}

          <div className="field">
            <label>{t.dailyReports.meal}</label>
            <div className="toolbar">
              {MEALS.map((m) => (
                <button
                  key={m.value}
                  type="button"
                  disabled={readOnly}
                  className={`chip${meal === m.value ? " on" : ""}`}
                  onClick={() => {
                    meal = meal === m.value ? "" : m.value;
                    render();
                  }}
                >
                  {m.label}
                </button>
              ))}
            </div>
          </div>

          <div className="field">
            <label>{t.dailyReports.mood}</label>
            <div className="toolbar">
              {MOODS.map((m) => (
                <button
                  key={m.value}
                  type="button"
                  disabled={readOnly}
                  className={`chip${mood === m.value ? " on" : ""}`}
                  onClick={() => {
                    mood = mood === m.value ? "" : m.value;
                    render();
                  }}
                >
                  {m.label}
                </button>
              ))}
            </div>
          </div>

          <div className="field">
            <label>
              {t.dailyReports.nap} ({t.dailyReports.napMinutes})
            </label>
            <input
              className="input"
              type="number"
              min={0}
              max={1440}
              readOnly={readOnly}
              defaultValue={nap}
              onChange={(e) => (nap = e.target.value)}
            />
          </div>

          <div className="field">
            <label>{t.dailyReports.activities}</label>
            <textarea
              className="input"
              rows={3}
              maxLength={4000}
              readOnly={readOnly}
              defaultValue={activities}
              onChange={(e) => (activities = e.target.value)}
            />
            <p className="hint">{t.dailyReports.activitiesHint}</p>
          </div>

          <div className="field">
            <label>{t.dailyReports.teacherNote}</label>
            <textarea
              className="input"
              rows={2}
              maxLength={2000}
              readOnly={readOnly}
              defaultValue={note}
              onChange={(e) => (note = e.target.value)}
            />
            <p className="hint">{t.dailyReports.teacherNoteHint}</p>
          </div>

          <div className="field">
            <label>{t.dailyReports.summary}</label>
            <textarea
              className="input"
              rows={3}
              maxLength={4000}
              readOnly={readOnly}
              defaultValue={summary}
              onChange={(e) => (summary = e.target.value)}
            />
            <p className="hint">{t.dailyReports.summaryHint}</p>
          </div>

          {error && <p className="error">{error}</p>}
          {!readOnly && (
            <button className="btn btn--full" type="submit" disabled={saving}>
              {saving ? t.common.saving : t.common.save}
            </button>
          )}
        </form>,
        {
          title: row.child_name,
          subtitle: `${t.dailyReports.title} — ${date}`,
          size: "default",
        },
      );
    }

    render();
  }

  async function onPublish(report: DailyReport): Promise<void> {
    // Backend ham tekshiradi, lekin bu yerda oldindan aytish tushunarliroq:
    // bo'sh hisobot e'lon qilinmaydi (matnsiz xabar ota-onaga foydasiz).
    if (!report.final_summary && !report.activities_text) {
      toast.show(t.dailyReports.needText, { type: "neg" });
      return;
    }
    const ok = await confirm({
      title: t.dailyReports.publishConfirm,
      body: t.dailyReports.publishConfirmBody,
      confirmLabel: t.dailyReports.publish,
      cancelLabel: t.common.cancel,
    });
    if (!ok) return;

    setBusy(report.id);
    try {
      await api.publishDailyReport(report.id);
      toast.show(t.dailyReports.publishedToast);
      load();
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t.common.errTitle, {
        type: "neg",
      });
    } finally {
      setBusy("");
    }
  }

  const publishedCount = roster.filter((r) => r.report?.is_published).length;
  const draftCount = roster.filter(
    (r) => r.report && !r.report.is_published,
  ).length;
  const missingCount = roster.filter((r) => !r.report).length;

  return (
    <>
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          marginBottom: 16,
        }}
      >
        <input
          className="input"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          style={{ marginTop: 0, width: "auto" }}
        />
      </div>

      <div className="card">
        <div className="att__sum">
          <div>
            {t.dailyReports.countDone}
            <b style={{ color: "var(--pos)" }}>{publishedCount}</b>
          </div>
          <div>
            {t.dailyReports.countDraft}
            <b style={{ color: "var(--warn)" }}>{draftCount}</b>
          </div>
          <div>
            {t.dailyReports.countMissing}
            <b style={{ color: "var(--ink-2)" }}>{missingCount}</b>
          </div>
        </div>

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
        </div>

        {!ready ? (
          <div className="panel-empty">{t.common.loading}</div>
        ) : roster.length === 0 ? (
          <div className="panel-empty">{t.common.empty}</div>
        ) : (
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>{t.common.name}</th>
                  <th>{t.common.status}</th>
                  <th className="r" />
                </tr>
              </thead>
              <tbody>
                {roster.map((row) => (
                  <tr key={row.child_id}>
                    <td>
                      <div className="cell-name">
                        <span className="avatar">
                          {initials(row.child_name)}
                        </span>
                        <b className="tr">{row.child_name}</b>
                      </div>
                    </td>
                    <td>
                      {!row.report ? (
                        <span className="badge badge--mute">
                          {t.dailyReports.notWritten}
                        </span>
                      ) : row.report.is_published ? (
                        <span className="badge badge--pos">
                          {t.dailyReports.published}
                        </span>
                      ) : (
                        <span className="badge badge--warn">
                          {t.dailyReports.draft}
                        </span>
                      )}
                    </td>
                    <td className="r">
                      <div className="row-actions">
                        <button
                          type="button"
                          className="btn btn-ghost btn--sm"
                          onClick={() => openForm(row)}
                        >
                          {!row.report
                            ? t.dailyReports.write
                            : row.report.is_published
                              ? t.dailyReports.view
                              : t.dailyReports.edit}
                        </button>
                        {row.report && !row.report.is_published && (
                          <button
                            type="button"
                            className="btn btn--sm"
                            disabled={busy === row.report.id}
                            onClick={() =>
                              void onPublish(row.report as DailyReport)
                            }
                          >
                            {busy === row.report.id
                              ? t.dailyReports.publishing
                              : t.dailyReports.publish}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
