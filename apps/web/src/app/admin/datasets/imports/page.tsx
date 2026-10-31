"use client";

import React from "react";
import { FileText, CheckCircle2 } from "lucide-react";

export default function AdminDatasetImportsPage() {
  return (
    <div className="space-y-6">
      <div className="pb-4 border-b border-slate-200">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
          <FileText className="w-6 h-6 text-emerald-600" />
          <span>Manifes Ingesti & Laporan Baris Tertolak (Quarantine)</span>
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Laporan validasi parsial, checksum integritas berkas, dan baris data yang ditolak oleh skema klinis.
        </p>
      </div>

      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm text-center py-12 text-slate-500 text-xs">
        <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
        <p className="font-semibold text-slate-900">Seluruh Berkas Inbox Terverifikasi</p>
        <p className="text-slate-500 mt-1">Tidak ada anomali atau baris tertolak pada karantina saat ini.</p>
      </div>
    </div>
  );
}
