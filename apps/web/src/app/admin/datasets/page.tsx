"use client";

import React, { useEffect, useState, useCallback } from "react";
import { 
  Database, Upload, RefreshCw, FileText, CheckCircle2, 
  ShieldCheck, AlertCircle, Check
} from "lucide-react";
import { API_BASE_URL, getToken } from "@/lib/api";

interface DatasetRecordItem {
  id: string;
  dataset_id: string;
  source_file: string;
  source_format: string;
  source_version: string;
  content_preview: string;
  annotation_label?: string | null;
  access_scope: string;
  checksum: string;
  approval_status: string;
  created_at: string;
}

export default function AdminDatasetsPage() {
  const [datasets, setDatasets] = useState<DatasetRecordItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchDatasets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/admin/datasets?limit=100`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Gagal mengambil daftar dataset.");
      const data = await res.json();
      setDatasets(data.records || []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    async function init() {
      try {
        const token = getToken();
        const res = await fetch(`${API_BASE_URL}/admin/datasets?limit=100`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Gagal mengambil daftar dataset.");
        const data = await res.json();
        if (!ignore) {
          setDatasets(data.records || []);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setError(err instanceof Error ? err.message : String(err));
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }
    init();
    return () => {
      ignore = true;
    };
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    setMessage(null);
    setError(null);
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/admin/datasets/sync?force=true`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Gagal melakukan sinkronisasi folder inbox.");
      const data = await res.json();
      setMessage(data.message || "Sinkronisasi berhasil.");
      await fetchDatasets();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSyncing(false);
    }
  };

  const handleApprove = async (id: string) => {
    setApprovingId(id);
    setMessage(null);
    setError(null);
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/admin/datasets/${id}/approve`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Gagal menyetujui dataset.");
      const data = await res.json();
      setMessage(data.message || "Dataset berhasil disetujui.");
      await fetchDatasets();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setApprovingId(null);
    }
  };

  const [exporting, setExporting] = useState(false);
  const [syncingRag, setSyncingRag] = useState(false);
  const [exportStats, setExportStats] = useState<{
    exported_records_count?: number;
    file_size_bytes?: number;
    synced_records_count?: number;
    indexed_chunks_count?: number;
  } | null>(null);

  const handleExportJSONL = async () => {
    setExporting(true);
    setMessage(null);
    setError(null);
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/admin/exports/jsonl`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Gagal mengekspor data ke JSONL.");
      const data = await res.json();
      setExportStats(prev => ({
        ...prev,
        exported_records_count: data.exported_records_count,
        file_size_bytes: data.file_size_bytes,
      }));
      setMessage(`Real-time Export Berhasil: ${data.exported_records_count} rekam diekspor ke ${data.export_file} (${data.file_size_bytes} bytes).`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setExporting(false);
    }
  };

  const handleSyncToRAG = async () => {
    setSyncingRag(true);
    setMessage(null);
    setError(null);
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/admin/exports/sync-to-rag`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Gagal menyinkronkan JSONL ke RAG.");
      const data = await res.json();
      setExportStats(prev => ({
        ...prev,
        synced_records_count: data.synced_records_count,
        indexed_chunks_count: data.indexed_chunks_count,
      }));
      setMessage(`Sinkronisasi RAG Berhasil: ${data.synced_records_count} rekam disinkronkan, ${data.indexed_chunks_count} chunks diindeks ke sqlite-vec & FTS5.`);
      await fetchDatasets();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSyncingRag(false);
    }
  };

  const handleDownloadJSONL = async () => {
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/admin/exports/jsonl`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Gagal mengunduh berkas JSONL.");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "clinical_records_export.jsonl";
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-200 gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <Database className="w-6 h-6 text-emerald-600" />
            <span>Manajemen Dataset Klinis & Pipeline RAG</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Data ditarik real-time dari CSV/TXT, diekspor ke kanonikal JSONL, dan diindeks ke Knowledge Graph serta Database Vektor (sqlite-vec + FTS5).
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold shadow-sm transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-emerald-600 ${syncing ? "animate-spin" : ""}`} />
            <span>{syncing ? "Memindai..." : "Pindai Inbox"}</span>
          </button>

          <button
            onClick={handleExportJSONL}
            disabled={exporting}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-indigo-700 text-xs font-semibold shadow-sm transition disabled:opacity-50"
          >
            <FileText className={`w-3.5 h-3.5 text-indigo-600 ${exporting ? "animate-spin" : ""}`} />
            <span>{exporting ? "Mengekspor..." : "Tarik Data Real-time ke JSONL"}</span>
          </button>

          <button
            onClick={handleSyncToRAG}
            disabled={syncingRag}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition shadow-sm disabled:opacity-50"
          >
            <ShieldCheck className={`w-3.5 h-3.5 ${syncingRag ? "animate-spin" : ""}`} />
            <span>{syncingRag ? "Mengindeks..." : "Sinkronkan JSONL ke RAG Vektor"}</span>
          </button>

          <button
            onClick={handleDownloadJSONL}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-medium shadow-sm transition"
          >
            <Upload className="w-3.5 h-3.5 rotate-180 text-cyan-600" />
            <span>Unduh JSONL</span>
          </button>
        </div>
      </div>

      {/* Real-time Pipeline Status Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="text-[11px] font-medium text-slate-500">Total Rekam Klinis di Database</div>
          <div className="text-xl font-bold text-slate-900 mt-1">{datasets.length}</div>
          <div className="text-[10px] text-emerald-600 mt-0.5">
            {datasets.filter(d => d.approval_status === "APPROVED").length} Approved • {datasets.filter(d => d.approval_status === "PENDING").length} Pending
          </div>
        </div>
        <div className="bg-indigo-50/60 p-4 rounded-xl border border-indigo-200/80 shadow-sm">
          <div className="text-[11px] font-medium text-indigo-800">Kanonikal JSONL Pipeline</div>
          <div className="text-xl font-bold text-indigo-900 mt-1">
            {exportStats?.exported_records_count ?? "Real-time Ready"}
          </div>
          <div className="text-[10px] text-indigo-600 mt-0.5">
            datasets/exports/clinical_records_export.jsonl
          </div>
        </div>
        <div className="bg-emerald-50/60 p-4 rounded-xl border border-emerald-200/80 shadow-sm">
          <div className="text-[11px] font-medium text-emerald-800">Vector Search & Knowledge Graph</div>
          <div className="text-xl font-bold text-emerald-900 mt-1">
            {exportStats?.indexed_chunks_count ? `${exportStats.indexed_chunks_count} Chunks` : "Aktif & Terindeks"}
          </div>
          <div className="text-[10px] text-emerald-600 mt-0.5">
            sqlite-vec (384-d) + FTS5 BM25 + Qwen 3.8-27b
          </div>
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

      {/* Dataset Records Table */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <FileText className="w-4 h-4 text-emerald-600" />
            <span>Inventaris Rekam Dataset Terindeks ({datasets.length} baris)</span>
          </h3>
          <span className="text-[11px] text-slate-500">
            {datasets.filter(d => d.approval_status === "APPROVED").length} Disetujui • {datasets.filter(d => d.approval_status === "PENDING").length} Menunggu Persetujuan
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="pb-3 font-semibold">Format</th>
                <th className="pb-3 font-semibold">Berkas Sumber</th>
                <th className="pb-3 font-semibold">Label / Kategori</th>
                <th className="pb-3 font-semibold">Pratinjau Konten (Tersensor)</th>
                <th className="pb-3 font-semibold">Status</th>
                <th className="pb-3 font-semibold text-right">Tindakan Admin</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-sans text-xs">
              {datasets.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    {loading ? "Memuat inventaris dataset..." : "Belum ada dataset. Klik 'Pindai Inbox' untuk memproses berkas inbox."}
                  </td>
                </tr>
              ) : (
                datasets.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50 transition">
                    <td className="py-3">
                      <span className="px-2 py-0.5 rounded bg-slate-100 text-cyan-800 font-mono text-[10px] font-bold border border-slate-200">
                        {d.source_format}
                      </span>
                    </td>
                    <td className="py-3 text-slate-900 font-medium">
                      {d.source_file}
                    </td>
                    <td className="py-3 text-slate-700">
                      <span className="px-2 py-0.5 rounded-full bg-slate-100 border border-slate-200 text-[10px] text-slate-600">
                        {d.annotation_label || "General"}
                      </span>
                    </td>
                    <td className="py-3 text-slate-500 max-w-md truncate">
                      {d.content_preview}
                    </td>
                    <td className="py-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                          d.approval_status === "APPROVED"
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : "bg-amber-50 text-amber-700 border border-amber-200"
                        }`}
                      >
                        {d.approval_status}
                      </span>
                    </td>
                    <td className="py-3 text-right">
                      {d.approval_status === "PENDING" ? (
                        <button
                          onClick={() => handleApprove(d.id)}
                          disabled={approvingId === d.id}
                          className="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-[11px] transition inline-flex items-center gap-1 shadow-sm disabled:opacity-50"
                        >
                          <Check className="w-3 h-3" />
                          <span>{approvingId === d.id ? "Menyetujui..." : "Approve"}</span>
                        </button>
                      ) : (
                        <span className="text-[11px] text-emerald-700 font-medium flex items-center justify-end gap-1">
                          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                          <span>Siap Diindeks</span>
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
