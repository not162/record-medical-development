"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Stethoscope, Lock, User as UserIcon, Mail, ArrowRight, AlertCircle, CheckCircle2, Shield } from "lucide-react";

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanUser = username.trim().toLowerCase();
    if (["admin", "administrator", "root", "superuser", "admin_rsukt", "system"].includes(cleanUser)) {
      setError("Nama pengguna ini dicadangkan khusus untuk administrator sistem dan tidak dapat didaftarkan.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Konfirmasi kata sandi tidak cocok.");
      return;
    }
    if (password.length < 8) {
      setError("Kata sandi harus memiliki panjang minimal 8 karakter.");
      return;
    }

    setLoading(true);
    try {
      await register({
        username,
        email,
        password,
        full_name: fullName || undefined,
      });

      setSuccess(true);
      setTimeout(() => {
        router.push("/login");
      }, 1500);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Gagal melakukan pendaftaran. Silakan coba kembali.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 bg-slate-50">
      <div className="w-full max-w-md space-y-8 bg-white border border-slate-200 p-8 rounded-2xl shadow-xl shadow-slate-200/50 relative overflow-hidden">
        {/* Subtle accent glow */}
        <div className="absolute -top-24 -left-24 w-48 h-48 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="text-center space-y-2">
          <div className="inline-flex w-12 h-12 rounded-xl bg-gradient-to-tr from-cyan-600 to-emerald-600 items-center justify-center shadow-md shadow-cyan-600/20 mb-2">
            <Stethoscope className="w-6 h-6 text-white" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">
            Pendaftaran Pengguna Baru
          </h2>
          <p className="text-xs text-slate-500">
            Daftar untuk berkonsultasi dengan Asisten AI Klinis RSUKT
          </p>
        </div>

        {error && (
          <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3 text-xs text-red-700">
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 flex items-start gap-3 text-xs text-emerald-700">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            <span>Pendaftaran berhasil! Mengalihkan ke halaman login...</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Username <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <UserIcon className="w-4 h-4" />
              </div>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="misal: pasien_andi"
                className="w-full pl-10 pr-4 py-2.5 bg-slate-50/80 border border-slate-300 rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-cyan-600 focus:bg-white focus:ring-2 focus:ring-cyan-500/20 transition"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Email Valid <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Mail className="w-4 h-4" />
              </div>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="andi@gmail.com"
                className="w-full pl-10 pr-4 py-2.5 bg-slate-50/80 border border-slate-300 rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-cyan-600 focus:bg-white focus:ring-2 focus:ring-cyan-500/20 transition"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Nama Lengkap (Opsional)
            </label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Andi Pratama"
              className="w-full px-4 py-2.5 bg-slate-50/80 border border-slate-300 rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-cyan-600 focus:bg-white focus:ring-2 focus:ring-cyan-500/20 transition"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Kata Sandi (Minimal 8 karakter) <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Lock className="w-4 h-4" />
              </div>
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-10 pr-4 py-2.5 bg-slate-50/80 border border-slate-300 rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-cyan-600 focus:bg-white focus:ring-2 focus:ring-cyan-500/20 transition"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Konfirmasi Kata Sandi <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Lock className="w-4 h-4" />
              </div>
              <input
                type="password"
                required
                minLength={8}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-10 pr-4 py-2.5 bg-slate-50/80 border border-slate-300 rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-cyan-600 focus:bg-white focus:ring-2 focus:ring-cyan-500/20 transition"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || success}
            className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-cyan-600 to-cyan-700 hover:from-cyan-700 hover:to-cyan-800 text-white font-semibold text-sm shadow-md shadow-cyan-600/20 transition flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? (
              <span>Mendaftarkan Akun...</span>
            ) : (
              <>
                <span>Daftar Sekarang (Role: USER)</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="pt-2 border-t border-slate-200 text-center text-xs text-slate-600 space-y-2">
          <div>
            Sudah memiliki akun?{" "}
            <Link href="/login" className="text-cyan-700 hover:text-cyan-800 font-semibold underline underline-offset-2">
              Masuk di sini
            </Link>
          </div>
          <div className="text-[11px] text-slate-500 flex items-center justify-center gap-1">
            <Shield className="w-3.5 h-3.5 text-cyan-600" />
            <span>Pendaftaran publik hanya menetapkan peran Pengguna Standar (USER)</span>
          </div>
          <div className="text-[10px] text-emerald-700 font-medium flex items-center justify-center gap-1">
            <Shield className="w-3 h-3 text-emerald-600" />
            <span>Keamanan data terjamin sesuai UU PDP No. 27/2022 & ISO 27001 ISMS</span>
          </div>
        </div>
      </div>
    </div>
  );
}
