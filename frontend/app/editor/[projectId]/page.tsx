"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Download,
  Eraser,
  Maximize2,
  Pause,
  Play,
  Scan,
  SkipBack,
  SkipForward,
  Upload,
  Wand2,
  X,
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import Header from "@/components/Header";
import RequireAuth from "@/components/RequireAuth";
import Assistant from "@/components/editor/Assistant";
import Timeline from "@/components/editor/Timeline";
import VideoStage from "@/components/editor/VideoStage";
import { Badge, Button, Panel, Progress, TextArea } from "@/components/ui";
import { screenToVideo } from "@/lib/coordinates";
import { useI18n } from "@/lib/i18n";
import { ApiError, api, fetchBlobUrl, type Job, type VideoMeta } from "@/services/api";
import { useEditor } from "@/stores";

type Op = "remove" | "replace" | "restyle";

function useJobPoll(jobId: string | null) {
  const [job, setJob] = useState<Job | null>(null);
  useEffect(() => {
    if (!jobId) {
      setJob(null);
      return;
    }
    let alive = true;
    const tick = async () => {
      try {
        const j = await api.job(jobId);
        if (alive) setJob(j);
        if (j.status === "done" || j.status === "failed" || j.status === "cancelled") return;
      } catch {
        /* keep polling */
      }
      if (alive) setTimeout(tick, 900);
    };
    tick();
    return () => {
      alive = false;
    };
  }, [jobId]);
  return job;
}

export default function EditorPage() {
  const params = useParams();
  const projectId = params.projectId as string;
  const { t } = useI18n();
  const router = useRouter();
  const qc = useQueryClient();
  const videoRef = useRef<HTMLVideoElement>(null);

  const { currentFrame, setFrame, selection, setSelection, setProject } = useEditor();
  const [videoBlob, setVideoBlob] = useState<string | null>(null);
  const [maskBlob, setMaskBlob] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [op, setOp] = useState<Op>("remove");
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [compare, setCompare] = useState(false);
  const [resultBlob, setResultBlob] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const job = useJobPoll(jobId);
  const { data: project, refetch: refetchProject } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.project(projectId),
  });
  const { data: meta } = useQuery({
    queryKey: ["meta", projectId],
    queryFn: () => api.metadata(projectId),
    enabled: !!project?.source_video,
    retry: false,
  });
  const { data: providers } = useQuery({ queryKey: ["providers"], queryFn: api.providers });
  const { data: objects } = useQuery({
    queryKey: ["objects", projectId],
    queryFn: () => api.objects(projectId),
    enabled: !!project?.source_video,
  });
  const { data: results } = useQuery({
    queryKey: ["results", projectId],
    queryFn: () => api.results(projectId),
    enabled: !!project?.source_video,
  });

  const aiReady = (providers || []).some((p) => p.state === "ready");
  const frames: number = meta?.frames || 0;
  const fps: number = meta?.fps || 30;

  useEffect(() => {
    setProject(projectId);
  }, [projectId, setProject]);

  // Load protected video bytes once per project version.
  useEffect(() => {
    let revoke = "";
    if (!project?.source_video) {
      setVideoBlob(null);
      return;
    }
    fetchBlobUrl(api.videoUrl(projectId))
      .then((u) => {
        revoke = u;
        setVideoBlob(u);
      })
      .catch((e) => setError(e instanceof Error ? e.message : t("common.error")));
    return () => {
      if (revoke) URL.revokeObjectURL(revoke);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project?.source_video, projectId]);

  // Load mask overlay for current selection+frame.
  useEffect(() => {
    let revoke = "";
    let cancelled = false;
    setMaskBlob(null);
    if (!selection) return;
    fetchBlobUrl(api.maskUrl(projectId, selection.objectId, selection.frame === currentFrame ? selection.frame : currentFrame))
      .then((u) => {
        if (cancelled) {
          URL.revokeObjectURL(u);
          return;
        }
        revoke = u;
        setMaskBlob(u);
      })
      .catch(() => {
        /* no mask for this frame — overlay stays empty */
      });
    return () => {
      cancelled = true;
      if (revoke) URL.revokeObjectURL(revoke);
    };
  }, [selection, currentFrame, projectId]);

  // Refresh lists when a job finishes.
  useEffect(() => {
    if (job?.status === "done") {
      qc.invalidateQueries({ queryKey: ["objects", projectId] });
      qc.invalidateQueries({ queryKey: ["results", projectId] });
      qc.invalidateQueries({ queryKey: ["history", projectId] });
    }
  }, [job?.status, projectId, qc]);

  const seek = useCallback(
    (frame: number) => {
      const v = videoRef.current;
      const f = Math.max(0, Math.min(Math.max(0, frames - 1), frame));
      setFrame(f);
      if (v && fps) {
        v.currentTime = f / fps;
      }
    },
    [frames, fps, setFrame]
  );

  const togglePlay = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) {
      v.play();
      setPlaying(true);
    } else {
      v.pause();
      setPlaying(false);
    }
  }, []);

  async function handleCanvasClick(cx: number, cy: number, cw: number, ch: number) {
    if (!meta?.width || !meta?.height || busy) return;
    videoRef.current?.pause();
    setPlaying(false);
    const p = screenToVideo(cx, cy, cw, ch, meta.width, meta.height);
    if (!p) return; // clicked on letterbox bars
    setBusy("segment");
    setError("");
    try {
      const res = await api.segment(projectId, {
        frame_number: currentFrame,
        points: [{ x: p.x, y: p.y, label: "positive" }],
      });
      setSelection({
        objectId: res.object_id,
        trackingId: res.tracking_id,
        frame: res.frame_number,
        box: res.box,
        provider: res.provider,
      });
      qc.invalidateQueries({ queryKey: ["objects", projectId] });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("common.error"));
    } finally {
      setBusy("");
    }
  }

  async function handleTrack() {
    if (!selection) return;
    setBusy("track");
    setError("");
    try {
      const j = await api.track(projectId, {
        object_id: selection.objectId,
        start_frame: selection.frame,
        direction: "forward",
      });
      setJobId(j.id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("common.error"));
    } finally {
      setBusy("");
    }
  }

  async function handleGenerate() {
    if (!selection) {
      setError(t("editor.noObject"));
      return;
    }
    if (op !== "remove" && !prompt.trim()) {
      setError(t("editor.promptPlaceholder"));
      return;
    }
    setBusy("generate");
    setError("");
    try {
      const j = await api.edit(projectId, op, {
        object_id: selection.objectId,
        prompt: op === "remove" ? "remove object" : prompt.trim(),
      });
      setJobId(j.id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("common.error"));
    } finally {
      setBusy("");
    }
  }

  async function handleUpload(file: File) {
    setUploading(true);
    setError("");
    try {
      await api.uploadVideo(projectId, file);
      await refetchProject();
      qc.invalidateQueries({ queryKey: ["meta", projectId] });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("common.error"));
    } finally {
      setUploading(false);
    }
  }

  async function handleExport() {
    setBusy("export");
    setError("");
    try {
      const j = await api.export(projectId);
      const url = await fetchBlobUrl(api.exportUrl(projectId));
      setResultBlob(url);
      setCompare(true);
      setJobId(j.id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("common.error"));
    } finally {
      setBusy("");
    }
  }

  const maskedFrames = (objects || []).flatMap(() => (selection ? [selection.frame] : []));

  return (
    <RequireAuth>
      <div className="flex min-h-screen flex-col">
        <Header />
        <main className="mx-auto w-full max-w-[1600px] flex-1 space-y-3 px-3 py-3">
          {/* Provider warning */}
          {!aiReady && (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-2.5 text-xs text-amber-200">
              {t("editor.mockWarning")}
            </div>
          )}
          {error && (
            <div className="flex items-center justify-between gap-3 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2.5 text-xs text-red-200">
              <span>{error}</span>
              <button onClick={() => setError("")} aria-label={t("common.close")}>
                <X size={14} />
              </button>
            </div>
          )}

          {!project?.source_video ? (
            <Panel>
              <label className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-ink-600 px-6 py-16 text-center hover:border-accent-500">
                <Upload size={32} className="text-slate-500" />
                <span className="mt-3 text-sm font-medium text-white">
                  {uploading ? t("common.loading") : t("dashboard.uploadVideo")}
                </span>
                <span className="mt-1 text-xs text-slate-500">MP4 · MOV · WebM</span>
                <input
                  type="file"
                  accept="video/mp4,video/quicktime,video/webm"
                  className="hidden"
                  disabled={uploading}
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleUpload(f);
                  }}
                />
              </label>
            </Panel>
          ) : (
            <>
              <div className="grid grid-cols-1 gap-3 xl:grid-cols-[300px_1fr_320px]">
                {/* LEFT: assistant */}
                <Panel title={t("editor.assistant")} className="order-2 xl:order-1">
                  <Assistant projectId={projectId} />
                </Panel>

                {/* CENTER: video */}
                <div className="order-1 space-y-3 xl:order-2">
                  <div className="flex items-center justify-between">
                    <h1 className="truncate text-sm font-semibold text-white">{project?.name}</h1>
                    <div className="flex gap-2">
                      {resultBlob && (
                        <Button variant="secondary" onClick={() => setCompare(!compare)}>
                          {t("editor.compare")}
                        </Button>
                      )}
                      <Button variant="secondary" onClick={handleExport} disabled={busy === "export"}>
                        <Download size={16} /> {t("editor.export")}
                      </Button>
                    </div>
                  </div>

                  {videoBlob && meta ? (
                    <div className={compare && resultBlob ? "grid grid-cols-1 gap-3 md:grid-cols-2" : ""}>
                      <div>
                        {compare && resultBlob && (
                          <p className="mb-1 text-xs text-slate-500">{t("editor.original")}</p>
                        )}
                        <VideoStage
                          videoUrl={videoBlob}
                          videoW={meta.width}
                          videoH={meta.height}
                          maskUrl={maskBlob}
                          box={selection && selection.frame === currentFrame ? selection.box : null}
                          fps={fps}
                          videoRef={videoRef}
                          onVideoTime={(_, f) => setFrame(f)}
                          onCanvasClick={handleCanvasClick}
                        />
                      </div>
                      {compare && resultBlob && (
                        <div>
                          <p className="mb-1 text-xs text-slate-500">{t("editor.result")}</p>
                          <video src={resultBlob} controls playsInline className="aspect-video w-full rounded-xl bg-black" style={{ objectFit: "contain" }} />
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-slate-500">{t("common.loading")}</p>
                  )}

                  {/* Transport */}
                  <div className="flex items-center justify-center gap-2">
                    <Button variant="ghost" onClick={() => seek(currentFrame - 1)} aria-label="prev frame">
                      <SkipBack size={16} />
                    </Button>
                    <Button variant="secondary" onClick={togglePlay} aria-label={playing ? "pause" : "play"}>
                      {playing ? <Pause size={16} /> : <Play size={16} />}
                    </Button>
                    <Button variant="ghost" onClick={() => seek(currentFrame + 1)} aria-label="next frame">
                      <SkipForward size={16} />
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => videoRef.current?.requestFullscreen?.()}
                      aria-label="fullscreen"
                    >
                      <Maximize2 size={16} />
                    </Button>
                  </div>

                  <Timeline frame={currentFrame} frames={frames} fps={fps} maskedFrames={maskedFrames} onSeek={seek} />

                  {job && (job.status === "running" || job.status === "queued") && (
                    <div className="rounded-xl border border-ink-700 bg-ink-900 p-4">
                      <p className="mb-2 text-xs text-slate-400">
                        {t("editor.jobRunning")} — {job.job_type} {Math.round(job.progress * 100)}%
                      </p>
                      <Progress value={job.progress} />
                    </div>
                  )}
                  {job && job.status === "failed" && (
                    <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-xs text-red-200">
                      {t("editor.jobFailed")}: {job.error_message.split("\n")[0]}
                    </div>
                  )}
                </div>

                {/* RIGHT: object + generation */}
                <div className="order-3 space-y-3">
                  <Panel title={t("editor.object")}>
                    {selection ? (
                      <div className="space-y-2 text-xs">
                        <div className="flex items-center justify-between">
                          <Badge tone="blue">#{selection.trackingId}</Badge>
                          <Badge tone={selection.provider === "sam" ? "green" : "amber"}>{selection.provider}</Badge>
                        </div>
                        <p className="text-slate-400">
                          {t("editor.frame")}: {selection.frame} · box ({Math.round(selection.box.x1)}, {Math.round(selection.box.y1)})–({Math.round(selection.box.x2)}, {Math.round(selection.box.y2)})
                        </p>
                        <Button variant="secondary" className="w-full" onClick={handleTrack} disabled={!!busy}>
                          <Scan size={16} /> {t("editor.track")}
                        </Button>
                        <Button variant="ghost" className="w-full" onClick={() => setSelection(null)}>
                          {t("common.close")}
                        </Button>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500">{t("editor.noObject")} {t("editor.selectHint")}</p>
                    )}
                    {(objects || []).length > 0 && (
                      <div className="mt-3 border-t border-ink-700 pt-2">
                        <ul className="space-y-1">
                          {(objects || []).map((o) => (
                            <li key={o.id}>
                              <button
                                onClick={() => setSelection({ objectId: o.id, trackingId: o.tracking_id, frame: currentFrame, box: { x1: 0, y1: 0, x2: 0, y2: 0 }, provider: "local" })}
                                className={`w-full truncate rounded-lg px-2 py-1 text-left text-xs ${selection?.objectId === o.id ? "bg-accent-500/20 text-white" : "text-slate-400 hover:bg-ink-800"}`}
                              >
                                #{o.tracking_id} {o.name} · {o.mask_count}
                              </button>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </Panel>

                  <Panel title={t("editor.operation")}>
                    <div className="grid grid-cols-3 gap-1 rounded-lg bg-ink-800 p-1">
                      {(["remove", "replace", "restyle"] as Op[]).map((o) => (
                        <button
                          key={o}
                          onClick={() => setOp(o)}
                          className={`rounded-md px-2 py-1.5 text-xs font-medium ${op === o ? "bg-accent-500 text-white" : "text-slate-400 hover:text-white"}`}
                        >
                          {o === "remove" ? <Eraser size={14} className="mr-1 inline" /> : <Wand2 size={14} className="mr-1 inline" />}
                          {t(`editor.${o}`)}
                        </button>
                      ))}
                    </div>
                    {op !== "remove" && (
                      <div className="mt-3">
                        <label className="mb-1 block text-xs text-slate-400">{t("editor.prompt")}</label>
                        <TextArea rows={4} value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder={t("editor.promptPlaceholder")} />
                      </div>
                    )}
                    <Button className="mt-3 w-full" onClick={handleGenerate} disabled={!!busy || !selection}>
                      {busy === "generate" ? t("common.loading") : t("editor.generate")}
                    </Button>
                  </Panel>

                  <Panel title={t("editor.results")}>
                    {(results || []).length === 0 ? (
                      <p className="text-xs text-slate-600">{t("editor.noResults")}</p>
                    ) : (
                      <ul className="space-y-2 text-xs text-slate-400">
                        {(results || []).slice(0, 10).map((r) => (
                          <li key={r.id} className="truncate">
                            {(r.metadata?.operation as string) || "result"} — {(r.metadata?.job_id as string)?.slice(0, 8)}
                          </li>
                        ))}
                      </ul>
                    )}
                  </Panel>
                </div>
              </div>
            </>
          )}
        </main>
      </div>
    </RequireAuth>
  );
}

export type { VideoMeta };
