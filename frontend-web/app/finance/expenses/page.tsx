"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent, type ReactNode } from "react";

import { AppShell, useAppUI } from "@/components/AppShell";
import { Donut } from "@/components/charts/Donut";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { useModal } from "@/components/ui/ModalProvider";
import { useToast } from "@/components/ui/ToastProvider";
import { useConfirm } from "@/components/ui/useConfirm";
import { ApiError, api, type Expense, type ExpenseCategory } from "@/lib/api";
import { isoDate, money, moneyPlain, monthRange } from "@/lib/format";
import { useAuth } from "@/lib/useAuth";

export default function ExpensesPage(): ReactNode {
  const { user, loading } = useAuth();
  if (loading || !user) return <div className="boot-screen">KIDSFLOW</div>;
  return (
    <AppShell user={user} active="expenses">
      <Suspense fallback={null}>
        <ExpensesContent />
      </Suspense>
    </AppShell>
  );
}

function ExpensesContent(): ReactNode {
  const { t, branchId, setPageMeta } = useAppUI();

  useEffect(() => {
    setPageMeta({ title: t.expenses.title, subtitle: t.expenses.subtitle });
  }, [setPageMeta, t]);
  const modal = useModal();
  const toast = useToast();
  const confirm = useConfirm();
  const router = useRouter();
  const searchParams = useSearchParams();
  const period = monthRange();

  const [categories, setCategories] = useState<ExpenseCategory[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [periodStart, setPeriodStart] = useState(period.start);
  const [periodEnd, setPeriodEnd] = useState(period.end);
  const [ready, setReady] = useState(false);

  function load(): void {
    if (!branchId) return;
    setReady(false);
    Promise.all([api.listExpenseCategories(), api.listExpenses(branchId, periodStart, periodEnd)])
      .then(([cats, exp]) => {
        setCategories(cats);
        setExpenses(exp);
      })
      // Ruxsat yetmasa 403 keladi — ushlanmasa sahifa buziladi.
      .catch(() => {
        setCategories([]);
        setExpenses([]);
      })
      .finally(() => setReady(true));
  }

  useEffect(load, [branchId, periodStart, periodEnd]);

  useEffect(() => {
    if (searchParams.get("new") === "1") {
      openExpenseForm();
      router.replace("/finance/expenses");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  function categoryName(id: string): string {
    return categories.find((c) => c.id === id)?.name ?? id;
  }

  function openExpenseForm(): void {
    let categoryId = categories[0]?.id ?? "";
    let amount = "";
    let expenseDate = isoDate(new Date());
    let vendor = "";
    let description = "";
    let recurring = false;
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
              await api.createExpense({
                branch_id: branchId,
                category_id: categoryId,
                amount,
                expense_date: expenseDate,
                vendor: vendor || undefined,
                description: description || undefined,
                is_recurring: recurring,
              });
              modal.close();
              toast.show(t.common.saved);
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
              <label>{t.expenses.category}</label>
              <select className="input" defaultValue={categoryId} onChange={(e) => (categoryId = e.target.value)}>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>
                {t.payments.amount} ({t.common.sum})
              </label>
              <input className="input" inputMode="decimal" required onChange={(e) => (amount = e.target.value)} />
            </div>
            <div className="field">
              <label>{t.common.date}</label>
              <input
                className="input"
                type="date"
                defaultValue={expenseDate}
                onChange={(e) => (expenseDate = e.target.value)}
              />
            </div>
            <div className="field">
              <label>{t.expenses.vendor}</label>
              <input className="input" onChange={(e) => (vendor = e.target.value)} />
            </div>
          </div>
          <div className="field">
            <label>{t.expenses.description}</label>
            <input className="input" onChange={(e) => (description = e.target.value)} />
          </div>
          <label className="check" style={{ marginBottom: 16 }}>
            <input type="checkbox" onChange={(e) => (recurring = e.target.checked)} />
            <span>{t.expenses.recurring}</span>
          </label>
          {error && <p className="error">{error}</p>}
          <button className="btn" type="submit" disabled={saving}>
            {saving ? t.common.saving : t.common.save}
          </button>
        </form>,
        { title: t.expenses.addExpense, size: "default" },
      );
    }
    render();
  }

  function openCategoryManager(): void {
    let newName = "";
    let newVariable = false;
    let saving = false;
    let error = "";

    function render(): void {
      modal.open(
        <div>
          {categories.map((c) => (
            <div
              key={c.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "10px 0",
                borderBottom: "1px solid var(--line-2)",
              }}
            >
              <b style={{ flex: 1 }}>{c.name}</b>
              <button
                type="button"
                className={`chip${c.is_variable ? " on" : ""}`}
                onClick={async () => {
                  await api.updateExpenseCategory(c.id, { is_variable: !c.is_variable });
                  load();
                  render();
                }}
              >
                {t.expenses.variableFlag}
              </button>
            </div>
          ))}
          <div className="form-sec">{t.expenses.newCategory}</div>
          <form
            onSubmit={async (e: FormEvent) => {
              e.preventDefault();
              saving = true;
              error = "";
              render();
              try {
                await api.createExpenseCategory({ name: newName, is_variable: newVariable });
                newName = "";
                newVariable = false;
                saving = false;
                load();
                render();
              } catch (err) {
                error = err instanceof ApiError ? err.message : t.common.errTitle;
                saving = false;
                render();
              }
            }}
          >
            <div className="field">
              <label>{t.expenses.categoryName}</label>
              <input className="input" required onChange={(e) => (newName = e.target.value)} />
            </div>
            <label className="check" style={{ marginBottom: 16 }}>
              <input type="checkbox" onChange={(e) => (newVariable = e.target.checked)} />
              <span>{t.expenses.variableFlag}</span>
            </label>
            <p className="field__hint" style={{ marginBottom: 12 }}>
              {t.expenses.variableHint}
            </p>
            {error && <p className="error">{error}</p>}
            <button className="btn btn-sm" type="submit" disabled={saving}>
              {saving ? t.common.saving : t.common.add}
            </button>
          </form>
        </div>,
        { title: t.expenses.manageCategories, size: "default" },
      );
    }
    render();
  }

  async function reverse(expense: Expense): Promise<void> {
    const ok = await confirm({
      title: t.common.reverseTitle,
      body: t.common.reverse,
      confirmLabel: t.common.reverse,
      cancelLabel: t.common.cancel,
      danger: true,
    });
    if (!ok) return;
    try {
      await api.reverseExpense(expense.id);
      toast.show(t.common.reverseDone);
      load();
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : t.common.errTitle, { type: "neg" });
    }
  }

  const total = expenses.reduce((s, e) => s + Number(e.amount), 0);
  const byCategory = categories
    .map((c) => ({
      label: c.name,
      total: expenses.filter((e) => e.category_id === c.id).reduce((s, e) => s + Number(e.amount), 0),
    }))
    .filter((r) => r.total > 0);

  const columns: DataTableColumn<Expense>[] = [
    {
      key: "date",
      label: t.common.date,
      sortValue: (e) => e.expense_date,
      render: (e) => (
        <span className="num" style={{ fontSize: 13, color: "var(--ink-2)", whiteSpace: "nowrap" }}>
          {e.expense_date}
        </span>
      ),
    },
    {
      key: "category",
      label: t.expenses.category,
      sortValue: (e) => categoryName(e.category_id),
      render: (e) => <span className="badge badge--mute">{categoryName(e.category_id)}</span>,
    },
    {
      // Izoh va sotuvchi bitta ustunda — mockupda ham jadval besh ustunli,
      // aks holda o'ng tomondagi donut tufayli qolgan ustunlar siqilib qoladi.
      key: "description",
      label: t.expenses.description,
      render: (e) => (
        <span>
          <b style={{ fontWeight: 500 }}>{e.description || e.vendor || "—"}</b>
          {e.description && e.vendor && (
            <small style={{ display: "block", color: "var(--ink-3)", fontSize: 12 }}>
              {e.vendor}
            </small>
          )}
        </span>
      ),
    },
    {
      key: "amount",
      label: t.payments.amount,
      align: "right",
      sortValue: (e) => Number(e.amount),
      render: (e) => (
        <span
          className="num"
          style={{ fontWeight: 600, whiteSpace: "nowrap", opacity: e.status === "REVERSED" ? 0.5 : 1 }}
        >
          {moneyPlain(e.amount)}
        </span>
      ),
    },
    {
      key: "status",
      label: t.common.status,
      align: "right",
      render: (e) =>
        e.status === "REVERSED" ? (
          <span className="muted">{t.common.reverseDone}</span>
        ) : (
          <button
            type="button"
            className="btn--quiet btn btn-sm"
            onClick={(ev) => {
              ev.stopPropagation();
              reverse(e);
            }}
          >
            {t.common.reverse}
          </button>
        ),
    },
  ];

  return (
    <>
      {/* Sarlavha topbarda turadi (mockupdagidek), bu yerda faqat davr. */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 8 }}>
          <input className="input" type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} style={{ marginTop: 0 }} />
          <input className="input" type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} style={{ marginTop: 0 }} />
        </div>
      </div>

      <div className="grid g-32">
        {!ready ? (
          <div className="card">
            <div className="card__body" style={{ paddingTop: "var(--s5)" }}>
              <div className="sk sk-line" style={{ width: "40%" }} />
            </div>
          </div>
        ) : (
          <DataTable
            columns={columns}
            rows={expenses}
            rowKey={(e) => e.id}
            searchText={(e) => `${categoryName(e.category_id)} ${e.vendor ?? ""} ${e.description ?? ""}`}
            searchPlaceholder={t.common.search}
            emptyTitle={t.common.nothingFound}
            emptySub={t.common.nothingFoundSub}
            clearFiltersLabel={t.common.clearFilters}
            showingLabel={t.common.showing}
            ofLabel={t.common.of}
            actions={
              <>
                <button type="button" className="btn-ghost btn btn-sm" onClick={openCategoryManager}>
                  {t.expenses.manageCategories}
                </button>
                <button type="button" className="btn btn-sm" onClick={openExpenseForm}>
                  + {t.expenses.addExpense}
                </button>
              </>
            }
          />
        )}
        <div className="card">
          <div className="card__head">
            <div>
              <h3>{t.expenses.byCategory}</h3>
              <p>
                {t.expenses.total}: {money(total)}
              </p>
            </div>
          </div>
          <div className="card__body">
            {byCategory.length > 0 ? (
              <Donut rows={byCategory} totalLabel={t.expenses.total} />
            ) : (
              <div className="panel-empty">{t.common.empty}</div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
