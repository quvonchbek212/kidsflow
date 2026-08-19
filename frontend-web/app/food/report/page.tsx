"use client";

import { useEffect, useState, type ReactNode } from "react";

import { AppShell, useAppUI } from "@/components/AppShell";
import { api, type StockReport } from "@/lib/api";
import { money } from "@/lib/format";
import { useAuth } from "@/lib/useAuth";

export default function FoodReportPage(): ReactNode {
  const { user, loading } = useAuth();
  if (loading || !user) return <div className="boot-screen">KIDSFLOW</div>;
  return (
    <AppShell user={user}>
      <ReportContent />
    </AppShell>
  );
}

function ReportContent(): ReactNode {
  const { t, branchId, period, setPageMeta } = useAppUI();

  useEffect(() => {
    setPageMeta({ title: t.food.reportTitle, subtitle: t.food.reportSub });
  }, [setPageMeta, t]);
  const [report, setReport] = useState<StockReport | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!branchId) return;
    setReady(false);
    api
      .stockReport(branchId, period.start, period.end)
      .then(setReport)
      .catch(() => setReport(null))
      .finally(() => setReady(true));
  }, [branchId, period]);

  return (
    <>
      {report && report.rows.length > 0 && (
        <div className="kpi mb-4" style={{ maxWidth: 280 }}>
          <div className="kpi__top">
            <span className="kpi__label">{t.food.totalValue}</span>
          </div>
          <div className="kpi__value">{money(report.total_value)}</div>
        </div>
      )}

      <div className="card">
        <div className="card__head">
          <div>
            <h3>{t.food.reportTitle}</h3>
            <p>
              {period.start} — {period.end}
            </p>
          </div>
        </div>
        {!ready ? (
          <div className="panel-empty">{t.common.loading}</div>
        ) : !report || report.rows.length === 0 ? (
          <div className="panel-empty">{t.common.empty}</div>
        ) : (
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>{t.common.name}</th>
                  <th className="r">{t.food.opening}</th>
                  <th className="r">{t.food.stockIn}</th>
                  <th className="r">{t.food.stockOut}</th>
                  <th className="r">{t.food.closing}</th>
                  <th className="r">{t.food.value}</th>
                </tr>
              </thead>
              <tbody>
                {report.rows.map((row) => (
                  <tr key={row.product_id}>
                    <td>
                      <b>{row.product_name}</b>
                    </td>
                    <td className="r num" style={{ color: "var(--ink-2)" }}>
                      {row.opening_stock} {row.unit}
                    </td>
                    <td className="r num" style={{ color: "var(--pos)" }}>
                      {row.stock_in} {row.unit}
                    </td>
                    <td className="r num" style={{ color: "var(--neg)" }}>
                      {row.stock_out} {row.unit}
                    </td>
                    <td className="r num" style={{ fontWeight: 600 }}>
                      {row.closing_stock} {row.unit}
                    </td>
                    <td className="r num">{money(row.closing_value)}</td>
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
