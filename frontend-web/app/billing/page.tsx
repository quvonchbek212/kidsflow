"use client";

import { useRouter, useSearchParams } from "next/navigation";
import {
  Suspense,
  useEffect,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";

import { AppShell, useAppUI } from "@/components/AppShell";
import { useConfirm } from "@/components/ui/useConfirm";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { LoadError, recoverWith } from "@/components/ui/LoadError";
import { useModal } from "@/components/ui/ModalProvider";
import { useToast } from "@/components/ui/ToastProvider";
import {
  ApiError,
  api,
  type Child,
  type FeePlan,
  type Invoice,
} from "@/lib/api";
import {
  initials,
  invoiceStatus,
  invoiceTone,
  isoDate,
  mlnf,
  money,
  moneyPlain,
  monthRange,
} from "@/lib/format";
import { useAuth } from "@/lib/useAuth";

export default function BillingPage(): ReactNode {
  const { user, loading } = useAuth();
  if (loading || !user) return <div className="boot-screen">KIDSFLOW</div>;
  return (
    <AppShell user={user} active="payments">
      <Suspense fallback={null}>
        <BillingContent />
      </Suspense>
    </AppShell>
  );
}

function BillingContent(): ReactNode {
  const { t, branchId, setPageMeta } = useAppUI();

  useEffect(() => {
    setPageMeta({ title: t.payments.title, subtitle: t.payments.subtitle });
  }, [setPageMeta, t]);
  const modal = useModal();
  const toast = useToast();
  const confirm = useConfirm();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [billingMonth, setBillingMonth] = useState(monthRange().start);
  const [children, setChildren] = useState<Child[]>([]);
  const [feePlans, setFeePlans] = useState<FeePlan[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [childGroup, setChildGroup] = useState<Record<string, string>>({});
  const [ready, setReady] = useState(false);
  const [loadError, setLoadError] = useState<unknown>(null);

  function load(): void {
    if (!branchId) return;
    setReady(false);
    setLoadError(null);
    Promise.all([
      api.listChildren(branchId),
      api.listFeePlans(),
      api
        .branchInvoices(branchId, billingMonth)
        .catch(recoverWith("Hisob-fakturalar", [])),
    ])
      .then(async ([childList, plans, inv]) => {
        setChildren(childList);
        setFeePlans(plans.filter((p) => p.branch_id === branchId));
        setInvoices(inv);

        // Bola→guruh nomi xaritasi bitta so'rovda. Ilgari avval guruhlar
        // ro'yxati, keyin har bir guruh uchun alohida roster olinardi.
        const attendance = await api
          .branchAttendanceSummary(branchId, isoDate(new Date()))
          .catch(recoverWith("Guruh taqsimoti", null));
        const map: Record<string, string> = {};
        for (const group of attendance?.groups ?? []) {
          for (const row of group.rows) map[row.child_id] = group.group_name;
        }
        setChildGroup(map);
      })
      .catch(setLoadError)
      .finally(() => setReady(true));
  }

  useEffect(load, [branchId, billingMonth]);

  useEffect(() => {
    if (searchParams.get("new") === "1") {
      openPaymentForm(null);
      router.replace("/billing");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  function childName(id: string): string {
    return children.find((c) => c.id === id)?.full_name ?? id;
  }

  const totalBilled = invoices.reduce(
    (s, i) => s + Number(i.adjusted_amount),
    0,
  );
  const totalCollected = invoices.reduce(
    (s, i) => s + Number(i.paid_amount),
    0,
  );
  const totalOutstanding = invoices.reduce(
    (s, i) => s + Number(i.outstanding_amount),
    0,
  );

  function openGenerateInvoices(): void {
    let genMonth = billingMonth;
    let feePlanId = feePlans[0]?.id ?? "";
    let dueDate = billingMonth.slice(0, 8) + "10";
    let saving = false;
    let error = "";
    let result = "";

    function render(): void {
      modal.open(
        <form
          onSubmit={async (e: FormEvent) => {
            e.preventDefault();
            saving = true;
            error = "";
            render();
            try {
              const dueDay = Number(dueDate.slice(8, 10));
              const res = await api.generateInvoices(
                branchId,
                genMonth,
                feePlanId || undefined,
                dueDay,
              );
              result = `${res.created} ${t.payments.invoicesCreated}, ${res.skipped} ${t.payments.invoicesSkipped}`;
              setBillingMonth(genMonth);
              render();
              load();
            } catch (err) {
              error = err instanceof ApiError ? err.message : t.common.errTitle;
              saving = false;
              render();
            }
          }}
        >
          <div className="form-grid">
            <div className="field">
              <label>{t.common.period}</label>
              <input
                className="input"
                type="date"
                defaultValue={genMonth}
                onChange={(e) => (genMonth = e.target.value)}
              />
            </div>
            <div className="field">
              <label>{t.payments.dueDate}</label>
              <input
                className="input"
                type="date"
                defaultValue={dueDate}
                onChange={(e) => (dueDate = e.target.value)}
              />
            </div>
            <div className="field span-2">
              <label>{t.groups.monthlyFee} (fallback)</label>
              <select
                className="input"
                defaultValue={feePlanId}
                onChange={(e) => (feePlanId = e.target.value)}
              >
                {feePlans.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} — {money(p.monthly_amount)}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {result && (
            <p className="info-box" style={{ marginTop: 12 }}>
              {result}
            </p>
          )}
          {error && <p className="error">{error}</p>}
          <button
            className="btn"
            type="submit"
            disabled={saving}
            style={{ marginTop: 8 }}
          >
            {saving ? t.common.saving : t.payments.generateInvoices}
          </button>
        </form>,
        { title: t.payments.generateInvoices, size: "default" },
      );
    }
    render();
  }

  function openPaymentForm(invoice: Invoice | null): void {
    let childId = invoice?.child_id ?? children[0]?.id ?? "";
    let amount = invoice ? invoice.outstanding_amount : "";
    let method = "CASH";
    let paidAt = isoDate(new Date());
    let reference = "";
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
              await api.recordPayment({
                child_id: childId,
                amount,
                payment_method: method,
                paid_at: new Date(paidAt).toISOString(),
                reference: reference || undefined,
              });
              modal.close();
              toast.show(t.payments.paymentDone);
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
              <label>{t.payments.child}</label>
              <select
                className="input"
                defaultValue={childId}
                onChange={(e) => (childId = e.target.value)}
              >
                {children.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.full_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>
                {t.payments.amount} ({t.common.sum})
              </label>
              <input
                className="input"
                inputMode="decimal"
                defaultValue={amount}
                required
                onChange={(e) => (amount = e.target.value)}
              />
            </div>
            <div className="field">
              <label>{t.common.date}</label>
              <input
                className="input"
                type="date"
                defaultValue={paidAt}
                onChange={(e) => (paidAt = e.target.value)}
              />
            </div>
          </div>
          <div className="segmented" style={{ marginBottom: 16 }}>
            {(["CASH", "CARD", "TERMINAL", "BANK", "OTHER"] as const).map(
              (m) => (
                <button
                  type="button"
                  key={m}
                  className={method === m ? "on" : ""}
                  onClick={() => {
                    method = m;
                    render();
                  }}
                >
                  {m === "CASH"
                    ? t.payments.cash
                    : m === "CARD"
                      ? t.payments.card
                      : m === "TERMINAL"
                        ? t.payments.terminal
                        : m === "BANK"
                          ? t.payments.bank
                          : t.payments.other}
                </button>
              ),
            )}
          </div>
          <div className="field">
            <label>
              {t.common.reason} ({t.common.optional})
            </label>
            <input
              className="input"
              defaultValue={reference}
              onChange={(e) => (reference = e.target.value)}
            />
          </div>
          {error && <p className="error">{error}</p>}
          <button
            className="btn"
            type="submit"
            disabled={saving}
            style={{ marginTop: 8 }}
          >
            {saving ? t.common.saving : t.payments.savePayment}
          </button>
        </form>,
        { title: t.payments.takePayment, size: "default" },
      );
    }
    render();
  }

  async function cancelInvoice(invoice: Invoice): Promise<void> {
    const ok = await confirm({
      title: t.common.confirm,
      body: t.payments.cancelInvoice,
      confirmLabel: t.common.confirm,
      cancelLabel: t.common.cancel,
      danger: true,
    });
    if (!ok) return;
    try {
      await api.cancelInvoice(invoice.id);
      toast.show(t.payments.cancelDone);
      load();
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t.common.errTitle, {
        type: "neg",
      });
    }
  }

  const columns: DataTableColumn<Invoice>[] = [
    {
      key: "child",
      label: t.payments.child,
      sortValue: (i) => childName(i.child_id),
      render: (i) => (
        <div className="cell-name">
          <span className="avatar">{initials(childName(i.child_id))}</span>
          <b className="tr">{childName(i.child_id)}</b>
        </div>
      ),
    },
    {
      key: "group",
      label: t.children.group,
      sortValue: (i) => childGroup[i.child_id] ?? "",
      render: (i) => (
        <span style={{ color: "var(--ink-2)" }}>
          {childGroup[i.child_id] ?? "—"}
        </span>
      ),
    },
    {
      key: "billed",
      label: t.payments.billed,
      align: "right",
      sortValue: (i) => Number(i.adjusted_amount),
      render: (i) => moneyPlain(i.adjusted_amount),
    },
    {
      key: "paid",
      label: t.payments.paid,
      align: "right",
      sortValue: (i) => Number(i.paid_amount),
      render: (i) => moneyPlain(i.paid_amount),
    },
    {
      key: "remaining",
      label: t.payments.outstanding,
      align: "right",
      sortValue: (i) => Number(i.outstanding_amount),
      render: (i) => (
        <span
          className="num"
          style={
            Number(i.outstanding_amount) > 0
              ? { color: "var(--neg)", fontWeight: 600 }
              : undefined
          }
        >
          {Number(i.outstanding_amount) > 0
            ? moneyPlain(i.outstanding_amount)
            : "—"}
        </span>
      ),
    },
    {
      key: "progress",
      label: t.payments.progress,
      render: (i) => {
        const pct =
          Number(i.adjusted_amount) > 0
            ? Math.round(
                (Number(i.paid_amount) / Number(i.adjusted_amount)) * 100,
              )
            : 0;
        return (
          <div className="bar" style={{ width: 100 }}>
            <i
              style={{
                width: `${pct}%`,
                background:
                  pct >= 100
                    ? "var(--pos)"
                    : pct > 0
                      ? "var(--warn)"
                      : "var(--neg)",
              }}
            />
          </div>
        );
      },
    },
    {
      key: "status",
      label: t.common.status,
      align: "right",
      sortValue: (i) => i.status,
      render: (i) => (
        <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
          <span className={`badge badge--${invoiceTone(i.status)}`}>
            {invoiceStatus(i.status)}
          </span>
          {i.status !== "CANCELLED" && i.status !== "PAID" && (
            <button
              type="button"
              className="btn--quiet btn btn-sm"
              onClick={(e) => {
                e.stopPropagation();
                cancelInvoice(i);
              }}
            >
              ✕
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <>
      {/* Sarlavha topbarda turadi (mockupdagidek), bu yerda faqat amallar. */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-end",
          marginBottom: 16,
        }}
      >
        <input
          className="input"
          type="date"
          value={billingMonth}
          onChange={(e) => setBillingMonth(e.target.value)}
          style={{ marginTop: 0, width: "auto" }}
        />
      </div>

      <div className="grid g-4" style={{ marginBottom: 16 }}>
        <div className="kpi">
          <div className="kpi__top">
            <span className="kpi__label">{t.payments.billed}</span>
          </div>
          <div className="kpi__value">
            {mlnf(totalBilled)}
            <span className="kpi__unit">{t.common.mln}</span>
          </div>
        </div>
        <div className="kpi">
          <div className="kpi__top">
            <span className="kpi__label">{t.payments.collected}</span>
            {totalBilled > 0 && (
              <span className="badge badge--pos">
                {Math.round((totalCollected / totalBilled) * 100)}%
              </span>
            )}
          </div>
          <div className="kpi__value" style={{ color: "var(--pos)" }}>
            {mlnf(totalCollected)}
            <span className="kpi__unit">{t.common.mln}</span>
          </div>
        </div>
        <div className="kpi">
          <div className="kpi__top">
            <span className="kpi__label">{t.payments.outstanding}</span>
          </div>
          <div className="kpi__value" style={{ color: "var(--neg)" }}>
            {mlnf(totalOutstanding)}
            <span className="kpi__unit">{t.common.mln}</span>
          </div>
        </div>
        {/* To'lash bajarilishi — mockupdagi 4-kartochka. Backendda to'lov
            sanalari ro'yxati yo'q, shuning uchun "o'rtacha to'lov kuni"
            o'rniga to'liq to'langan hisob-fakturalar ulushi ko'rsatiladi. */}
        <div className="kpi">
          <div className="kpi__top">
            <span className="kpi__label">{t.payments.progress}</span>
          </div>
          <div className="kpi__value">
            {invoices.filter((i) => i.status === "PAID").length}
            <span className="kpi__unit">/ {invoices.length}</span>
          </div>
          <div className="bar" style={{ marginTop: "var(--s3)" }}>
            <i
              style={{
                width: invoices.length
                  ? `${(invoices.filter((i) => i.status === "PAID").length / invoices.length) * 100}%`
                  : "0%",
                background: "var(--pos)",
              }}
            />
          </div>
        </div>
      </div>

      {loadError ? (
        <LoadError error={loadError} onRetry={load} />
      ) : !ready ? (
        <div className="card">
          <div className="card__body" style={{ paddingTop: "var(--s5)" }}>
            <div className="sk sk-line" style={{ width: "40%" }} />
          </div>
        </div>
      ) : (
        <DataTable
          columns={columns}
          rows={invoices}
          rowKey={(i) => i.id}
          searchText={(i) => childName(i.child_id)}
          searchPlaceholder={t.common.search}
          filters={[
            { key: "all", label: t.common.all },
            { key: "paid", label: t.payments.filterPaid },
            { key: "partial", label: t.payments.filterPartial },
            { key: "unpaid", label: t.payments.filterUnpaid },
          ]}
          filterFn={(i, f) => {
            if (f === "paid") return Number(i.outstanding_amount) === 0;
            if (f === "partial")
              return (
                Number(i.outstanding_amount) > 0 && Number(i.paid_amount) > 0
              );
            return Number(i.paid_amount) === 0;
          }}
          onRowClick={(i) => openPaymentForm(i)}
          emptyTitle={t.common.nothingFound}
          emptySub={t.common.nothingFoundSub}
          clearFiltersLabel={t.common.clearFilters}
          showingLabel={t.common.showing}
          ofLabel={t.common.of}
          actions={
            <>
              <button
                type="button"
                className="btn-ghost btn btn-sm"
                onClick={openGenerateInvoices}
              >
                {t.payments.generateInvoices}
              </button>
              <button
                type="button"
                className="btn btn-sm"
                onClick={() => openPaymentForm(null)}
              >
                + {t.payments.newPayment}
              </button>
            </>
          }
        />
      )}
    </>
  );
}
