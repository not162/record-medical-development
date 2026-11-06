"use client";

import React, { useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api, PatientProfile } from "@/lib/api";
import { BLOOD_TYPES, ageFromIso, todayLocalIso } from "@/lib/age";
import {
  User, ShieldCheck, FileText, CheckCircle2, Lock, Save, AlertCircle, Camera, Trash2, Loader2, Mail, CalendarDays, Droplet,
} from "lucide-react";

const PHOTO_SIDE = 256;          // foto diperkecil di perangkat sebelum diunggah
const PHOTO_MAX_BYTES = 300 * 1024;

/** Potong tengah persegi + perkecil ke 256 px, lalu WebP (fallback JPEG). */
async function toProfilePhoto(file: File): Promise<string> {
  if (!/^image\/(jpeg|png|webp)$/.test(file.type)) throw new Error("Pilih foto JPG, PNG, atau WebP.");
  if (file.size > 15 * 1024 * 1024) throw new Error("Ukuran file asli maksimal 15 MB.");
  const bmp = await createImageBitmap(file);
  const side = Math.min(bmp.width, bmp.height);
  const c = document.createElement("canvas");
  c.width = c.height = PHOTO_SIDE;
  c.getContext("2d")!.drawImage(bmp, (bmp.width - side) / 2, (bmp.height - side) / 2, side, side, 0, 0, PHOTO_SIDE, PHOTO_SIDE);
  bmp.close();
  for (const q of [0.85, 0.7, 0.55]) {
    let url = c.toDataURL("image/webp", q);
    if (!url.startsWith("data:image/webp")) url = c.toDataURL("image/jpeg", q);
    if ((url.length * 3) / 4 < PHOTO_MAX_BYTES) return url;
  }
  throw new Error("Foto terlalu besar setelah dikompres. Coba foto lain.");
}

const fmtDate = (iso?: string | null) =>
  iso ? new Date(`${iso}T00:00:00`).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" }) : "-";

function LockedField({ icon: Icon, label, value, note }: { icon: React.ElementType; label: string; value: React.ReactNode; note: string }) {
  return (
    <div>
      <div className="flex items-center gap-1.5 text-slate-700 font-medium mb-1.5">
        <Icon className="w-3.5 h-3.5 text-slate-500" /> {label}
        <Lock className="w-3 h-3 text-slate-400" aria-label="terkunci" />
      </div>
      <div className="w-full px-3 py-2 bg-slate-100 border border-slate-200 rounded-xl text-slate-800">{value}</div>
      <p className="mt-1 text-[10.5px] text-slate-500">{note}</p>
    </div>
  );
}

export default function ProfilePage() {
  const { user } = useAuth();
  const fileRef = useRef<HTMLInputElement>(null);
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [fullName, setFullName] = useState("");
  const [gender, setGender] = useState("");
  const [medicalHistory, setMedicalHistory] = useState("");
  const [legacyBirth, setLegacyBirth] = useState("");
  const [legacyBlood, setLegacyBlood] = useState("");
  const [confirmClinical, setConfirmClinical] = useState(false);
  // dibaca di effect (bukan saat render) agar tidak dibekukan saat prerender
  const [today, setToday] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const apply = (p: PatientProfile) => {
    setProfile(p);
    setFullName(p.full_name ?? user?.full_name ?? "");
    setGender(p.gender ?? "");
    setMedicalHistory(p.medical_history_summary ?? "");
  };

  useEffect(() => {
    api.auth.getProfile().then(apply).catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  // usia mengikuti kalender: cek pergantian hari tiap menit (mis. lewat tengah malam / ulang tahun)
  useEffect(() => {
    const tick = () => setToday(todayLocalIso());
    tick();
    const t = setInterval(tick, 60_000);
    return () => clearInterval(t);
  }, []);

  const run = async (key: string, fn: () => Promise<PatientProfile>, ok: string) => {
    setBusy(key);
    setError(null);
    setNotice(null);
    try {
      apply(await fn());
      setNotice(ok);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Gagal menyimpan.");
    } finally {
      setBusy(null);
    }
  };

  if (loading) {
    return <div className="flex-1 flex items-center justify-center p-6 text-slate-500 text-xs">Memuat profil...</div>;
  }

  const locks = profile?.locks ?? {};
  const age = profile?.birth_date && today ? ageFromIso(profile.birth_date, today) : null;
  const clinicalLocked = Boolean(locks.clinical);
  const initials = (fullName || user?.username || "?").trim().slice(0, 1).toUpperCase();

  return (
    <div className="flex-1 p-4 sm:p-6 max-w-4xl w-full mx-auto space-y-5 overflow-y-auto">
      <div className="pb-4 border-b border-slate-200">
        <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <User className="w-5 h-5 text-cyan-600" /> Profil Saya
        </h1>
        <p className="text-xs text-slate-600 mt-1">
          Data kesehatan membantu asisten memberi jawaban yang sesuai dan memperingatkan obat yang tidak cocok.
        </p>
      </div>

      {notice && (
        <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center gap-2 text-xs text-emerald-800">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" /> {notice}
        </div>
      )}
      {error && (
        <div role="alert" className="p-3 rounded-xl bg-red-50 border border-red-200 flex items-center gap-2 text-xs text-red-800">
          <AlertCircle className="w-4 h-4 text-red-600" /> {error}
        </div>
      )}

      {/* Foto & nama: bebas diubah */}
      <section className="p-5 rounded-2xl bg-white border border-slate-200 shadow-sm flex flex-col sm:flex-row gap-5 items-start sm:items-center">
        <div className="relative shrink-0">
          {profile?.photo_data_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={profile.photo_data_url} alt="Foto profil" className="w-24 h-24 rounded-2xl object-cover border border-slate-200" />
          ) : (
            <div className="w-24 h-24 rounded-2xl bg-cyan-50 border border-cyan-200 flex items-center justify-center text-3xl font-bold text-cyan-700">
              {initials}
            </div>
          )}
          {busy === "photo" && (
            <div className="absolute inset-0 rounded-2xl bg-white/70 flex items-center justify-center">
              <Loader2 className="w-5 h-5 animate-spin text-cyan-700" />
            </div>
          )}
        </div>
        <div className="flex-1 w-full space-y-3 text-xs">
          <div className="flex flex-wrap gap-2">
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={async (e) => {
                const f = e.target.files?.[0];
                e.target.value = "";
                if (!f) return;
                try {
                  const url = await toProfilePhoto(f);
                  await run("photo", () => api.auth.uploadPhoto(url), "Foto profil diperbarui.");
                } catch (err: unknown) {
                  setError(err instanceof Error ? err.message : "Foto gagal diproses.");
                }
              }}
            />
            <button type="button" onClick={() => fileRef.current?.click()} disabled={busy !== null}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold disabled:opacity-50">
              <Camera className="w-4 h-4" /> {profile?.photo_data_url ? "Ganti foto" : "Tambah foto"}
            </button>
            {profile?.photo_data_url && (
              <button type="button" disabled={busy !== null} onClick={() => run("photo", api.auth.deletePhoto, "Foto profil dihapus.")}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-300 bg-white text-slate-700 font-semibold hover:bg-slate-50 disabled:opacity-50">
                <Trash2 className="w-4 h-4" /> Hapus
              </button>
            )}
          </div>
          <p className="text-[10.5px] text-slate-500">JPG/PNG/WebP. Foto dipotong persegi dan diperkecil di perangkat Anda sebelum diunggah.</p>
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              run("name", () => api.auth.updateProfile({ full_name: fullName.trim() }), "Nama disimpan.");
            }}
          >
            <label className="sr-only" htmlFor="pf-name">Nama lengkap</label>
            <input id="pf-name" value={fullName} onChange={(e) => setFullName(e.target.value)} maxLength={100} placeholder="Nama lengkap"
              className="flex-1 px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:border-cyan-500 focus:bg-white" />
            <button type="submit" disabled={busy !== null || fullName.trim() === (profile?.full_name ?? "")}
              className="px-3 py-2 rounded-xl border border-cyan-600 text-cyan-700 font-semibold hover:bg-cyan-50 disabled:opacity-40">
              Simpan nama
            </button>
          </form>
        </div>
      </section>

      {/* Data akun dari registrasi: terkunci */}
      <section className="p-5 rounded-2xl bg-white border border-slate-200 shadow-sm space-y-4 text-xs">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-600" /> Data dari pendaftaran
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <LockedField icon={Mail} label="Email" value={profile?.email || user?.email || "-"} note="Ditetapkan saat pendaftaran." />
          {profile?.birth_date ? (
            <LockedField icon={CalendarDays} label="Tanggal lahir & usia"
              value={<>{fmtDate(profile.birth_date)} · <b>{age ? `${age.years} th ${age.months} bln ${age.days} hr` : "-"}</b></>}
              note={`Usia dihitung otomatis per ${fmtDate(today)}.`} />
          ) : (
            <div>
              <label htmlFor="pf-birth" className="block text-slate-700 font-medium mb-1.5">Tanggal lahir (isi sekali)</label>
              <input id="pf-birth" type="date" max={today || undefined} value={legacyBirth} onChange={(e) => setLegacyBirth(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-amber-300 rounded-xl text-slate-900" />
              <p className="mt-1 text-[10.5px] text-amber-700">Akun Anda dibuat sebelum aturan ini. Setelah disimpan tidak bisa diubah.</p>
            </div>
          )}
          {profile?.blood_type ? (
            <LockedField icon={Droplet} label="Golongan darah" value={profile.blood_type} note="Ditetapkan saat pendaftaran." />
          ) : (
            <div>
              <label htmlFor="pf-blood" className="block text-slate-700 font-medium mb-1.5">Golongan darah (isi sekali)</label>
              <select id="pf-blood" value={legacyBlood} onChange={(e) => setLegacyBlood(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-amber-300 rounded-xl text-slate-900">
                <option value="">Pilih...</option>
                {BLOOD_TYPES.map((b) => <option key={b} value={b}>{b}</option>)}
              </select>
              <p className="mt-1 text-[10.5px] text-amber-700">Setelah disimpan tidak bisa diubah.</p>
            </div>
          )}
        </div>
        {(!profile?.birth_date || !profile?.blood_type) && (
          <button type="button" disabled={busy !== null || (!legacyBirth && !legacyBlood)}
            onClick={() => {
              if (!window.confirm("Tanggal lahir/golongan darah tidak bisa diubah lagi setelah disimpan. Lanjutkan?")) return;
              run("legacy", () => api.auth.updateProfile({
                ...(legacyBirth && !profile?.birth_date ? { birth_date: legacyBirth } : {}),
                ...(legacyBlood && !profile?.blood_type ? { blood_type: legacyBlood } : {}),
              }), "Data pendaftaran dilengkapi dan dikunci.");
            }}
            className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-semibold disabled:opacity-40">
            Simpan & kunci
          </button>
        )}
      </section>

      {/* Data klinis rahasia: hanya sekali */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run("clinical", () => api.auth.updateProfile({ gender, medical_history_summary: medicalHistory.trim() }),
            "Data klinis disimpan dan dikunci.");
        }}
        className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4 text-xs"
      >
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <FileText className="w-4 h-4 text-cyan-600" /> Data klinis rahasia
          {clinicalLocked && <span className="ml-auto inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 border border-slate-200 text-slate-700 text-[10.5px] font-semibold"><Lock className="w-3 h-3" /> Terkunci</span>}
        </h3>

        {clinicalLocked ? (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-[180px_1fr] gap-4">
              <LockedField icon={User} label="Jenis kelamin" value={profile?.gender === "P" ? "Perempuan" : profile?.gender === "L" ? "Laki-laki" : "-"} note="" />
              <LockedField icon={FileText} label="Penyakit kronis, alergi, obat rutin" value={<span className="whitespace-pre-wrap">{profile?.medical_history_summary || "-"}</span>} note="" />
            </div>
            <p className="text-[11px] text-slate-600 flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-slate-500" />
              Disimpan {profile?.clinical_locked_at ? new Date(profile.clinical_locked_at).toLocaleString("id-ID") : ""}. Data klinis hanya bisa diisi sekali;
              untuk koreksi, hubungi petugas rekam medis RSUKT.
            </p>
          </>
        ) : (
          <>
            <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-[11.5px]">
              Data klinis bersifat rahasia dan <b>hanya bisa disimpan satu kali</b>. Isi selengkap mungkin sebelum menyimpan.
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-[180px_1fr] gap-4">
              <div>
                <label htmlFor="pf-gender" className="block text-slate-700 font-medium mb-1.5">Jenis kelamin</label>
                <select id="pf-gender" required value={gender} onChange={(e) => setGender(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:border-cyan-500">
                  <option value="" disabled>Pilih...</option>
                  <option value="L">Laki-laki</option>
                  <option value="P">Perempuan</option>
                </select>
              </div>
              <div>
                <label htmlFor="pf-history" className="block text-slate-700 font-medium mb-1.5">Penyakit kronis, alergi obat, dan obat yang sedang dikonsumsi</label>
                <textarea id="pf-history" rows={4} maxLength={4000} value={medicalHistory} onChange={(e) => setMedicalHistory(e.target.value)}
                  placeholder="Contoh: Hipertensi terkontrol Amlodipine 5 mg; alergi Penisilin (biduran); asma intermiten."
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-500 focus:outline-none focus:border-cyan-500" />
              </div>
            </div>
            <label className="flex items-start gap-2 text-[11.5px] text-slate-700">
              <input type="checkbox" checked={confirmClinical} onChange={(e) => setConfirmClinical(e.target.checked)} className="mt-0.5 accent-cyan-600" />
              Saya sudah memeriksa data di atas dan mengerti data ini tidak bisa diubah lagi.
            </label>
            <div className="flex justify-end">
              <button type="submit" disabled={busy !== null || !confirmClinical || !gender}
                className="px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold shadow-sm flex items-center gap-1.5 disabled:opacity-40">
                <Save className="w-4 h-4" /> {busy === "clinical" ? "Menyimpan..." : "Simpan & kunci"}
              </button>
            </div>
          </>
        )}
      </form>
    </div>
  );
}
