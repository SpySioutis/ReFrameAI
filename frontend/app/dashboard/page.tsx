"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Film, Plus, Search, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import Header from "@/components/Header";
import RequireAuth from "@/components/RequireAuth";
import { Badge, Button, Card, Input } from "@/components/ui";
import { useI18n } from "@/lib/i18n";
import { api, type Project } from "@/services/api";

function ProjectCard({ p, onDelete }: { p: Project; onDelete: (id: string) => void }) {
  const { t } = useI18n();
  const router = useRouter();
  const [confirm, setConfirm] = useState(false);

  return (
    <Card className="group overflow-hidden">
      <button
        onClick={() => router.push(`/editor/${p.id}`)}
        className="flex h-36 w-full items-center justify-center bg-ink-800 text-slate-600 transition-colors hover:text-accent-400"
        aria-label={p.name}
      >
        <Film size={40} />
      </button>
      <div className="p-4">
        <div className="flex items-start justify-between gap-2">
          <button onClick={() => router.push(`/editor/${p.id}`)} className="truncate text-left text-sm font-semibold text-white hover:text-accent-400">
            {p.name}
          </button>
          <Badge tone={p.source_video ? "green" : "neutral"}>{p.status}</Badge>
        </div>
        <p className="mt-1 text-xs text-slate-500">
          {p.resolution || "—"} {p.fps ? `· ${p.fps.toFixed(0)}fps` : ""} {p.duration ? `· ${p.duration.toFixed(1)}s` : ""}
        </p>
        <p className="mt-1 text-xs text-slate-600">
          {t("dashboard.modified")}: {p.updated_at ? new Date(p.updated_at).toLocaleString() : "—"}
        </p>
        <div className="mt-3 flex gap-2">
          {confirm ? (
            <>
              <Button variant="danger" className="flex-1 px-2 text-xs" onClick={() => onDelete(p.id)}>
                {t("dashboard.delete")}?
              </Button>
              <Button variant="ghost" className="px-2 text-xs" onClick={() => setConfirm(false)}>
                {t("dashboard.cancel")}
              </Button>
            </>
          ) : (
            <>
              <Button variant="secondary" className="flex-1" onClick={() => router.push(`/editor/${p.id}`)}>
                {t("dashboard.open")}
              </Button>
              <Button variant="ghost" aria-label={t("dashboard.delete")} onClick={() => setConfirm(true)}>
                <Trash2 size={16} />
              </Button>
            </>
          )}
        </div>
      </div>
    </Card>
  );
}

export default function DashboardPage() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const router = useRouter();

  const { data, isLoading, error } = useQuery({ queryKey: ["projects"], queryFn: api.projects });

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const list = [...(data || [])].sort((a, b) => b.updated_at.localeCompare(a.updated_at));
    return q ? list.filter((p) => p.name.toLowerCase().includes(q)) : list;
  }, [data, search]);

  async function create() {
    setCreating(true);
    try {
      const p = await api.createProject(`Project ${new Date().toLocaleString()}`);
      await qc.invalidateQueries({ queryKey: ["projects"] });
      router.push(`/editor/${p.id}`);
    } finally {
      setCreating(false);
    }
  }

  async function remove(id: string) {
    await api.deleteProject(id);
    await qc.invalidateQueries({ queryKey: ["projects"] });
  }

  return (
    <RequireAuth>
      <div className="min-h-screen">
        <Header />
        <main className="mx-auto max-w-7xl px-4 py-8">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <h1 className="text-2xl font-bold text-white">{t("dashboard.title")}</h1>
            <Button onClick={create} disabled={creating}>
              <Plus size={16} /> {t("dashboard.new")}
            </Button>
          </div>
          <div className="relative mt-4 max-w-md">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t("dashboard.search")} className="pl-9" />
          </div>
          {isLoading && <p className="mt-8 text-sm text-slate-500">{t("common.loading")}</p>}
          {error && <p className="mt-8 text-sm text-red-300">{t("common.error")}</p>}
          {data && filtered.length === 0 && (
            <p className="mt-8 rounded-xl border border-dashed border-ink-600 p-8 text-center text-sm text-slate-500">
              {t("dashboard.empty")}
            </p>
          )}
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filtered.map((p) => (
              <ProjectCard key={p.id} p={p} onDelete={remove} />
            ))}
          </div>
        </main>
      </div>
    </RequireAuth>
  );
}
