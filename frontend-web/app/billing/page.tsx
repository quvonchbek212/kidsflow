"use client";

import { useRouter, useSearchParams } from "next/navigation";
import {
  Suspense,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { useAppUI } from "@/components/AppShell";
import { PaymentForm } from "@/components/PaymentForm";
import { CountUp } from "@/components/ui/CountUp";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { LoadError, recoverWith } from "@/components/ui/LoadError";
import { useModal } from "@/components/ui/ModalProvider";
import { useToast } from "@/components/ui/ToastProvider";
import {
  api,
  type Child,
  type Invoice,
} from "@/lib/api";
import {
  initials,
  invoiceStatus,
  invoiceTone,
  mlnf,
  moneyPlain,
  monthRange,
} from "@/lib/format";

export default function BillingPage(): ReactNode {
  return (
    <Suspense fallback={null}>
      <BillingContent />
    </Suspense>
  );
}

function BillingContent(): ReactNode {
  const { t, branchId, setPageMeta } = useAppUI();

  useEffect(() => {
    setPageMeta({ title: t.payments.title, subtitle: t.payments.subtitle });
  }, [setPageMeta, t]);
  const modal = useModal();
  const toast = useToast();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [billingMonth, setBillingMonth] = useState(monthRange().start);
  const [children, setChildren] = useState<Child[]>([]);
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
      api
        .branchInvoices(branchId, billingMonth)
        .catch(recoverWith("Hisob-fakturalar", [])),
      api.listGroups(branchId).catch(recoverWith("Guruhlar", [])),
    ])
      .then(([childList, inv, groupList]) => {
        setChildren(childList);
        setInvoices(inv);

        // Bola→guruh nomi: bolaning o'z enrollmentidan. Ilgari buning uchun
        // butun filialning kunlik davomat xulosasi (og'ir so'rov) olinardi.
        const names = new Map(groupList.map((g) => [g.id, g.name]));
        const map: Record<string, string> = {};
        for (const c of childList) {
          const name =
            c.status !== "left" && c.enrollment
              ? names.get(c.enrollment.group_id)
              : undefined;
          if (name) map[c.id] = name;
        }
        setChildGroup(map);
      })
      .catch(setLoadError)
      .finally(() => setReady(true));
  }

  useEffect(load, [branchId, billingMonth]);

  // `?new=1` (boshqaruv paneli yoki "Yangi" menyusidan) — forma bolalar
  // ro'yxati yuklangach ochiladi. Ilgari u darhol ochilib, bo'sh ro'yxat
  // bilan qolardi.
  useEffect(() => {
    if (!ready) return;
    if (searchParams.get("new") === "1") {
      openPaymentForm(null);
      router.replace("/billing");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, ready]);

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

  function openPaymentForm(invoice: Invoice | null): void {
    modal.open(
      <PaymentForm
        childList={children}
        childGroup={childGroup}
        initialChildId={invoice?.child_id}
        initialAmount={invoice?.outstanding_amount}
        t={t}
        onCancel={modal.close}
        onChanged={load}
        onSaved={() => {
          modal.close();
          toast.show(t.payments.paymentDone);
          load();
        }}
      />,
      { title: t.payments.takePayment, size: "default" },
    );
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
      // Hisob-fakturani bekor qilish tugmasi ("✕") olib tashlangan:
      // hisoblar avtomatik yaratiladi. Backenddagi bekor qilish endpointi
      // saqlanib qolgan.
      render: (i) => (
        <span className={`badge badge--${invoiceTone(i.status)}`}>
          {invoiceStatus(i.status)}
        </span>
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
          aria-label={t.common.period}
          title={t.common.period}
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
            <CountUp value={totalBilled} format={mlnf} />
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
            <CountUp value={totalCollected} format={mlnf} />
            <span className="kpi__unit">{t.common.mln}</span>
          </div>
        </div>
        <div className="kpi">
          <div className="kpi__top">
            <span className="kpi__label">{t.payments.outstanding}</span>
          </div>
          <div className="kpi__value" style={{ color: "var(--neg)" }}>
            <CountUp value={totalOutstanding} format={mlnf} />
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
          emptySub={
            invoices.length === 0
              ? t.payments.autoInvoiceHint
              : t.common.nothingFoundSub
          }
          clearFiltersLabel={t.common.clearFilters}
          showingLabel={t.common.showing}
          ofLabel={t.common.of}
          actions={
            <button
              type="button"
              className="btn btn-sm"
              onClick={() => openPaymentForm(null)}
            >
              + {t.payments.newPayment}
            </button>
          }
        />
      )}
    </>
  );
}
