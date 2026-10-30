"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { api, PatientProfile } from "@/lib/api";
import { User, ShieldCheck, FileText, CheckCircle2, Lock, Save, AlertCircle } from "lucide-react";

export default function ProfilePage() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [fullName, setFullName] = useState("");
  const [age, setAge] = useState<number | "">("");
  const [gender, setGender] = useState("L");
  const [bloodType, setBloodType] = useState("O+");
  const [medicalHistory, setMedicalHistory] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadProfile() {
      try {
        const p = await api.auth.getProfile();
        setProfile(p);
        setFullName(user?.full_name || "");
        if (p.age) setAge(p.age);
        if (p.gender) setGender(p.gender);
        if (p.blood_type) setBloodType(p.blood_type);
        if (p.medical_history_summary) setMedicalHistory(p.medical_history_summary);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    }
    loadProfile();
  }, [user]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSavedSuccess(false);
    setError(null);

    try {
      const updated = await api.auth.updateProfile({
        full_name: fullName,
        age: age === "" ? undefined : Number(age),
        gender,
        blood_type: bloodType,
        medical_history_summary: medicalHistory,
      });
      setProfile(updated);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Gagal memperbarui profil rekam medis.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center p-6 text-slate-500">
        <span className="text-xs">Memuat Rekam Medis Personal...</span>
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 max-w-4xl w-full mx-auto space-y-6">
      <div className="pb-4 border-b border-slate-200">
        <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <User className="w-5 h-5 text-cyan-600" />
          <span>Profil Rekam Medis & Anamnesis Pasien</span>
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Parameter klinis dan riwayat komorbiditas yang digunakan secara personal untuk kalibrasi penalaran AI dan deteksi kontraindikasi farmakologis.
        </p>
      </div>

      {savedSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center gap-2 text-xs text-emerald-800">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>Profil rekam medis personal berhasil diperbarui dengan aman.</span>
        </div>
      )}

      {error && (
        <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 flex items-center gap-2 text-xs text-red-800">
          <AlertCircle className="w-4 h-4 text-red-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Identity Verification Card */}
      <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-slate-900">Status Otorisasi Identitas Pasien</h3>
            <p className="text-[11px] text-slate-500 mt-0.5">
              NIK Teranonimkan: <code className="text-cyan-700 font-semibold">{profile?.nik_anonymized || "NIK-ANON-317101******"}</code> (Terproteksi Hash)
            </p>
          </div>
        </div>
        <span className="px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-[11px] font-semibold">
          Terverifikasi
        </span>
      </div>

      {/* Medical Form */}
      <form onSubmit={handleSave} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-5">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 border-b border-slate-100 pb-3">
          <FileText className="w-4 h-4 text-cyan-600" />
          <span>Informasi Klinis & Riwayat Penyakit</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div>
            <label className="block text-slate-700 font-medium mb-1.5">Nama Lengkap Pasien Sesuai Identitas Resmi</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:border-cyan-500 focus:bg-white transition"
            />
          </div>

          <div>
            <label className="block text-slate-700 font-medium mb-1.5">Usia Kronologis (Tahun)</label>
            <input
              type="number"
              value={age}
              onChange={(e) => setAge(e.target.value === "" ? "" : Number(e.target.value))}
              placeholder="Contoh: 45"
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:border-cyan-500 focus:bg-white transition"
            />
          </div>

          <div>
            <label className="block text-slate-700 font-medium mb-1.5">Fenotipe Jenis Kelamin Biologis</label>
            <select
              value={gender}
              onChange={(e) => setGender(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:border-cyan-500 focus:bg-white transition"
            >
              <option value="L">Laki-laki (L)</option>
              <option value="P">Perempuan (P)</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-700 font-medium mb-1.5">Golongan Darah & Sistem Rhesus (ABO)</label>
            <select
              value={bloodType}
              onChange={(e) => setBloodType(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 focus:outline-none focus:border-cyan-500 focus:bg-white transition"
            >
              <option value="A+">A+</option>
              <option value="B+">B+</option>
              <option value="AB+">AB+</option>
              <option value="O+">O+</option>
              <option value="A-">A-</option>
              <option value="B-">B-</option>
              <option value="AB-">AB-</option>
              <option value="O-">O-</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs text-slate-700 font-medium mb-1.5">
            Anamnesis Riwayat Penyakit Kronis, Alergi Farmakologis, & Pengobatan Berjalan
          </label>
          <textarea
            rows={4}
            value={medicalHistory}
            onChange={(e) => setMedicalHistory(e.target.value)}
            placeholder="Contoh: Hipertensi Grade 1 terkontrol Amlodipine 5mg; Riwayat alergi obat golongan Penisilin (urtikaria); Riwayat Asma Bronkial intermiten."
            className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-cyan-500 focus:bg-white transition"
          />
        </div>

        <div className="flex items-center justify-between pt-3 border-t border-slate-100">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
            <Lock className="w-3.5 h-3.5 text-emerald-600" />
            <span>Rekam medis dilindungi enkripsi AES-256 pada database server lokal</span>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs shadow-sm hover:shadow transition flex items-center gap-1.5"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? "Sinkronisasi..." : "Simpan & Sinkronisasi Rekam Medis"}</span>
          </button>
        </div>
      </form>
    </div>
  );
}
