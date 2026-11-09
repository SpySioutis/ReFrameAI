"use client";

import React from "react";

type BtnVariant = "primary" | "secondary" | "ghost" | "danger";

export function Button({
  children,
  variant = "primary",
  className = "",
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: BtnVariant }) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-accent-500/50";
  const styles: Record<BtnVariant, string> = {
    primary: "bg-accent-500 hover:bg-accent-600 text-white",
    secondary: "bg-ink-700 hover:bg-ink-600 text-slate-100 border border-ink-600",
    ghost: "text-slate-300 hover:text-white hover:bg-ink-800",
    danger: "bg-red-600/90 hover:bg-red-600 text-white",
  };
  return (
    <button className={`${base} ${styles[variant]} ${className}`} {...rest}>
      {children}
    </button>
  );
}

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-ink-700 bg-ink-900 ${className}`}>{children}</div>
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full rounded-lg border border-ink-600 bg-ink-850 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-accent-500 focus:outline-none ${props.className || ""}`}
    />
  );
}

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={`w-full rounded-lg border border-ink-600 bg-ink-850 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-accent-500 focus:outline-none ${props.className || ""}`}
    />
  );
}

export function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "green" | "amber" | "red" | "blue" }) {
  const tones = {
    neutral: "bg-ink-700 text-slate-300",
    green: "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30",
    amber: "bg-amber-500/15 text-amber-300 border border-amber-500/30",
    red: "bg-red-500/15 text-red-300 border border-red-500/30",
    blue: "bg-accent-500/15 text-accent-400 border border-accent-500/30",
  } as const;
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function Progress({ value }: { value: number }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-700">
      <div
        className="h-full rounded-full bg-accent-500 transition-all"
        style={{ width: `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%` }}
      />
    </div>
  );
}

export function Panel({ title, children, className = "" }: { title?: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-ink-700 bg-ink-900 ${className}`}>
      {title && (
        <header className="border-b border-ink-700 px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}
