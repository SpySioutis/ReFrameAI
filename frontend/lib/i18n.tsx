"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import en from "@/locales/en.json";
import el from "@/locales/el.json";

export type Locale = "en" | "el";

type Dict = Record<string, unknown>;

const DICTS: Record<Locale, Dict> = { en: en as Dict, el: el as Dict };
const STORAGE_KEY = "reframe-locale";

function lookup(dict: Dict, key: string): string | undefined {
  let cur: unknown = dict;
  for (const part of key.split(".")) {
    if (typeof cur !== "object" || cur === null) return undefined;
    cur = (cur as Dict)[part];
  }
  return typeof cur === "string" ? cur : undefined;
}

interface I18nCtx {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (key: string) => string;
}

const Ctx = createContext<I18nCtx>({ locale: "en", setLocale: () => {}, t: (k) => k });

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved === "en" || saved === "el") setLocaleState(saved);
    } catch {
      /* ignore */
    }
  }, []);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    try {
      window.localStorage.setItem(STORAGE_KEY, l);
    } catch {
      /* ignore */
    }
    if (typeof document !== "undefined") document.documentElement.lang = l;
  }, []);

  const t = useCallback(
    (key: string): string => {
      const hit = lookup(DICTS[locale], key) ?? lookup(DICTS.en, key);
      if (hit === undefined) {
        if (process.env.NODE_ENV === "development") {
          // eslint-disable-next-line no-console
          console.warn(`[i18n] missing key: ${key}`);
        }
        return key;
      }
      return hit;
    },
    [locale]
  );

  const value = useMemo(() => ({ locale, setLocale, t }), [locale, setLocale, t]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useI18n(): I18nCtx {
  return useContext(Ctx);
}
