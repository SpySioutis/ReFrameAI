"use client";

import { ArrowRight, MousePointerClick, Eraser, Wand2, Bot, Upload, MoveRight, Play } from "lucide-react";
import Link from "next/link";
import Header from "@/components/Header";
import { Badge, Button, Card } from "@/components/ui";
import { useI18n } from "@/lib/i18n";

export default function LandingPage() {
  const { t } = useI18n();

  return (
    <div className="min-h-screen">
      <Header />
      {/* Hero */}
      <section className="mx-auto max-w-7xl px-4 pb-16 pt-16 text-center md:pt-24">
        <Badge tone="blue">{t("hero.badge")}</Badge>
        <h1 className="mx-auto mt-6 max-w-3xl text-4xl font-extrabold tracking-tight text-white md:text-6xl">
          {t("hero.title")}
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-slate-400">{t("hero.subtitle")}</p>
        <p className="mt-2 text-sm font-medium text-accent-400">{t("tagline")}</p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Link href="/signup">
            <Button className="px-6 py-3 text-base">
              {t("hero.primaryCta")} <ArrowRight size={18} />
            </Button>
          </Link>
          <a href="#features">
            <Button variant="secondary" className="px-6 py-3 text-base">{t("hero.secondaryCta")}</Button>
          </a>
        </div>

        {/* Demo strip */}
        <Card className="mx-auto mt-12 max-w-4xl overflow-hidden">
          <div className="flex items-center gap-2 border-b border-ink-700 px-4 py-2.5">
            <span className="h-2.5 w-2.5 rounded-full bg-red-500/70" />
            <span className="h-2.5 w-2.5 rounded-full bg-amber-500/70" />
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500/70" />
            <span className="ml-2 text-xs text-slate-500">reframe — editor</span>
          </div>
          <div className="grid grid-cols-1 gap-px bg-ink-700 md:grid-cols-3">
            <div className="bg-ink-900 p-6 text-left">
              <MousePointerClick className="text-accent-400" size={22} />
              <p className="mt-3 text-sm font-semibold text-white">1. {t("how.s2t")}</p>
              <p className="mt-1 text-xs text-slate-500">{t("how.s2b")}</p>
            </div>
            <div className="bg-ink-900 p-6 text-left">
              <Wand2 className="text-accent-400" size={22} />
              <p className="mt-3 text-sm font-semibold text-white">2. {t("how.s3t")}</p>
              <p className="mt-1 text-xs text-slate-500">{t("how.s3b")}</p>
            </div>
            <div className="bg-ink-900 p-6 text-left">
              <Play className="text-accent-400" size={22} />
              <p className="mt-3 text-sm font-semibold text-white">3. {t("how.s4t")}</p>
              <p className="mt-1 text-xs text-slate-500">{t("how.s4b")}</p>
            </div>
          </div>
        </Card>
      </section>

      {/* Features */}
      <section id="features" className="mx-auto max-w-7xl px-4 pb-16">
        <h2 className="text-center text-2xl font-bold text-white md:text-3xl">{t("features.title")}</h2>
        <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[
            { icon: MousePointerClick, k: "select" },
            { icon: Eraser, k: "remove" },
            { icon: Wand2, k: "replace" },
            { icon: Bot, k: "agent" },
          ].map(({ icon: Icon, k }) => (
            <Card key={k} className="p-6">
              <Icon className="text-accent-400" size={24} />
              <h3 className="mt-4 font-semibold text-white">{t(`features.${k}.title`)}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">{t(`features.${k}.body`)}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* How */}
      <section id="how" className="border-y border-ink-700 bg-ink-900/50">
        <div className="mx-auto max-w-7xl px-4 py-16">
          <h2 className="text-center text-2xl font-bold text-white md:text-3xl">{t("how.title")}</h2>
          <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-4">
            {["s1", "s2", "s3", "s4"].map((s, i) => (
              <div key={s} className="flex items-start gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent-500/20 text-sm font-bold text-accent-400">
                  {i + 1}
                </span>
                <div>
                  <h3 className="font-semibold text-white">{t(`how.${s}t`)}</h3>
                  <p className="mt-1 text-sm text-slate-400">{t(`how.${s}b`)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="mx-auto max-w-5xl px-4 py-16">
        <h2 className="text-center text-2xl font-bold text-white md:text-3xl">{t("pricing.title")}</h2>
        <p className="mt-2 text-center text-sm text-amber-300/90">{t("pricing.note")}</p>
        <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-3">
          {[t("pricing.starter"), t("pricing.pro"), t("pricing.team")].map((name, i) => (
            <Card key={name} className={`p-6 text-center ${i === 1 ? "border-accent-500/50" : ""}`}>
              <h3 className="font-semibold text-white">{name}</h3>
              <p className="mt-2 text-3xl font-extrabold text-white">
                {i === 0 ? "€0" : i === 1 ? "€19" : "€49"}
                <span className="text-sm font-normal text-slate-500">/mo</span>
              </p>
              <div className="mt-4">
                <Link href="/signup">
                  <Button variant={i === 1 ? "primary" : "secondary"} className="w-full">
                    {t("hero.primaryCta")} <MoveRight size={16} />
                  </Button>
                </Link>
              </div>
            </Card>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-ink-700">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-2 px-4 py-6 text-xs text-slate-500 md:flex-row">
          <span>© 2026 {t("brand")} — {t("footer.rights")}</span>
          <span className="flex gap-4">
            <a href="/settings">{t("footer.status")}</a>
            <Upload size={0} className="hidden" />
          </span>
        </div>
      </footer>
    </div>
  );
}
