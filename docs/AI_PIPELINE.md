# AI_PIPELINE.md

## Providers (all via `https://api.meta.ai/v1`, Bearer `MODEL_API_KEY`)

### SAM 3.1 — segmentation & tracking (`app/ai/sam/`)
- Image: `POST /v1/responses`, `model=sam-3.1`, `input_text` (concept noun phrase
  **or** object-prompt tokens, never both) + `input_image` (data URL).
- Video: upload once via `POST /v1/files` (`purpose=user_data`) → `input_video.file_id`,
  `metadata={propagation_direction, mask_encoding: one_bit, include_confidence}`.
- Response: `output_text` lines `<Nf>id<|box;…|><|mask;…|>…` parsed by `parser.py`
  (boxes fully parsed; mask base85 unwrapped; box-ellipse fallback when the packed
  bitfield layout can't be verified — labeled honestly).
- Coordinate rule: frontend sends **source pixels** with media `w/h` (see
  `frontend/lib/coordinates.ts`); aspect mismatch → API 400.
- Limits honored: MP4/MOV H.264/H.265/MPEG-4 only, ≤15k frames, ≤16 objects.
- No key → `local` GrabCut fallback (clearly labeled `provider="local"`).

### Muse Image 1.0 — generation (`app/ai/muse_image/`)
- `POST /v1/images/generations` (text-to-image) and `POST /v1/images/edits`
  (JSON `{images:[{image_url: dataURL}], prompt}`) — verified shapes.
- **No `mask` param** (API returns 400) → mask-aware editing is an intermediate
  pipeline: crop around object → edit → feathered composite (see below).
- Prompts are wrapped with preservation requirements (perspective, lighting,
  shadows, reflections, scale, context).

### Muse Spark 1.3 — planning (`app/ai/muse_spark/`)
- `POST /v1/chat/completions`, `model=muse-spark-1.3`, JSON planning prompt.
- Output: `{operation, target, prompt, tool, args, needs_clarification, question}`.
- Allowlisted tools only (`orchestration/tools.py`, Pydantic-validated). No shell.
- No key → deterministic rule-based planner (remove/replace/restyle/detect).

## Temporal consistency (`app/video/temporal.py`, `inpaint.py`)

1. Masks per frame (SAM tracking or Farneback optical-flow propagation).
2. **Remove**: Telea inpaint per frame over flow-propagated masks (no flicker gaps).
3. **Replace/restyle**: ONE Muse Image hero from the middle keyframe crop, then
   centroid motion-following + feathered alpha composite per frame. Never
   generate frames independently.
4. Encode H.264 +faststart, mux source audio (AAC), preserve FPS.
5. Future: swap `inpaint_frame` for ProPainter; add video-diffusion refinement.

## Pipeline stages (never conflated)

segmentation (SAM) → tracking (flow/SAM-video) → generation (Muse Image) →
inpainting (OpenCV/ProPainter) → temporal consistency (flow+smoothing) →
compositing (feathered alpha) → export (FFmpeg+audio).
