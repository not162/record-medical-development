"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { 
  LayoutDashboard, Database, FileText, CheckSquare, 
  Cpu, Activity, BarChart3, BookOpen, GitFork, 
  ThumbsUp, ShieldAlert, Settings, LogOut,
  ShieldCheck, AlertTriangle
} from "lucide-react";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, role, isAuthenticated, isLoading, logout } = useAuth();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && (!isAuthenticated || (role !== "ADMIN" && role !== "RESEARCHER"))) {
      // Don't auto redirect immediately if showing error banner
    }
  }, [isLoading, isAuthenticated, role]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-700">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-xs text-slate-500">Memverifikasi Otorisasi Hak Akses Administrator...</span>
        </div>
      </div>
    );
  }

  // Server-side / Client-side RBAC Guard
  if (!isAuthenticated || (role !== "ADMIN" && role !== "RESEARCHER")) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-6">
        <div className="max-w-md w-full bg-white p-8 rounded-2xl text-center space-y-5 border border-red-200 shadow-xl">
          <div className="w-14 h-14 rounded-2xl bg-red-50 border border-red-200 flex items-center justify-center text-red-600 mx-auto shadow-md shadow-red-500/10">
            <AlertTriangle className="w-7 h-7" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900">Akses Ditolak (403 Forbidden)</h2>
            <p className="text-xs text-slate-600 mt-2 leading-relaxed">
              Area ini adalah Workspace Riset dan Manajemen Data khusus Administrator. Akun Anda (<strong>{user?.username || "Tamu"}</strong>) dengan peran <strong>{role || "UNAUTHORIZED"}</strong> tidak memiliki izin mengakses rute administratif.
            </p>
          </div>
          <div className="flex flex-col gap-2 pt-2">
            <Link
              href="/chat"
              className="py-2.5 px-4 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white font-semibold text-xs transition shadow-sm"
            >
              Kembali ke Chatbot Klinis
            </Link>
            <Link
              href="/login"
              className="py-2.5 px-4 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-700 font-semibold text-xs transition"
            >
              Ganti Akun (Login Administrator)
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const operationalNavItems = [
    { href: "/admin/dashboard", label: "Dashboard Operasional", icon: LayoutDashboard },
    { href: "/admin/feedback", label: "Feedback Pasien", icon: ThumbsUp },
    { href: "/admin/audit-logs", label: "Log Audit Sistem", icon: ShieldAlert },
    { href: "/admin/settings", label: "Pengaturan Sistem", icon: Settings },
  ];

  const researchNavItems = [
    { href: "/admin/training", label: "Model Training & Simulasi", icon: Activity },
    { href: "/admin/models", label: "Model Registry", icon: Cpu },
    { href: "/admin/evaluation", label: "Evaluasi & Benchmark", icon: BarChart3 },
    { href: "/admin/datasets", label: "Manajemen Dataset", icon: Database },
    { href: "/admin/datasets/imports", label: "Import Manifests", icon: FileText },
    { href: "/admin/annotations", label: "Annotation Studio", icon: CheckSquare },
    { href: "/admin/knowledge-base", label: "Knowledge Index (RAG)", icon: BookOpen },
    { href: "/admin/graph", label: "GraphRAG Visualizer", icon: GitFork },
  ];

  return (
    <div className="flex h-screen overflow-hidden bg-slate-100">
      {/* Admin Sidebar */}
      <aside className="w-64 border-r border-slate-200 bg-white flex flex-col justify-between shrink-0 shadow-sm">
        <div className="overflow-y-auto">
          {/* Header */}
          <div className="p-4 border-b border-slate-200 flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-600 flex items-center justify-center text-white shadow-md shadow-emerald-600/20">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-bold text-sm tracking-tight text-slate-900">RSUKT Admin AI</h2>
              <span className="text-[10px] text-emerald-700 font-semibold tracking-wide uppercase">Research Workspace</span>
            </div>
          </div>

          {/* Nav Items Grouped by Role Category */}
          <nav className="p-3 space-y-4">
            {/* Kategori 1: Operasional Klinik */}
            <div>
              <div className="px-3 pb-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                <span>Operasional Klinik</span>
                {role === "ADMIN" && (
                  <span className="text-[9px] px-1.5 py-0.2 bg-emerald-50 text-emerald-700 rounded border border-emerald-200">Aktif</span>
                )}
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

            {/* Kategori 2: Workspace Riset & AI Engineering */}
            <div>
              <div className="px-3 pb-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                <span>Workspace Riset AI</span>
                {role === "RESEARCHER" && (
                  <span className="text-[9px] px-1.5 py-0.2 bg-sky-50 text-sky-700 rounded border border-sky-200">Periset Aktif</span>
                )}
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
              <p className={`text-xs font-semibold truncate ${role === "RESEARCHER" ? "text-sky-700" : "text-emerald-700"}`}>
                {user?.username}
              </p>
              <span className={`inline-block px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider border ${
                role === "RESEARCHER"
                  ? "bg-sky-50 text-sky-700 border-sky-200"
                  : "bg-emerald-50 text-emerald-700 border-emerald-200"
              }`}>
                {role === "RESEARCHER" ? "ADMIN PERISET" : "ADMIN OPERASIONAL"}
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
        <header className="h-14 border-b border-slate-200 bg-white/90 backdrop-blur-md px-6 flex items-center justify-between shrink-0 shadow-sm">
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
              FastAPI Engine Connected
            </span>
          </div>
        </header>

        <div className="p-6 flex-1">{children}</div>
      </main>
    </div>
  );
}
