"use client";

import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";

type Props = Omit<React.InputHTMLAttributes<HTMLInputElement>, "type">;

/** Input password dengan tombol tampilkan/sembunyikan. */
export function PasswordInput({ className = "", ...props }: Props) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <input {...props} type={show ? "text" : "password"} className={`field pr-11 ${className}`} />
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        aria-label={show ? "Sembunyikan kata sandi" : "Tampilkan kata sandi"}
        className="absolute inset-y-0 right-0 flex w-11 items-center justify-center text-slate-400 hover:text-slate-700"
      >
        {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </button>
    </div>
  );
}

/** Skor kekuatan sederhana 0-4 untuk meter visual (bukan validasi keamanan). */
export function passwordStrength(pw: string): number {
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++;
  if (/\d/.test(pw) && /[^A-Za-z0-9]/.test(pw)) score++;
  return Math.min(score, 4);
}

const LABELS = ["Terlalu lemah", "Lemah", "Cukup", "Kuat", "Sangat kuat"];
const COLORS = ["bg-red-500", "bg-red-500", "bg-amber-500", "bg-emerald-500", "bg-emerald-500"];

export function StrengthMeter({ password }: { password: string }) {
  if (!password) return null;
  const s = passwordStrength(password);
  return (
    <div className="mt-2" aria-live="polite">
      <div className="flex gap-1">
        {[0, 1, 2, 3].map((i) => (
          <span key={i} className={`h-1 flex-1 rounded-full ${i < s ? COLORS[s] : "bg-slate-200"}`} />
        ))}
      </div>
      <p className="mt-1 text-[11px] text-slate-500">Kekuatan: {LABELS[s]}</p>
    </div>
  );
}
