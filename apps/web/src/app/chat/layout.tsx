"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { 
  Bot, MessageSquarePlus, History, User, Settings, 
  LogOut, ShieldAlert, Stethoscope, ChevronRight,
  Menu, X, Shield
} from "lucide-react";

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  const navItems = [
    { href: "/chat", label: "Chatbot Klinis", icon: Bot },
    { href: "/chat/history", label: "Riwayat Sesi", icon: History },
    { href: "/profile", label: "Rekam Medis Saya", icon: User },
    { href: "/settings", label: "Pengaturan Akun", icon: Settings },
  ];

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 relative flex-col lg:flex-row">
      {isLoading && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-slate-50 text-slate-700">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-cyan-600 border-t-transparent rounded-full animate-spin"></div>
            <span className="text-xs text-slate-500">Memuat Sesi Klinis...</span>
          </div>
        </div>
      )}

      {!isLoading && !isAuthenticated && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-slate-50 text-slate-700">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-cyan-600 border-t-transparent rounded-full animate-spin"></div>
            <span className="text-xs text-slate-500">Mengarahkan ke halaman login...</span>
          </div>
        </div>
      )}

      {/* Mobile Top App Bar (Only visible on screens < lg) */}
      <header className="lg:hidden flex items-center justify-between px-3.5 py-2.5 bg-white border-b border-slate-200 shrink-0 shadow-xs z-30">
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="p-1.5 rounded-lg text-slate-700 hover:bg-slate-100 transition focus:outline-none"
            aria-label="Buka Menu"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-cyan-600 to-emerald-600 flex items-center justify-center text-white shadow-xs">
              <Stethoscope className="w-4 h-4" />
            </div>
            <div>
              <h1 className="font-bold text-xs tracking-tight text-slate-900 leading-tight">RSUKT Chatbot</h1>
              <span className="text-[9px] text-cyan-700 font-medium block">Asisten Medis Pasien</span>
            </div>
          </div>
        </div>

        <Link
          href="/chat"
          className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-700 text-white text-[11px] font-semibold shadow-xs"
        >
          <MessageSquarePlus className="w-3.5 h-3.5" />
          <span>Sesi Baru</span>
        </Link>
      </header>

      {/* Mobile Slide-over Drawer Backdrop */}
      {mobileMenuOpen && (
        <div 
          className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs lg:hidden transition-opacity"
          onClick={() => setMobileMenuOpen(false)}
        >
          <div 
            className="w-72 max-w-[85%] h-full bg-white shadow-2xl flex flex-col justify-between"
            onClick={(e) => e.stopPropagation()}
          >
            <div>
              {/* Drawer header */}
              <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-600 to-emerald-600 flex items-center justify-center text-white shadow-xs">
                    <Stethoscope className="w-4 h-4" />
                  </div>
                  <div>
                    <h2 className="font-bold text-sm text-slate-900">RSUKT Chatbot</h2>
                    <span className="text-[10px] text-cyan-700 font-semibold">Menu Utama</span>
                  </div>
                </div>
                <button
                  onClick={() => setMobileMenuOpen(false)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Action Button */}
              <div className="p-3">
                <Link
                  href="/chat"
                  onClick={() => setMobileMenuOpen(false)}
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white font-semibold text-xs transition shadow-sm"
                >
                  <MessageSquarePlus className="w-4 h-4" />
                  <span>Percakapan Baru</span>
                </Link>
              </div>

              {/* Navigation Items */}
              <nav className="px-3 space-y-1">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.href;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium transition ${
                        isActive
                          ? "bg-cyan-50 text-cyan-800 border border-cyan-200 font-semibold shadow-xs"
                          : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <Icon className={`w-4 h-4 ${isActive ? "text-cyan-700" : "text-slate-400"}`} />
                        <span>{item.label}</span>
                      </div>
                      {isActive && <ChevronRight className="w-3.5 h-3.5 text-cyan-600" />}
                    </Link>
                  );
                })}
              </nav>
            </div>

            {/* Drawer footer */}
            <div className="p-3 border-t border-slate-200 space-y-2 bg-slate-50/70">
              {/* Compliance Trust Bar */}
              <div className="p-2 rounded-xl bg-white border border-slate-200 text-[9px] text-slate-600 flex items-center justify-between shadow-2xs">
                <span className="font-semibold text-slate-700 flex items-center gap-1">
                  <Shield className="w-3 h-3 text-cyan-600" />
                  UU PDP • ISO 27001 • HIPAA
                </span>
                <span className="text-[8px] bg-cyan-50 px-1.5 py-0.5 rounded border border-cyan-200 text-cyan-800 font-mono font-medium">
                  Permenkes RME
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-200">
                <div className="flex items-center gap-2 overflow-hidden">
                  <div className="w-7 h-7 rounded-lg bg-cyan-100 border border-cyan-200 flex items-center justify-center text-cyan-700 text-xs font-bold shrink-0">
                    {user?.username?.charAt(0).toUpperCase()}
                  </div>
                  <div className="truncate">
                    <p className="text-xs font-semibold text-slate-800 truncate">{user?.username}</p>
                    <p className="text-[10px] text-slate-500 truncate">{user?.email}</p>
                  </div>
                </div>
                <button
                  onClick={logout}
                  title="Keluar"
                  className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Desktop Sidebar (Only visible on screen >= lg) */}
      <aside className="hidden lg:flex w-64 border-r border-slate-200 bg-white flex-col justify-between shrink-0 shadow-xs">
        <div>
          {/* Brand header */}
          <div className="p-4 border-b border-slate-200 flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-600 to-emerald-600 flex items-center justify-center text-white shadow-md shadow-cyan-600/20">
              <Stethoscope className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-bold text-sm tracking-tight text-slate-900">RSUKT Chatbot</h2>
              <span className="text-[10px] text-cyan-700 font-semibold">Asisten Medis Pasien</span>
            </div>
          </div>

          {/* New Chat Button */}
          <div className="p-3">
            <Link
              href="/chat"
              className="w-full flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white font-semibold text-xs transition shadow-md shadow-cyan-600/20"
            >
              <MessageSquarePlus className="w-4 h-4" />
              <span>Percakapan Baru</span>
            </Link>
          </div>

          {/* Navigation Items */}
          <nav className="px-3 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition ${
                    isActive
                      ? "bg-cyan-50 text-cyan-800 border border-cyan-200 shadow-sm font-semibold"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className={`w-4 h-4 ${isActive ? "text-cyan-700" : "text-slate-400"}`} />
                    <span>{item.label}</span>
                  </div>
                  {isActive && <ChevronRight className="w-3.5 h-3.5 text-cyan-600" />}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Footer Sidebar: User info & Safety alert */}
        <div className="p-3 border-t border-slate-200 space-y-3 bg-slate-50/50">
          {/* Compliance Trust Bar */}
          <div className="p-2 rounded-xl bg-slate-100 border border-slate-200/80 text-[9px] text-slate-600 flex items-center justify-between shadow-2xs">
            <span className="font-semibold text-slate-700 flex items-center gap-1">
              <Shield className="w-3 h-3 text-cyan-600" />
              UU PDP • ISO 27001 • HIPAA
            </span>
            <span className="text-[8px] bg-white px-1.5 py-0.5 rounded border border-slate-200 text-slate-500 font-mono font-medium">
              Permenkes RME
            </span>
          </div>

          <div className="p-2.5 rounded-xl bg-amber-50 border border-amber-200 text-[10px] text-amber-800 leading-relaxed flex items-start gap-2 shadow-xs">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
            <span>Chatbot bersifat edukatif & tidak meresepkan obat. Gawat darurat? Segera hubungi IGD 119.</span>
          </div>

          <div className="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-200 shadow-xs">
            <div className="flex items-center gap-2 overflow-hidden">
              <div className="w-7 h-7 rounded-lg bg-cyan-100 border border-cyan-200 flex items-center justify-center text-cyan-700 text-xs font-bold shrink-0">
                {user?.username?.charAt(0).toUpperCase()}
              </div>
              <div className="truncate">
                <p className="text-xs font-semibold text-slate-800 truncate">{user?.username}</p>
                <p className="text-[10px] text-slate-500 truncate">{user?.email}</p>
              </div>
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

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 w-full overflow-hidden bg-slate-50 pb-16 lg:pb-0">
        {children}
      </main>

      {/* Mobile Bottom Navigation Bar (PWA / MWA standard) */}
      <nav className="lg:hidden fixed bottom-0 inset-x-0 bg-white/95 backdrop-blur-md border-t border-slate-200 flex items-center justify-around py-2 px-1 z-40 shadow-lg">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex flex-col items-center gap-1 px-3 py-1 rounded-xl text-[10px] font-medium transition ${
                isActive ? "text-cyan-700 font-bold" : "text-slate-500 hover:text-slate-800"
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? "text-cyan-600" : "text-slate-400"}`} />
              <span className="truncate max-w-[65px]">{item.label.split(" ")[0]}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
