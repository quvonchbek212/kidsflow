"use client";

/**
 * To'lov qabul qilish formasi.
 *
 * Ilgari bola oddiy `<select>` dan tanlanardi: 50+ bolali filialda kerakli
 * ismni topish uzoq edi va ro'yxatdagi birinchi bola avtomatik tanlanib
 * turgani uchun to'lov adashib boshqa bolaga yozilib ketishi mumkin edi.
 * Endi bola ism yoki guruh bo'yicha qidiriladi, tanlangach uning joriy qarzi
 * ko'rinadi va summa maydoniga o'zi qo'yiladi.
 */

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
  type ReactNode,
} from "react";

import { IconSearch } from "@/components/icons";
import { ApiError, api, type Child, type Payment } from "@/lib/api";
import type { AppStrings } from "@/lib/app-i18n";
import { initials, isoDate, money, moneyPlain } from "@/lib/format";

const METHODS = ["CASH", "CARD", "TERMINAL", "BANK", "OTHER"] as const;
type Method = (typeof METHODS)[number];

/* Ro'yxat juda uzun bo'lmasin — qidiruv baribir aniqlashtiradi. */
const MAX_RESULTS = 40;

/** Apostrof turlari va katta-kichik harf farqisiz solishtirish uchun. */
function normalize(value: string): string {
  return value
    .toLowerCase()
    .replace(/['`ʻʼ‘’]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

/** Backend `"1500000.00"` qaytaradi — maydonda butun so'm saqlanadi. */
function wholeSum(value: string | number | undefined): string {
  const num = Number(value);
  return Number.isFinite(num) && num > 0 ? String(Math.round(num)) : "";
}

export function PaymentForm({
  childList,
  childGroup,
  initialChildId,
  initialAmount,
  t,
  onCancel,
  onSaved,
  onChanged,
}: {
  childList: Child[];
  childGroup: Record<string, string>;
  initialChildId?: string;
  initialAmount?: string;
  t: AppStrings;
  onCancel: () => void;
  onSaved: () => void;
  /** To'lov bekor qilinganda — sahifadagi ro'yxat yangilanishi uchun. */
  onChanged?: () => void;
}): ReactNode {
  const [childId, setChildId] = useState<string | null>(
    initialChildId ?? null,
  );
  const [query, setQuery] = useState("");
  const [activeIdx, setActiveIdx] = useState(0);
  // Ro'yxat pastdagi maydonlar ustida suzadi va faqat qidiruv fokusda
  // bo'lganda ochiq turadi — oyna balandligi o'zgarmaydi.
  const [listOpen, setListOpen] = useState(true);
  const [amount, setAmount] = useState(wholeSum(initialAmount));
  // Foydalanuvchi summani o'zi yozgan bo'lsa, qarz uni ustidan yozmaydi.
  const [amountTouched, setAmountTouched] = useState(Boolean(initialAmount));
  const [debt, setDebt] = useState<number | null>(null);
  const [method, setMethod] = useState<Method>("CASH");
  const [paidAt, setPaidAt] = useState(isoDate(new Date()));
  const [reference, setReference] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  // Tanlangan bolaning oxirgi to'lovlari: xato kiritilganini shu yerdan
  // bekor qilish mumkin. Tasdiq ro'yxat ichida (ikki bosqich) — alohida
  // tasdiq oynasi bu formani yopib yuborardi.
  const [payments, setPayments] = useState<Payment[] | null>(null);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [reversingId, setReversingId] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  const listRef = useRef<HTMLUListElement>(null);

  const selected = childList.find((c) => c.id === childId) ?? null;

  const results = useMemo(() => {
    const tokens = normalize(query).split(" ").filter(Boolean);
    return childList
      .filter((c) => {
        if (tokens.length === 0) return true;
        const hay = normalize(`${c.full_name} ${childGroup[c.id] ?? ""}`);
        return tokens.every((tok) => hay.includes(tok));
      })
      .sort((a, b) => {
        // Faol bolalar yuqorida — ketgan bolaning eski qarzi ham to'lanishi
        // mumkin, shuning uchun ular yashirilmaydi.
        const rank = (c: Child): number => (c.status === "active" ? 0 : 1);
        return rank(a) - rank(b) || a.full_name.localeCompare(b.full_name);
      })
      .slice(0, MAX_RESULTS);
  }, [childList, childGroup, query]);

  // Qidiruv o'zgarsa belgi birinchi natijaga qaytadi.
  useEffect(() => setActiveIdx(0), [query]);

  // Klaviatura bilan yurilganda belgilangan qator ko'rinib tursin.
  useEffect(() => {
    listRef.current
      ?.querySelector<HTMLElement>(`[data-idx="${activeIdx}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }, [activeIdx]);

  // Tanlangan bolaning barcha oylar bo'yicha qarzi.
  useEffect(() => {
    if (!childId) {
      setDebt(null);
      setPayments(null);
      return;
    }
    let cancelled = false;
    setDebt(null);
    setPayments(null);
    setConfirmingId(null);
    api
      .childPayments(childId)
      .then((rows) => {
        if (!cancelled) setPayments(rows);
      })
      .catch(() => {
        if (!cancelled) setPayments([]);
      });
    api
      .childInvoices(childId)
      .then((invoices) => {
        if (cancelled) return;
        const total = invoices
          // Qoralama hali ota-onaga chiqarilmagan, bekor qilingani esa qarz emas.
          .filter((inv) => inv.status !== "CANCELLED" && inv.status !== "DRAFT")
          .reduce((sum, inv) => sum + Number(inv.outstanding_amount || 0), 0);
        setDebt(total);
        if (!amountTouched) setAmount(wholeSum(total));
      })
      .catch(() => {
        if (!cancelled) setDebt(0);
      });
    return () => {
      cancelled = true;
    };
    // `amountTouched` ataylab kuzatilmaydi: summa yozilganda qarz qayta
    // so'ralmasin. `reloadKey` — to'lov bekor qilingach qarz va ro'yxat
    // qayta olinadi.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [childId, reloadKey]);

  async function reverse(paymentId: string): Promise<void> {
    setReversingId(paymentId);
    setHistoryError("");
    try {
      await api.reversePayment(paymentId);
      setConfirmingId(null);
      setReloadKey((k) => k + 1);
      onChanged?.();
    } catch (err) {
      setHistoryError(err instanceof ApiError ? err.message : t.common.errTitle);
    } finally {
      setReversingId(null);
    }
  }

  function choose(id: string): void {
    setChildId(id);
    setError("");
  }

  function changeChild(): void {
    setChildId(null);
    setQuery("");
    setListOpen(true);
    if (!amountTouched) setAmount("");
  }

  function onSearchKey(e: KeyboardEvent<HTMLInputElement>): void {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      // Formani yubormasin — faqat bolani tanlasin.
      e.preventDefault();
      const pick = results[activeIdx];
      if (pick) choose(pick.id);
    }
  }

  async function submit(e: FormEvent): Promise<void> {
    e.preventDefault();
    if (!childId || !amount || saving) return;
    setSaving(true);
    setError("");
    try {
      await api.recordPayment({
        child_id: childId,
        amount,
        payment_method: method,
        paid_at: new Date(paidAt).toISOString(),
        reference: reference.trim() || undefined,
      });
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t.common.errTitle);
      setSaving(false);
    }
  }

  const methodLabel: Record<Method, string> = {
    CASH: t.payments.cash,
    CARD: t.payments.card,
    TERMINAL: t.payments.terminal,
    BANK: t.payments.bank,
    OTHER: t.payments.other,
  };

  const debtRounded = debt === null ? null : Math.round(debt);

  return (
    <form className="payform" onSubmit={submit}>
      <div className="field">
        <span className="field__label" id="payform-child-label">
          {t.payments.child}
        </span>

        {selected ? (
          <div className="payform__child">
            <span className="avatar">{initials(selected.full_name)}</span>
            <span className="payform__child-body">
              <b className="tr">{selected.full_name}</b>
              <small className="tr">{childGroup[selected.id] ?? "—"}</small>
            </span>
            <span
              className={`payform__debt${
                debtRounded === null ? "" : debtRounded > 0 ? " neg" : " pos"
              }`}
            >
              {debtRounded === null ? (
                <span className="sk sk-line" style={{ width: 90 }} />
              ) : debtRounded > 0 ? (
                <>
                  <small>{t.payments.debtNow}</small>
                  <b>{money(debtRounded)}</b>
                </>
              ) : (
                <b>{t.payments.noDebt}</b>
              )}
            </span>
            <button
              type="button"
              className="btn btn--ghost btn--sm payform__change"
              onClick={changeChild}
            >
              {t.payments.changeChild}
            </button>
          </div>
        ) : (
          <div className="payform__picker">
            <div className="payform__search">
              <IconSearch size={16} />
              <input
                className="input"
                autoFocus
                value={query}
                placeholder={t.payments.searchHint}
                role="combobox"
                aria-labelledby="payform-child-label"
                aria-expanded={listOpen}
                aria-controls="payform-results"
                aria-activedescendant={
                  results[activeIdx]
                    ? `payform-opt-${results[activeIdx].id}`
                    : undefined
                }
                onChange={(e) => {
                  setQuery(e.target.value);
                  setListOpen(true);
                }}
                onFocus={() => setListOpen(true)}
                onBlur={() => setListOpen(false)}
                onKeyDown={onSearchKey}
              />
            </div>
            {listOpen && (
              <ul
                id="payform-results"
                role="listbox"
                className="payform__results"
                ref={listRef}
              >
                {results.length === 0 ? (
                  <li className="payform__empty">{t.common.nothingFound}</li>
                ) : (
                  results.map((c, i) => (
                    <li
                      key={c.id}
                      id={`payform-opt-${c.id}`}
                      data-idx={i}
                      role="option"
                      aria-selected={i === activeIdx}
                      className={`payform__opt${i === activeIdx ? " on" : ""}`}
                      // mousedown: input fokusni yo'qotib ro'yxat yopilmasin.
                      onMouseDown={(e) => {
                        e.preventDefault();
                        choose(c.id);
                      }}
                      onMouseEnter={() => setActiveIdx(i)}
                    >
                      <span className="avatar">{initials(c.full_name)}</span>
                      <span className="payform__opt-body">
                        <b className="tr">{c.full_name}</b>
                        <small className="tr">
                          {childGroup[c.id] ?? "—"}
                        </small>
                      </span>
                    </li>
                  ))
                )}
              </ul>
            )}
          </div>
        )}
      </div>

      <div className="form-grid">
        <div className="field">
          <label className="field__label" htmlFor="payform-amount">
            {t.payments.amount}
          </label>
          <div className="payform__amount">
            <input
              id="payform-amount"
              className="input"
              inputMode="numeric"
              autoComplete="off"
              placeholder="0"
              required
              value={amount ? moneyPlain(amount) : ""}
              onChange={(e) => {
                setAmount(e.target.value.replace(/\D/g, ""));
                setAmountTouched(true);
              }}
            />
            <span className="payform__unit">{t.common.sum}</span>
          </div>
          {debtRounded !== null &&
            debtRounded > 0 &&
            Number(amount) !== debtRounded && (
              <button
                type="button"
                className="chip payform__fill"
                onClick={() => {
                  setAmount(String(debtRounded));
                  setAmountTouched(true);
                }}
              >
                {t.payments.payFullDebt}: {money(debtRounded)}
              </button>
            )}
        </div>
        <label className="field">
          <span className="field__label">{t.common.date}</span>
          <input
            className="input"
            type="date"
            value={paidAt}
            max={isoDate(new Date())}
            onChange={(e) => setPaidAt(e.target.value)}
          />
        </label>
      </div>

      <div className="field">
        <span className="field__label">{t.payments.paymentMethod}</span>
        <div className="segmented payform__methods">
          {METHODS.map((m) => (
            <button
              type="button"
              key={m}
              className={method === m ? "on" : ""}
              aria-pressed={method === m}
              onClick={() => setMethod(m)}
            >
              {methodLabel[m]}
            </button>
          ))}
        </div>
      </div>

      <label className="field">
        <span className="field__label">
          {t.common.reason} ({t.common.optional})
        </span>
        <input
          className="input"
          value={reference}
          maxLength={255}
          onChange={(e) => setReference(e.target.value)}
        />
      </label>

      {childId && (
        <div className="payform__history">
          <span className="field__label">{t.payments.recentPayments}</span>
          {payments === null ? (
            <span className="sk sk-line" style={{ width: "60%" }} />
          ) : payments.length === 0 ? (
            <p className="hint hint--left">{t.payments.noPayments}</p>
          ) : (
            <ul className="payform__history-list">
              {payments.slice(0, 5).map((p) => {
                const reversed = p.status === "REVERSED";
                return (
                  <li key={p.id} className={reversed ? "is-reversed" : ""}>
                    <span className="num">{isoDate(new Date(p.paid_at))}</span>
                    <span className="tr">
                      {methodLabel[p.payment_method as Method] ??
                        p.payment_method}
                    </span>
                    <b className="num">{money(p.amount)}</b>
                    {reversed ? (
                      <span className="badge badge--mute">
                        {t.payments.paymentReversed}
                      </span>
                    ) : confirmingId === p.id ? (
                      <span className="payform__confirm">
                        <button
                          type="button"
                          className="btn btn--danger btn--sm"
                          disabled={reversingId === p.id}
                          onClick={() => void reverse(p.id)}
                        >
                          {reversingId === p.id
                            ? t.common.saving
                            : t.payments.reverseConfirm}
                        </button>
                        <button
                          type="button"
                          className="btn btn--ghost btn--sm"
                          onClick={() => setConfirmingId(null)}
                        >
                          {t.common.no}
                        </button>
                      </span>
                    ) : (
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        onClick={() => setConfirmingId(p.id)}
                      >
                        {t.common.reverse}
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
          {historyError && (
            <p className="error" role="alert">
              {historyError}
            </p>
          )}
        </div>
      )}

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      <div className="modal-actions">
        <span className="spacer" />
        <button type="button" className="btn btn--ghost" onClick={onCancel}>
          {t.common.cancel}
        </button>
        <button
          className="btn"
          type="submit"
          disabled={saving || !childId || !amount}
        >
          {saving ? t.common.saving : t.payments.savePayment}
        </button>
      </div>
    </form>
  );
}
