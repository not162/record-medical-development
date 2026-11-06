"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogIn, UserPlus } from "lucide-react";
import { BrandMark } from "@/components/BrandMark";
import { ThemeToggle } from "@/components/ThemeToggle";
import { InstallAppButton } from "@/components/InstallAppButton";

const NAV = [
  { href: "/", label: "Beranda" },
  { href: "/privacy", label: "Privasi" },
  { href: "/terms", label: "Ketentuan" },
];

/** Kerangka halaman publik/auth: header ringkas + latar glow + kartu di tengah. */
export function AuthShell({ children, wide = false }: { children: React.ReactNode; wide?: boolean }) {
  const pathname = usePathname();
  const onRegister = pathname?.startsWith("/register");

  return (
    <div className="brand-glow flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/80 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 px-4">
          <BrandMark />
          <nav className="hidden items-center gap-1 md:flex" aria-label="Navigasi utama">
            {NAV.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                className="rounded-lg px-3 py-1.5 text-sm font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-900 transition"
              >
                {n.label}
              </Link>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <InstallAppButton />
            <ThemeToggle />
            {onRegister ? (
              <Link href="/login" className="btn-primary inline-flex h-9 items-center gap-1.5 px-3.5 text-xs font-bold">
                <LogIn className="h-3.5 w-3.5" />
                Masuk
              </Link>
            ) : (
              <Link href="/register" className="btn-primary inline-flex h-9 items-center gap-1.5 px-3.5 text-xs font-bold">
                <UserPlus className="h-3.5 w-3.5" />
                Daftar
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="flex flex-1 items-start justify-center px-4 py-10 sm:items-center sm:py-14">
        <div className={`surface-card w-full p-6 sm:p-8 ${wide ? "max-w-xl" : "max-w-md"}`}>{children}</div>
      </main>

      <footer className="pb-6 text-center text-[11px] text-slate-500">
        © 2026 Clinic with Agent Healthy · Asisten kesehatan AI, bukan pengganti dokter.
      </footer>
    </div>
  );
}

export function FieldLabel({ htmlFor, children }: { htmlFor: string; children: React.ReactNode }) {
  return (
    <label htmlFor={htmlFor} className="mb-1.5 block text-[13px] font-semibold text-slate-700">
      {children}
    </label>
  );
}

export function FieldHint({ children }: { children: React.ReactNode }) {
  return <p className="mt-1.5 text-[11.5px] leading-snug text-slate-500">{children}</p>;
}

export function FormAlert({ tone, children }: { tone: "error" | "success" | "info"; children: React.ReactNode }) {
  const cls =
    tone === "error"
      ? "border-red-200 bg-red-50 text-red-700"
      : tone === "info"
        ? "border-amber-200 bg-amber-50 text-amber-800"
        : "border-emerald-200 bg-emerald-50 text-emerald-700";
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`rounded-xl border px-3.5 py-3 text-[13px] ${cls}`}>
      {children}
    </div>
  );
}
