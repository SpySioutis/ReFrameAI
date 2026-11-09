"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import Header from "@/components/Header";
import { Button, Card, Input } from "@/components/ui";
import { useI18n } from "@/lib/i18n";
import { ApiError, api } from "@/services/api";
import { useAuth } from "@/stores";

function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const { t } = useI18n();
  const router = useRouter();
  const setAuth = useAuth((s) => s.setAuth);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = mode === "login" ? await api.login(email, password) : await api.register(email, password);
      setAuth(res.token, res.user.email);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("auth.error"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-md px-4 pt-16">
        <Card className="p-8">
          <h1 className="text-xl font-bold text-white">
            {mode === "login" ? t("auth.loginTitle") : t("auth.signupTitle")}
          </h1>
          <form onSubmit={submit} className="mt-6 space-y-4">
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-slate-400">{t("auth.email")}</span>
              <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-slate-400">{t("auth.password")}</span>
              <Input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete={mode === "login" ? "current-password" : "new-password"} />
            </label>
            {error && <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p>}
            <Button type="submit" disabled={busy} className="w-full">
              {busy ? t("common.loading") : mode === "login" ? t("auth.loginBtn") : t("auth.signupBtn")}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-slate-500">
            {mode === "login" ? t("auth.noAccount") : t("auth.hasAccount")}{" "}
            <Link href={mode === "login" ? "/signup" : "/login"} className="text-accent-400 hover:text-accent-500">
              {mode === "login" ? t("auth.signupBtn") : t("auth.loginBtn")}
            </Link>
          </p>
        </Card>
      </main>
    </div>
  );
}

export function LoginPage() {
  return <AuthForm mode="login" />;
}

export function SignupPage() {
  return <AuthForm mode="signup" />;
}
