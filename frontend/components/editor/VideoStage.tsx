"use client";

import { useEffect, useRef, useState } from "react";
import { contentRect } from "@/lib/coordinates";

interface Props {
  videoUrl: string;
  videoW: number;
  videoH: number;
  maskUrl: string | null;
  box: { x1: number; y1: number; x2: number; y2: number } | null;
  onVideoTime: (time: number, frame: number) => void;
  onCanvasClick: (containerX: number, containerY: number, containerW: number, containerH: number) => void;
  fps: number;
  videoRef: React.RefObject<HTMLVideoElement>;
}

/** Video + click-capture canvas + mask/box overlay. */
export default function VideoStage({ videoUrl, videoW, videoH, maskUrl, box, onVideoTime, onCanvasClick, fps, videoRef }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [maskImg, setMaskImg] = useState<HTMLImageElement | null>(null);

  // Load mask image (blob URL fetched with auth by parent -> here plain URL works).
  useEffect(() => {
    if (!maskUrl) {
      setMaskImg(null);
      return;
    }
    const img = new Image();
    img.onload = () => setMaskImg(img);
    img.onerror = () => setMaskImg(null);
    img.src = maskUrl;
    return () => {
      img.onload = null;
    };
  }, [maskUrl]);

  // Redraw overlay whenever size/mask/box changes.
  useEffect(() => {
    const draw = () => {
      const container = containerRef.current;
      const canvas = canvasRef.current;
      if (!container || !canvas || !videoW || !videoH) return;
      const cw = container.clientWidth;
      const ch = container.clientHeight;
      if (canvas.width !== cw || canvas.height !== ch) {
        canvas.width = cw;
        canvas.height = ch;
      }
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.clearRect(0, 0, cw, ch);
      const r = contentRect(cw, ch, videoW, videoH);
      if (maskImg) {
        ctx.save();
        ctx.globalAlpha = 0.45;
        ctx.drawImage(maskImg, r.x, r.y, r.w, r.h);
        ctx.restore();
      }
      if (box) {
        const sx = r.w / videoW;
        const sy = r.h / videoH;
        ctx.save();
        ctx.strokeStyle = "#5b8cff";
        ctx.lineWidth = 2;
        ctx.strokeRect(r.x + box.x1 * sx, r.y + box.y1 * sy, (box.x2 - box.x1) * sx, (box.y2 - box.y1) * sy);
        ctx.restore();
      }
    };
    draw();
    window.addEventListener("resize", draw);
    return () => window.removeEventListener("resize", draw);
  }, [maskImg, box, videoW, videoH, videoUrl]);

  return (
    <div ref={containerRef} className="relative aspect-video w-full overflow-hidden rounded-xl bg-black">
      <video
        ref={videoRef}
        src={videoUrl}
        className="absolute inset-0 h-full w-full"
        style={{ objectFit: "contain" }}
        controls={false}
        playsInline
        preload="metadata"
        onTimeUpdate={(e) => {
          const v = e.currentTarget;
          onVideoTime(v.currentTime, Math.floor(v.currentTime * (fps || 30)));
        }}
      />
      <canvas
        ref={canvasRef}
        className="absolute inset-0 h-full w-full cursor-crosshair"
        onClick={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          onCanvasClick(e.clientX - rect.left, e.clientY - rect.top, rect.width, rect.height);
        }}
      />
    </div>
  );
}
