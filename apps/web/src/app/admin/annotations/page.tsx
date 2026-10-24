"use client";

import React, { useEffect, useState } from "react";
import { CheckSquare, Edit3, Tag, CheckCircle2, AlertCircle, Save, X, Search } from "lucide-react";
import { API_BASE_URL, getToken } from "@/lib/api";

interface AnnotationRecord {
  document_id: string;
  dataset_id: string;
  source_file: string;
  annotation_label: string;
  content_preview: string;
  approval_status: string;
  created_at: string;
}

const PRESET_LABELS = [
  "Kardiologi",
  "Pulmonologi",
  "Gawat Darurat",
  "Endokrinologi",
  "Reasoning Error: Contraindicated Drug",
  "Reasoning Error: Dose Omission",
  "Normal Reasoning: Evidence Grounded",
  "Contraindication Flag: Asthma Beta-Blocker",
  "Contraindication Flag: STEMI Nitrates",
];

export default function AdminAnnotationsPage() {
  const [annotations, setAnnotations] = useState<AnnotationRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedItem, setSelectedItem] = useState<AnnotationRecord | null>(null);
  const [newLabel, setNewLabel] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchAnnotations = async () => {
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/admin/annotations?limit=100`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Gagal mengambil data anotasi terawasi.");
      const data = await res.json();
      setAnnotations(data.annotations || []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Terjadi kesalahan.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        const token = getToken();
        const res = await fetch(`${API_BASE_URL}/admin/annotations?limit=100`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Gagal mengambil data anotasi terawasi.");
        const data = await res.json();
        if (!ignore) {
          setAnnotations(data.annotations || []);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setError(err instanceof Error ? err.message : "Terjadi kesalahan.");
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }
    load();
    return () => {
      ignore = true;
    };
  }, []);

  const handleOpenEdit = (item: AnnotationRecord) => {
    setSelectedItem(item);
    setNewLabel(item.annotation_label || "");
    setNotes("");
    setMessage(null);
    setError(null);
  };

  const handleSaveAnnotation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem || !newLabel.trim()) return;

    setSaving(true);
    setError(null);
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/admin/annotations`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          document_id: selectedItem.document_id,
          annotation_label: newLabel.trim(),
          notes: notes.trim() || undefined,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Gagal menyimpan label anotasi.");
      }

      setMessage(`Label untuk dokumen ${selectedItem.document_id.slice(0, 8)} berhasil diperbarui.`);
      setSelectedItem(null);
      await fetchAnnotations();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Gagal menyimpan anotasi.");
    } finally {
      setSaving(false);
    }
  };

  const filteredAnnotations = annotations.filter(
    (a) =>
      a.annotation_label?.toLowerCase().includes(search.toLowerCase()) ||
      a.source_file?.toLowerCase().includes(search.toLowerCase()) ||
      a.content_preview?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-200 gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <CheckSquare className="w-6 h-6 text-emerald-600" />
            <span>Annotation Studio | Kurasi Label Terawasi (Supervised ML)</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Studio pelabelan ground-truth untuk mendeteksi reasoning error, kontraindikasi obat, dan klasifikasi risiko klinis sebelum training model (Sprint 06).
          </p>
        </div>

        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Cari label atau konten..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 pr-3 py-1.5 rounded-xl bg-white border border-slate-200 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-emerald-500 w-60 shadow-sm"
          />
        </div>
      </div>

      {message && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center gap-2 text-xs text-emerald-800">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{message}</span>
        </div>
      )}

      {error && (
        <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 flex items-center gap-2 text-xs text-red-800">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-[11px] font-medium text-slate-500">Total Anotasi Terverifikasi</div>
          <div className="text-xl font-bold text-slate-900 mt-1">{annotations.length} Rekam</div>
          <div className="text-[10px] text-emerald-600 mt-0.5">Siap digunakan untuk Training Model</div>
        </div>
        <div className="bg-indigo-50/60 p-4 rounded-xl border border-indigo-200/80 shadow-sm">
          <div className="text-[11px] font-medium text-indigo-800">Kategori Reasoning Error</div>
          <div className="text-xl font-bold text-indigo-900 mt-1">
            {annotations.filter(a => a.annotation_label.toLowerCase().includes("error") || a.annotation_label.toLowerCase().includes("contraindication")).length} Rekam
          </div>
          <div className="text-[10px] text-indigo-600 mt-0.5">Safety & Contraindication Flags</div>
        </div>
        <div className="bg-emerald-50/60 p-4 rounded-xl border border-emerald-200/80 shadow-sm">
          <div className="text-[11px] font-medium text-emerald-800">Audit Trail Konsensus</div>
          <div className="text-xl font-bold text-emerald-900 mt-1">100% Immutable</div>
          <div className="text-[10px] text-emerald-600 mt-0.5">Semua perubahan label tercatat di audit_logs</div>
        </div>
      </div>

      {/* Annotation Records Table */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Tag className="w-4 h-4 text-emerald-600" />
            <span>Koleksi Dataset Teranotasi ({filteredAnnotations.length})</span>
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="pb-3 font-semibold">Berkas Sumber</th>
                <th className="pb-3 font-semibold">Label Anotasi Saat Ini</th>
                <th className="pb-3 font-semibold">Pratinjau Rekam Medis</th>
                <th className="pb-3 font-semibold">Status</th>
                <th className="pb-3 font-semibold text-right">Aksi</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-sans text-xs">
              {filteredAnnotations.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    {loading ? "Memuat koleksi anotasi..." : "Belum ada rekam dengan label anotasi."}
                  </td>
                </tr>
              ) : (
                filteredAnnotations.map((item) => (
                  <tr key={item.document_id} className="hover:bg-slate-50 transition">
                    <td className="py-3 font-medium text-slate-900">
                      {item.source_file}
                    </td>
                    <td className="py-3">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${
                        item.annotation_label.toLowerCase().includes("error") || item.annotation_label.toLowerCase().includes("contraindication")
                          ? "bg-rose-50 text-rose-700 border-rose-200"
                          : "bg-emerald-50 text-emerald-700 border-emerald-200"
                      }`}>
                        {item.annotation_label}
                      </span>
                    </td>
                    <td className="py-3 text-slate-500 max-w-md truncate">
                      {item.content_preview}
                    </td>
                    <td className="py-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-100 text-slate-700 border border-slate-200">
                        {item.approval_status}
                      </span>
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => handleOpenEdit(item)}
                        className="px-2.5 py-1 rounded-lg bg-white hover:bg-slate-50 text-slate-700 text-[11px] font-medium transition inline-flex items-center gap-1 border border-slate-200 shadow-sm"
                      >
                        <Edit3 className="w-3 h-3 text-emerald-600" />
                        <span>Koreksi Label</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Annotation Modal */}
      {selectedItem && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 p-6 space-y-5 bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Tag className="w-4 h-4 text-emerald-600" />
                <span>Koreksi Anotasi Rekam Klinis</span>
              </h3>
              <button
                onClick={() => setSelectedItem(null)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1">
              <span className="text-[10px] text-slate-500 uppercase font-mono">Pratinjau Kasus</span>
              <p className="text-slate-700 italic">{selectedItem.content_preview}</p>
            </div>

            <form onSubmit={handleSaveAnnotation} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Label Terstandarisasi
                </label>
                <input
                  type="text"
                  value={newLabel}
                  onChange={(e) => setNewLabel(e.target.value)}
                  placeholder="Ketik atau pilih preset di bawah..."
                  className="w-full px-3 py-2 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-emerald-500 focus:bg-white transition"
                  required
                />
                
                {/* Presets */}
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {PRESET_LABELS.map((p) => (
                    <button
                      type="button"
                      key={p}
                      onClick={() => setNewLabel(p)}
                      className="px-2 py-0.5 rounded text-[10px] bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 transition"
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Catatan Justifikasi Klinis (Opsional)
                </label>
                <textarea
                  rows={3}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Contoh: Berdasarkan protokol PERKI 2023, pemberian beta-blocker pada asma aktif diklasifikasikan sebagai kontraindikasi absolut."
                  className="w-full px-3 py-2 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-emerald-500 focus:bg-white transition"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setSelectedItem(null)}
                  className="px-4 py-2 rounded-xl bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium border border-slate-200 transition"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={saving || !newLabel.trim()}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition shadow-sm disabled:opacity-50"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>{saving ? "Menyimpan..." : "Simpan Anotasi"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
