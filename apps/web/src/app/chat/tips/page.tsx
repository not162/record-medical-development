"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  HeartPulse, Utensils, GlassWater, Footprints, Moon, Sparkles, Droplet, Scale,
  Loader2, AlertCircle, ShieldCheck, RefreshCw, Info,
} from "lucide-react";
import { api, WellnessLifestyle, WellnessResult, WellnessSection } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { isAdminRole } from "@/lib/roles";

const SECTION_ICON: Record<WellnessSection["id"], React.ElementType> = {
  food: Utensils,
  drink: GlassWater,
  activity: Footprints,
  sleep: Moon,
  habits: Sparkles,
};

const MISSING_LABEL: Record<string, string> = {
  birth_date: "tanggal lahir",
  gender: "jenis kelamin",
  blood_type: "golongan darah",
};

const CONDITION_LABEL: Record<string, string> = {
  hipertensi: "Hipertensi",
  diabetes: "Diabetes",
  kolesterol: "Kolesterol",
  asam_urat: "Asam urat",
  maag: "Maag/asam lambung",
};

function num(v: string): number | undefined {
  const n = Number(v);
  return v.trim() === "" || Number.isNaN(n) ? undefined : n;
}

export default function HealthyTipsPage() {
  const { role, isLoading: authLoading } = useAuth();
  const blocked = isAdminRole(role);
  const [data, setData] = useState<WellnessResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ activity: "", sleep: "", water: "", height: "", weight: "", smoker: "" });

  const load = useCallback(async (lifestyle: WellnessLifestyle = {}) => {
    if (authLoading || blocked) return;
    setLoading(true);
    setError(null);
    try {
      setData(await api.wellness.recommendations(lifestyle));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Gagal memuat rekomendasi.");
    } finally {
      setLoading(false);
    }
  }, [authLoading, blocked]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- muat sekali setelah peran diketahui
    load();
  }, [load]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    load({
      activity: (form.activity || undefined) as WellnessLifestyle["activity"],
      sleep_hours: num(form.sleep),
      water_glasses: num(form.water),
      height_cm: num(form.height),
      weight_kg: num(form.weight),
      smoker: form.smoker === "" ? undefined : form.smoker === "ya",
    });
  };

  const field = "w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-cyan-500";

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        <header className="flex items-start gap-3">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-600 text-white flex items-center justify-center shrink-0 shadow-sm">
            <HeartPulse className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-extrabold tracking-tight text-slate-900">Tips Hidup Sehat</h1>
            <p className="text-sm text-slate-600">
              Rekomendasi makanan, minuman, aktivitas, dan tidur yang disesuaikan dengan usia dan biodata Anda.
            </p>
          </div>
        </header>

        <div className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800">
          <ShieldCheck className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            Dihitung dengan aturan gizi dan kesehatan yang tetap, <b>tanpa AI/LLM</b>. Biodata Anda tidak dikirim ke model AI, dan isian gaya hidup di bawah tidak disimpan.
          </span>
        </div>

        {data && data.basis.missing_fields.length > 0 && (
          <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
            <Info className="w-4 h-4 shrink-0 mt-0.5" />
            <span>
              Lengkapi {data.basis.missing_fields.map((f) => MISSING_LABEL[f] ?? f).join(", ")} di{" "}
              <Link href="/profile" className="font-semibold underline">Profil Saya</Link> agar rekomendasi lebih tepat.
            </span>
          </div>
        )}

        {data && (
          <section className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-xl border border-slate-200 bg-white p-3">
              <div className="text-[11px] text-slate-500">Usia</div>
              <div className="text-lg font-bold text-slate-900">{data.basis.age ?? "—"}{data.basis.age != null && " th"}</div>
              <div className="text-[11px] text-slate-500">{data.basis.age_group_label}</div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-3">
              <div className="text-[11px] text-slate-500">Jenis kelamin</div>
              <div className="text-lg font-bold text-slate-900">
                {data.basis.gender === "L" ? "Laki-laki" : data.basis.gender === "P" ? "Perempuan" : "—"}
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-3">
              <div className="text-[11px] text-slate-500">Golongan darah</div>
              <div className="text-lg font-bold text-slate-900">{data.basis.blood_type ?? "—"}</div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-3">
              <div className="text-[11px] text-slate-500">Dari riwayat</div>
              <div className="text-sm font-semibold text-slate-900">
                {data.basis.conditions.length ? data.basis.conditions.map((c) => CONDITION_LABEL[c] ?? c).join(", ") : "Tidak ada catatan"}
              </div>
            </div>
          </section>
        )}

        <form onSubmit={submit} className="rounded-2xl border border-slate-200 bg-white p-4 space-y-3">
          <div>
            <h2 className="text-sm font-bold text-slate-900">Kebiasaan Anda (opsional)</h2>
            <p className="text-xs text-slate-500">Isi untuk rekomendasi yang lebih personal. Data ini hanya dipakai sekali dan tidak disimpan.</p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <label className="text-xs text-slate-600 space-y-1">
              <span>Aktivitas fisik</span>
              <select className={field} value={form.activity} onChange={(e) => setForm({ ...form, activity: e.target.value })}>
                <option value="">Pilih</option>
                <option value="rendah">Rendah (banyak duduk)</option>
                <option value="sedang">Sedang</option>
                <option value="tinggi">Tinggi (rutin olahraga)</option>
              </select>
            </label>
            <label className="text-xs text-slate-600 space-y-1">
              <span>Tidur (jam/malam)</span>
              <input className={field} type="number" inputMode="decimal" min={0} max={24} step={0.5} value={form.sleep} onChange={(e) => setForm({ ...form, sleep: e.target.value })} />
            </label>
            <label className="text-xs text-slate-600 space-y-1">
              <span>Air putih (gelas/hari)</span>
              <input className={field} type="number" inputMode="numeric" min={0} max={40} value={form.water} onChange={(e) => setForm({ ...form, water: e.target.value })} />
            </label>
            <label className="text-xs text-slate-600 space-y-1">
              <span>Tinggi badan (cm)</span>
              <input className={field} type="number" inputMode="decimal" min={50} max={250} value={form.height} onChange={(e) => setForm({ ...form, height: e.target.value })} />
            </label>
            <label className="text-xs text-slate-600 space-y-1">
              <span>Berat badan (kg)</span>
              <input className={field} type="number" inputMode="decimal" min={10} max={400} value={form.weight} onChange={(e) => setForm({ ...form, weight: e.target.value })} />
            </label>
            <label className="text-xs text-slate-600 space-y-1">
              <span>Merokok</span>
              <select className={field} value={form.smoker} onChange={(e) => setForm({ ...form, smoker: e.target.value })}>
                <option value="">Pilih</option>
                <option value="tidak">Tidak</option>
                <option value="ya">Ya</option>
              </select>
            </label>
          </div>
          <button type="submit" disabled={loading} className="inline-flex items-center gap-2 rounded-xl bg-cyan-600 hover:bg-cyan-700 disabled:opacity-60 px-4 py-2 text-sm font-semibold text-white">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            Perbarui rekomendasi
          </button>
        </form>

        {error && (
          <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            <AlertCircle className="w-4 h-4" /> {error}
          </div>
        )}

        {loading && !data && (
          <div className="flex items-center gap-2 text-sm text-slate-500"><Loader2 className="w-4 h-4 animate-spin" /> Menyusun rekomendasi...</div>
        )}

        {data && (
          <>
            {data.body && (
              <section className="rounded-2xl border border-slate-200 bg-white p-4 flex items-start gap-3">
                <Scale className="w-5 h-5 text-cyan-600 shrink-0 mt-0.5" />
                <div>
                  <h2 className="text-sm font-bold text-slate-900">Indeks Massa Tubuh: {data.body.bmi} — {data.body.category}</h2>
                  <p className="text-sm text-slate-600">{data.body.tip}</p>
                </div>
              </section>
            )}

            <div className="grid gap-4 md:grid-cols-2">
              {data.sections.map((s) => {
                const Icon = SECTION_ICON[s.id] ?? Sparkles;
                return (
                  <section key={s.id} className="rounded-2xl border border-slate-200 bg-white p-4 space-y-3">
                    <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
                      <Icon className="w-4 h-4 text-cyan-600" /> {s.title}
                    </h2>
                    <ul className="space-y-3">
                      {s.items.map((it) => (
                        <li key={it.title} className="space-y-0.5">
                          <div className="text-sm font-semibold text-slate-900">{it.title}</div>
                          <p className="text-sm text-slate-600 leading-relaxed">{it.detail}</p>
                          <p className="text-[11px] text-slate-400">Alasan: {it.reason}</p>
                        </li>
                      ))}
                    </ul>
                  </section>
                );
              })}
            </div>

            {data.blood && (
              <section className="rounded-2xl border border-slate-200 bg-white p-4 space-y-2">
                <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
                  <Droplet className="w-4 h-4 text-red-500" /> Golongan Darah {data.blood.blood_type}
                </h2>
                <p className="text-sm text-slate-600">Bisa mendonorkan ke: <b>{data.blood.can_donate_to.join(", ")}</b></p>
                <p className="text-sm text-slate-600">Bisa menerima dari: <b>{data.blood.can_receive_from.join(", ")}</b></p>
                <p className="text-sm text-slate-600">
                  {data.blood.donor_eligible_by_age
                    ? "Usia Anda memenuhi syarat donor darah PMI (17–60 th). Syarat lain seperti berat badan dan hemoglobin dicek di lokasi donor."
                    : "Usia Anda belum/tidak memenuhi syarat usia donor darah PMI (17–60 th)."}
                </p>
                <p className="text-[11px] text-slate-400">{data.blood.note}</p>
              </section>
            )}

            <footer className="space-y-1 text-[11px] text-slate-500">
              <p>{data.disclaimer}</p>
              <p>Acuan: {data.sources.join(" · ")}</p>
            </footer>
          </>
        )}
      </div>
    </div>
  );
}
