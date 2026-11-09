"use client";

import { Languages } from "lucide-react";
import { useI18n, type Locale } from "@/lib/i18n";

export default function LanguageSwitch() {
  const { locale, setLocale, t } = useI18n();
  const next: Locale = locale === "en" ? "el" : "en";
  return (
    <button
      onClick={() => setLocale(next)}
      title={t("common.languageSwitch")}
      aria-label={t("settings.language")}
      className="inline-flex items-center gap-1.5 rounded-lg border border-ink-600 bg-ink-850 px-2.5 py-1.5 text-xs font-semibold text-slate-300 hover:border-ink-600 hover:text-white"
    >
      <Languages size={14} />
      <span>{locale === "en" ? "EN" : "ΕΛ"}</span>
      <span className="text-slate-500">⇄</span>
      <span className="text-slate-500">{locale === "en" ? "ΕΛ" : "EN"}</span>
    </button>
  );
}
