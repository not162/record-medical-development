export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" ? "/api/v1" : "http://127.0.0.1:8000/api/v1");

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
    let errorDetail = "Terjadi kesalahan pada permintaan server.";
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {
      errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorDetail);
  }

  return response.json();
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
};
