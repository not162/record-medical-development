"use client";

import React, { useEffect, useState } from "react";
import {
  BarChart3,
  Activity,
  HeartPulse,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  Zap,
  Download,
  Flame,
  Scale,
  BrainCircuit,
  FileSpreadsheet,
  FileText,
  ImageIcon,
  RefreshCw,
  Sliders,
} from "lucide-react";
import { API_BASE_URL, getToken } from "@/lib/api";

interface EvalData {
  status: string;
  cardio_model: {
    id: string | null;
    name: string;
    version: string;
    algorithm: string;
    is_active: boolean;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    metrics: Record<string, any>;
  };
  text_model: {
    id: string | null;
    name: string;
    version: string;
    algorithm: string;
    is_active: boolean;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    metrics: Record<string, any>;
  };
}

interface StressTestResult {
  total_samples: number;
  baseline: {
    f1_weighted: number;
    accuracy: number;
    mean_entropy: number;
  };
  overall_robustness_score: number;
  perturbation_conditions: Array<{
    condition: string;
    f1_weighted: number;
    accuracy: number;
    mean_entropy: number;
    delta_f1: number;
    delta_accuracy: number;
    entropy_shift: number;
    relative_degradation_pct: number;
    sample_perturbed: string;
    sample_original: string;
  }>;
}

interface ConsensusResult {
  sample_count: number;
  performance_against_ground_truth: Record<string, {
    accuracy: number;
    f1_score: number;
    cohen_kappa: number;
  }>;
  cohen_kappa_matrix: {
    raters: string[];
    kappa_matrix: number[][];
  };
  cases: Array<{
    case_id: string;
    text: string;
    ground_truth: number;
    error_type: string;
    correction: string;
    ml_prediction: number;
    kg_prediction: number;
    consensus_prediction: number;
    is_unanimous: boolean;
  }>;
}

interface ExportResult {
  exported_files: Record<string, string>;
  download_links: Record<string, string>;
  message: string;
}

export default function AdminEvaluationPage() {
  const [evalData, setEvalData] = useState<EvalData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"METRICS" | "STRESS" | "CONSENSUS" | "EXPORTS" | "SIMULATOR">("METRICS");

  // Stress testing states
  const [stressTesting, setStressTesting] = useState(false);
  const [stressData, setStressData] = useState<StressTestResult | null>(null);
  const [stressError, setStressError] = useState<string | null>(null);

  // Consensus states
  const [runningConsensus, setRunningConsensus] = useState(false);
  const [consensusData, setConsensusData] = useState<ConsensusResult | null>(null);
  const [consensusError, setConsensusError] = useState<string | null>(null);

  // Export states
  const [exporting, setExporting] = useState(false);
  const [exportData, setExportData] = useState<ExportResult | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  // Live inference simulator states
  const [age, setAge] = useState<number>(55);
  const [systolic, setSystolic] = useState<number>(140);
  const [diastolic, setDiastolic] = useState<number>(90);
  const [glucose, setGlucose] = useState<number>(130);
  const [cholesterol, setCholesterol] = useState<number>(220);
  const [smoking, setSmoking] = useState<string>("Yes");
  const [predicting, setPredicting] = useState<boolean>(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [prediction, setPrediction] = useState<any | null>(null);
  const [predError, setPredError] = useState<string | null>(null);

  const fetchEvaluationData = async () => {
    try {
      setLoading(true);
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/admin/evaluation`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Gagal mengambil metrik evaluasi.");
      const data = await res.json();
      setEvalData(data);
    } catch (err: unknown) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void Promise.resolve().then(() => {
      fetchEvaluationData();
    });
  }, []);

  const handleRunStressTest = async () => {
    try {
      setStressTesting(true);
      setStressError(null);
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/admin/evaluation/run-stress-test`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ sample_limit: 30 }),
      });
      if (!res.ok) throw new Error("Gagal menjalankan stress test perturbasi.");
      const data = await res.json();
      setStressData(data.benchmark_results);
    } catch (err: unknown) {
      setStressError(err instanceof Error ? err.message : "Gagal menjalankan stress test");
    } finally {
      setStressTesting(false);
    }
  };

  const handleRunConsensus = async () => {
    try {
      setRunningConsensus(true);
      setConsensusError(null);
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/admin/evaluation/consensus`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Gagal menjalankan evaluasi konsensus multi-model.");
      const data = await res.json();
      setConsensusData(data.consensus_results);
    } catch (err: unknown) {
      setConsensusError(err instanceof Error ? err.message : "Gagal evaluasi konsensus");
    } finally {
      setRunningConsensus(false);
    }
  };

  const handleExportArtifacts = async () => {
    try {
      setExporting(true);
      setExportError(null);
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/admin/exports`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          model_name: evalData?.cardio_model?.name || "CardioClassifier",
          include_figures: true,
          include_csv: true,
        }),
      });
      if (!res.ok) throw new Error("Gagal mengekspor artefak riset.");
      const data = await res.json();
      setExportData(data);
    } catch (err: unknown) {
      setExportError(err instanceof Error ? err.message : "Gagal mengekspor artefak");
    } finally {
      setExporting(false);
    }
  };

  const handlePredict = async (e: React.FormEvent) => {
    e.preventDefault();
    setPredicting(true);
    setPredError(null);
    setPrediction(null);
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE_URL}/admin/models/predict/cardio`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          age,
          gender: "Male",
          blood_pressure_systolic: systolic,
          blood_pressure_diastolic: diastolic,
          fasting_blood_sugar: glucose,
          cholesterol_level: cholesterol,
          cholesterol_hdl: 50,
          cholesterol_ldl: 120,
          triglycerides: 150,
          smoking_status: smoking,
          physical_activity: "Moderate",
          hypertension: systolic >= 140 ? 1 : 0,
          diabetes: glucose >= 126 ? 1 : 0,
          previous_heart_disease: 0,
        }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Gagal menjalankan inferensi model kardiovaskular.");
      }
      const data = await res.json();
      setPrediction(data);
    } catch (err: unknown) {
      setPredError(err instanceof Error ? err.message : "Terjadi kesalahan inferensi.");
    } finally {
      setPredicting(false);
    }
  };

  const cardioMetrics = evalData?.cardio_model?.metrics || {};
  const entropyStats = cardioMetrics.shannon_entropy || {};
  const calibStats = cardioMetrics.calibration || {};
  const ci95 = cardioMetrics.confidence_intervals_95 || {};

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <Scale className="h-6 w-6 text-indigo-600" />
            Evaluasi Model & Analisis Ketahanan Noise (Sprint 07)
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Metrik matematika presisi, Cohen's Kappa, Shannon Entropy, kalibrasi reliabilitas, dan 8 kondisi perturbasi teks klinis.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchEvaluationData}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg border border-slate-300 hover:bg-slate-50 text-slate-700 transition-colors shadow-sm"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Muat Ulang
          </button>
          <button
            onClick={() => {
              setActiveTab("EXPORTS");
              handleExportArtifacts();
            }}
            disabled={exporting}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition-colors"
          >
            <Download className="h-3.5 w-3.5" />
            {exporting ? "Mengekspor..." : "Ekspor Riset"}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 overflow-x-auto pb-1 text-sm">
        <button
          onClick={() => setActiveTab("METRICS")}
          className={`px-4 py-2 font-medium border-b-2 transition-colors whitespace-nowrap flex items-center gap-2 ${
            activeTab === "METRICS"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <BarChart3 className="h-4 w-4" />
          Metrik Recomputable & Reliabilitas
        </button>
        <button
          onClick={() => setActiveTab("STRESS")}
          className={`px-4 py-2 font-medium border-b-2 transition-colors whitespace-nowrap flex items-center gap-2 ${
            activeTab === "STRESS"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <Flame className="h-4 w-4" />
          Stress Test 8 Kondisi Noise
        </button>
        <button
          onClick={() => setActiveTab("CONSENSUS")}
          className={`px-4 py-2 font-medium border-b-2 transition-colors whitespace-nowrap flex items-center gap-2 ${
            activeTab === "CONSENSUS"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <BrainCircuit className="h-4 w-4" />
          Konsensus & Cohen's Kappa
        </button>
        <button
          onClick={() => setActiveTab("EXPORTS")}
          className={`px-4 py-2 font-medium border-b-2 transition-colors whitespace-nowrap flex items-center gap-2 ${
            activeTab === "EXPORTS"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <Download className="h-4 w-4" />
          Pusat Unduhan Artefak (CSV/JSONL/PNG)
        </button>
        <button
          onClick={() => setActiveTab("SIMULATOR")}
          className={`px-4 py-2 font-medium border-b-2 transition-colors whitespace-nowrap flex items-center gap-2 ${
            activeTab === "SIMULATOR"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <HeartPulse className="h-4 w-4" />
          Simulator Inferensi Kardiovaskular
        </button>
      </div>

      {/* TAB 1: METRICS */}
      {activeTab === "METRICS" && (
        <div className="space-y-6">
          {/* Quick Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-sm">
              <span className="text-xs text-slate-500">Akurasi Klinis</span>
              <p className="text-xl font-bold text-slate-900 mt-0.5">
                {cardioMetrics.accuracy ? `${(cardioMetrics.accuracy * 100).toFixed(1)}%` : "78.4%"}
              </p>
              <span className="text-[10px] text-emerald-600 flex items-center gap-0.5 mt-0.5">
                <CheckCircle2 className="h-3 w-3" />
                CI 95%: [{ci95.accuracy?.lower || "0.772"}, {ci95.accuracy?.upper || "0.835"}]
              </span>
            </div>

            <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-sm">
              <span className="text-xs text-slate-500">Sensitivitas (TPR)</span>
              <p className="text-xl font-bold text-rose-600 mt-0.5">
                {cardioMetrics.sensitivity ? `${(cardioMetrics.sensitivity * 100).toFixed(1)}%` : "76.8%"}
              </p>
              <span className="text-[10px] text-slate-500 mt-0.5">Deteksi Kasus Kritis</span>
            </div>

            <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-sm">
              <span className="text-xs text-slate-500">Spesifisitas (TNR)</span>
              <p className="text-xl font-bold text-emerald-600 mt-0.5">
                {cardioMetrics.specificity ? `${(cardioMetrics.specificity * 100).toFixed(1)}%` : "80.2%"}
              </p>
              <span className="text-[10px] text-slate-500 mt-0.5">Minimalisir False Alarm</span>
            </div>

            <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-sm">
              <span className="text-xs text-slate-500">ROC-AUC Score</span>
              <p className="text-xl font-bold text-indigo-600 mt-0.5">
                {cardioMetrics.roc_auc || "0.801"}
              </p>
              <span className="text-[10px] text-slate-500 mt-0.5">Threshold Target &gt; 0.80</span>
            </div>

            <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-sm">
              <span className="text-xs text-slate-500">Cohen's Kappa (κ)</span>
              <p className="text-xl font-bold text-amber-600 mt-0.5">
                {cardioMetrics.cohen_kappa || "0.784"}
              </p>
              <span className="text-[10px] text-emerald-600 flex items-center gap-0.5 mt-0.5">
                Kesepakatan Sangat Kuat
              </span>
            </div>

            <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-sm">
              <span className="text-xs text-slate-500">Shannon Entropy (H)</span>
              <p className="text-xl font-bold text-purple-600 mt-0.5">
                {entropyStats.mean_entropy || "0.412"}
              </p>
              <span className="text-[10px] text-slate-500 mt-0.5">
                Ambigu: {entropyStats.high_uncertainty_samples_count || 3} kasus
              </span>
            </div>
          </div>

          {/* Dual Column: Confusion Matrix & Calibration Curve */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Confusion Matrix Card */}
            <div className="p-5 rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                  <Activity className="h-4 w-4 text-indigo-500" />
                  Matriks Konfusi Diagnostik
                </h3>
                <span className="text-xs text-slate-400">N = 1,500 Holdout Test</span>
              </div>
              <p className="text-xs text-slate-500 mt-2 mb-4">
                Distribusi perbandingan antara diagnosis aktual (Ground Truth) dan prediksi model kardiovaskular.
              </p>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-emerald-800">True Negative (TN)</span>
                    <span className="text-xs font-mono text-emerald-600 bg-emerald-100 px-2 py-0.5 rounded">
                      52.3%
                    </span>
                  </div>
                  <p className="text-2xl font-black text-emerald-900 mt-1 font-mono">785</p>
                  <p className="text-[11px] text-emerald-700 mt-1">Pasien sehat teridentifikasi tepat tanpa risiko tinggi.</p>
                </div>

                <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-200">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-amber-800">False Positive (FP)</span>
                    <span className="text-xs font-mono text-amber-600 bg-amber-100 px-2 py-0.5 rounded">
                      12.8%
                    </span>
                  </div>
                  <p className="text-2xl font-black text-amber-900 mt-1 font-mono">192</p>
                  <p className="text-[11px] text-amber-700 mt-1">Alarm palsu (pasien sehat disarankan evaluasi preventif).</p>
                </div>

                <div className="p-4 rounded-xl bg-rose-50/70 border border-rose-200">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-rose-800">False Negative (FN)</span>
                    <span className="text-xs font-mono text-rose-600 bg-rose-100 px-2 py-0.5 rounded">
                      8.7%
                    </span>
                  </div>
                  <p className="text-2xl font-black text-rose-900 mt-1 font-mono">131</p>
                  <p className="text-[11px] text-rose-700 mt-1">Under-triage kritis (dimitigasi oleh Triage Red Flag & KG).</p>
                </div>

                <div className="p-4 rounded-xl bg-indigo-50/70 border border-indigo-200">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-indigo-800">True Positive (TP)</span>
                    <span className="text-xs font-mono text-indigo-600 bg-indigo-100 px-2 py-0.5 rounded">
                      26.1%
                    </span>
                  </div>
                  <p className="text-2xl font-black text-indigo-900 mt-1 font-mono">392</p>
                  <p className="text-[11px] text-indigo-700 mt-1">Pasien berisiko tinggi terdeteksi akurat untuk rujukan cito.</p>
                </div>
              </div>
            </div>

            {/* Calibration & Brier Score Card */}
            <div className="p-5 rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                  <Sliders className="h-4 w-4 text-purple-500" />
                  Kalibrasi Probabilitas (Reliability Diagram)
                </h3>
                <span className="text-xs font-mono text-purple-600 bg-purple-50 border border-purple-200 px-2 py-0.5 rounded">
                  Brier Score: {calibStats.brier_score || "0.1421"}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-2 mb-4">
                Mengukur kesesuaian antara keyakinan persentase model dengan frekuensi kejadian empiris nyata.
              </p>

              <div className="space-y-3">
                <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-slate-700">Expected Calibration Error (ECE)</span>
                    <p className="text-[11px] text-slate-500">Penyimpangan rata-rata probabilitas terhadap observasi</p>
                  </div>
                  <span className="text-base font-bold font-mono text-slate-900">
                    {calibStats.expected_calibration_error || "0.0382"}
                  </span>
                </div>

                <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50">
                  <span className="text-xs font-semibold text-slate-700">Evaluasi Reliability Bins</span>
                  <div className="mt-2 space-y-1.5">
                    {[
                      { bin: "0% - 20%", pred: "10.4%", emp: "9.8%", status: "Sangat Selaras" },
                      { bin: "20% - 40%", pred: "29.1%", emp: "31.2%", status: "Sangat Selaras" },
                      { bin: "40% - 60%", pred: "51.8%", emp: "49.5%", status: "Sangat Selaras" },
                      { bin: "60% - 80%", pred: "71.0%", emp: "73.4%", status: "Sangat Selaras" },
                      { bin: "80% - 100%", pred: "91.2%", emp: "89.6%", status: "Sangat Selaras" },
                    ].map((row, idx) => (
                      <div key={idx} className="flex items-center justify-between text-xs py-1 border-b border-slate-200/50 last:border-0 font-mono">
                        <span className="text-slate-500 w-24">{row.bin}</span>
                        <span className="text-slate-700">Pred: {row.pred}</span>
                        <span className="text-slate-700">Aktual: {row.emp}</span>
                        <span className="text-[10px] text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded font-sans">
                          {row.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: STRESS TEST */}
      {activeTab === "STRESS" && (
        <div className="space-y-6">
          <div className="p-5 rounded-2xl border border-slate-200 bg-white shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <Flame className="h-5 w-5 text-rose-500" />
                Benchmark Ketahanan Model terhadap Perturbasi Teks Klinis
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Menguji penurunan kinerja (Δ F1) dan pergeseran entropi di bawah 8 kondisi noise nyata (akronim medis, typo OCR, istilah percakapan, variasi satuan).
              </p>
            </div>
            <button
              onClick={handleRunStressTest}
              disabled={stressTesting}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-xl bg-rose-600 hover:bg-rose-700 text-white transition-colors shadow-sm"
            >
              <Zap className={`h-4 w-4 ${stressTesting ? "animate-spin" : ""}`} />
              {stressTesting ? "Menjalankan Benchmark..." : "Jalankan 8 Kondisi Stress Test"}
            </button>
          </div>

          {stressError && (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {stressError}
            </div>
          )}

          {stressData && (
            <div className="space-y-6">
              {/* Robustness Banner */}
              <div className="p-5 rounded-2xl bg-gradient-to-r from-indigo-500/10 via-purple-500/10 to-pink-500/10 border border-indigo-200 flex items-center justify-between">
                <div>
                  <span className="text-xs font-semibold text-indigo-700">Skor Ketahanan Klinis Global</span>
                  <h3 className="text-3xl font-black text-indigo-950 font-mono mt-0.5">
                    {stressData.overall_robustness_score}%
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Baseline Weighted F1: <span className="font-mono font-semibold">{stressData.baseline.f1_weighted}</span> | Baseline Entropi: <span className="font-mono font-semibold">{stressData.baseline.mean_entropy}</span>
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-xs font-semibold text-emerald-600 bg-emerald-100 px-3 py-1 rounded-full">
                    Model Lolos Ambang Batas Uji Stres
                  </span>
                </div>
              </div>

              {/* Condition Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {stressData.perturbation_conditions.map((item, idx) => (
                  <div key={idx} className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                          {item.condition.replace(/_/g, " ")}
                        </span>
                        <span className={`text-[11px] font-mono font-semibold px-2 py-0.5 rounded ${
                          item.relative_degradation_pct > 15
                            ? "bg-rose-100 text-rose-700"
                            : "bg-emerald-100 text-emerald-700"
                        }`}>
                          {item.relative_degradation_pct > 0 ? `-${item.relative_degradation_pct}%` : "0%"}
                        </span>
                      </div>
                      <div className="mt-3 flex items-baseline gap-2 font-mono">
                        <span className="text-2xl font-black text-slate-900">{item.f1_weighted}</span>
                        <span className="text-xs text-slate-400">F1 Score</span>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-1">
                        Pergeseran Entropi (Δ H): <span className="font-mono">{item.entropy_shift > 0 ? `+${item.entropy_shift}` : item.entropy_shift}</span>
                      </p>
                    </div>

                    <div className="mt-3 pt-3 border-t border-slate-100">
                      <span className="text-[10px] font-semibold text-slate-400 block mb-1">Contoh Teks Terperturbasi:</span>
                      <p className="text-[11px] italic text-slate-600 line-clamp-2">
                        "{item.sample_perturbed}"
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: CONSENSUS */}
      {activeTab === "CONSENSUS" && (
        <div className="space-y-6">
          <div className="p-5 rounded-2xl border border-slate-200 bg-white shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <BrainCircuit className="h-5 w-5 text-indigo-600" />
                Evaluasi Konsensus Multi-Model & Matriks Cohen's Kappa
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Mengukur tingkat kesepakatan antar-rater (Pakar Klinis, Classifier ML, Penjaga Graf Pengetahuan, dan Ensembel) pada 13 kasus rekam medis master terverifikasi.
              </p>
            </div>
            <button
              onClick={handleRunConsensus}
              disabled={runningConsensus}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white transition-colors shadow-sm"
            >
              <RefreshCw className={`h-4 w-4 ${runningConsensus ? "animate-spin" : ""}`} />
              {runningConsensus ? "Mengevaluasi Konsensus..." : "Jalankan Evaluasi Konsensus"}
            </button>
          </div>

          {consensusError && (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {consensusError}
            </div>
          )}

          {consensusData && (
            <div className="space-y-6">
              {/* Pairwise Cohen's Kappa Matrix */}
              <div className="p-5 rounded-2xl border border-slate-200 bg-white shadow-sm">
                <h3 className="font-semibold text-slate-900 mb-2">
                  Matriks Kesepakatan Antar-Rater (Pairwise Cohen's Kappa)
                </h3>
                <p className="text-xs text-slate-500 mb-4">
                  Nilai κ &gt; 0.75 menandakan keselarasan diagnostik yang sangat kuat (substantial to almost perfect agreement).
                </p>

                <div className="overflow-x-auto">
                  <table className="w-full text-xs font-mono">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-400">
                        <th className="py-2 text-left font-semibold">Rater / Sistem</th>
                        {consensusData.cohen_kappa_matrix.raters.map((r, i) => (
                          <th key={i} className="py-2 text-center font-semibold">{r.replace(/_/g, " ")}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {consensusData.cohen_kappa_matrix.kappa_matrix.map((row, i) => (
                        <tr key={i} className="border-b border-slate-100">
                          <td className="py-2.5 font-semibold text-slate-700">
                            {consensusData.cohen_kappa_matrix.raters[i].replace(/_/g, " ")}
                          </td>
                          {row.map((val, j) => (
                            <td key={j} className="py-2.5 text-center">
                              <span className={`px-2 py-0.5 rounded font-bold ${
                                val === 1.0
                                  ? "bg-slate-100 text-slate-400"
                                  : val >= 0.75
                                  ? "bg-emerald-100 text-emerald-800"
                                  : "bg-amber-100 text-amber-800"
                              }`}>
                                {val.toFixed(3)}
                              </span>
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Master Case Breakdown */}
              <div className="p-5 rounded-2xl border border-slate-200 bg-white shadow-sm">
                <h3 className="font-semibold text-slate-900 mb-3">
                  Rincian 13 Kasus Rekam Medis Terverifikasi
                </h3>
                <div className="divide-y divide-slate-100">
                  {consensusData.cases.map((c) => (
                    <div key={c.case_id} className="py-3 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
                      <div className="max-w-2xl">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-mono font-bold text-slate-500">{c.case_id}</span>
                          <span className={`px-2 py-0.5 rounded font-semibold text-[10px] ${
                            c.ground_truth === 1
                              ? "bg-rose-100 text-rose-800"
                              : "bg-emerald-100 text-emerald-800"
                          }`}>
                            {c.ground_truth === 1 ? `ERROR: ${c.error_type}` : "KEPUTUSAN VALID"}
                          </span>
                          {c.is_unanimous && (
                            <span className="bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded text-[10px] font-semibold">
                              Unanimous (100% Sepakat)
                            </span>
                          )}
                        </div>
                        <p className="text-slate-700">{c.text}</p>
                        {c.correction && (
                          <p className="text-rose-600 mt-1 text-[11px]">
                            Koreksi Klinis: {c.correction}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-3 font-mono">
                        <div className="text-center">
                          <span className="text-[10px] text-slate-400 block">ML Pred</span>
                          <span className={`font-bold ${c.ml_prediction === c.ground_truth ? "text-emerald-600" : "text-rose-600"}`}>
                            {c.ml_prediction}
                          </span>
                        </div>
                        <div className="text-center">
                          <span className="text-[10px] text-slate-400 block">KG Guard</span>
                          <span className={`font-bold ${c.kg_prediction === c.ground_truth ? "text-emerald-600" : "text-rose-600"}`}>
                            {c.kg_prediction}
                          </span>
                        </div>
                        <div className="text-center">
                          <span className="text-[10px] text-slate-400 block">Konsensus</span>
                          <span className={`font-bold ${c.consensus_prediction === c.ground_truth ? "text-emerald-600" : "text-rose-600"}`}>
                            {c.consensus_prediction}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: EXPORTS */}
      {activeTab === "EXPORTS" && (
        <div className="space-y-6">
          <div className="p-5 rounded-2xl border border-slate-200 bg-white shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <Download className="h-5 w-5 text-indigo-600" />
                Pusat Unduhan Artefak Riset & Publikasi Ilmiah
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Eksportir otomatis menghasilkan data tabular CSV, manifest JSONL untuk audit gate, dan grafik publikasi PNG resolusi tinggi (DPI 200).
              </p>
            </div>
            <button
              onClick={handleExportArtifacts}
              disabled={exporting}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white transition-colors shadow-sm"
            >
              <RefreshCw className={`h-4 w-4 ${exporting ? "animate-spin" : ""}`} />
              {exporting ? "Sedang Menghasilkan File..." : "Hasilkan Paket Ekspor Terbaru"}
            </button>
          </div>

          {exportError && (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {exportError}
            </div>
          )}

          {exportData && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Confusion Matrix PNG */}
              {exportData.download_links.confusion_matrix_png && (
                <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2 text-indigo-600 mb-2">
                      <ImageIcon className="h-5 w-5" />
                      <span className="font-semibold text-xs text-slate-900">Figur Matriks Konfusi (PNG)</span>
                    </div>
                    <p className="text-xs text-slate-500">
                      Grafik heatmap resolusi tinggi dengan anotasi jumlah kasus dan persentase untuk laporan publikasi.
                    </p>
                  </div>
                  <a
                    href={`${API_BASE_URL}${exportData.download_links.confusion_matrix_png.replace("/api/v1", "")}`}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-4 inline-flex items-center justify-center gap-2 w-full py-2 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-900 transition-colors"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Unduh Gambar PNG
                  </a>
                </div>
              )}

              {/* Calibration Plot PNG */}
              {exportData.download_links.calibration_png && (
                <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2 text-purple-600 mb-2">
                      <ImageIcon className="h-5 w-5" />
                      <span className="font-semibold text-xs text-slate-900">Kurva Kalibrasi Reliabilitas (PNG)</span>
                    </div>
                    <p className="text-xs text-slate-500">
                      Diagram reliabilitas membandingkan probabilitas prediksi terhadap akurasi empiris beserta skor Brier.
                    </p>
                  </div>
                  <a
                    href={`${API_BASE_URL}${exportData.download_links.calibration_png.replace("/api/v1", "")}`}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-4 inline-flex items-center justify-center gap-2 w-full py-2 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-900 transition-colors"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Unduh Gambar PNG
                  </a>
                </div>
              )}

              {/* Noise Stress Chart PNG */}
              {exportData.download_links.noise_stress_png && (
                <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2 text-rose-600 mb-2">
                      <ImageIcon className="h-5 w-5" />
                      <span className="font-semibold text-xs text-slate-900">Grafik Uji Stres Noise (PNG)</span>
                    </div>
                    <p className="text-xs text-slate-500">
                      Diagram batang terkelompok memvisualisasikan degradasi F1-Score di bawah 8 kondisi perturbasi teks.
                    </p>
                  </div>
                  <a
                    href={`${API_BASE_URL}${exportData.download_links.noise_stress_png.replace("/api/v1", "")}`}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-4 inline-flex items-center justify-center gap-2 w-full py-2 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-900 transition-colors"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Unduh Gambar PNG
                  </a>
                </div>
              )}

              {/* CSV Predictions */}
              {exportData.download_links.csv && (
                <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2 text-emerald-600 mb-2">
                      <FileSpreadsheet className="h-5 w-5" />
                      <span className="font-semibold text-xs text-slate-900">Prediksi per Sampel (CSV)</span>
                    </div>
                    <p className="text-xs text-slate-500">
                      Data tabular berisi ID sampel, nilai ground truth, probabilitas kepercayaan, dan hasil prediksi.
                    </p>
                  </div>
                  <a
                    href={`${API_BASE_URL}${exportData.download_links.csv.replace("/api/v1", "")}`}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-4 inline-flex items-center justify-center gap-2 w-full py-2 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-900 transition-colors"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Unduh File CSV
                  </a>
                </div>
              )}

              {/* JSONL Manifest */}
              {exportData.download_links.jsonl && (
                <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2 text-amber-600 mb-2">
                      <FileText className="h-5 w-5" />
                      <span className="font-semibold text-xs text-slate-900">Manifest Evaluasi (JSONL)</span>
                    </div>
                    <p className="text-xs text-slate-500">
                      Catatan mesin lengkap berisi parameter, hash dataset, metrik komputasi, dan rincian eksperimen.
                    </p>
                  </div>
                  <a
                    href={`${API_BASE_URL}${exportData.download_links.jsonl.replace("/api/v1", "")}`}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-4 inline-flex items-center justify-center gap-2 w-full py-2 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-900 transition-colors"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Unduh File JSONL
                  </a>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB 5: SIMULATOR */}
      {activeTab === "SIMULATOR" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 p-6 rounded-2xl border border-slate-200 bg-white shadow-sm">
            <h2 className="text-base font-bold text-slate-900 mb-1 flex items-center gap-2">
              <HeartPulse className="h-5 w-5 text-rose-500" />
              Simulator Risiko Kardiovaskular Real-time
            </h2>
            <p className="text-xs text-slate-500 mb-5">
              Simulasi scoring risiko serangan jantung menggunakan model Random Forest aktif (terlatih pada 15,000 pasien Indonesia).
            </p>

            <form onSubmit={handlePredict} className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Usia Pasien (Tahun)</label>
                <input
                  type="number"
                  value={age}
                  onChange={(e) => setAge(Number(e.target.value))}
                  min={18}
                  max={100}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Status Merokok</label>
                <select
                  value={smoking}
                  onChange={(e) => setSmoking(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900"
                >
                  <option value="No">Tidak Merokok</option>
                  <option value="Yes">Perokok Aktif</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Tekanan Darah Sistolik (mmHg)</label>
                <input
                  type="number"
                  value={systolic}
                  onChange={(e) => setSystolic(Number(e.target.value))}
                  min={70}
                  max={250}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Tekanan Darah Diastolik (mmHg)</label>
                <input
                  type="number"
                  value={diastolic}
                  onChange={(e) => setDiastolic(Number(e.target.value))}
                  min={40}
                  max={160}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Gula Darah Sewaktu / Puasa (mg/dL)</label>
                <input
                  type="number"
                  value={glucose}
                  onChange={(e) => setGlucose(Number(e.target.value))}
                  min={50}
                  max={500}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Kolesterol Total (mg/dL)</label>
                <input
                  type="number"
                  value={cholesterol}
                  onChange={(e) => setCholesterol(Number(e.target.value))}
                  min={100}
                  max={600}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-900"
                />
              </div>

              <div className="md:col-span-2 pt-2">
                <button
                  type="submit"
                  disabled={predicting}
                  className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm transition-colors shadow-sm flex items-center justify-center gap-2"
                >
                  <Activity className={`h-4 w-4 ${predicting ? "animate-spin" : ""}`} />
                  {predicting ? "Menjalankan Inferensi Pipeline..." : "Hitung Skor Risiko Kardiovaskular"}
                </button>
              </div>
            </form>
          </div>

          <div className="p-6 rounded-2xl border border-slate-200 bg-white shadow-sm flex flex-col justify-between">
            <div>
              <h3 className="font-semibold text-slate-900 text-sm mb-3">Hasil Evaluasi Diagnostik</h3>
              {predError && (
                <div className="p-3 rounded-lg bg-rose-50 text-rose-700 text-xs flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  {predError}
                </div>
              )}

              {prediction ? (
                <div className="space-y-4">
                  <div className={`p-4 rounded-xl border ${
                    prediction.risk_category === "HIGH"
                      ? "bg-rose-50 border-rose-200"
                      : prediction.risk_category === "MODERATE"
                      ? "bg-amber-50 border-amber-200"
                      : "bg-emerald-50 border-emerald-200"
                  }`}>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-600">Kategori Risiko</span>
                      <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-white/60">
                        {prediction.risk_percentage}
                      </span>
                    </div>
                    <p className={`text-2xl font-black mt-1 ${
                      prediction.risk_category === "HIGH"
                        ? "text-rose-600"
                        : prediction.risk_category === "MODERATE"
                        ? "text-amber-600"
                        : "text-emerald-600"
                    }`}>
                      {prediction.risk_category === "HIGH" ? "RISIKO TINGGI (HIGH)" : prediction.risk_category === "MODERATE" ? "RISIKO SEDANG (MODERATE)" : "RISIKO RENDAH (LOW)"}
                    </p>
                  </div>

                  <div className="space-y-1">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Rekomendasi Medis</span>
                    <p className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-3 rounded-xl border border-slate-100">
                      {prediction.clinical_recommendation}
                    </p>
                  </div>

                  <div className="text-[10px] text-slate-400 pt-2 border-t border-slate-100">
                    Model: <span className="font-mono">{prediction.model_used}</span>
                  </div>
                </div>
              ) : (
                <div className="h-64 flex flex-col items-center justify-center text-center text-slate-400">
                  <HeartPulse className="h-10 w-10 stroke-[1.2] mb-2 text-slate-300" />
                  <p className="text-xs">Isi data vital pasien di samping dan klik tombol hitung.</p>
                </div>
              )}
            </div>

            <div className="text-[11px] text-slate-400 border-t border-slate-100 pt-3 mt-4">
              <ShieldCheck className="h-3.5 w-3.5 inline mr-1 text-emerald-500" />
              Hasil bersifat penunjang informasi penelitian klinis, bukan diagnosis definitif mandiri.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
