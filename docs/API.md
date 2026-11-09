# API.md

Base URL (dev): `http://localhost:8000`. All `/api/*` except register/login/health
require `Authorization: Bearer <token>`.

## Auth

- `POST /api/auth/register` `{email, password(≥8)}` → `{token, user}`
- `POST /api/auth/login` `{email, password}` → `{token, user}`
- `POST /api/auth/logout` → `{ok:true}`
- `GET /api/auth/me` → `{id, email}`

## Projects

- `GET /api/projects` → `Project[]`
- `POST /api/projects` `{name}` → `Project`
- `GET /api/projects/{id}` → `Project`
- `DELETE /api/projects/{id}` → `{ok:true}`

## Video

- `POST /api/projects/{id}/video` multipart `file` (mp4/mov/webm) → `Project` (updated meta)
- `GET /api/projects/{id}/video/metadata` → `{duration, fps, width, height, frames, has_audio, codec}`
- `GET /api/projects/{id}/video/file` → video bytes
- `GET /api/projects/{id}/video/thumbnail` → jpeg bytes
- `GET /api/projects/{id}/frames/{n}` → jpeg bytes (cached)

## Objects

- `POST /api/projects/{id}/objects/segment`
  `{frame_number, points:[{x,y,label}], box?, concept?}` → `{object_id, tracking_id, box, mask_id, provider, confidence}`
- `POST /api/projects/{id}/objects/track` `{object_id, start_frame, end_frame?, direction}` → `Job`
- `POST /api/projects/{id}/objects/refine` `{object_id, frame_number, points, box?}` → segment result
- `GET /api/projects/{id}/objects` → `[{id, name, tracking_id, mask_count}]`
- `GET /api/projects/{id}/objects/{oid}/masks/{n}` → mask PNG bytes

## Editing

- `POST /api/projects/{id}/edit/remove` `{object_id}` → `Job`
- `POST /api/projects/{id}/edit/replace` `{object_id, prompt, strength?}` → `Job`
- `POST /api/projects/{id}/edit/restyle` `{object_id, prompt, strength?}` → `Job`
- `GET /api/projects/{id}/history` → operation history
- `GET /api/projects/{id}/results` → result assets

## Jobs

- `GET /api/jobs/{id}` → `{id, job_type, status, progress, error_message, metadata}`
- `POST /api/jobs/{id}/cancel` → `{ok:true}`
- `GET /api/jobs/{id}/events` → SSE `progress` events until done/failed/cancelled

Statuses: `queued | running | done | failed | cancelled`.

## Export

- `POST /api/projects/{id}/export` `{quality?, preserve_audio?}` → `Job` (done, `metadata.result`)
- `GET /api/projects/{id}/export/file` → MP4 bytes (latest successful result or source)

## Assistant

- `POST /api/assistant/chat` `{project_id?, messages:[{role, content}]}` →
  `{reply, plan:{operation,target,prompt,args}|null, suggested_tool|null}`

## Providers

- `GET /api/providers` → `[{name, state, message, model}]`
  states: `not_configured | ready | processing | rate_limited | failed | temporarily_unavailable`

## Health

- `GET /api/health` → `{ok, ai_configured, env}`

## Errors

JSON `{detail, code?}` with HTTP 400 (validation), 401 (auth), 404 (missing),
429 (rate limited), 5xx (provider failures include upstream excerpt).
