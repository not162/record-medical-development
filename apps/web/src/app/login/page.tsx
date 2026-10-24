"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Stethoscope, Lock, User as UserIcon, ArrowRight, AlertCircle, Shield } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [usernameOrEmail, setUsernameOrEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const loggedUser = await login({
        username_or_email: usernameOrEmail,
        password,
      });

      if (loggedUser.role === "ADMIN") {
        router.push("/admin/dashboard");
      } else {
        router.push("/chat");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Gagal masuk. Periksa kembali username/email dan kata sandi.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 bg-slate-50">
      <div className="w-full max-w-md space-y-8 bg-white border border-slate-200 p-8 rounded-2xl shadow-xl shadow-slate-200/50 relative overflow-hidden">
        {/* Subtle accent glow */}
        <div className="absolute -top-24 -left-24 w-48 h-48 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-24 -right-24 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="text-center space-y-2">
          <div className="inline-flex w-12 h-12 rounded-xl bg-gradient-to-tr from-cyan-600 to-emerald-600 items-center justify-center shadow-md shadow-cyan-600/20 mb-2">
            <Stethoscope className="w-6 h-6 text-white" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">
            Masuk ke Sistem Klinis
          </h2>
          <p className="text-xs text-slate-500">
            Akses Chatbot Edukasi Pasien atau Workspace Riset Administrator
          </p>
        </div>

        {error && (
          <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3 text-xs text-red-700">
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Username atau Email
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <UserIcon className="w-4 h-4" />
              </div>
              <input
                type="text"
                required
                value={usernameOrEmail}
                onChange={(e) => setUsernameOrEmail(e.target.value)}
                placeholder="nama_pengguna atau email@rsukt.go.id"
                className="w-full pl-10 pr-4 py-2.5 bg-slate-50/80 border border-slate-300 rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-cyan-600 focus:bg-white focus:ring-2 focus:ring-cyan-500/20 transition"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-xs font-semibold text-slate-700">
                Kata Sandi
              </label>
              <Link
                href="/forgot-password"
                className="text-xs text-cyan-700 hover:text-cyan-800 font-medium hover:underline"
              >
                Lupa Kata Sandi?
              </Link>
            </div>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Lock className="w-4 h-4" />
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-10 pr-4 py-2.5 bg-slate-50/80 border border-slate-300 rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-cyan-600 focus:bg-white focus:ring-2 focus:ring-cyan-500/20 transition"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-cyan-600 to-cyan-700 hover:from-cyan-700 hover:to-cyan-800 text-white font-semibold text-sm shadow-md shadow-cyan-600/20 transition flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? (
              <span>Memproses Verifikasi...</span>
            ) : (
              <>
                <span>Masuk Sekarang</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="pt-2 border-t border-slate-200 text-center text-xs text-slate-600 space-y-2">
          <div>
            Belum memiliki akun?{" "}
            <Link href="/register" className="text-cyan-700 hover:text-cyan-800 font-semibold underline underline-offset-2">
              Daftar Akun Baru (User)
            </Link>
          </div>
          <div className="text-[10px] text-slate-500 flex items-center justify-center gap-1">
            <Shield className="w-3 h-3 text-emerald-600" />
            <span>Keamanan data terlindungi sesuai UU PDP No. 27/2022 & ISO 27001 ISMS</span>
          </div>
        </div>
      </div>
    </div>
  );
}
