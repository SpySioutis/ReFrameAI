"use client";

import { useQuery } from "@tanstack/react-query";
import { Bot, Send } from "lucide-react";
import { useState } from "react";
import { Button, Input } from "@/components/ui";
import { useI18n } from "@/lib/i18n";
import { api } from "@/services/api";

interface Msg {
  role: "user" | "assistant";
  content: string;
}

export default function Assistant({ projectId }: { projectId: string }) {
  const { t } = useI18n();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const { data: history } = useQuery({ queryKey: ["history", projectId], queryFn: () => api.history(projectId) });

  async function send() {
    const text = draft.trim();
    if (!text || busy) return;
    const next: Msg[] = [...messages, { role: "user" as const, content: text }];
    setMessages(next);
    setDraft("");
    setBusy(true);
    try {
      const res = await api.assistant(next, projectId);
      setMessages([...next, { role: "assistant", content: res.reply }]);
    } catch (e) {
      setMessages([...next, { role: "assistant", content: e instanceof Error ? e.message : t("common.error") }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="scroll-thin max-h-64 flex-1 space-y-2 overflow-y-auto">
        {messages.length === 0 && (
          <p className="rounded-lg bg-ink-800 p-3 text-xs leading-relaxed text-slate-500">
            <Bot size={14} className="mr-1 inline text-accent-400" />
            {t("editor.selectHint")}
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`rounded-lg p-2.5 text-xs leading-relaxed ${m.role === "user" ? "bg-accent-500/15 text-slate-100" : "bg-ink-800 text-slate-300"}`}>
            {m.content}
          </div>
        ))}
        {busy && <p className="text-xs text-slate-500">{t("common.loading")}</p>}
      </div>
      <div className="mt-3 flex gap-2">
        <Input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder={t("editor.askPlaceholder")} onKeyDown={(e) => e.key === "Enter" && send()} />
        <Button onClick={send} disabled={busy} aria-label={t("editor.send")}>
          <Send size={16} />
        </Button>
      </div>
      <div className="mt-4 border-t border-ink-700 pt-3">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">{t("editor.history")}</p>
        {(history || []).length === 0 ? (
          <p className="text-xs text-slate-600">{t("editor.noHistory")}</p>
        ) : (
          <ul className="scroll-thin max-h-32 space-y-1 overflow-y-auto">
            {(history || []).slice(0, 20).map((h) => (
              <li key={h.id} className="truncate text-xs text-slate-500">
                <span className="font-medium text-slate-400">{h.operation}</span> — {h.prompt || "—"}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
