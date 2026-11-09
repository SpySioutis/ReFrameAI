"use client";

import { Clapperboard } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useI18n } from "@/lib/i18n";
import { useAuth } from "@/stores";
import LanguageSwitch from "./LanguageSwitch";
import { Button } from "./ui";

export default function Header() {
  const { t } = useI18n();
  const { token, email, logout, hydrated } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const onLanding = pathname === "/";

  return (
    <header className="sticky top-0 z-40 border-b border-ink-700 bg-ink-950/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-4 px-4">
        <Link href={token ? "/dashboard" : "/"} className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-500 text-white">
            <Clapperboard size={18} />
          </span>
          <span className="text-base font-bold tracking-tight text-white">{t("brand")}</span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {onLanding ? (
            <>
              <a href="#features" className="rounded-lg px-3 py-1.5 text-sm text-slate-400 hover:text-white">{t("nav.features")}</a>
              <a href="#how" className="rounded-lg px-3 py-1.5 text-sm text-slate-400 hover:text-white">{t("nav.howItWorks")}</a>
              <a href="#pricing" className="rounded-lg px-3 py-1.5 text-sm text-slate-400 hover:text-white">{t("nav.pricing")}</a>
            </>
          ) : token ? (
            <>
              <Link href="/dashboard" className="rounded-lg px-3 py-1.5 text-sm text-slate-400 hover:text-white">{t("nav.dashboard")}</Link>
              <Link href="/projects" className="rounded-lg px-3 py-1.5 text-sm text-slate-400 hover:text-white">{t("nav.projects")}</Link>
              <Link href="/settings" className="rounded-lg px-3 py-1.5 text-sm text-slate-400 hover:text-white">{t("nav.settings")}</Link>
            </>
          ) : null}
        </nav>

        <div className="flex items-center gap-2">
          <LanguageSwitch />
          {hydrated && token ? (
            <>
              <span className="hidden max-w-40 truncate text-xs text-slate-500 sm:inline">{email}</span>
              <Button variant="ghost" onClick={() => { logout(); router.push("/"); }}>
                {t("nav.logout")}
              </Button>
            </>
          ) : (
            hydrated && (
              <>
                <Link href="/login" className="rounded-lg px-3 py-1.5 text-sm text-slate-300 hover:text-white">
                  {t("nav.login")}
                </Link>
                <Link href="/signup">
                  <Button>{t("nav.startEditing")}</Button>
                </Link>
              </>
            )
          )}
        </div>
      </div>
    </header>
  );
}
