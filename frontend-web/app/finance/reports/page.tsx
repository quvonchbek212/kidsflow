"use client";

import { useEffect, useState, type ReactNode } from "react";

import { useAppUI } from "@/components/AppShell";
import { IconDownload } from "@/components/icons";
import { EmptyState } from "@/components/ui/EmptyState";
import { api, type FinanceDashboard, type Group } from "@/lib/api";
import { downloadCsv } from "@/lib/csv";
import { mlnf, money } from "@/lib/format";

export default function FinanceReportsPage(): ReactNode {
  return <ReportsContent />;
}

/** P&L jadvalining bitta qatori. `kind` ko'rinishni belgilaydi. */
interface PlRow {
  label: string;
  amount: number;
  kind?: "section" | "sum" | "total";
  /** React kaliti. Nomlar takrorlanishi mumkin (bir xil nomli ikki guruh),
   *  shuning uchun mavjud bo'lganda barqaror ID ishlatiladi. */
  key?: string;
}

function ReportsContent(): ReactNode {
  const { t, branchId, period, setPageMeta } = useAppUI();

  useEffect(() => {
    setPageMeta({
      title: t.reports.title,
      subtitle: `${t.reports.subtitle} · ${period.start} — ${period.end}`,
    });
  }, [setPageMeta, t, period]);

  const [finance, setFinance] = useState<FinanceDashboard | null>(null);
  const [groups, setGroups] = useState<Group[]>([]);
  const [ready, setReady] = useState(false);

  function load(): void {
    // Filialsiz chaqirilsa hisobot ikkala filialning yig'indisini ko'rsatardi.
    if (!branchId) return;
    setReady(false);
    Promise.all([
      api.dashboard(period.start, period.end, branchId),
      api.listGroups(branchId),
    ])
      .then(([dash, groupList]) => {
        setFinance(dash);
        setGroups(groupList);
      })
      .catch(() => setFinance(null))
      .finally(() => setReady(true));
  }

  useEffect(load, [branchId, period]);

  const groupName = (id: string) => groups.find((g) => g.id === id)?.name ?? id;

  if (!ready || !finance) {
    return (
      <div className="card">
        <div className="card__body" style={{ paddingTop: "var(--s5)" }}>
          <div className="sk sk-line" style={{ width: "40%" }} />
          <div className="sk sk-block" style={{ height: 220, marginTop: 18 }} />
        </div>
      </div>
    );
  }

  const totalRevenue = Number(finance.accrual_revenue);
  const totalExpenses = Number(finance.expenses);
  const net = totalRevenue - totalExpenses;

  // Daromad bo'limi guruh kesimidan tuziladi — backend boshqa kesim bermaydi,
  // shuning uchun mockupdagi "tarif turlari" o'rniga guruhlar turadi.
  const revenueRows: PlRow[] = finance.revenue_by_group.map((r) => ({
    key: r.group_id,
    label: groupName(r.group_id),
    amount: Number(r.total),
  }));
  const expenseRows: PlRow[] = finance.expenses_by_category.map((c) => ({
    label: c.category_name,
    amount: Number(c.total),
  }));

  const plRows: PlRow[] = [
    { label: t.reports.revenueSection, amount: 0, kind: "section" },
    ...revenueRows,
    { label: t.reports.totalRevenue, amount: totalRevenue, kind: "sum" },
    { label: t.reports.expenseSection, amount: 0, kind: "section" },
    ...expenseRows,
    { label: t.reports.totalExpenses, amount: totalExpenses, kind: "sum" },
    { label: t.reports.netTotal, amount: net, kind: "total" },
  ];

  const maxGroupRevenue = Math.max(1, ...revenueRows.map((r) => r.amount));

  const periodSuffix = `${period.start}_${period.end}`;
  const readyReports: [string, () => void][] = [
    [
      t.reports.repPl,
      () =>
        downloadCsv(`${t.reports.repPl}_${periodSuffix}`, [
          [t.common.name, t.common.sum],
          ...plRows
            .filter((r) => r.kind !== "section")
            .map((r) => [r.label, r.amount] as (string | number)[]),
        ]),
    ],
    [
      t.reports.repRevenueByGroup,
      () =>
        downloadCsv(`${t.reports.repRevenueByGroup}_${periodSuffix}`, [
          [t.groups.groupName, t.reports.revenue],
          ...revenueRows.map((r) => [r.label, r.amount] as (string | number)[]),
        ]),
    ],
    [
      t.reports.repExpenses,
      () =>
        downloadCsv(`${t.reports.repExpenses}_${periodSuffix}`, [
          [t.expenses.category, t.common.sum],
          ...expenseRows.map((r) => [r.label, r.amount] as (string | number)[]),
        ]),
    ],
  ];

  return (
    <>
      {/* Sarlavha topbarda; chop etishda esa `#printHead` chiqadi. */}
      <div id="printHead">
        <h2>{t.reports.title}</h2>
        <p>
          {t.reports.plTitle} · {period.start} — {period.end}
        </p>
      </div>

      <div className="grid g-32 mb-4">
        <div className="card">
          <div className="card__head">
            <div>
              <h3>{t.reports.plTitle}</h3>
              <p>
                {period.start} — {period.end}
              </p>
            </div>
            <button
              type="button"
              className="btn-ghost btn btn-sm"
              style={{ marginLeft: "auto" }}
              onClick={() => window.print()}
            >
              {t.common.print}
            </button>
            <button
              type="button"
              className="btn-ghost btn btn-sm"
              style={{ marginLeft: 8 }}
              onClick={readyReports[0][1]}
            >
              {t.reports.downloadCsv}
            </button>
          </div>
          <div className="card__body--flush">
            <table className="tbl">
              <tbody>
                {plRows.map((row, i) =>
                  row.kind === "section" ? (
                    <tr
                      key={`${row.label}-${i}`}
                      style={{ background: "var(--surface-2)" }}
                    >
                      <td
                        colSpan={2}
                        style={{
                          fontSize: 11,
                          fontWeight: 600,
                          letterSpacing: ".08em",
                          color: "var(--ink-3)",
                          padding: "10px var(--s5)",
                        }}
                      >
                        {row.label}
                      </td>
                    </tr>
                  ) : (
                    <tr
                      key={`${row.label}-${i}`}
                      style={
                        row.kind === "total"
                          ? {
                              fontWeight: 700,
                              fontSize: 16,
                              background: "var(--brand-bg)",
                            }
                          : row.kind === "sum"
                            ? {
                                fontWeight: 600,
                                borderTop: "1px solid var(--line)",
                              }
                            : undefined
                      }
                    >
                      <td>{row.label}</td>
                      <td
                        className="r num"
                        style={{
                          color:
                            row.kind === "total"
                              ? net >= 0
                                ? "var(--pos)"
                                : "var(--neg)"
                              : undefined,
                          fontWeight: row.kind ? 600 : 400,
                        }}
                      >
                        {money(row.amount)}
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <div className="card mb-4">
            <div className="card__head">
              <div>
                <h3>{t.reports.revenueByGroup}</h3>
              </div>
            </div>
            <div className="card__body">
              {revenueRows.length === 0 ? (
                <EmptyState title={t.common.empty} />
              ) : (
                revenueRows.map((row) => (
                  <div key={row.key ?? row.label} style={{ marginBottom: 16 }}>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        fontSize: 13,
                        marginBottom: 6,
                      }}
                    >
                      <span>{row.label}</span>
                      <b className="num">
                        {mlnf(row.amount)} {t.common.mln}
                      </b>
                    </div>
                    <div className="bar">
                      <i
                        style={{
                          width: `${(row.amount / maxGroupRevenue) * 100}%`,
                        }}
                      />
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="card">
            <div className="card__head">
              <div>
                <h3>{t.reports.readyReports}</h3>
              </div>
            </div>
            <div
              className="card__body"
              style={{ display: "flex", flexDirection: "column", gap: 8 }}
            >
              {readyReports.map(([label, run]) => (
                <button
                  key={label}
                  type="button"
                  className="btn-ghost btn btn--full"
                  style={{ justifyContent: "space-between" }}
                  onClick={run}
                >
                  {label}
                  <IconDownload size={15} />
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
