"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

import {
  IconCheck,
  IconChevronDown,
  IconGlobe,
  IconMoon,
  IconSun,
} from "@/components/icons";
import type { Lang } from "@/lib/lang";
import { useTheme } from "@/lib/useTheme";

const LANGS: Lang[] = ["uz", "ru", "en"];

// Ro'yxatda til o'z nomi bilan yoziladi ("Русский", "English") — qisqartma
// faqat tugmada qoladi, chunki burchakda joy tor.
const LANG_LABEL: Record<Lang, string> = {
  uz: "O'zbekcha",
  ru: "Русский",
  en: "English",
};

/** Kirish sahifalarining o'ng yuqori burchagi: til va mavzu. */
export function AuthTopbar({
  lang,
  setLang,
  themeLabel,
  languageLabel,
}: {
  lang: Lang;
  setLang: (l: Lang) => void;
  themeLabel: string;
  languageLabel: string;
}): ReactNode {
  const { dark, toggle } = useTheme();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent): void {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent): void {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="auth-topbar">
      <div className="pop" ref={ref}>
        <button
          type="button"
          className={`auth-langbtn${open ? " on" : ""}`}
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-label={languageLabel}
          title={languageLabel}
          onClick={() => setOpen((v) => !v)}
        >
          <IconGlobe size={16} />
          <span>{lang.toUpperCase()}</span>
          <IconChevronDown size={14} />
        </button>
        {open && (
          <div className="pop__panel auth-lang-panel" role="listbox">
            {LANGS.map((l) => (
              <button
                key={l}
                type="button"
                role="option"
                aria-selected={l === lang}
                className={`pop__item${l === lang ? " on" : ""}`}
                onClick={() => {
                  setLang(l);
                  setOpen(false);
                }}
              >
                <span>{LANG_LABEL[l]}</span>
                {l === lang && <IconCheck size={15} />}
              </button>
            ))}
          </div>
        )}
      </div>
      <button
        type="button"
        className="btn--icon auth-themebtn"
        onClick={toggle}
        title={themeLabel}
        aria-label={themeLabel}
        aria-pressed={dark}
      >
        {dark ? <IconMoon size={18} /> : <IconSun size={18} />}
      </button>
    </div>
  );
}
