"use client";

import React, { useEffect, useState } from "react";
import { 
  Activity, Play, RefreshCw, Terminal, CheckCircle2, AlertCircle, X,
  Cpu, Sparkles, FileCode, FileSpreadsheet, Database,
  ShieldCheck, Zap, Sliders, Server
} from "lucide-react";
import { API_BASE_URL, getToken } from "@/lib/api";

interface TrainingJobItem {
  id: string;
  task_type: string;
  model_name: string;
  algorithm: string;
  status: "PENDING" | "TRAINING" | "COMPLETED" | "FAILED";
  progress_percent: number;
  model_registry_id?: string | null;
  created_by: string;
  created_at: string;
  completed_at?: string | null;
  error_message?: string | null;
}

interface SimulationResult {
  status: string;
  lcd_soft_label_cross_entropy: {
    synthetic_qa_sample: {
      question_id: string;
      question: string;
      teacher_rationale: string;
      synthetic_target_med: string;
      icd10: string;
      confidence_soft_label: number;
    };
    distillation_loss_metrics: {
      temperature: number;
      soft_label_loss: number;
      teacher_confidence_entropy: number;
      student_confidence_entropy: number;
    };
  };
  neural_translation_scanning: {
    source_language: {
      source_language_code: string;
      source_language_label: string;
      latency_ms: number;
      confidence: number;
    };
    bpe_tokens: string[];
    bpe_token_count: number;
    target_steering_token: string;
    encoder_output: {
      layers: number;
      hidden_dimension: number;
      vectors_count: number;
      sample_vector_preview: number[];
    };
    decoder_distribution: {
      vocabulary_candidates: number;
      top_logits_preview: Record<string, number>;
    };
    beam_search: {
      beam_width: number;
      top_candidates: Array<{ candidate: string; score: number }>;
      selected_best_translation: string;
    };
  };
  training_loop_preference_learning: {
    dataset_records_simulated: number;
    initial_learning_rate: number;
    final_learning_rate: number;
    lr_decay_schedule: string;
    crash_safe_checkpoint: {
      checkpoint_dir: string;
      atomic_strategy: string;
      safety_guarantee: string;
      latest_checkpoint_file: string;
      saved_epoch: number;
    };
    preference_learning_metrics: {
      paradigm: string;
      rl_algorithm: string;
      ppo_clip_ratio: number;
      grpo_group_advantages: number[];
      reward_model_score: number;
      on_policy_distillation_kl: number;
      continual_pretraining_perplexity: number;
    };
  };
}

export default function AdminTrainingPage() {
  const [activeTab, setActiveTab] = useState<"queue" | "pipeline_modes">("queue");
  const [jobs, setJobs] = useState<TrainingJobItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showLaunchModal, setShowLaunchModal] = useState(false);
  const [selectedJobLogs, setSelectedJobLogs] = useState<{ id: string; logs: string } | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [taskType, setTaskType] = useState<string>("CARDIOVASCULAR_RISK");
  const [algorithm, setAlgorithm] = useState<string>("random_forest");
  const [modelVersion, setModelVersion] = useState<string>("v1.2.0");
  const [autoActivate, setAutoActivate] = useState<boolean>(true);

  // Pipeline Modes Simulation States
  const [selectedFormat, setSelectedFormat] = useState<"jsonl" | "csv" | "python">("jsonl");
  const [simQuery, setSimQuery] = useState("Dada terasa sakit, sesak napas dan nyeri tembus ke punggung");
  const [simulating, setSimulating] = useState(false);
  const [simResult, setSimResult] = useState<SimulationResult | null>(null);

  const fetchJobs = async () => {
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/admin/models/jobs`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Gagal mengambil antrean training jobs.");
      const data = await res.json();
      setJobs(data || []);
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
        const res = await fetch(`${API_BASE_URL}/admin/models/jobs`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Gagal mengambil antrean training jobs.");
        const data = await res.json();
        if (!ignore) {
          setJobs(data || []);
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
    const interval = setInterval(load, 5000);
    return () => {
      ignore = true;
      clearInterval(interval);
    };
  }, []);

  const handleLaunchJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setMessage(null);
    setError(null);
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/admin/models/train`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          task_type: taskType,
          algorithm: algorithm,
          model_version: modelVersion.trim(),
          auto_activate: autoActivate,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Gagal memulai training job.");
      }

      const data = await res.json();
      setMessage(data.message || "Training job berhasil dikirim ke background worker.");
      setShowLaunchModal(false);
      await fetchJobs();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Gagal memulai job.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRunPipelineSimulation = async () => {
    setSimulating(true);
    setError(null);
    try {
      const token = getToken();
      const res = await fetch(
        `${API_BASE_URL}/admin/pipeline/simulate-modes?query=${encodeURIComponent(simQuery)}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      if (!res.ok) throw new Error("Gagal menjalankan simulasi pipeline mode.");
      const data: SimulationResult = await res.json();
      setSimResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Terjadi kendala simulasi pipeline.");
    } finally {
      setSimulating(false);
    }
  };

  const handleViewLogs = async (jobId: string) => {
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/admin/models/jobs/${jobId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Gagal mengambil log job.");
      const data = await res.json();
      setSelectedJobLogs({ id: jobId, logs: data.logs || "Belum ada log tercatat." });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Gagal memuat log.");
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="pb-4 border-b border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <Activity className="w-6 h-6 text-emerald-600" />
            <span>Worker Pelatihan Klinis & Mode Pemrosesan Data</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Mendukung antrean pelatihan worker terisolasi dan simulasi mode pemrosesan data (Python, CSV, JSONL) berbasis LCD, Neural Translation, dan Post-Pretraining Loop.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {activeTab === "queue" ? (
            <>
              <button
                onClick={fetchJobs}
                disabled={loading}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold shadow-xs transition"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-emerald-600 ${loading ? "animate-spin" : ""}`} />
                <span>Segarkan</span>
              </button>

              <button
                onClick={() => setShowLaunchModal(true)}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition shadow-xs"
              >
                <Play className="w-4 h-4 fill-white" />
                <span>Jadwalkan Training Baru</span>
              </button>
            </>
          ) : (
            <button
              onClick={handleRunPipelineSimulation}
              disabled={simulating}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 text-white font-semibold text-xs transition shadow-xs"
            >
              <Zap className="w-4 h-4" />
              <span>{simulating ? "Menyimulasikan Pipeline..." : "Jalankan Simulasi Mode"}</span>
            </button>
          )}
        </div>
      </div>

      {/* Tabs Selector */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setActiveTab("queue")}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition ${
            activeTab === "queue"
              ? "bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-2xs"
              : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          <Server className="w-3.5 h-3.5 text-emerald-600" />
          <span>Antrean Worker & Model Registry ({jobs.length})</span>
        </button>

        <button
          onClick={() => {
            setActiveTab("pipeline_modes");
            if (!simResult) handleRunPipelineSimulation();
          }}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition ${
            activeTab === "pipeline_modes"
              ? "bg-cyan-50 text-cyan-800 border border-cyan-200 shadow-2xs"
              : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          <Sliders className="w-3.5 h-3.5 text-cyan-600" />
          <span>Simulasi Mode Pemrosesan Data (Python, CSV, JSONL)</span>
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

      {/* TAB 1: QUEUE WORKER TABLE */}
      {activeTab === "queue" && (
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-4">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="pb-3 font-semibold">Job ID</th>
                  <th className="pb-3 font-semibold">Task & Model</th>
                  <th className="pb-3 font-semibold">Algoritma</th>
                  <th className="pb-3 font-semibold">Status Worker</th>
                  <th className="pb-3 font-semibold">Progress</th>
                  <th className="pb-3 font-semibold">Waktu Pembuatan</th>
                  <th className="pb-3 font-semibold text-right">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-sans text-xs">
                {jobs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500">
                      {loading ? "Memuat antrean job pelatihan..." : "Belum ada job pelatihan. Klik 'Jadwalkan Training Baru' untuk memulai."}
                    </td>
                  </tr>
                ) : (
                  jobs.map((j) => (
                    <tr key={j.id} className="hover:bg-slate-50 transition">
                      <td className="py-3 font-mono text-slate-500 text-[11px]">
                        {j.id.slice(0, 8)}...
                      </td>
                      <td className="py-3 font-medium text-slate-900">
                        <div>{j.model_name}</div>
                        <span className="text-[10px] text-slate-500">{j.task_type}</span>
                      </td>
                      <td className="py-3 text-slate-700 font-mono text-[10px]">
                        {j.algorithm}
                      </td>
                      <td className="py-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                            j.status === "COMPLETED"
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : j.status === "FAILED"
                              ? "bg-red-50 text-red-700 border border-red-200"
                              : j.status === "TRAINING"
                              ? "bg-sky-50 text-sky-700 border border-sky-200 animate-pulse"
                              : "bg-slate-100 text-slate-600 border border-slate-200"
                          }`}
                        >
                          {j.status}
                        </span>
                      </td>
                      <td className="py-3">
                        <div className="w-24 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${
                              j.status === "COMPLETED"
                                ? "bg-emerald-500"
                                : j.status === "FAILED"
                                ? "bg-red-500"
                                : "bg-sky-500"
                            }`}
                            style={{ width: `${j.progress_percent}%` }}
                          />
                        </div>
                        <span className="text-[10px] text-slate-500 mt-0.5 block">
                          {j.progress_percent}%
                        </span>
                      </td>
                      <td className="py-3 text-slate-500 text-[11px]">
                        {new Date(j.created_at).toLocaleString("id-ID", {
                          hour: "2-digit",
                          minute: "2-digit",
                          day: "numeric",
                          month: "short",
                        })}
                      </td>
                      <td className="py-3 text-right">
                        <button
                          onClick={() => handleViewLogs(j.id)}
                          className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-semibold transition"
                        >
                          Lihat Log
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: PIPELINE MODES SIMULATION (PYTHON, CSV, JSONL) */}
      {activeTab === "pipeline_modes" && (
        <div className="space-y-5">
          {/* Controls Bar: Format Selector & Query */}
          <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                <span>Format Data Aliran:</span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setSelectedFormat("jsonl")}
                    className={`flex items-center gap-1 px-3 py-1.5 rounded-lg border text-xs font-medium transition ${
                      selectedFormat === "jsonl"
                        ? "bg-cyan-50 border-cyan-300 text-cyan-800 font-bold"
                        : "bg-slate-50 border-slate-200 text-slate-600"
                    }`}
                  >
                    <Database className="w-3.5 h-3.5 text-cyan-600" />
                    <span>JSON Lines (.jsonl)</span>
                  </button>

                  <button
                    onClick={() => setSelectedFormat("csv")}
                    className={`flex items-center gap-1 px-3 py-1.5 rounded-lg border text-xs font-medium transition ${
                      selectedFormat === "csv"
                        ? "bg-cyan-50 border-cyan-300 text-cyan-800 font-bold"
                        : "bg-slate-50 border-slate-200 text-slate-600"
                    }`}
                  >
                    <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Tabular CSV (.csv)</span>
                  </button>

                  <button
                    onClick={() => setSelectedFormat("python")}
                    className={`flex items-center gap-1 px-3 py-1.5 rounded-lg border text-xs font-medium transition ${
                      selectedFormat === "python"
                        ? "bg-cyan-50 border-cyan-300 text-cyan-800 font-bold"
                        : "bg-slate-50 border-slate-200 text-slate-600"
                    }`}
                  >
                    <FileCode className="w-3.5 h-3.5 text-amber-600" />
                    <span>Python Pipeline (.py)</span>
                  </button>
                </div>
              </div>

              <div className="text-[11px] text-slate-500 font-mono">
                Format: <strong className="text-slate-800 uppercase">{selectedFormat}</strong> • Engine: <strong className="text-cyan-700">Qwen / Llama Distill</strong>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <input
                type="text"
                value={simQuery}
                onChange={(e) => setSimQuery(e.target.value)}
                placeholder="Masukkan keluhan atau teks klinis..."
                className="flex-1 p-2 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-900 focus:outline-none focus:border-cyan-500"
              />
              <button
                onClick={handleRunPipelineSimulation}
                disabled={simulating}
                className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white font-semibold text-xs shadow-xs transition"
              >
                {simulating ? "Memproses..." : "Eksekusi Simulasi"}
              </button>
            </div>
          </div>

          {/* 3 Core Data Processing Mode Cards */}
          {simResult && (
            <div className="space-y-5">
              {/* Mode 1: LCD Soft-Label Cross Entropy */}
              <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-3">
                <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-700 font-bold text-xs">
                      1
                    </div>
                    <div>
                      <h3 className="font-bold text-xs text-slate-900">
                        Mode 1: LCD • Soft-Label Cross Entropy from Synthetic Data
                      </h3>
                      <p className="text-[10px] text-slate-500">
                        Synthetic data merupakan perpaduan antara <strong className="text-slate-700">teacher-taught from reasoning models</strong> dan jawaban programatik terhadap <strong className="text-slate-700">code-generated questions</strong>.
                      </p>
                    </div>
                  </div>
                  <span className="px-2 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-amber-800 text-[10px] font-semibold">
                    Distillation Loss
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
                    <span className="text-[10px] font-semibold text-slate-600 block">
                      Sampel Pertanyaan Programatik (Code-Generated QA):
                    </span>
                    <p className="font-semibold text-slate-800 text-xs">
                      "{simResult.lcd_soft_label_cross_entropy.synthetic_qa_sample.question}"
                    </p>
                    <div className="text-[11px] text-slate-600 pt-1 border-t border-slate-200">
                      <strong>Teacher Rationale:</strong> {simResult.lcd_soft_label_cross_entropy.synthetic_qa_sample.teacher_rationale}
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-slate-500 pt-1">
                      <span>Target: <strong className="text-cyan-700">{simResult.lcd_soft_label_cross_entropy.synthetic_qa_sample.synthetic_target_med}</strong></span>
                      <span>ICD-10: <strong className="font-mono text-emerald-700">{simResult.lcd_soft_label_cross_entropy.synthetic_qa_sample.icd10}</strong></span>
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-amber-50/60 border border-amber-200 space-y-2">
                    <span className="text-[10px] font-semibold text-amber-900 block">
                      Metrik Soft-Label Loss (Temperature-Scaled):
                    </span>
                    <div className="grid grid-cols-2 gap-2 text-[11px]">
                      <div className="p-2 bg-white rounded-lg border border-amber-200">
                        <span className="text-slate-500 block text-[9px]">Temperature (T)</span>
                        <span className="font-bold text-amber-900 font-mono">
                          {simResult.lcd_soft_label_cross_entropy.distillation_loss_metrics.temperature}
                        </span>
                      </div>
                      <div className="p-2 bg-white rounded-lg border border-amber-200">
                        <span className="text-slate-500 block text-[9px]">Soft-Label Loss</span>
                        <span className="font-bold text-emerald-700 font-mono">
                          {simResult.lcd_soft_label_cross_entropy.distillation_loss_metrics.soft_label_loss.toFixed(4)}
                        </span>
                      </div>
                      <div className="p-2 bg-white rounded-lg border border-amber-200">
                        <span className="text-slate-500 block text-[9px]">Teacher Entropy</span>
                        <span className="font-bold text-slate-800 font-mono">
                          {simResult.lcd_soft_label_cross_entropy.distillation_loss_metrics.teacher_confidence_entropy.toFixed(4)}
                        </span>
                      </div>
                      <div className="p-2 bg-white rounded-lg border border-amber-200">
                        <span className="text-slate-500 block text-[9px]">Student Entropy</span>
                        <span className="font-bold text-slate-800 font-mono">
                          {simResult.lcd_soft_label_cross_entropy.distillation_loss_metrics.student_confidence_entropy.toFixed(4)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Mode 2: Neural Translation & Scanning Pipeline */}
              <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-3">
                <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-xl bg-cyan-50 border border-cyan-200 flex items-center justify-center text-cyan-700 font-bold text-xs">
                      2
                    </div>
                    <div>
                      <h3 className="font-bold text-xs text-slate-900">
                        Mode 2: Scanning Deteksi Bahasa & Neural Translation Pipeline
                      </h3>
                      <p className="text-[10px] text-slate-500">
                        Tiny Classifier (latency ms) ➔ Tokenisasi BPE ➔ Add Target Token (&lt;2med_id&gt;) ➔ Transformer Encoder Vectors ➔ Decoder Conditional Probs ➔ Beam Search.
                      </p>
                    </div>
                  </div>
                  <span className="px-2 py-0.5 rounded-full bg-cyan-50 border border-cyan-200 text-cyan-800 text-[10px] font-semibold">
                    Beam Width: {simResult.neural_translation_scanning.beam_search.beam_width}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                  {/* Step A: Language Detection & BPE */}
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                    <span className="text-[10px] font-bold text-slate-700 flex items-center gap-1">
                      <Zap className="w-3 h-3 text-cyan-600" />
                      1. Deteksi Bahasa & BPE
                    </span>
                    <div className="text-[11px] space-y-1">
                      <div>Bahasa: <strong>{simResult.neural_translation_scanning.source_language.source_language_label}</strong></div>
                      <div>Latency Classifier: <strong className="font-mono text-cyan-700">{simResult.neural_translation_scanning.source_language.latency_ms} ms</strong></div>
                      <div>Target Token: <strong className="font-mono text-cyan-800">{simResult.neural_translation_scanning.target_steering_token}</strong></div>
                    </div>
                    <div className="pt-1 border-t border-slate-200">
                      <span className="text-[9px] text-slate-500 block mb-1">Subwords BPE ({simResult.neural_translation_scanning.bpe_token_count}):</span>
                      <div className="flex flex-wrap gap-1">
                        {simResult.neural_translation_scanning.bpe_tokens.slice(0, 7).map((tok, i) => (
                          <span key={i} className="px-1.5 py-0.2 rounded bg-white border border-slate-200 text-[9px] font-mono text-slate-700">
                            {tok}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Step B: Transformer Encoder & Decoder */}
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                    <span className="text-[10px] font-bold text-slate-700 flex items-center gap-1">
                      <Cpu className="w-3 h-3 text-indigo-600" />
                      2. Encoder-Decoder Vectors
                    </span>
                    <div className="text-[11px] space-y-1">
                      <div>Layers: <strong>{simResult.neural_translation_scanning.encoder_output.layers} Transformer Blocks</strong></div>
                      <div>Hidden Dim: <strong className="font-mono">{simResult.neural_translation_scanning.encoder_output.hidden_dimension}D</strong></div>
                      <div>Vektor Urutan: <strong className="font-mono">{simResult.neural_translation_scanning.encoder_output.vectors_count} tokens</strong></div>
                    </div>
                    <div className="pt-1 border-t border-slate-200">
                      <span className="text-[9px] text-slate-500 block mb-1">Sample Vector Preview:</span>
                      <span className="font-mono text-[9px] text-slate-600 bg-white p-1 rounded border border-slate-200 block truncate">
                        [{simResult.neural_translation_scanning.encoder_output.sample_vector_preview.join(", ")}...]
                      </span>
                    </div>
                  </div>

                  {/* Step C: Beam Search Candidates */}
                  <div className="p-3 rounded-xl bg-cyan-50/70 border border-cyan-200 space-y-2">
                    <span className="text-[10px] font-bold text-cyan-900 flex items-center gap-1">
                      <Sparkles className="w-3 h-3 text-cyan-700" />
                      3. Beam Search Candidates
                    </span>
                    <div className="space-y-1.5">
                      {simResult.neural_translation_scanning.beam_search.top_candidates.map((c, i) => (
                        <div key={i} className="flex items-center justify-between p-1.5 rounded-lg bg-white border border-cyan-100 text-[10px]">
                          <span className="font-medium text-slate-800 truncate">{c.candidate}</span>
                          <span className="font-mono font-bold text-cyan-800 pl-1 shrink-0">
                            {(c.score * 100).toFixed(1)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Mode 3: Post-Pretraining Loop & Preference Learning */}
              <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-3">
                <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 font-bold text-xs">
                      3
                    </div>
                    <div>
                      <h3 className="font-bold text-xs text-slate-900">
                        Mode 3: Post-Pretraining Loop, Checkpoints, & Preference Learning (PPO / GRPO)
                      </h3>
                      <p className="text-[10px] text-slate-500">
                        Transisi dari Supervised Fine-Tuning (SFT) dan demonstrasi menuju preference learning (PPO/GRPO), reward design, crash-safe atomic checkpoints, dan on-policy distillation.
                      </p>
                    </div>
                  </div>
                  <span className="px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-[10px] font-semibold">
                    {simResult.training_loop_preference_learning.preference_learning_metrics.rl_algorithm}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  {/* LR Decay & Crash-Safe Checkpoints */}
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                    <span className="text-[10px] font-bold text-slate-700 flex items-center gap-1">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                      Cosine LR Decay & Crash-Safe Atomic Checkpoints
                    </span>
                    <div className="grid grid-cols-2 gap-2 text-[11px]">
                      <div className="p-2 bg-white rounded-lg border border-slate-200">
                        <span className="text-slate-500 block text-[9px]">Jadwal LR</span>
                        <span className="font-semibold text-slate-800 font-mono text-[10px]">
                          {simResult.training_loop_preference_learning.lr_decay_schedule}
                        </span>
                      </div>
                      <div className="p-2 bg-white rounded-lg border border-slate-200">
                        <span className="text-slate-500 block text-[9px]">LR Akhir</span>
                        <span className="font-bold text-emerald-700 font-mono text-[10px]">
                          {simResult.training_loop_preference_learning.final_learning_rate.toExponential(2)}
                        </span>
                      </div>
                    </div>
                    <div className="p-2 bg-white rounded-lg border border-slate-200 space-y-1 text-[10px]">
                      <span className="text-slate-500 block">Strategi Checkpoint Atomik:</span>
                      <div className="font-mono text-emerald-800 font-semibold">
                        {simResult.training_loop_preference_learning.crash_safe_checkpoint.atomic_strategy}
                      </div>
                      <div className="text-[9px] text-slate-500">
                        File: {simResult.training_loop_preference_learning.crash_safe_checkpoint.latest_checkpoint_file}
                      </div>
                    </div>
                  </div>

                  {/* RLHF, GRPO & On-Policy Distillation */}
                  <div className="p-3 rounded-xl bg-emerald-50/60 border border-emerald-200 space-y-2">
                    <span className="text-[10px] font-bold text-emerald-900 flex items-center gap-1">
                      <Activity className="w-3.5 h-3.5 text-emerald-700" />
                      Preference Learning & On-Policy Distillation
                    </span>
                    <div className="grid grid-cols-2 gap-2 text-[11px]">
                      <div className="p-2 bg-white rounded-lg border border-emerald-200">
                        <span className="text-slate-500 block text-[9px]">PPO Clip Ratio</span>
                        <span className="font-bold text-slate-800 font-mono">
                          {simResult.training_loop_preference_learning.preference_learning_metrics.ppo_clip_ratio}
                        </span>
                      </div>
                      <div className="p-2 bg-white rounded-lg border border-emerald-200">
                        <span className="text-slate-500 block text-[9px]">Reward Model Score</span>
                        <span className="font-bold text-emerald-700 font-mono">
                          {simResult.training_loop_preference_learning.preference_learning_metrics.reward_model_score.toFixed(3)}
                        </span>
                      </div>
                      <div className="p-2 bg-white rounded-lg border border-emerald-200">
                        <span className="text-slate-500 block text-[9px]">On-Policy Distill KL</span>
                        <span className="font-bold text-cyan-700 font-mono">
                          {simResult.training_loop_preference_learning.preference_learning_metrics.on_policy_distillation_kl.toFixed(4)}
                        </span>
                      </div>
                      <div className="p-2 bg-white rounded-lg border border-emerald-200">
                        <span className="text-slate-500 block text-[9px]">Continual Pretrain PPL</span>
                        <span className="font-bold text-slate-800 font-mono">
                          {simResult.training_loop_preference_learning.preference_learning_metrics.continual_pretraining_perplexity.toFixed(2)}
                        </span>
                      </div>
                    </div>
                    <div className="text-[10px] text-emerald-800 pt-0.5">
                      GRPO Group Advantages: <span className="font-mono font-semibold">[{simResult.training_loop_preference_learning.preference_learning_metrics.grpo_group_advantages.join(", ")}]</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Launch Job Modal */}
      {showLaunchModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 p-6 space-y-4 bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Play className="w-4 h-4 text-emerald-600 fill-emerald-600" />
                <span>Jadwalkan Job Pelatihan Klinis Baru</span>
              </h3>
              <button
                onClick={() => setShowLaunchModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleLaunchJob} className="space-y-4 text-xs">
              <div className="space-y-1">
                <label className="font-medium text-slate-700">Tipe Tugas Klinis (Clinical Task)</label>
                <select
                  value={taskType}
                  onChange={(e) => setTaskType(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-slate-200 bg-white text-slate-800 focus:outline-none focus:border-emerald-500"
                >
                  <option value="CARDIOVASCULAR_RISK">CARDIOVASCULAR_RISK (Prediksi Risiko Kardiovaskular 10 Tahun)</option>
                  <option value="SYMPTOM_CLASSIFICATION">SYMPTOM_CLASSIFICATION (Klasifikasi Departemen dari Keluhan Pasien)</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="font-medium text-slate-700">Algoritma Machine Learning</label>
                <select
                  value={algorithm}
                  onChange={(e) => setAlgorithm(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-slate-200 bg-white text-slate-800 focus:outline-none focus:border-emerald-500"
                >
                  <option value="random_forest">Random Forest Classifier (Ensemble)</option>
                  <option value="logistic_regression">Logistic Regression (L2 Regularized)</option>
                  <option value="xgboost">XGBoost Gradient Boosting</option>
                  <option value="qwen_distill">Qwen 2.5 On-Policy Distillation (GRPO)</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="font-medium text-slate-700">Versi Model</label>
                <input
                  type="text"
                  value={modelVersion}
                  onChange={(e) => setModelVersion(e.target.value)}
                  placeholder="v1.2.0"
                  className="w-full p-2.5 rounded-xl border border-slate-200 bg-white text-slate-800 focus:outline-none focus:border-emerald-500 font-mono"
                  required
                />
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="auto_activate"
                  checked={autoActivate}
                  onChange={(e) => setAutoActivate(e.target.checked)}
                  className="w-4 h-4 rounded text-emerald-600 focus:ring-emerald-500 border-slate-300"
                />
                <label htmlFor="auto_activate" className="text-slate-700 text-xs cursor-pointer">
                  Otomatis aktifkan model di Model Registry setelah training sukses
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowLaunchModal(false)}
                  className="px-4 py-2 rounded-xl bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 transition"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition shadow-xs disabled:opacity-50"
                >
                  <Play className="w-3.5 h-3.5 fill-white" />
                  <span>{submitting ? "Mengirim Job..." : "Mulai Pelatihan"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Log Viewer Modal */}
      {selectedJobLogs && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="w-full max-w-2xl max-h-[85vh] rounded-2xl border border-slate-200 p-6 space-y-4 bg-white shadow-xl flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Terminal className="w-4 h-4 text-emerald-600" />
                <span>Log Eksekusi Worker: {selectedJobLogs.id.slice(0, 8)}...</span>
              </h3>
              <button
                onClick={() => setSelectedJobLogs(null)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 rounded-xl bg-slate-900 border border-slate-700 font-mono text-[11px] text-emerald-400 space-y-1 whitespace-pre-wrap">
              {selectedJobLogs.logs}
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-100">
              <button
                onClick={() => setSelectedJobLogs(null)}
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
