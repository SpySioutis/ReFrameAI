import { useAuth } from "@/stores";

const API = process.env.NEXT_PUBLIC_API_URL || "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = useAuth.getState().token;
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (init.body && typeof init.body === "string" && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return (await res.json()) as T;
  return undefined as T;
}

export const api = {
  // auth
  register: (email: string, password: string) =>
    req<{ token: string; user: { id: string; email: string } }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  login: (email: string, password: string) =>
    req<{ token: string; user: { id: string; email: string } }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => req<{ id: string; email: string }>("/api/auth/me"),
  providers: () =>
    req<{ name: string; state: string; message: string; model: string }[]>("/api/providers"),
  health: () => req<{ ok: boolean; ai_configured: boolean; env: string }>("/api/health"),

  // projects
  projects: () => req<Project[]>("/api/projects"),
  createProject: (name: string) =>
    req<Project>("/api/projects", { method: "POST", body: JSON.stringify({ name }) }),
  project: (id: string) => req<Project>(`/api/projects/${id}`),
  deleteProject: (id: string) => req(`/api/projects/${id}`, { method: "DELETE" }),

  // video
  uploadVideo: async (projectId: string, file: File): Promise<Project> => {
    const token = useAuth.getState().token;
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API}/api/projects/${projectId}/video`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        detail = (await res.json()).detail || detail;
      } catch {
        /* ignore */
      }
      throw new ApiError(res.status, detail);
    }
    return (await res.json()) as Project;
  },
  metadata: (projectId: string) =>
    req<VideoMeta>(`/api/projects/${projectId}/video/metadata`),
  videoUrl: (projectId: string) => `${API}/api/projects/${projectId}/video/file`,
  thumbUrl: (projectId: string) => `${API}/api/projects/${projectId}/video/thumbnail`,
  frameUrl: (projectId: string, frame: number) =>
    `${API}/api/projects/${projectId}/frames/${frame}`,

  // objects
  segment: (projectId: string, body: SegmentBody) =>
    req<SegmentResult>(`/api/projects/${projectId}/objects/segment`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  track: (projectId: string, body: { object_id: string; start_frame: number; end_frame?: number; direction?: string }) =>
    req<Job>(`/api/projects/${projectId}/objects/track`, { method: "POST", body: JSON.stringify(body) }),
  objects: (projectId: string) =>
    req<{ id: string; name: string; tracking_id: number; mask_count: number }[]>(
      `/api/projects/${projectId}/objects`
    ),
  maskUrl: (projectId: string, objectId: string, frame: number) =>
    `${API}/api/projects/${projectId}/objects/${objectId}/masks/${frame}`,

  // editing
  edit: (projectId: string, op: "remove" | "replace" | "restyle", body: EditBody) =>
    req<Job>(`/api/projects/${projectId}/edit/${op}`, { method: "POST", body: JSON.stringify(body) }),
  history: (projectId: string) =>
    req<{ id: string; operation: string; prompt: string; object_id: string; created_at: string }[]>(
      `/api/projects/${projectId}/history`
    ),
  results: (projectId: string) =>
    req<{ id: string; path: string; metadata: Record<string, unknown> }[]>(
      `/api/projects/${projectId}/results`
    ),
  export: (projectId: string) =>
    req<Job>(`/api/projects/${projectId}/export`, { method: "POST", body: JSON.stringify({}) }),
  exportUrl: (projectId: string) => `${API}/api/projects/${projectId}/export/file`,

  // jobs
  job: (jobId: string) => req<Job>(`/api/jobs/${jobId}`),
  cancelJob: (jobId: string) => req(`/api/jobs/${jobId}/cancel`, { method: "POST" }),

  // assistant
  assistant: (messages: { role: string; content: string }[], project_id?: string) =>
    req<{ reply: string; plan: Record<string, unknown> | null; suggested_tool: string | null }>(
      "/api/assistant/chat",
      { method: "POST", body: JSON.stringify({ messages, project_id }) }
    ),
};

export function authHeaders(): Record<string, string> {
  const token = useAuth.getState().token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Fetch a protected binary URL with the auth token (for <video>/<img> we use blob URLs). */
export async function fetchBlobUrl(url: string): Promise<string> {
  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) throw new ApiError(res.status, `fetch failed: ${res.statusText}`);
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export interface Project {
  id: string;
  name: string;
  source_video: string;
  thumbnail: string;
  duration: number;
  fps: number;
  resolution: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface VideoMeta {
  duration: number;
  fps: number;
  width: number;
  height: number;
  frames: number;
  has_audio: boolean;
  codec: string;
}

export interface SegmentBody {
  frame_number: number;
  points: { x: number; y: number; label: "positive" | "negative" }[];
  box?: { x1: number; y1: number; x2: number; y2: number };
  concept?: string;
}

export interface SegmentResult {
  object_id: string;
  tracking_id: number;
  frame_number: number;
  box: { x1: number; y1: number; x2: number; y2: number };
  mask_id: string;
  confidence: number | null;
  provider: string;
}

export interface Job {
  id: string;
  job_type: string;
  status: string;
  progress: number;
  error_message: string;
  metadata: Record<string, unknown>;
}

export interface EditBody {
  object_id?: string;
  prompt: string;
  strength?: number;
  preserve_audio?: boolean;
}
