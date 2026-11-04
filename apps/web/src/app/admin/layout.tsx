"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { ThemeToggle } from "@/components/ThemeToggle";
import { isAdminRole, isSuperadmin, canAccess, roleLabel } from "@/lib/roles";
import { 
  LayoutDashboard, Database, FileText, CheckSquare, 
  Cpu, Activity, BarChart3, BookOpen, GitFork, 
  ThumbsUp, ShieldAlert, Settings, LogOut,
  ShieldCheck, AlertTriangle, Users, Lock,
  Sparkles,
} from "lucide-react";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, role, isAuthenticated, isLoading, logout } = useAuth();
  const pathname = usePathname();

  const superadmin = isSuperadmin(role);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-700">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-xs text-slate-500">Memeriksa hak akses...</span>
        </div>
      </div>
    );
  }

  // Server-side / Client-side RBAC Guard
  if (!isAuthenticated || !isAdminRole(role)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-6">
        <div className="max-w-md w-full bg-white p-8 rounded-2xl text-center space-y-5 border border-red-200 shadow-sm">
          <div className="w-14 h-14 rounded-2xl bg-red-50 border border-red-200 flex items-center justify-center text-red-600 mx-auto shadow-sm">
            <AlertTriangle className="w-7 h-7" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Halaman ini hanya untuk admin</h2>
            <p className="text-xs text-slate-600 mt-2 leading-relaxed">
              Akun Anda (<strong>{user?.username || "Tamu"}</strong>) tidak punya izin untuk membuka area admin. Silakan masuk dengan akun admin.
            </p>
          </div>
          <div className="flex flex-col gap-2 pt-2">
            <Link
              href="/chat"
              className="py-2.5 px-4 rounded-xl btn-primary font-semibold text-xs transition shadow-sm"
            >
              Kembali ke Asisten
            </Link>
            <Link
              href="/login"
              className="py-2.5 px-4 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-700 font-semibold text-xs transition"
            >
              Masuk dengan akun lain
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const operationalNavItems = [
    { href: "/admin/dashboard", label: "Ringkasan", icon: LayoutDashboard },
    { href: "/admin/feedback", label: "Masukan Pengguna", icon: ThumbsUp },
    { href: "/admin/audit-logs", label: "Catatan Aktivitas", icon: ShieldAlert },
    { href: "/admin/settings", label: superadmin ? "Pengaturan" : "Pengaturan (hanya lihat)", icon: Settings },
  ];

  const researchNavItems = [
    { href: "/admin/training", label: "Latih Model AI", icon: Activity },
    { href: "/admin/models", label: "Daftar Model AI", icon: Cpu },
    { href: "/admin/evaluation", label: "Uji Kualitas Model", icon: BarChart3 },
    { href: "/admin/datasets", label: "Kelola Data Latih", icon: Database },
    { href: "/admin/datasets/imports", label: "Riwayat Impor Data", icon: FileText },
    { href: "/admin/annotations", label: "Pemberian Label Data", icon: CheckSquare },
    { href: "/admin/knowledge-base", label: "Basis Pengetahuan", icon: BookOpen },
    { href: "/admin/graph", label: "Peta Hubungan Penyakit", icon: GitFork },
    { href: "/admin/insights", label: "Insight Pasien & RLHF", icon: Sparkles },
    { href: "/admin/users", label: "Kelola Pengguna", icon: Users },
  ];

  const allowed = canAccess(role, pathname);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-100">
      {/* Admin Sidebar */}
      <aside className="w-64 border-r border-slate-200 bg-white flex flex-col justify-between shrink-0 shadow-sm">
        <div className="overflow-y-auto">
          {/* Header */}
          <div className="p-4 border-b border-slate-200 flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-600 flex items-center justify-center text-white shadow-sm">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-bold text-sm tracking-tight text-slate-900">RSUKT Admin AI</h2>
              <span className="text-[10px] text-emerald-700 font-semibold tracking-wide uppercase">Ruang Kerja Admin</span>
            </div>
          </div>

          {/* Nav Items Grouped by Role Category */}
          <nav className="p-3 space-y-4">
            {/* Kategori 1: Menu Admin */}
            <div>
              <div className="px-3 pb-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                <span>Menu Admin</span>
                
              </div>
              <div className="space-y-0.5">
                {operationalNavItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.href;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium transition ${
                        isActive
                          ? "bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-xs font-semibold"
                          : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                      }`}
                    >
                      <Icon className={`w-4 h-4 ${isActive ? "text-emerald-700" : "text-slate-400"}`} />
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            </div>

            {/* Kategori 2: khusus Admin Riset */}
            {superadmin && (
            <div>
              <div className="px-3 pb-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                <span>Khusus Admin Riset</span>
              </div>
              <div className="space-y-0.5">
                {researchNavItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.href;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium transition ${
                        isActive
                          ? "bg-sky-50 text-sky-800 border border-sky-200 shadow-xs font-semibold"
                          : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                      }`}
                    >
                      <Icon className={`w-4 h-4 ${isActive ? "text-sky-700" : "text-slate-400"}`} />
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            </div>
            )}
          </nav>
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-slate-200 space-y-2 bg-slate-50/50">
          <div className="p-2.5 rounded-xl bg-emerald-50/80 border border-emerald-200 text-[10px] text-emerald-800 flex items-center gap-2 shadow-2xs">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="leading-tight font-medium">Separasi Akses: Data privat pasien terenkripsi & terisolasi (UU PDP No. 27/2022).</span>
          </div>

          <div className="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-200 shadow-sm">
            <div className="truncate">
              <p className={`text-xs font-semibold truncate ${superadmin ? "text-sky-700" : "text-emerald-700"}`}>
                {user?.username}
              </p>
              <span className={`inline-block px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider border ${
                superadmin
                  ? "bg-sky-50 text-sky-700 border-sky-200"
                  : "bg-emerald-50 text-emerald-700 border-emerald-200"
              }`}>
                {roleLabel(role)}
              </span>
            </div>
            <button
              onClick={logout}
              title="Keluar (Logout)"
              className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition shrink-0"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Admin Viewport */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto bg-slate-100">
        {/* Top Navbar */}
        <header className="h-14 border-b border-slate-200 bg-white px-6 flex items-center justify-between shrink-0 shadow-sm">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span>Admin</span>
            <span>/</span>
            <span className="text-slate-900 font-semibold capitalize">
              {pathname.replace("/admin/", "").replace("/", " / ") || "Dashboard"}
            </span>
          </div>

          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-[11px] font-semibold">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Server terhubung
            </span>
            <ThemeToggle small />
          </div>
        </header>

        <div className="p-6 flex-1">
          {allowed ? (
            children
          ) : (
            <div className="max-w-md mx-auto mt-16 bg-white p-8 rounded-2xl text-center space-y-4 border border-amber-200 shadow-sm">
              <div className="w-14 h-14 rounded-2xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 mx-auto">
                <Lock className="w-7 h-7" />
              </div>
              <h2 className="text-lg font-bold text-slate-900">Halaman ini hanya untuk Admin Riset</h2>
              <p className="text-xs text-slate-600 leading-relaxed">
                Akun Anda adalah Admin Operasional, jadi belum bisa membuka halaman ini. Hubungi Admin Riset kalau Anda butuh aksesnya.
              </p>
              <Link
                href="/admin/dashboard"
                className="inline-block py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs transition shadow-sm"
              >
                Kembali ke Ringkasan
              </Link>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
