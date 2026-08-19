"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { AppShell, useAppUI } from "@/components/AppShell";
import { IconPlus, IconTrash } from "@/components/icons";
import { useModal } from "@/components/ui/ModalProvider";
import { useToast } from "@/components/ui/ToastProvider";
import {
  ApiError,
  api,
  type FoodProduct,
  type Meal,
  type MealIngredient,
} from "@/lib/api";
import { isoDate } from "@/lib/format";
import { useAuth } from "@/lib/useAuth";

export default function FoodMealsPage(): ReactNode {
  const { user, loading } = useAuth();
  if (loading || !user) return <div className="boot-screen">KIDSFLOW</div>;
  return (
    <AppShell user={user}>
      <MealsContent />
    </AppShell>
  );
}

function MealsContent(): ReactNode {
  const { t, branchId, setPageMeta } = useAppUI();

  useEffect(() => {
    setPageMeta({ title: t.food.mealsTitle, subtitle: t.food.mealsSub });
  }, [setPageMeta, t]);
  const modal = useModal();
  const toast = useToast();

  const [products, setProducts] = useState<FoodProduct[]>([]);
  const [meals, setMeals] = useState<Meal[]>([]);
  const [ready, setReady] = useState(false);

  function load(): void {
    if (!branchId) return;
    setReady(false);
    Promise.all([api.listMeals(branchId), api.listFoodProducts(branchId)])
      .then(([m, p]) => {
        setMeals(m);
        setProducts(p);
      })
      .catch(() => {
        setMeals([]);
        setProducts([]);
      })
      .finally(() => setReady(true));
  }

  useEffect(load, [branchId]);

  const productName = (id: string): string =>
    products.find((p) => p.id === id)?.name ?? id;
  const productUnit = (id: string): string =>
    products.find((p) => p.id === id)?.unit ?? "";

  function openMealForm(): void {
    let name = "";
    let description = "";
    let rows: MealIngredient[] = [];
    let saving = false;
    let error = "";

    function render(): void {
      modal.open(
        <form
          onSubmit={async (e: FormEvent) => {
            e.preventDefault();
            if (rows.length === 0) {
              error = t.food.addIngredient;
              render();
              return;
            }
            saving = true;
            error = "";
            render();
            try {
              await api.createMeal({
                branch_id: branchId,
                name,
                description: description || undefined,
                ingredients: rows,
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
              <label>
                {t.common.name}
                <span className="req">*</span>
              </label>
              <input
                className="input"
                required
                onChange={(e) => (name = e.target.value)}
              />
            </div>
            <div className="field">
              <label>{t.expenses.description}</label>
              <input
                className="input"
                onChange={(e) => (description = e.target.value)}
              />
            </div>
          </div>

          <div className="form-sec">{t.food.ingredients}</div>
          {rows.map((row, i) => (
            <div key={i} style={{ display: "flex", gap: 8, marginBottom: 8 }}>
              <select
                className="input"
                defaultValue={row.product_id}
                onChange={(e) => {
                  rows[i] = { ...rows[i], product_id: e.target.value };
                }}
              >
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.unit})
                  </option>
                ))}
              </select>
              <input
                className="input"
                style={{ width: 120 }}
                inputMode="decimal"
                defaultValue={row.quantity_per_serving}
                title={t.food.perServing}
                onChange={(e) => {
                  rows[i] = {
                    ...rows[i],
                    quantity_per_serving: e.target.value,
                  };
                }}
              />
              <button
                type="button"
                className="btn--icon"
                aria-label={t.common.cancel}
                onClick={() => {
                  rows = rows.filter((_, idx) => idx !== i);
                  render();
                }}
              >
                <IconTrash size={16} />
              </button>
            </div>
          ))}
          <button
            type="button"
            className="btn-ghost btn btn-sm"
            disabled={products.length === 0}
            onClick={() => {
              rows = [
                ...rows,
                { product_id: products[0].id, quantity_per_serving: "1" },
              ];
              render();
            }}
          >
            <IconPlus size={14} /> {t.food.addIngredient}
          </button>

          {error && <p className="error">{error}</p>}
          <div style={{ marginTop: 16 }}>
            <button className="btn" type="submit" disabled={saving}>
              {saving ? t.common.saving : t.common.save}
            </button>
          </div>
        </form>,
        { title: t.food.addMeal, size: "wide" },
      );
    }
    render();
  }

  function openServeForm(meal: Meal): void {
    let servingDate = isoDate(new Date());
    let count = "1";
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
              await api.logMeal({
                meal_id: meal.id,
                serving_date: servingDate,
                servings_count: Number(count),
              });
              modal.close();
              toast.show(t.common.saved);
              load();
            } catch (err) {
              error = err instanceof ApiError ? err.message : t.food.noStock;
              saving = false;
              render();
            }
          }}
        >
          <div className="form-grid">
            <div className="field">
              <label>{t.common.date}</label>
              <input
                className="input"
                type="date"
                defaultValue={servingDate}
                onChange={(e) => (servingDate = e.target.value)}
              />
            </div>
            <div className="field">
              <label>
                {t.food.servings}
                <span className="req">*</span>
              </label>
              <input
                className="input"
                inputMode="numeric"
                defaultValue={count}
                required
                onChange={(e) => (count = e.target.value)}
              />
            </div>
          </div>
          <p className="field__hint">
            {meal.ingredients
              .map(
                (ing) =>
                  `${productName(ing.product_id)} ${ing.quantity_per_serving} ${productUnit(ing.product_id)}`,
              )
              .join(" · ")}
          </p>
          {error && <p className="error">{error}</p>}
          <button
            className="btn"
            type="submit"
            disabled={saving}
            style={{ marginTop: 8 }}
          >
            {saving ? t.common.saving : t.common.save}
          </button>
        </form>,
        { title: t.food.serveTitle, subtitle: meal.name, size: "default" },
      );
    }
    render();
  }

  return (
    <>
      <div className="card">
        <div className="card__head">
          <div>
            <h3>{t.food.mealsTitle}</h3>
          </div>
          <button type="button" className="btn btn-sm" onClick={openMealForm}>
            <IconPlus size={14} /> {t.food.addMeal}
          </button>
        </div>
        {!ready ? (
          <div className="panel-empty">{t.common.loading}</div>
        ) : meals.length === 0 ? (
          <div className="panel-empty">{t.common.empty}</div>
        ) : (
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>{t.common.name}</th>
                  <th>{t.food.ingredients}</th>
                  <th className="r" />
                </tr>
              </thead>
              <tbody>
                {meals.map((m) => (
                  <tr key={m.id}>
                    <td>
                      <b>{m.name}</b>
                      {m.description && (
                        <>
                          <br />
                          <small className="muted">{m.description}</small>
                        </>
                      )}
                    </td>
                    <td style={{ color: "var(--ink-2)" }}>
                      {m.ingredients
                        .map(
                          (ing) =>
                            `${productName(ing.product_id)} (${ing.quantity_per_serving} ${productUnit(ing.product_id)})`,
                        )
                        .join(", ")}
                    </td>
                    <td className="r">
                      <button
                        type="button"
                        className="btn-ghost btn btn-sm"
                        onClick={() => openServeForm(m)}
                      >
                        {t.food.serve}
                      </button>
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
