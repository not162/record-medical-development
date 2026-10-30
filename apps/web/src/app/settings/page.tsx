"use client";

import React from "react";
import { useAuth } from "@/lib/auth-context";
import { Settings, Shield, Key, Trash2 } from "lucide-react";

export default function SettingsPage() {
  const { user } = useAuth();

  return (
    <div className="flex-1 p-6 max-w-4xl w-full mx-auto space-y-6">
      <div className="pb-4 border-b border-slate-200">
        <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <Settings className="w-5 h-5 text-cyan-600" />
          <span>Pengaturan Akun & Privasi</span>
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Kelola preferensi keamanan, sesi login, dan izin penggunaan data klinis.
        </p>
      </div>

      <div className="space-y-4 text-xs">
        {/* Account Info */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Shield className="w-4 h-4 text-cyan-600" />
            <span>Kredensial Akun Pengguna</span>
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <div>
              <span className="text-slate-500 block">Username Terdaftar:</span>
              <p className="font-semibold text-slate-900 mt-0.5">{user?.username}</p>
            </div>
            <div>
              <span className="text-slate-500 block">Email Pengguna:</span>
              <p className="font-semibold text-slate-900 mt-0.5">{user?.email}</p>
            </div>
            <div>
              <span className="text-slate-500 block">Peran Sistem:</span>
              <span className="inline-block mt-0.5 px-2 py-0.5 rounded bg-cyan-50 border border-cyan-200 text-cyan-800 font-semibold">
                {user?.role}
              </span>
            </div>
          </div>
        </div>

        {/* Clinical Privacy Settings */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Key className="w-4 h-4 text-emerald-600" />
            <span>Tata Kelola Privasi & Kepatuhan UU PDP No. 27/2022</span>
          </h3>
          <div className="space-y-3 pt-2 text-slate-700">
            <label className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" defaultChecked className="rounded border-slate-300 text-cyan-600 focus:ring-cyan-500" />
              <span>Informed Consent (Pasal 20): Izinkan agen AI merujuk riwayat medis pribadi untuk kalibrasi diagnosis diferensial</span>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" defaultChecked className="rounded border-slate-300 text-cyan-600 focus:ring-cyan-500" />
              <span>Purifikasi PII Otomatis (Pasal 35): Anonimisasi NIK, nama faskes, dan data pengenal sebelum evaluasi model AI</span>
            </label>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="p-5 rounded-2xl bg-red-50/70 border border-red-200 space-y-3">
          <h3 className="text-sm font-bold text-red-700 flex items-center gap-2">
            <Trash2 className="w-4 h-4" />
            <span>Hak Penghapusan Data (Right to Erasure - UU PDP Pasal 8 & 10)</span>
          </h3>
          <p className="text-slate-600 text-[11px]">
            Sesuai UU PDP No. 27/2022 Pasal 8 dan ISO/IEC 27001 Annex A.12, subjek data berhak menarik persetujuan dan meminta penghapusan permanen seluruh jejak rekam konsultasi klinis.
          </p>
          <button className="px-4 py-2 rounded-xl bg-white hover:bg-red-50 border border-red-300 text-red-700 font-semibold text-xs shadow-sm transition">
            Hapus Permanen Seluruh Riwayat Anamnesis Klinis
          </button>
        </div>
      </div>
    </div>
  );
}
