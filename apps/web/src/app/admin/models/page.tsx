"use client";

import React, { useEffect, useState } from "react";
import { Cpu, CheckCircle2, FileText, AlertCircle, RefreshCw, Zap, X } from "lucide-react";
import { API_BASE_URL, getToken } from "@/lib/api";

interface ModelRecord {
  id: string;
  model_name: string;
  model_version: string;
  algorithm: string;
  task_type: string;
  is_active: boolean;
  dataset_source: string;
  dataset_checksum: string;
  metrics: {
    f1_score?: number;
    roc_auc?: number;
    sensitivity?: number;
    specificity?: number;
    precision?: number;
    recall?: number;
    test_sample_size?: number;
    confusion_matrix?: unknown;
    classes?: string[];
  };
  hyperparameters: Record<string, unknown>;
  artifact_path: string;
  trained_by: string;
  created_at: string;
}

export default function AdminModelsPage() {
  const [models, setModels] = useState<ModelRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTask, setSelectedTask] = useState<string>("ALL");
  const [selectedModelCard, setSelectedModelCard] = useState<{ name: string; card: string } | null>(null);
  const [activatingId, setActivatingId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchModels = async () => {
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/admin/models`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Gagal mengambil data katalog Model Registry.");
      const data = await res.json();
      setModels(data || []);
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
        const res = await fetch(`${API_BASE_URL}/admin/models`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Gagal mengambil data katalog Model Registry.");
        const data = await res.json();
        if (!ignore) {
          setModels(data || []);
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

  const handleActivate = async (modelId: string) => {
    setActivatingId(modelId);
    setMessage(null);
    setError(null);
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/admin/models/${modelId}/activate`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Gagal mengaktifkan model.");
      const data = await res.json();
      setMessage(data.message || "Model berhasil diaktifkan untuk inferensi.");
      await fetchModels();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Gagal mengaktifkan model.");
    } finally {
      setActivatingId(null);
    }
  };

  const handleViewModelCard = async (modelId: string, modelName: string) => {
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/admin/models/${modelId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Gagal mengambil Model Card.");
      const data = await res.json();
      setSelectedModelCard({
        name: `${modelName} (${data.model_version})`,
        card: data.model_card || "Model Card belum didokumentasikan.",
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Gagal memuat Model Card.");
    }
  };

  const filteredModels = selectedTask === "ALL"
    ? models
    : models.filter((m) => m.task_type === selectedTask);

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-200 gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <Cpu className="w-6 h-6 text-emerald-600" />
            <span>Admin Model Registry & Versioning</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Katalog model klasifikasi terawasi terverifikasi, metrik performa klinis (F1, ROC-AUC, Sensitivitas), dan pemilihan model aktif produksi.
          </p>
        </div>

        <button
          onClick={fetchModels}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold shadow-sm transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-emerald-600 ${loading ? "animate-spin" : ""}`} />
          <span>Segarkan Registry</span>
        </button>
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

      {/* Task Filters */}
      <div className="flex flex-wrap items-center gap-2">
        {[
          { label: "Semua Model", value: "ALL" },
          { label: "Cardiovascular Risk", value: "CARDIOVASCULAR_RISK" },
          { label: "Clinical Text & Routing", value: "CLINICAL_TEXT_CLASSIFICATION" },
        ].map((t) => (
          <button
            key={t.value}
            onClick={() => setSelectedTask(t.value)}
            className={`px-3 py-1.5 rounded-xl border text-xs font-medium transition ${
              selectedTask === t.value
                ? "bg-emerald-50 border-emerald-300 text-emerald-800"
                : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Model Registry Table */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="pb-3 font-semibold">Model & Versi</th>
                <th className="pb-3 font-semibold">Algoritma</th>
                <th className="pb-3 font-semibold">Task Klinis</th>
                <th className="pb-3 font-semibold">F1-Score</th>
                <th className="pb-3 font-semibold">ROC-AUC / Sensitivitas</th>
                <th className="pb-3 font-semibold">Status Produksi</th>
                <th className="pb-3 font-semibold text-right">Aksi</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-sans text-xs">
              {filteredModels.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    {loading ? "Memuat katalog model..." : "Belum ada model terdaftar. Buka menu Training untuk melatih model baru."}
                  </td>
                </tr>
              ) : (
                filteredModels.map((m) => (
                  <tr key={m.id} className="hover:bg-slate-50 transition">
                    <td className="py-3 font-medium text-slate-900">
                      <div>{m.model_name}</div>
                      <span className="text-[10px] text-slate-500 font-mono">Ver: {m.model_version}</span>
                    </td>
                    <td className="py-3 text-slate-700">
                      <span className="px-2 py-0.5 rounded bg-slate-100 border border-slate-200 font-mono text-[10px] text-cyan-800 font-semibold">
                        {m.algorithm}
                      </span>
                    </td>
                    <td className="py-3 text-slate-500 text-[11px]">
                      {m.task_type === "CARDIOVASCULAR_RISK" ? "Cardio Risk Prediction" : "Text Department Routing"}
                    </td>
                    <td className="py-3 font-mono text-emerald-600 font-bold">
                      {m.metrics?.f1_score !== undefined ? m.metrics.f1_score : "-"}
                    </td>
                    <td className="py-3 font-mono text-slate-700">
                      {m.metrics?.roc_auc !== undefined ? (
                        <span>AUC: {m.metrics.roc_auc} (Sens: {m.metrics.sensitivity})</span>
                      ) : (
                        <span>Prec: {m.metrics?.precision ?? "-"}</span>
                      )}
                    </td>
                    <td className="py-3">
                      {m.is_active ? (
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1 w-fit">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          <span>ACTIVE</span>
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full text-[10px] bg-slate-100 text-slate-500 border border-slate-200">
                          STANDBY
                        </span>
                      )}
                    </td>
                    <td className="py-3 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleViewModelCard(m.id, m.model_name)}
                          className="px-2.5 py-1 rounded-lg bg-white hover:bg-slate-50 text-slate-700 text-[11px] font-medium transition inline-flex items-center gap-1 border border-slate-200 shadow-sm"
                        >
                          <FileText className="w-3 h-3 text-cyan-600" />
                          <span>Model Card</span>
                        </button>
                        {!m.is_active && (
                          <button
                            onClick={() => handleActivate(m.id)}
                            disabled={activatingId === m.id}
                            className="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-semibold transition inline-flex items-center gap-1 shadow-sm disabled:opacity-50"
                          >
                            <Zap className="w-3 h-3" />
                            <span>{activatingId === m.id ? "Mengaktifkan..." : "Aktifkan"}</span>
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Model Card Modal */}
      {selectedModelCard && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-2xl max-h-[85vh] rounded-2xl border border-slate-200 p-6 space-y-4 bg-white shadow-xl flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <FileText className="w-4 h-4 text-emerald-600" />
                <span>{selectedModelCard.name}</span>
              </h3>
              <button
                onClick={() => setSelectedModelCard(null)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto pr-2 text-xs text-slate-700 space-y-3 font-sans leading-relaxed whitespace-pre-wrap">
              {selectedModelCard.card}
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-100">
              <button
                onClick={() => setSelectedModelCard(null)}
                className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition"
              >
                Tutup
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
