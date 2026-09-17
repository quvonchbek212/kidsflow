"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { useAppUI } from "@/components/AppShell";
import { IconPlus, IconTrash } from "@/components/icons";
import { useModal } from "@/components/ui/ModalProvider";
import { useToast } from "@/components/ui/ToastProvider";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  ApiError,
  api,
  type FoodProduct,
  type Meal,
  type MealIngredient,
} from "@/lib/api";
import { isoDate } from "@/lib/format";

export default function FoodMealsPage(): ReactNode {
  return <MealsContent />;
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
    // Har qatorga barqaror `uid` beriladi. Indeksni React kaliti qilib
    // ishlatib bo'lmaydi: maydonlar boshqarilmaydigan (`defaultValue`), va
    // o'rtadagi qator o'chirilganda React DOM'ni qayta ishlatib, qolgan
    // qatorlarda eski qiymatlar ko'rinib qolardi.
    let rows: (MealIngredient & { uid: number })[] = [];
    let nextUid = 1;
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
                // `uid` faqat React kaliti uchun — backendga ketmaydi.
                ingredients: rows.map((r) => ({
                  product_id: r.product_id,
                  quantity_per_serving: r.quantity_per_serving,
                })),
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
            <label className="field">
              <span className="field__label">
                {t.common.name}
                <span className="req">*</span>
              </span>
              <input
                className="input"
                required
                onChange={(e) => (name = e.target.value)}
              />
            </label>
            <label className="field">
              <span className="field__label">{t.expenses.description}</span>
              <input
                className="input"
                onChange={(e) => (description = e.target.value)}
              />
            </label>
          </div>

          <div className="form-sec">{t.food.ingredients}</div>
          {rows.map((row, i) => (
            <div
              key={row.uid}
              style={{ display: "flex", gap: 8, marginBottom: 8 }}
            >
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
                aria-label={t.common.removeRow}
                title={t.common.removeRow}
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
                {
                  uid: nextUid++,
                  product_id: products[0].id,
                  quantity_per_serving: "1",
                },
              ];
              render();
            }}
          >
            <IconPlus size={14} /> {t.food.addIngredient}
          </button>

          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <div className="modal-actions">
            <button className="btn" type="submit" disabled={saving}>
              {saving ? t.common.saving : t.common.save}
            </button>
          </div>
        </form>,
        // Ikkita maydon uchun 780px juda keng edi — o'ng yarmi bo'sh qolardi.
        { title: t.food.addMeal, size: "default" },
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
            <label className="field">
              <span className="field__label">{t.common.date}</span>
              <input
                className="input"
                type="date"
                defaultValue={servingDate}
                onChange={(e) => (servingDate = e.target.value)}
              />
            </label>
            <label className="field">
              <span className="field__label">
                {t.food.servings}
                <span className="req">*</span>
              </span>
              <input
                className="input"
                inputMode="numeric"
                defaultValue={count}
                required
                onChange={(e) => (count = e.target.value)}
              />
            </label>
          </div>
          <p className="field__hint">
            {meal.ingredients
              .map(
                (ing) =>
                  `${productName(ing.product_id)} ${ing.quantity_per_serving} ${productUnit(ing.product_id)}`,
              )
              .join(" · ")}
          </p>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <div className="modal-actions">
            <button className="btn" type="submit" disabled={saving}>
              {saving ? t.common.saving : t.common.save}
            </button>
          </div>
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
          <EmptyState title={t.common.empty} />
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
