"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2, ShieldCheck } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { homePathForRole } from "@/lib/roles";
import { AuthShell, FieldLabel, FormAlert } from "@/components/auth/AuthShell";
import { PasswordInput } from "@/components/auth/PasswordInput";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [usernameOrEmail, setUsernameOrEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const loggedUser = await login({ username_or_email: usernameOrEmail.trim(), password }, remember);
      router.push(homePathForRole(loggedUser.role));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Gagal masuk. Cek lagi username/email dan kata sandi Anda.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell>
      <h1 className="text-[22px] font-extrabold tracking-tight text-slate-900">Masuk ke Clinic with Agent Healthy</h1>
      <p className="mt-1 text-sm text-slate-500">Gunakan username atau email dan kata sandi akun Anda.</p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4" noValidate={false}>
        {error && <FormAlert tone="error">{error}</FormAlert>}

        <div>
          <FieldLabel htmlFor="login-id">Username atau email</FieldLabel>
          <input
            id="login-id"
            name="username"
            type="text"
            required
            autoComplete="username"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            value={usernameOrEmail}
            onChange={(e) => setUsernameOrEmail(e.target.value)}
            className="field"
          />
        </div>

        <div>
          <FieldLabel htmlFor="login-password">Kata sandi</FieldLabel>
          <PasswordInput
            id="login-password"
            name="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        <div className="flex items-center justify-between gap-3 text-sm">
          <label className="flex cursor-pointer select-none items-center gap-2 text-slate-700">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 accent-blue-600"
            />
            Ingat saya
          </label>
          <Link href="/forgot-password" className="font-semibold text-blue-600 hover:underline">
            Lupa kata sandi?
          </Link>
        </div>

        <button type="submit" disabled={loading} className="btn-primary flex h-11 w-full items-center justify-center gap-2 text-sm font-bold">
          {loading && <Loader2 className="h-4 w-4 animate-spin" />}
          {loading ? "Sedang masuk..." : "Masuk"}
        </button>
      </form>

      <p className="mt-5 text-center text-sm text-slate-500">
        Belum punya akun?{" "}
        <Link href="/register" className="font-semibold text-blue-600 hover:underline">
          Daftar sebagai pasien
        </Link>
      </p>
      <p className="mt-4 flex items-center justify-center gap-1.5 text-[11px] text-slate-500">
        <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
        Data kesehatan Anda dijaga kerahasiaannya.
      </p>
    </AuthShell>
  );
}
