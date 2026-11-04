"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2, ShieldCheck } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { AuthShell, FieldHint, FieldLabel, FormAlert } from "@/components/auth/AuthShell";
import { PasswordInput, StrengthMeter } from "@/components/auth/PasswordInput";

const RESERVED = ["admin", "administrator", "root", "superuser", "admin_rsukt", "system"];
const USERNAME_RE = /^[a-z0-9._]{3,30}$/;
const EMAIL_RE = /^[\w.-]+@[\w.-]+\.\w+$/;

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();

  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [agree, setAgree] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const cleanUser = username.trim().toLowerCase();
  const mismatch = confirmPassword.length > 0 && confirmPassword !== password;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!USERNAME_RE.test(cleanUser)) {
      setError("Username 3–30 karakter: huruf kecil, angka, titik, atau garis bawah.");
      return;
    }
    if (RESERVED.includes(cleanUser)) {
      setError("Username ini tidak bisa dipakai. Silakan pilih username lain.");
      return;
    }
    if (!EMAIL_RE.test(email.trim())) {
      setError("Format email belum valid.");
      return;
    }
    if (password.length < 8) {
      setError("Kata sandi minimal 8 karakter.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Konfirmasi kata sandi tidak cocok.");
      return;
    }
    if (!agree) {
      setError("Centang persetujuan Ketentuan & Kebijakan Privasi untuk melanjutkan.");
      return;
    }

    setLoading(true);
    try {
      await register({
        username: cleanUser,
        email: email.trim().toLowerCase(),
        password,
        full_name: fullName.trim() || undefined,
      });
      setSuccess(true);
      setTimeout(() => router.push("/login"), 1500);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Pendaftaran gagal. Silakan coba lagi.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell wide>
      <h1 className="text-[22px] font-extrabold tracking-tight text-slate-900">Daftar Akun Pasien</h1>
      <p className="mt-1 text-sm text-slate-500">
        Gratis. Akun baru otomatis terdaftar sebagai pengguna biasa untuk bertanya seputar kesehatan.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        {error && <FormAlert tone="error">{error}</FormAlert>}
        {success && <FormAlert tone="success">Pendaftaran berhasil! Mengarahkan ke halaman masuk...</FormAlert>}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <FieldLabel htmlFor="reg-username">Username</FieldLabel>
            <input
              id="reg-username"
              name="username"
              required
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              aria-invalid={username.length > 0 && !USERNAME_RE.test(cleanUser)}
              className="field"
            />
            <FieldHint>3–30 karakter: huruf kecil, angka, titik, garis bawah.</FieldHint>
          </div>
          <div>
            <FieldLabel htmlFor="reg-fullname">Nama lengkap (opsional)</FieldLabel>
            <input
              id="reg-fullname"
              name="name"
              autoComplete="name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="field"
            />
          </div>
        </div>

        <div>
          <FieldLabel htmlFor="reg-email">Email</FieldLabel>
          <input
            id="reg-email"
            name="email"
            type="email"
            required
            autoComplete="email"
            autoCapitalize="none"
            spellCheck={false}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="field"
          />
          <FieldHint>Dipakai untuk masuk dan memulihkan kata sandi.</FieldHint>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <FieldLabel htmlFor="reg-password">Kata sandi</FieldLabel>
            <PasswordInput
              id="reg-password"
              name="new-password"
              required
              minLength={8}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {password ? <StrengthMeter password={password} /> : <FieldHint>Minimal 8 karakter.</FieldHint>}
          </div>
          <div>
            <FieldLabel htmlFor="reg-confirm">Ulangi kata sandi</FieldLabel>
            <PasswordInput
              id="reg-confirm"
              name="confirm-password"
              required
              minLength={8}
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              aria-invalid={mismatch}
            />
            {mismatch && <p className="mt-1.5 text-[11.5px] text-red-600">Kata sandi belum sama.</p>}
          </div>
        </div>

        <label className="flex cursor-pointer items-start gap-2.5 text-[13px] text-slate-600">
          <input
            type="checkbox"
            checked={agree}
            onChange={(e) => setAgree(e.target.checked)}
            className="mt-0.5 h-4 w-4 shrink-0 rounded border-slate-300 accent-blue-600"
          />
          <span>
            Saya menyetujui{" "}
            <Link href="/terms" className="font-semibold text-blue-600 hover:underline">
              Ketentuan Layanan
            </Link>{" "}
            dan{" "}
            <Link href="/privacy" className="font-semibold text-blue-600 hover:underline">
              Kebijakan Privasi
            </Link>
            .
          </span>
        </label>

        <button
          type="submit"
          disabled={loading || success}
          className="btn-primary flex h-11 w-full items-center justify-center gap-2 text-sm font-bold"
        >
          {loading && <Loader2 className="h-4 w-4 animate-spin" />}
          {loading ? "Membuat akun..." : "Daftar sekarang"}
        </button>
      </form>

      <p className="mt-5 text-center text-sm text-slate-500">
        Sudah punya akun?{" "}
        <Link href="/login" className="font-semibold text-blue-600 hover:underline">
          Masuk
        </Link>
        <span className="mx-1.5">·</span>
        <Link href="/forgot-password" className="font-semibold text-blue-600 hover:underline">
          Lupa kata sandi?
        </Link>
      </p>
      <p className="mt-4 flex items-center justify-center gap-1.5 text-[11px] text-slate-500">
        <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
        Data kesehatan Anda dijaga kerahasiaannya.
      </p>
    </AuthShell>
  );
}
