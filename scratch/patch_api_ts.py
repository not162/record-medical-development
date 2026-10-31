with open("apps/web/src/lib/api.ts", "r", encoding="utf-8") as f:
    code = f.read().replace("\r\n", "\n")

chat_types = """
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
"""

chat_api_block = """  chat: {
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
"""

# Insert chat types before `export const api = {`
target_api = "export const api = {"
assert target_api in code, "target_api not found"
code = code.replace(target_api, chat_types + "\n" + target_api)

# Insert chat api block before closing `};`
last_brace = "\n  },\n};"
replacement_brace = "\n  },\n" + chat_api_block + "};"
assert last_brace in code, "last_brace not found"
code = code.replace(last_brace, replacement_brace)

with open("apps/web/src/lib/api.ts", "w", encoding="utf-8", newline="\n") as f:
    f.write(code)

print("api.ts successfully patched!")

