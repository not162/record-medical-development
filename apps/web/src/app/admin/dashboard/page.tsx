"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { 
  Users, MessageSquare, CheckCircle2, 
  ThumbsUp, Activity, ShieldAlert, Cpu, ArrowUpRight,
  RefreshCw, FileSpreadsheet, FileCode
} from "lucide-react";
import { api, AuditLog, API_BASE_URL } from "@/lib/api";

interface DashboardSummary {
  status: string;
  system_time: string;
  admin_user: string;
  metrics: {
    total_registered_users: number;
    total_chat_sessions: number;
    total_dataset_records: number;
    approved_knowledge_records: number;
    feedback_metrics: {
      total: number;
      likes: number;
      dislikes: number;
      satisfaction_ratio: number;
    };
  };
}

export default function AdminDashboardPage() {
  const [dashboardData, setDashboardData] = useState<DashboardSummary | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exportingFormat, setExportingFormat] = useState<string | null>(null);

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.admin.getDashboard();
      setDashboardData(data as unknown as DashboardSummary);
      const logs = await api.admin.getAuditLogs(6, 0);
      setAuditLogs(logs);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    const run = async () => {
      try {
        const data = await api.admin.getDashboard();
        if (!ignore) {
          setDashboardData(data as unknown as DashboardSummary);
          const logs = await api.admin.getAuditLogs(6, 0);
          setAuditLogs(logs);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setError(err instanceof Error ? err.message : String(err));
          setLoading(false);
        }
      }
    };
    run();
    return () => {
      ignore = true;
    };
  }, []);

  if (loading && !dashboardData) {
    return (
      <div className="flex-1 flex items-center justify-center p-12 text-slate-500">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-xs">Memuat Metrik Operasional Real-time...</span>
        </div>
      </div>
    );
  }

  const defaultMetrics = {
    total_registered_users: 0,
    total_chat_sessions: 0,
    total_dataset_records: 0,
    approved_knowledge_records: 0,
    feedback_metrics: {
      total: 0,
      likes: 0,
      dislikes: 0,
      satisfaction_ratio: 0,
    },
  };
  const metrics = dashboardData?.metrics || defaultMetrics;
  const feedback = metrics.feedback_metrics;

  const handleExportColab = async (format: "csv" | "jsonl") => {
    const token = localStorage.getItem("clinical_token") || localStorage.getItem("token");
    if (!token) return;
    setExportingFormat(format);
    try {
      const res = await fetch(`${API_BASE_URL}/admin/conversations/export?format=${format}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const blob = await res.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = `rsukt_colab_conversations_${Date.now()}.${format}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(downloadUrl);
      } else {
        alert("Gagal mengekspor percakapan untuk Google Colab.");
      }
    } catch (err: unknown) {
      alert(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setExportingFormat(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Title & Refresh */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Pusat Komando Riset & Operasional AI
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Status real-time database SQLite, model terlatih, audit keamanan, dan kurasi dataset klinis.
          </p>
        </div>

        <button
          onClick={fetchDashboard}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold shadow-sm transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-emerald-600 ${loading ? "animate-spin" : ""}`} />
          <span>Sinkronisasi Data</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-xs text-red-800">
          {error}
        </div>
      )}

      {/* Ekspor Google Colab Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white p-5 rounded-2xl shadow-sm border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-amber-400 text-slate-900">
              Colab Training Ready
            </span>
            <span className="text-xs text-slate-300">Format ChatML & Tabular CSV</span>
          </div>
          <h3 className="text-base font-bold text-white mt-1">
            Ekspor Benchmark Pengetahuan Klinis Terverifikasi (De-Identified)
          </h3>
          <p className="text-xs text-slate-300 mt-0.5">
            Unduh korpus data protokol kesehatan & benchmark medis yang telah disetujui (Approved) bebas dari data pribadi pasien sesuai UU PDP Pasal 4.
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          <button
            onClick={() => handleExportColab("csv")}
            disabled={exportingFormat !== null}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-xs text-white font-semibold shadow transition disabled:opacity-50"
            title="Unduh seluruh data percakapan format CSV untuk pandas / machine learning tabular"
          >
            <FileSpreadsheet className="w-4 h-4 text-sky-200" />
            <span>{exportingFormat === "csv" ? "Mengunduh CSV..." : "Ekspor CSV (Colab)"}</span>
          </button>

          <button
            onClick={() => handleExportColab("jsonl")}
            disabled={exportingFormat !== null}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-xs text-white font-semibold shadow transition disabled:opacity-50"
            title="Unduh percakapan format JSONL ChatML siap fine-tuning Llama/Unsloth di Colab"
          >
            <FileCode className="w-4 h-4 text-purple-200" />
            <span>{exportingFormat === "jsonl" ? "Mengunduh JSONL..." : "Ekspor JSONL (Colab)"}</span>
          </button>
        </div>
      </div>

      {/* Metrics Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1 */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Pengguna Terdaftar</span>
            <div className="w-8 h-8 rounded-lg bg-cyan-50 border border-cyan-200 flex items-center justify-center text-cyan-600">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <h3 className="text-3xl font-extrabold text-slate-900">
              {metrics.total_registered_users ?? 0}
            </h3>
            <p className="text-[11px] text-slate-500 mt-1">Akun pasien & staf terautentikasi</p>
          </div>
        </div>

        {/* Card 2 */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Sesi Chatbot Klinis</span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
              <MessageSquare className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <h3 className="text-3xl font-extrabold text-slate-900">
              {metrics.total_chat_sessions ?? 0}
            </h3>
            <p className="text-[11px] text-slate-500 mt-1">Riwayat percakapan evidence-grounded</p>
          </div>
        </div>

        {/* Card 3 */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Knowledge Terverifikasi</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <h3 className="text-3xl font-extrabold text-emerald-600">
              {metrics.approved_knowledge_records ?? 0}
            </h3>
            <p className="text-[11px] text-slate-500 mt-1">
              Dari {metrics.total_dataset_records ?? 0} total rekam terindeks
            </p>
          </div>
        </div>

        {/* Card 4 */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Kepuasan Respon Dokter</span>
            <div className="w-8 h-8 rounded-lg bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-600">
              <ThumbsUp className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <h3 className="text-3xl font-extrabold text-purple-600">
              {(feedback.satisfaction_ratio * 100).toFixed(0)}%
            </h3>
            <p className="text-[11px] text-slate-500 mt-1">
              {feedback.likes ?? 0} Likes (+1.75%) • {feedback.dislikes ?? 0} Dislikes (-0.74%)
            </p>
          </div>
        </div>
      </div>

      {/* Quick Launchpad & Active Models */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm lg:col-span-2 space-y-4">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-600" />
            <span>Pintasan Cepat Alur Riset Klinis</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <Link
              href="/admin/datasets"
              className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 hover:border-emerald-400 hover:bg-emerald-50/20 transition group flex flex-col justify-between"
            >
              <div>
                <span className="font-semibold text-slate-900 group-hover:text-emerald-600 transition flex items-center justify-between">
                  <span>1. Dataset Ingestion</span>
                  <ArrowUpRight className="w-4 h-4" />
                </span>
                <p className="text-[11px] text-slate-500 mt-1">
                  Upload & validasi format CSV, TXT, dan JSONL ke folder inbox terlindungi.
                </p>
              </div>
              <span className="text-[10px] text-emerald-600 font-medium mt-3 block">Buka Kurasi Data &rarr;</span>
            </Link>

            <Link
              href="/admin/training"
              className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 hover:border-cyan-400 hover:bg-cyan-50/20 transition group flex flex-col justify-between"
            >
              <div>
                <span className="font-semibold text-slate-900 group-hover:text-cyan-600 transition flex items-center justify-between">
                  <span>2. Pelatihan Model Lokal</span>
                  <ArrowUpRight className="w-4 h-4" />
                </span>
                <p className="text-[11px] text-slate-500 mt-1">
                  Latih baseline Logistic Regression, Triase 6 departemen, dan IndoBERT Safety Guardrail.
                </p>
              </div>
              <span className="text-[10px] text-cyan-600 font-medium mt-3 block">Kelola Training Job &rarr;</span>
            </Link>

            <Link
              href="/admin/evaluation"
              className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 hover:border-purple-400 hover:bg-purple-50/20 transition group flex flex-col justify-between"
            >
              <div>
                <span className="font-semibold text-slate-900 group-hover:text-purple-600 transition flex items-center justify-between">
                  <span>3. Evaluasi & Metrik Akurasi</span>
                  <ArrowUpRight className="w-4 h-4" />
                </span>
                <p className="text-[11px] text-slate-500 mt-1">
                  Matriks konfusi, kurva ROC-AUC (0.8007), Cohen's Kappa (&kappa;=0.92), dan Shannon Entropy.
                </p>
              </div>
              <span className="text-[10px] text-purple-600 font-medium mt-3 block">Inspeksi Laporan &rarr;</span>
            </Link>

            <Link
              href="/admin/graph"
              className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 hover:border-amber-400 hover:bg-amber-50/20 transition group flex flex-col justify-between"
            >
              <div>
                <span className="font-semibold text-slate-900 group-hover:text-amber-600 transition flex items-center justify-between">
                  <span>4. GraphRAG Knowledge Tree</span>
                  <ArrowUpRight className="w-4 h-4" />
                </span>
                <p className="text-[11px] text-slate-500 mt-1">
                  Visualisasi graf relasi simpul penyakit, kontraindikasi obat, dan sumber rujukan sitasi.
                </p>
              </div>
              <span className="text-[10px] text-amber-600 font-medium mt-3 block">Buka Kanvas Graf &rarr;</span>
            </Link>
          </div>
        </div>

        {/* System & Engine Status */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-cyan-600" />
            <span>Kesiapan Mesin AI</span>
          </h3>

          <div className="space-y-3 text-xs">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
              <div>
                <p className="font-semibold text-slate-900">Groq LLM Generation</p>
                <p className="text-[10px] text-slate-500">Llama 3.3 70B Versatile</p>
              </div>
              <span className="px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-[10px] font-semibold">
                Online
              </span>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
              <div>
                <p className="font-semibold text-slate-900">Database Relasional</p>
                <p className="text-[10px] text-slate-500">SQLite (WAL + FK On)</p>
              </div>
              <span className="px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-[10px] font-semibold">
                Active
              </span>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
              <div>
                <p className="font-semibold text-slate-900">Safety Guardrail Model</p>
                <p className="text-[10px] text-slate-500">IndoBERT Embeddings (768-d)</p>
              </div>
              <span className="px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-[10px] font-semibold">
                Trained
              </span>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
              <div>
                <p className="font-semibold text-slate-900">Prediktor Kardiovaskular</p>
                <p className="text-[10px] text-slate-500">Random Forest 15k (ROC 0.8007)</p>
              </div>
              <span className="px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-[10px] font-semibold">
                Trained
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Audit Logs Table */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-emerald-600" />
            <span>Log Audit Keamanan & Akses Terakhir</span>
          </h3>
          <Link
            href="/admin/audit-logs"
            className="text-xs text-emerald-600 hover:text-emerald-700 font-semibold flex items-center gap-1"
          >
            <span>Lihat Semua Log</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="pb-2.5 font-semibold">Waktu (UTC)</th>
                <th className="pb-2.5 font-semibold">Aksi</th>
                <th className="pb-2.5 font-semibold">Tipe Sumber Daya</th>
                <th className="pb-2.5 font-semibold">Status</th>
                <th className="pb-2.5 font-semibold">Detail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {auditLogs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-4 text-center text-slate-500">
                    Belum ada rekaman audit log.
                  </td>
                </tr>
              ) : (
                auditLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50 transition">
                    <td className="py-2.5 text-slate-500">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="py-2.5 font-semibold text-slate-900">
                      <code className="text-cyan-700">{log.action}</code>
                    </td>
                    <td className="py-2.5 text-slate-600">{log.resource_type}</td>
                    <td className="py-2.5">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                          log.status === "SUCCESS"
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : "bg-red-50 text-red-700 border border-red-200"
                        }`}
                      >
                        {log.status}
                      </span>
                    </td>
                    <td className="py-2.5 text-slate-500 max-w-xs truncate">
                      {log.details || "-"}
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
