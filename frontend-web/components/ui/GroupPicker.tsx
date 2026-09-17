"use client";

/**
 * Guruh tanlagich — kunlik hisobot va davomat sahifalari uchun.
 *
 * Ilgari guruhlar chip qatori edi: 15 ta guruhda u kompyuterda 2 qatorni,
 * telefonda 5 qatorni (~330px) egallardi. Endi bitta tugma — unda tanlangan
 * guruh nomi turadi, bosilganda ro'yxat ochiladi. Guruhlar ko'p bo'lsa
 * ro'yxat tepasida qidiruv maydoni chiqadi.
 */

import {
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";

import {
  IconCheck,
  IconChevronDown,
  IconSearch,
  IconUsers,
} from "@/components/icons";
import type { AppStrings } from "@/lib/app-i18n";

export interface GroupOption {
  id: string;
  name: string;
}

export interface GroupPickerLabels {
  /** Ro'yxat nomi (skrinriderlar uchun), masalan "Guruhlar". */
  groups: string;
  /** Hech narsa tanlanmaganda tugmada chiqadi: "Guruhni tanlang". */
  choose: string;
  search: string;
  notFound: string;
}

export function groupPickerLabels(t: AppStrings): GroupPickerLabels {
  return {
    groups: t.pages.groups,
    choose: t.pages.chooseGroup,
    search: t.pages.groupsSearch,
    notFound: t.pages.groupsNotFound,
  };
}

// Shundan ko'p guruh bo'lsa ro'yxat tepasida qidiruv chiqadi. Kam bo'lsa
// qidiruv faqat joy oladi — ro'yxatning o'zi bir qarashda ko'rinadi.
const SEARCH_THRESHOLD = 7;

export function GroupPicker({
  groups,
  value,
  onChange,
  labels,
}: {
  groups: GroupOption[];
  value: string;
  onChange: (id: string) => void;
  labels: GroupPickerLabels;
}): ReactNode {
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const listId = useId();

  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);

  const current = groups.find((g) => g.id === value);
  const withSearch = groups.length >= SEARCH_THRESHOLD;

  const needle = query.trim().toLocaleLowerCase();
  const filtered = needle
    ? groups.filter((g) => g.name.toLocaleLowerCase().includes(needle))
    : groups;
  const activeOption = filtered[activeIndex];

  function openList(): void {
    setQuery("");
    const selected = groups.findIndex((g) => g.id === value);
    setActiveIndex(selected >= 0 ? selected : 0);
    setOpen(true);
  }

  function closeList(returnFocus: boolean): void {
    setOpen(false);
    if (returnFocus) triggerRef.current?.focus();
  }

  function pick(id: string): void {
    onChange(id);
    closeList(true);
  }

  // Ochilganda fokus qidiruvga (u bo'lmasa ro'yxatga) o'tadi; tashqariga
  // bosilsa yopiladi.
  useEffect(() => {
    if (!open) return;
    (searchRef.current ?? listRef.current)?.focus();
    function onPointerDown(e: PointerEvent): void {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  // Klaviatura bilan yurilganda faol qator ro'yxat ichida ko'rinib tursin.
  useEffect(() => {
    if (!open) return;
    const option = listRef.current?.children[activeIndex] as
      | HTMLElement
      | undefined;
    option?.scrollIntoView({ block: "nearest" });
  }, [open, activeIndex]);

  function onListKey(e: KeyboardEvent<HTMLElement>): void {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Home") {
      e.preventDefault();
      setActiveIndex(0);
    } else if (e.key === "End") {
      e.preventDefault();
      setActiveIndex(Math.max(filtered.length - 1, 0));
    } else if (e.key === "Enter" || (e.key === " " && !withSearch)) {
      e.preventDefault();
      if (activeOption) pick(activeOption.id);
    } else if (e.key === "Escape") {
      e.preventDefault();
      closeList(true);
    }
  }

  function onTriggerKey(e: KeyboardEvent<HTMLButtonElement>): void {
    if (!open && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      e.preventDefault();
      openList();
    }
  }

  const activeDescendant = activeOption
    ? `${listId}-${activeOption.id}`
    : undefined;

  return (
    <div
      className="gpick"
      ref={rootRef}
      onBlur={(e) => {
        // Fokus komponentdan butunlay chiqib ketsa (Tab) — yopiladi.
        // `relatedTarget` bo'sh bo'lsa (fokuslanmaydigan qatorga bosildi)
        // yopilmaydi: aks holda ro'yxat `click` yetib kelmasdan yo'qolardi.
        // Tashqariga bosishni `pointerdown` tinglovchisi ushlaydi.
        const next = e.relatedTarget as Node | null;
        if (open && next && !rootRef.current?.contains(next)) {
          setOpen(false);
        }
      }}
    >
      <button
        type="button"
        ref={triggerRef}
        className={`gpick__trigger${open ? " on" : ""}`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={
          current ? `${labels.groups}: ${current.name}` : labels.choose
        }
        disabled={groups.length === 0}
        onClick={() => (open ? closeList(false) : openList())}
        onKeyDown={onTriggerKey}
      >
        <span className="gpick__icon">
          <IconUsers size={15} />
        </span>
        <span className={`gpick__value${current ? "" : " is-empty"}`}>
          {current ? current.name : labels.choose}
        </span>
        {groups.length > 1 && (
          <span className="gpick__count">{groups.length}</span>
        )}
        <span className="gpick__chevron">
          <IconChevronDown size={16} />
        </span>
      </button>

      {open && (
        <div className="gpick__pop">
          {withSearch && (
            <div className="gpick__search">
              <IconSearch size={15} />
              <input
                ref={searchRef}
                className="input"
                type="search"
                role="combobox"
                aria-expanded
                aria-controls={listId}
                aria-autocomplete="list"
                aria-activedescendant={activeDescendant}
                aria-label={labels.search}
                placeholder={labels.search}
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setActiveIndex(0);
                }}
                onKeyDown={onListKey}
              />
            </div>
          )}
          {filtered.length === 0 ? (
            <p className="gpick__empty">{labels.notFound}</p>
          ) : (
            <ul
              className="gpick__list"
              id={listId}
              role="listbox"
              aria-label={labels.groups}
              aria-activedescendant={withSearch ? undefined : activeDescendant}
              tabIndex={withSearch ? undefined : -1}
              ref={listRef}
              onKeyDown={withSearch ? undefined : onListKey}
            >
              {filtered.map((g, i) => {
                const selected = g.id === value;
                return (
                  <li
                    key={g.id}
                    id={`${listId}-${g.id}`}
                    role="option"
                    aria-selected={selected}
                    className={`gpick__option${i === activeIndex ? " active" : ""}${selected ? " selected" : ""}`}
                    onPointerMove={() => setActiveIndex(i)}
                    onClick={() => pick(g.id)}
                  >
                    <span>{g.name}</span>
                    {selected && <IconCheck size={15} />}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
