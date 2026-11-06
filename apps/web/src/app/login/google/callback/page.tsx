"use client";

import React, { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { homePathForRole } from "@/lib/roles";
import { consumeGooglePending, googleRedirectUri } from "@/lib/auth/google-oauth";
import { AuthShell, FormAlert } from "@/components/auth/AuthShell";

function GoogleCallback() {
  const params = useSearchParams();
  const router = useRouter();
  const { loginWithGoogle } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return; // code Google hanya bisa dipakai sekali (StrictMode memanggil efek dua kali)
    ran.current = true;
    const run = async () => {
      if (params.get("error")) {
        setError("Login Google dibatalkan.");
        return;
      }
      const code = params.get("code");
      const pending = consumeGooglePending(params.get("state"));
      if (!code || !pending) {
        setError("Sesi login Google tidak valid atau sudah kedaluwarsa. Silakan coba lagi.");
        return;
      }
      try {
        const u = await loginWithGoogle({ code, code_verifier: pending.verifier, redirect_uri: googleRedirectUri() }, pending.remember);
        router.replace(homePathForRole(u.role));
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Login Google gagal.");
      }
    };
    run();
  }, [params, loginWithGoogle, router]);

  return (
    <AuthShell>
      <h1 className="text-[22px] font-extrabold tracking-tight text-slate-900">Masuk dengan Google</h1>
      {error ? (
        <div className="mt-6 space-y-4">
          <FormAlert tone="error">{error}</FormAlert>
          <Link href="/login" className="inline-block text-sm font-semibold text-cyan-700 hover:underline">Kembali ke halaman masuk</Link>
        </div>
      ) : (
        <p className="mt-6 flex items-center gap-2 text-sm text-slate-600">
          <Loader2 className="w-4 h-4 animate-spin" /> Memverifikasi akun Google Anda...
        </p>
      )}
    </AuthShell>
  );
}

export default function GoogleCallbackPage() {
  return (
    <Suspense fallback={null}>
      <GoogleCallback />
    </Suspense>
  );
}
