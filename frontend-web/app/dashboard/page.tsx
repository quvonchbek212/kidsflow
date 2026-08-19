"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { BarChart, type BarChartMonth } from "@/components/charts/BarChart";
import { Donut } from "@/components/charts/Donut";
import { Sparkline } from "@/components/charts/Sparkline";
import { AppShell, useAppUI } from "@/components/AppShell";
import {
  IconCalendar,
  IconTrendingDown,
  IconUsers,
  IconWallet,
} from "@/components/icons";
import { api, type FinanceDashboard, type Invoice } from "@/lib/api";
import { downloadCsv } from "@/lib/csv";
import {
  initials,
  invoiceStatus,
  invoiceTone,
  isoDate,
  lastMonths,
  money,
  moneyPlain,
  mlnf,
} from "@/lib/format";
import { useAuth } from "@/lib/useAuth";

export default function DashboardPage(): ReactNode {
  const { user, loading } = useAuth();
  if (loading || !user) return <div className="boot-screen">KIDSFLOW</div>;
  return (
    <AppShell user={user} active="dashboard">
      <DashboardContent />
    </AppShell>
  );
}

interface TodayAttendance {
  present: number;
  total: number;
  sick: number;
  absent: number;
}

function DashboardContent(): ReactNode {
  const { t, branchId, period, setPageMeta } = useAppUI();
  const router = useRouter();

  useEffect(() => {
    setPageMeta({ title: t.dashboard.title, subtitle: t.dashboard.subtitle });
  }, [setPageMeta, t]);
  const [finance, setFinance] = useState<FinanceDashboard | null>(null);
  const [months, setMonths] = useState<BarChartMonth[]>([]);
  const [today, setToday] = useState<TodayAttendance>({
    present: 0,
    total: 0,
    sick: 0,
    absent: 0,
  });
  const [recentPaid, setRecentPaid] = useState<Invoice[]>([]);
  const [childNames, setChildNames] = useState<Record<string, string>>({});
  const [childGroups, setChildGroups] = useState<Record<string, string>>({});
  const [debtorCount, setDebtorCount] = useState(0);
  const [trend, setTrend] = useState<
    { label: string; present: number; total: number }[]
  >([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!branchId) return;
    let cancelled = false;
    setReady(false);

    Promise.all([
      api.dashboard(period.start, period.end, branchId),
      api.listGroups(branchId),
      Promise.all(
        lastMonths(6).map((m) =>
          api
            .dashboard(m.start, m.end, branchId)
            .then((d) => ({
              label: m.label,
              income: Number(d.accrual_revenue),
              outcome: Number(d.expenses),
            }))
            .catch(() => ({ label: m.label, income: 0, outcome: 0 })),
        ),
      ),
    ])
      .then(async ([dash, groupList, monthly]) => {
        if (cancelled) return;
        setFinance(dash);
        setMonths(monthly);
        // Filial kesimini server bajaradi; bu yerda faqat faollari qoladi.
        const branchGroups = groupList.filter((g) => g.is_active);

        const rosters = await Promise.all(
          branchGroups.map((g) =>
            api.attendanceRoster(g.id, isoDate(new Date())).catch(() => []),
          ),
        );
        let present = 0;
        let total = 0;
        let sick = 0;
        let absent = 0;
        const groupOfChild: Record<string, string> = {};
        for (let i = 0; i < rosters.length; i++) {
          for (const row of rosters[i]) {
            groupOfChild[row.child_id] = branchGroups[i].name;
            total += 1;
            if (row.status === "PRESENT" || row.status === "LATE") present += 1;
            else if (row.status === "SICK") sick += 1;
            else if (row.status === "ABSENT") absent += 1;
          }
        }
        if (!cancelled) {
          setToday({ present, total, sick, absent });
          setChildGroups(groupOfChild);
        }

        // Davomat tendensiyasi: backendda faqat guruh kesimida bor, shuning
        // uchun barcha guruhlar bo'yicha kunma-kun qo'shib chiqiladi.
        const trends = await Promise.all(
          branchGroups.map((g) =>
            api.attendanceTrend(g.id, 11).catch(() => null),
          ),
        );
        const byDay = new Map<string, { present: number; total: number }>();
        for (const tr of trends) {
          for (const p of tr?.points ?? []) {
            const acc = byDay.get(p.attendance_date) ?? {
              present: 0,
              total: 0,
            };
            acc.present += p.present_count;
            acc.total += p.total_count;
            byDay.set(p.attendance_date, acc);
          }
        }
        if (!cancelled) {
          setTrend(
            [...byDay.entries()]
              .sort((a, b) => a[0].localeCompare(b[0]))
              .map(([date, acc]) => ({ label: date.slice(8), ...acc })),
          );
        }

        const [children, invoices] = await Promise.all([
          api.listChildren(branchId).catch(() => []),
          api
            .branchInvoices(branchId, period.start.slice(0, 7) + "-01")
            .catch(() => []),
        ]);
        if (!cancelled) {
          const names: Record<string, string> = {};
          for (const c of children) names[c.id] = c.full_name;
          setChildNames(names);
          setRecentPaid(
            invoices.filter((i) => Number(i.paid_amount) > 0).slice(0, 8),
          );
          // Qarzdor oilalar soni — qoldig'i bor hisob-fakturalar bo'yicha.
          setDebtorCount(
            new Set(
              invoices
                .filter((i) => Number(i.outstanding_amount) > 0)
                .map((i) => i.child_id),
            ).size,
          );
        }
      })
      // Ruxsat yetmasa (masalan tarbiyachi) so'rov 403 qaytaradi — bu ushlanmasa
      // brauzerda "unhandled rejection" bo'lib sahifani buzadi.
      .catch(() => {
        if (!cancelled) setFinance(null);
      })
      .finally(() => {
        if (!cancelled) setReady(true);
      });

    return () => {
      cancelled = true;
    };
  }, [branchId, period]);

  const netProfit = finance
    ? Number(finance.accrual_revenue) - Number(finance.expenses)
    : 0;
  const margin =
    finance && Number(finance.accrual_revenue) > 0
      ? ((netProfit / Number(finance.accrual_revenue)) * 100).toFixed(1)
      : "0";
  const breakeven = finance?.break_even;

  // Eng katta xarajat kategoriyasi va 30 kundan ortiq kechikkan qarz —
  // mini-kartochkalarning pastki qatorida ko'rsatiladi (mockupdagidek).
  const biggestCategory =
    finance && finance.expenses_by_category.length > 0
      ? finance.expenses_by_category.reduce((a, b) =>
          Number(b.total) > Number(a.total) ? b : a,
        )
      : null;
  const over30 = (finance?.aging ?? [])
    .filter((a) => a.label === "aging_31_60" || a.label === "aging_60_plus")
    .reduce((sum, a) => sum + Number(a.total), 0);

  // Mini-kartochkalardagi o'zgarish nishoni — o'tgan oyga nisbatan foiz.
  // `months` oxirgi 6 oyni beradi, oxirgisi joriy oy.
  const pctChange = (key: "income" | "outcome"): number | null => {
    if (months.length < 2) return null;
    const prev = months[months.length - 2][key];
    const cur = months[months.length - 1][key];
    if (!prev) return null;
    return ((cur - prev) / prev) * 100;
  };
  // "Bitta bola bo'yicha hisob" qatorlari: o'zgaruvchan kategoriyalar, keyin
  // eng katta ikkita doimiy kategoriya, qolgani "boshqa"ga yig'iladi.
  const kids = Math.max(1, breakeven?.active_children ?? 1);
  const cats = finance?.expenses_by_category ?? [];
  const variableCats = cats.filter((c) => c.is_variable);
  const fixedCats = [...cats.filter((c) => !c.is_variable)].sort(
    (a, b) => Number(b.total) - Number(a.total),
  );
  const namedFixed = fixedCats.slice(0, 2);
  const restFixed = fixedCats.slice(2).reduce((s, c) => s + Number(c.total), 0);
  const unitRows: { label: string; perChild: number }[] = [
    ...variableCats.map((c) => ({
      label: c.category_name,
      perChild: Number(c.total) / kids,
    })),
    ...namedFixed.map((c) => ({
      label: c.category_name,
      perChild: Number(c.total) / kids,
    })),
    ...(restFixed > 0
      ? [{ label: t.dashboard.uOther, perChild: restFixed / kids }]
      : []),
  ];
  const netPerChild =
    Number(breakeven?.fee_per_child ?? 0) -
    unitRows.reduce((s, r) => s + r.perChild, 0);

  const changeBadge = (key: "income" | "outcome"): ReactNode => {
    const pct = pctChange(key);
    if (pct === null) return null;
    // Daromadning o'sishi yaxshi, xarajatniki emas — rang shunga qarab.
    const good = key === "income" ? pct >= 0 : pct <= 0;
    return (
      <span className={`badge badge--${good ? "pos" : "warn"}`}>
        <span className="dot" />
        {pct >= 0 ? "+" : ""}
        {pct.toFixed(1)}%
      </span>
    );
  };

  if (!ready) {
    return (
      <div className="bento">
        <div className="kpi b-6 r-2" style={{ minHeight: 240 }}>
          <div className="sk sk-line" style={{ width: "40%" }} />
          <div
            className="sk"
            style={{ height: 48, width: "60%", margin: "16px 0" }}
          />
        </div>
        <div className="kpi b-3" style={{ minHeight: 110 }}>
          <div className="sk sk-line" style={{ width: "60%" }} />
        </div>
        <div className="kpi b-3" style={{ minHeight: 110 }}>
          <div className="sk sk-line" style={{ width: "60%" }} />
        </div>
      </div>
    );
  }

  return (
    <div className="bento stagger">
      {/* Hero KPI — mockupdagidek pastida uch ustunli xulosa chizig'i bor */}
      <div
        className="kpi kpi--accent b-6 r-2"
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
        }}
      >
        <div className="kpi__top">
          <span className="kpi__label">{t.dashboard.netProfit}</span>
          <span className="badge">
            {margin}% {t.dashboard.margin}
          </span>
        </div>
        <div>
          <div className="kpi__value" style={{ fontSize: 52 }}>
            {mlnf(netProfit)}
            <span className="kpi__unit" style={{ fontSize: 16 }}>
              {t.common.mln} {t.common.sum}
            </span>
          </div>
          {breakeven && (
            <div className="kpi__foot" style={{ marginTop: "var(--s4)" }}>
              {t.dashboard.aboveBreakeven}:{" "}
              {mlnf(
                Number(finance!.accrual_revenue) -
                  Number(breakeven.breakeven_revenue),
              )}{" "}
              {t.common.mln}
            </div>
          )}
        </div>
        <div
          style={{
            marginTop: "var(--s5)",
            paddingTop: "var(--s4)",
            borderTop: "1px solid rgba(255,255,255,.18)",
            display: "flex",
            gap: "var(--s6)",
            flexWrap: "wrap",
          }}
        >
          {[
            [t.dashboard.income, mlnf(finance?.accrual_revenue ?? 0)],
            [t.dashboard.outcome, mlnf(finance?.expenses ?? 0)],
            [
              t.dashboard.breakeven,
              breakeven ? mlnf(breakeven.breakeven_revenue) : "—",
            ],
          ].map(([label, value]) => (
            <div key={label}>
              <div
                style={{
                  fontSize: 11,
                  color: "rgba(255,255,255,.65)",
                  fontWeight: 600,
                }}
              >
                {label}
              </div>
              <div
                className="num"
                style={{ fontSize: 20, fontWeight: 600, marginTop: 3 }}
              >
                {value} {t.common.mln}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="kpi b-3">
        <div className="mini">
          <div>
            <div className="mini__top">
              <span className="mini__lbl">{t.dashboard.income}</span>
              {changeBadge("income")}
            </div>
            <div className="mini__big">
              {mlnf(finance?.accrual_revenue ?? 0)}
              <span className="kpi__unit">{t.common.mln}</span>
            </div>
          </div>
          <div className="mini__sub">
            {t.dashboard.collectedLabel}: {mlnf(finance?.cash_collected ?? 0)}{" "}
            {t.common.mln}
          </div>
        </div>
      </div>

      <div className="kpi b-3">
        <div className="mini">
          <div>
            <div className="mini__top">
              <span className="mini__lbl">{t.dashboard.outcome}</span>
              {changeBadge("outcome")}
            </div>
            <div className="mini__big">
              {mlnf(finance?.expenses ?? 0)}
              <span className="kpi__unit">{t.common.mln}</span>
            </div>
          </div>
          <div className="mini__sub">
            {biggestCategory
              ? `${t.dashboard.biggest}: ${biggestCategory.category_name} ${mlnf(biggestCategory.total)} ${t.common.mln}`
              : "—"}
          </div>
        </div>
      </div>

      <div className="kpi b-3">
        <div className="mini">
          <div>
            <div className="mini__top">
              <span className="mini__lbl">{t.dashboard.debt}</span>
              {debtorCount > 0 && (
                <span className="badge badge--neg">
                  <span className="dot" />
                  {debtorCount} {t.dashboard.families}
                </span>
              )}
            </div>
            <div className="mini__big" style={{ color: "var(--neg)" }}>
              {mlnf(finance?.outstanding ?? 0)}
              <span className="kpi__unit">{t.common.mln}</span>
            </div>
          </div>
          <div className="mini__sub">
            {mlnf(over30)} {t.common.mln} — {t.dashboard.over30}
          </div>
        </div>
      </div>

      <div className="kpi b-3">
        <div className="mini">
          <div>
            <div className="mini__top">
              <span className="mini__lbl">{t.dashboard.todayAttendance}</span>
              {today.total > 0 && (
                <span className="badge badge--pos">
                  {Math.round((today.present / today.total) * 100)}%
                </span>
              )}
            </div>
            <div className="mini__big">
              {today.present}
              <span className="kpi__unit">/ {today.total}</span>
            </div>
            <div className="bar" style={{ marginTop: "var(--s3)" }}>
              <i
                style={{
                  width: today.total
                    ? `${(today.present / today.total) * 100}%`
                    : "0%",
                }}
              />
            </div>
          </div>
          <div className="mini__sub">
            <b style={{ color: "var(--warn)" }}>{today.sick}</b>{" "}
            {t.dashboard.sick} ·{" "}
            <b style={{ color: "var(--neg)" }}>{today.absent}</b>{" "}
            {t.dashboard.absent}
          </div>
        </div>
      </div>

      <div className="card b-8">
        <div className="card__head">
          <div>
            <h3>{t.dashboard.chartTitle}</h3>
            <p>{t.dashboard.chartSub}</p>
          </div>
          <button
            type="button"
            className="btn-ghost btn btn-sm"
            style={{ marginLeft: "auto" }}
            onClick={() =>
              downloadCsv(t.dashboard.chartTitle, [
                [
                  t.common.period,
                  t.dashboard.income,
                  t.dashboard.outcome,
                  t.dashboard.netProfit,
                ],
                ...months.map((m) => [
                  m.label,
                  m.income,
                  m.outcome,
                  m.income - m.outcome,
                ]),
              ])
            }
          >
            {t.reports.downloadCsv}
          </button>
        </div>
        <div className="card__body">
          <BarChart
            data={months}
            breakeven={breakeven ? Number(breakeven.breakeven_revenue) : null}
            incomeLabel={t.dashboard.income}
            outcomeLabel={t.dashboard.outcome}
            breakevenLabel={t.dashboard.breakeven}
          />
          <div className="legend">
            <span>
              <i style={{ background: "var(--brand)" }} /> {t.dashboard.income}
            </span>
            <span>
              <i style={{ background: "var(--line)" }} /> {t.dashboard.outcome}
            </span>
            {breakeven && (
              <span>
                <i className="dash" /> {t.dashboard.breakeven}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="card b-4">
        <div className="card__head">
          <div>
            <h3>{t.dashboard.expenseStructure}</h3>
            <p>
              {period.start} — {period.end}
            </p>
          </div>
        </div>
        <div className="card__body">
          {finance && finance.expenses_by_category.length > 0 ? (
            <Donut
              rows={finance.expenses_by_category.map((c) => ({
                label: c.category_name,
                total: Number(c.total),
              }))}
              totalLabel={t.common.all}
            />
          ) : (
            <div className="panel-empty">{t.common.empty}</div>
          )}
        </div>
      </div>

      <div className="card b-4">
        <div className="card__head">
          <div>
            <h3>{t.dashboard.agingTitle}</h3>
            <p>{t.dashboard.agingSub}</p>
          </div>
        </div>
        <div className="card__body">
          {finance?.aging.map((row) => {
            const totalDebt =
              finance.aging.reduce((s, r) => s + Number(r.total), 0) || 1;
            const label =
              row.label === "not_due"
                ? t.dashboard.notDue
                : row.label === "aging_1_30"
                  ? t.dashboard.aging1_30
                  : row.label === "aging_31_60"
                    ? t.dashboard.aging31_60
                    : t.dashboard.aging60plus;
            const color =
              row.label === "not_due"
                ? "var(--brand-2)"
                : row.label === "aging_1_30"
                  ? "var(--warn)"
                  : row.label === "aging_31_60"
                    ? "var(--warn-2)"
                    : "var(--neg)";
            return (
              <div
                className="aging__row"
                key={row.label}
                style={{ marginBottom: 14 }}
              >
                <b>{label}</b>
                <span className="num">{money(row.total)}</span>
                <div className="aging__bar">
                  <i
                    style={{
                      width: `${(Number(row.total) / totalDebt) * 100}%`,
                      background: color,
                    }}
                  />
                </div>
              </div>
            );
          })}
          <button
            type="button"
            className="btn-ghost btn btn--full"
            style={{ marginTop: 8 }}
            onClick={() => router.push("/parents?audience=debtors")}
          >
            {t.dashboard.sendReminders}
          </button>
        </div>
      </div>

      {breakeven && (
        <div className="card b-4">
          <div className="card__head">
            <div>
              <h3>{t.dashboard.unitTitle}</h3>
              <p>{t.dashboard.unitSub}</p>
            </div>
          </div>
          <div className="card__body">
            {/* Mockupdagi qatorlar (oziq-ovqat / tarbiyachi / ijara) qattiq
                yozilmagan — eng katta xarajat kategoriyalari o'z nomi bilan
                chiqadi, qolgani "boshqa"ga yig'iladi. Shu tufayli kategoriya
                nomlari o'zgarsa ham jadval to'g'ri qoladi. */}
            <div className="unit__row">
              <span>{t.dashboard.uFee}</span>
              <span className="num">{money(breakeven.fee_per_child)}</span>
            </div>
            {unitRows.map((row) => (
              <div className="unit__row" key={row.label}>
                <span>{row.label}</span>
                <span className="num" style={{ color: "var(--neg)" }}>
                  −{money(row.perChild)}
                </span>
              </div>
            ))}
            <div className="unit__row unit__total">
              <span>{t.dashboard.netProfit}</span>
              <span className="num">
                {netPerChild >= 0 ? "+" : ""}
                {money(netPerChild)}
              </span>
            </div>
            <p
              className="muted"
              style={{ fontSize: 12, marginTop: 12, lineHeight: 1.5 }}
            >
              {t.dashboard.unitNote}: <b>{breakeven.breakeven_children}</b>
            </p>
          </div>
        </div>
      )}

      {/* Tez amallar — mockupdagi `.quick` bloki */}
      <div className="card b-4">
        <div className="card__head">
          <div>
            <h3>{t.dashboard.quickActions}</h3>
          </div>
        </div>
        <div className="card__body">
          <div className="quick">
            <button
              type="button"
              className="quick__b"
              onClick={() => router.push("/billing?new=1")}
            >
              <IconWallet size={18} />
              {t.payments.takePayment}
            </button>
            <button
              type="button"
              className="quick__b"
              onClick={() => router.push("/finance/expenses?new=1")}
            >
              <IconTrendingDown size={18} />
              {t.expenses.addExpense}
            </button>
            <button
              type="button"
              className="quick__b"
              onClick={() => router.push("/children?new=1")}
            >
              <IconUsers size={18} />
              {t.children.addChild}
            </button>
            <button
              type="button"
              className="quick__b"
              onClick={() => router.push("/attendance")}
            >
              <IconCalendar size={18} />
              {t.nav.attendance}
            </button>
          </div>
          {trend.length > 1 && (
            <>
              <div style={{ marginTop: "var(--s4)" }}>
                <Sparkline points={trend} />
              </div>
              <p
                style={{
                  fontSize: 11.5,
                  color: "var(--ink-3)",
                  marginTop: 6,
                  textAlign: "center",
                }}
              >
                {t.dashboard.trendTitle}
              </p>
            </>
          )}
        </div>
      </div>

      <div className="card b-12">
        <div className="card__head">
          <div>
            <h3>{t.dashboard.recentPayments}</h3>
          </div>
          <button
            type="button"
            className="btn--quiet btn"
            onClick={() => router.push("/billing")}
          >
            {t.dashboard.viewAll} →
          </button>
        </div>
        {recentPaid.length === 0 ? (
          <div className="panel-empty">{t.common.empty}</div>
        ) : (
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>{t.payments.child}</th>
                  <th>{t.children.group}</th>
                  <th className="r">{t.payments.billed}</th>
                  <th className="r">{t.payments.paid}</th>
                  <th className="r">{t.payments.outstanding}</th>
                  <th className="r">{t.common.status}</th>
                </tr>
              </thead>
              <tbody>
                {recentPaid.map((inv) => {
                  const name = childNames[inv.child_id] ?? inv.billing_period;
                  return (
                    <tr
                      key={inv.id}
                      className="clickable"
                      onClick={() => router.push("/billing")}
                    >
                      <td>
                        <div className="cell-name">
                          <span className="avatar">{initials(name)}</span>
                          <b className="tr">{name}</b>
                        </div>
                      </td>
                      <td style={{ color: "var(--ink-2)" }}>
                        {childGroups[inv.child_id] ?? "—"}
                      </td>
                      <td className="r num">
                        {moneyPlain(inv.adjusted_amount)}
                      </td>
                      <td className="r num" style={{ color: "var(--pos)" }}>
                        {moneyPlain(inv.paid_amount)}
                      </td>
                      <td className="r num">
                        {moneyPlain(inv.outstanding_amount)}
                      </td>
                      <td className="r">
                        <span
                          className={`badge badge--${invoiceTone(inv.status)}`}
                        >
                          {invoiceStatus(inv.status)}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
