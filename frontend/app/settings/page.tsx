"use client";

import { useQuery } from "@tanstack/react-query";
import Header from "@/components/Header";
import RequireAuth from "@/components/RequireAuth";
import { Badge, Panel } from "@/components/ui";
import { useI18n } from "@/lib/i18n";
import { api } from "@/services/api";
import { useAuth } from "@/stores";

export default function SettingsPage() {
  const { t, locale, setLocale } = useI18n();
  const email = useAuth((s) => s.email);
  const { data: providers } = useQuery({ queryKey: ["providers"], queryFn: api.providers });

  return (
    <RequireAuth>
      <div className="min-h-screen">
        <Header />
        <main className="mx-auto max-w-3xl space-y-4 px-4 py-8">
          <h1 className="text-2xl font-bold text-white">{t("settings.title")}</h1>

          <Panel title={t("settings.language")}>
            <div className="flex gap-2" role="radiogroup" aria-label={t("settings.language")}>
              <button
                role="radio"
                aria-checked={locale === "en"}
                onClick={() => setLocale("en")}
                className={`rounded-lg border px-4 py-2 text-sm ${locale === "en" ? "border-accent-500 bg-accent-500/15 text-white" : "border-ink-600 text-slate-400"}`}
              >
                {t("settings.english")}
              </button>
              <button
                role="radio"
                aria-checked={locale === "el"}
                onClick={() => setLocale("el")}
                className={`rounded-lg border px-4 py-2 text-sm ${locale === "el" ? "border-accent-500 bg-accent-500/15 text-white" : "border-ink-600 text-slate-400"}`}
              >
                {t("settings.greek")}
              </button>
            </div>
          </Panel>

          <Panel title={t("settings.providers")}>
            <ul className="space-y-2">
              {(providers || []).map((p) => (
                <li key={p.name} className="flex items-center justify-between gap-3 rounded-lg border border-ink-700 px-3 py-2">
                  <div>
                    <p className="text-sm font-medium text-white">{p.name} <span className="text-xs text-slate-500">· {p.model}</span></p>
                    <p className="text-xs text-slate-500">{p.message}</p>
                  </div>
                  <Badge tone={p.state === "ready" ? "green" : "amber"}>
                    {p.state === "ready" ? t("settings.ready") : t("settings.notConfigured")}
                  </Badge>
                </li>
              ))}
              {!providers && <li className="text-sm text-slate-500">{t("common.loading")}</li>}
            </ul>
          </Panel>

          <Panel title={t("settings.account")}>
            <p className="text-sm text-slate-300">{email}</p>
          </Panel>
        </main>
      </div>
    </RequireAuth>
  );
}
