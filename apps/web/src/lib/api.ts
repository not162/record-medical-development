const rawApiUrl = process.env.NEXT_PUBLIC_API_URL;
export const API_BASE_URL = rawApiUrl
  ? (rawApiUrl.endsWith("/api/v1") ? rawApiUrl : `${rawApiUrl.replace(/\/+$/, "")}/api/v1`)
  : (typeof window !== "undefined" ? "/api/v1" : "http://127.0.0.1:8000/api/v1");

export interface User {
  id: string;
  username: string;
  email: string;
  role: "USER" | "ADMIN";
  full_name?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface PatientProfile {
  id: string;
  user_id: string;
  nik_anonymized?: string | null;
  age?: number | null;
  gender?: string | null;
  blood_type?: string | null;
  medical_history_summary?: string | null;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  username: string;
  email: string;
  role: "USER" | "ADMIN";
  full_name?: string | null;
}

export interface AuditLog {
  id: string;
  user_id?: string | null;
  action: string;
  resource_type: string;
  resource_id?: string | null;
  status: string;
  ip_address?: string | null;
  details?: string | null;
  created_at: string;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("clinical_token");
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem("clinical_token", token);
}

export function removeToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("clinical_token");
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = "";
    try {
      const errJson = await response.json();
      errorDetail = formatErrorDetail(errJson?.detail, response.status);
    } catch {
      // Non-JSON response
    }

    if (!errorDetail) {
      if (response.status === 404) {
        errorDetail = "Layanan atau endpoint klinis tidak ditemukan (404 Not Found).";
      } else if (response.status === 401) {
        errorDetail = "Kredensial tidak valid atau sesi otentikasi telah berakhir (401 Unauthorized).";
      } else if (response.status === 403) {
        errorDetail = "Akses ditolak: Anda tidak memiliki hak otorisasi yang memadai (403 Forbidden).";
      } else if (response.status >= 500) {
        errorDetail = "Gangguan pada server gateway klinis (500 Internal Error). Silakan coba beberapa saat lagi.";
      } else {
        errorDetail = `HTTP ${response.status}: ${response.statusText || "Permintaan gagal diproses."}`;
      }
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

/** Mengubah `detail` FastAPI (string / array validasi 422) menjadi pesan ramah. */
export function formatErrorDetail(detail: unknown, status?: number): string {
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((d) => {
        if (typeof d === "string") return d;
        if (d && typeof d === "object") {
          const item = d as { msg?: string; loc?: unknown[] };
          const field = Array.isArray(item.loc) ? item.loc.filter((x) => x !== "body").join(".") : "";
          return item.msg ? (field ? `${field}: ${item.msg}` : item.msg) : "";
        }
        return "";
      })
      .filter(Boolean);
    if (msgs.length) return msgs.join("; ");
  }
  if (status === 401) return "Sesi berakhir atau tidak berwenang. Silakan masuk kembali.";
  if (status === 403) return "Anda tidak memiliki izin untuk aksi ini.";
  if (status === 404) return "Data tidak ditemukan.";
  if (status && status >= 500) return "Server sedang bermasalah. Coba lagi beberapa saat.";
  return "";
}

// ---------- Tipe: Knowledge Base ----------
export interface KnowledgeDoc {
  id: string;
  title: string;
  department: string;
  content: string;
  source?: string | null;
  approval_status: string;
}

export interface KnowledgeInput {
  title: string;
  department: string;
  content: string;
  source?: string | null;
  approval_status?: string;
}

// ---------- Tipe: Graph ----------
export type GraphCategory = "DISEASE" | "SYMPTOM" | "DRUG" | "DEPARTMENT" | "GUIDELINE";
export type GraphRelation = "CONTRAINDICATES" | "HAS_SYMPTOM" | "RECOMMENDS" | "TREATED_IN" | "GOVERNED_BY";

export interface GraphNodeInput {
  id?: string;
  name: string;
  category: GraphCategory;
  properties?: Record<string, string | number | boolean | null>;
}

export interface GraphEdgeInput {
  source: string;
  target: string;
  relation: GraphRelation;
  properties?: Record<string, string | number | boolean | null>;
}

// ---------- Tipe: Jobs ----------
export interface ProcessJobsResult {
  status?: string;
  message?: string;
  job_id?: string | null;
  processed?: number;
  [key: string]: unknown;
}

const jsonBody = (data: unknown) => JSON.stringify(data);

// Terjemahan payload UI graf (name/category/properties) -> kontrak backend (id/label/type/department/reason)
const graphNodePayload = (d: Partial<GraphNodeInput>) => {
  const out: Record<string, unknown> = {};
  if (d.id) out.id = d.id;
  if (d.name !== undefined) out.label = d.name;
  if (d.category !== undefined) out.type = d.category;
  const dept = d.properties?.department;
  if (typeof dept === "string") out.department = dept;
  return out;
};


// ---------- Tipe: Clinical Chat (Paginasi & Clean DTO Pasien) ----------
export interface SessionItem {
  id: string;
  title: string;
  summary?: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface PaginatedSessions {
  items: SessionItem[];
  next_cursor?: string | null;
  has_more: boolean;
}

export interface ChatCitation {
  chunk_id: string;
  doc_id: string;
  department: string;
  title?: string;
  relevance_score?: number;
}

export interface ChatMessageItem {
  id: string;
  session_id: string;
  sender_role: "user" | "assistant" | "system";
  content: string;
  citations?: ChatCitation[] | null;
  safety_alert?: boolean;
  created_at: string;
}

export interface SessionDetail {
  id: string;
  title: string;
  summary?: string | null;
  created_at: string;
  updated_at: string;
  total_messages: number;
  has_more: boolean;
  next_cursor?: string | null;
  messages: ChatMessageItem[];
}

export interface QuotaStatus {
  quota_used: number;
  quota_max: number;
  quota_remaining: number;
  is_clinic_health_lock: boolean;
  reset_at: string | null;
  seconds_remaining: number;
  window_hours: number;
  policy: string;
  referral_info: {
    emergency_phone: string;
    hospital_name: string;
    clinic_name: string;
    operating_hours: string;
  };
}

export const api = {
  auth: {
    login: (credentials: { username_or_email: string; password: string }) =>
      apiRequest<AuthResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify(credentials),
      }),
    register: (data: { username: string; email: string; password: string; full_name?: string }) =>
      apiRequest<User>("/auth/register", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    logout: () =>
      apiRequest<{ message: string }>("/auth/logout", {
        method: "POST",
      }),
    me: () => apiRequest<User>("/auth/me"),
    getProfile: () => apiRequest<PatientProfile>("/profile"),
    updateProfile: (data: Partial<PatientProfile> & { full_name?: string }) =>
      apiRequest<PatientProfile>("/profile", {
        method: "PUT",
        body: JSON.stringify(data),
      }),
  },
  admin: {
    // Knowledge base CRUD (DatasetRecord)
    listKnowledge: () => apiRequest<KnowledgeDoc[] | { items: KnowledgeDoc[] }>("/admin/knowledge"),
    getKnowledge: (id: string) => apiRequest<KnowledgeDoc>(`/admin/knowledge/${encodeURIComponent(id)}`),
    createKnowledge: (data: KnowledgeInput) =>
      apiRequest<KnowledgeDoc>("/admin/knowledge", { method: "POST", body: jsonBody(data) }),
    updateKnowledge: (id: string, data: Partial<KnowledgeInput>) =>
      apiRequest<KnowledgeDoc>(`/admin/knowledge/${encodeURIComponent(id)}`, { method: "PUT", body: jsonBody(data) }),
    deleteKnowledge: (id: string) =>
      apiRequest<Record<string, unknown>>(`/admin/knowledge/${encodeURIComponent(id)}`, { method: "DELETE" }),
    reindexKnowledge: () =>
      apiRequest<Record<string, unknown>>("/admin/knowledge/reindex", { method: "POST" }),
    // Graph CRUD
    createGraphNode: (data: GraphNodeInput) =>
      apiRequest<Record<string, unknown>>("/admin/graph/nodes", { method: "POST", body: jsonBody({ id: data.id || `NODE:${Date.now().toString(36)}`, ...graphNodePayload(data) }) }),
    updateGraphNode: (id: string, data: Partial<GraphNodeInput>) =>
      apiRequest<Record<string, unknown>>(`/admin/graph/nodes/${encodeURIComponent(id)}`, { method: "PUT", body: jsonBody(graphNodePayload({ ...data, id: undefined })) }),
    deleteGraphNode: (id: string) =>
      apiRequest<Record<string, unknown>>(`/admin/graph/nodes/${encodeURIComponent(id)}`, { method: "DELETE" }),
    createGraphEdge: (data: GraphEdgeInput) =>
      apiRequest<Record<string, unknown>>("/admin/graph/edges", {
        method: "POST",
        body: jsonBody({
          source: data.source,
          target: data.target,
          relation: data.relation,
          reason: typeof data.properties?.notes === "string" ? data.properties.notes : "",
        }),
      }),
    deleteGraphEdge: (id: string | number) =>
      apiRequest<Record<string, unknown>>(`/admin/graph/edges/${encodeURIComponent(String(id))}`, { method: "DELETE" }),
    seedGraph: () =>
      apiRequest<Record<string, unknown>>("/admin/graph/seed", { method: "POST" }),
    // Training queue
    processJobs: () =>
      apiRequest<ProcessJobsResult>("/admin/jobs/process", { method: "POST" }),
    getDashboard: () => apiRequest<Record<string, unknown>>("/admin/dashboard"),
    getAuditLogs: (limit = 50, offset = 0) =>
      apiRequest<AuditLog[]>(`/admin/audit-logs?limit=${limit}&offset=${offset}`),
    getUsers: (limit = 50, offset = 0) =>
      apiRequest<User[]>(`/admin/users?limit=${limit}&offset=${offset}`),
    runPeriodicAudit: () =>
      apiRequest<{ status: string; message: string; audit_data: Record<string, unknown> }>("/admin/audit/run-periodic", {
        method: "POST",
      }),
    getPeriodicAuditReports: () =>
      apiRequest<Array<{ filename: string; timestamp: string; overall_status: string; duration_seconds: number; critical_findings_count: number }>>("/admin/audit/reports"),
  },
  chat: {
    listSessions: (limit = 20, cursor?: string) => {
      const q = new URLSearchParams();
      q.set("limit", String(limit));
      if (cursor) q.set("cursor", cursor);
      return apiRequest<PaginatedSessions>(`/chat/sessions?${q.toString()}`);
    },
    createSession: (title?: string) =>
      apiRequest<{ id: string; title: string; created_at: string; updated_at: string }>("/chat/sessions", {
        method: "POST",
        body: JSON.stringify({ title: title || "Konsultasi Klinis Baru" }),
      }),
    getSession: (sessionId: string, limit = 20, before?: string) => {
      const q = new URLSearchParams();
      q.set("limit", String(limit));
      if (before) q.set("before", before);
      return apiRequest<SessionDetail>(`/chat/sessions/${encodeURIComponent(sessionId)}?${q.toString()}`);
    },
    deleteSession: (sessionId: string) =>
      apiRequest<{ status: string; message: string }>(`/chat/sessions/${encodeURIComponent(sessionId)}`, {
        method: "DELETE",
      }),
    sendMessage: (data: { session_id: string; content: string; reasoning_mode?: "thinking" | "fast" }) =>
      apiRequest<{
        session_id: string;
        reasoning_mode: string;
        quota_status: QuotaStatus;
        user_message: ChatMessageItem;
        assistant_message: ChatMessageItem;
      }>("/chat/messages", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    getQuota: () => apiRequest<QuotaStatus>("/chat/quota"),
    resetQuota: () => apiRequest<{ message: string; quota: QuotaStatus }>("/chat/quota/reset", { method: "POST" }),
    submitFeedback: (data: {
      session_id: string;
      message_id: string;
      feedback_type: "LIKE" | "DISLIKE";
      improvement_category?: string;
      notes?: string;
    }) =>
      apiRequest<{ status: string; reward_rate: number; adjusted_score: number; meta: Record<string, unknown> }>(
        "/chat/feedback",
        {
          method: "POST",
          body: JSON.stringify(data),
        }
      ),
  },
};
