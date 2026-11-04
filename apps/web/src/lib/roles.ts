/**
 * Pusat aturan peran (role) di frontend.
 *
 * USER        = pasien
 * ADMIN       = "Admin Operasional" (urus pengguna & operasional)
 * RESEARCHER  = "Admin Riset (Superadmin)" (semua yang bisa ADMIN + riset AI)
 *
 * Backend kadang masih mengirim 'ADMIN_PERISET' (nama lama) -> dianggap RESEARCHER.
 * Aturan di sini hanya untuk tampilan; keamanan sebenarnya tetap di backend.
 */

export type UserRole = "USER" | "ADMIN" | "RESEARCHER";

/** Ubah nilai peran apa pun dari server menjadi salah satu peran yang dikenal. */
export function normalizeRole(role: string | null | undefined): UserRole | null {
  if (!role) return null;
  const r = role.trim().toUpperCase();
  if (r === "RESEARCHER" || r === "ADMIN_PERISET" || r === "SUPERADMIN") return "RESEARCHER";
  if (r === "ADMIN") return "ADMIN";
  if (r === "USER") return "USER";
  return null;
}

/** Admin Operasional atau Admin Riset (boleh masuk /admin). */
export function isAdminRole(role: string | null | undefined): boolean {
  const r = normalizeRole(role);
  return r === "ADMIN" || r === "RESEARCHER";
}

/** Admin Riset (Superadmin). */
export function isSuperadmin(role: string | null | undefined): boolean {
  return normalizeRole(role) === "RESEARCHER";
}

export function roleLabel(role: string | null | undefined): string {
  switch (normalizeRole(role)) {
    case "RESEARCHER":
      return "Admin Riset (Superadmin)";
    case "ADMIN":
      return "Admin Operasional";
    case "USER":
      return "Pasien";
    default:
      return "Tidak dikenal";
  }
}

/** Halaman yang boleh dibuka Admin Operasional. */
export const OPERATIONAL_PATHS = [
  "/admin/dashboard",
  "/admin/feedback",
  "/admin/audit-logs",
  "/admin/settings",
] as const;

/** Halaman khusus Admin Riset. */
export const RESEARCH_PATHS = [
  "/admin/training",
  "/admin/models",
  "/admin/evaluation",
  "/admin/datasets",
  "/admin/datasets/imports",
  "/admin/annotations",
  "/admin/knowledge-base",
  "/admin/graph",
  "/admin/users",
  "/admin/insights",
] as const;

function matches(path: string, base: string): boolean {
  return path === base || path.startsWith(base + "/");
}

/** Apakah peran ini boleh membuka alamat (path) tertentu di /admin. */
export function canAccess(role: string | null | undefined, path: string): boolean {
  const r = normalizeRole(role);
  if (!r || r === "USER") return false;
  if (!path.startsWith("/admin")) return true;
  if (r === "RESEARCHER") return true;
  // ADMIN: hanya halaman operasional (selain itu ditolak, termasuk alamat tak dikenal)
  return OPERATIONAL_PATHS.some((p) => matches(path, p));
}

/** Tujuan setelah masuk (login) menurut peran. */
export function homePathForRole(role: string | null | undefined): string {
  return isAdminRole(role) ? "/admin/dashboard" : "/chat";
}
