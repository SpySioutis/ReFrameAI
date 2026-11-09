"use client";

import { useI18n } from "@/lib/i18n";

interface Props {
  frame: number;
  frames: number;
  fps: number;
  maskedFrames: number[];
  onSeek: (frame: number) => void;
}

export default function Timeline({ frame, frames, fps, maskedFrames, onSeek }: Props) {
  const { t } = useI18n();
  const time = fps ? frame / fps : 0;
  const total = fps && frames ? frames / fps : 0;
  const masked = new Set(maskedFrames);

  return (
    <div className="rounded-xl border border-ink-700 bg-ink-900 p-4">
      <div className="mb-2 flex items-center justify-between text-xs text-slate-400">
        <span className="font-semibold uppercase tracking-wider">{t("editor.timeline")}</span>
        <span className="tabular-nums">
          {t("editor.frame")} {frame} / {Math.max(0, frames - 1)} · {time.toFixed(2)}s / {total.toFixed(2)}s
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={Math.max(0, frames - 1)}
        value={Math.min(frame, Math.max(0, frames - 1))}
        onChange={(e) => onSeek(Number(e.target.value))}
        className="w-full"
        aria-label={t("editor.timeline")}
      />
      {/* Mask track */}
      <div className="relative mt-1 h-2 w-full overflow-hidden rounded bg-ink-800">
        {maskedFrames.slice(0, 2000).map((f) => (
          <span
            key={f}
            className="absolute top-0 h-full w-1 bg-accent-500/80"
            style={{ left: `${frames > 1 ? (f / (frames - 1)) * 100 : 0}%` }}
          />
        ))}
        {masked.size === 0 && <span className="absolute inset-0" />}
      </div>
    </div>
  );
}
