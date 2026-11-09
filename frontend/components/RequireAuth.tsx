"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/stores";

export default function RequireAuth({ children }: { children: React.ReactNode }) {
  const { token, hydrated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (hydrated && !token) router.replace("/login");
  }, [hydrated, token, router]);

  if (!hydrated) return <div className="p-8 text-sm text-slate-500">…</div>;
  if (!token) return null;
  return <>{children}</>;
}
