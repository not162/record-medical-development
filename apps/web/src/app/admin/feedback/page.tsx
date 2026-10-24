"use client";

import React, { useState, useEffect, useCallback } from "react";
import { 
  ThumbsUp, ThumbsDown, Download, RefreshCw, 
  Search, CheckCircle2, AlertCircle, Edit3, MessageSquare, Sparkles, X, User
} from "lucide-react";

interface FeedbackItem {
  id: string;
  user_id: string;
  username: string;
  user_fullname: string;
  session_id: string;
  message_id: string;
  feedback_type: "LIKE" | "DISLIKE";
  reward_rate: number;
  base_score: number;
  adjusted_score: number;
  model_version: string;
  notes: string | null;
  created_at: string;
  assistant_content: string;
  user_prompt: string;
}

interface FeedbackSummary {
  total_feedbacks: number;
  likes: number;
  dislikes: number;
  satisfaction_ratio: number;
  mean_adjusted_score: number;
  reward_formula: string;
  reward_rates: {
    LIKE: string;
    DISLIKE: string;
  };
}

export default function AdminFeedbackPage() {
  const [feedbacks, setFeedbacks] = useState<FeedbackItem[]>([]);
  const [summary, setSummary] = useState<FeedbackSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [exporting, setExporting] = useState(false);
  const [exportResult, setExportResult] = useState<{ count: number; filename: string; url: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Review modal state
  const [selectedFeedback, setSelectedFeedback] = useState<FeedbackItem | null>(null);
  const [editNotes, setEditNotes] = useState("");
  const [savingNote, setSavingNote] = useState(false);

  const fetchFeedbackData = useCallback(async () => {
    setLoading(true);
    setError(null);
    const token = localStorage.getItem("clinical_token");
    if (!token) return;

    try {
      const url = filterType === "ALL" 
        ? "http://127.0.0.1:8000/api/v1/admin/feedback" 
        : `http://127.0.0.1:8000/api/v1/admin/feedback?feedback_type=${filterType}`;

      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setFeedbacks(data.records || []);
        setSummary(data.summary || null);
      } else {
        setError("Gagal memuat riwayat umpan balik.");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [filterType]);

  useEffect(() => {
    let ignore = false;
    const run = async () => {
      const token = localStorage.getItem("clinical_token");
      if (!token) return;
      try {
        const url = filterType === "ALL" 
          ? "http://127.0.0.1:8000/api/v1/admin/feedback" 
          : `http://127.0.0.1:8000/api/v1/admin/feedback?feedback_type=${filterType}`;
        const res = await fetch(url, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok && !ignore) {
          const data = await res.json();
          setFeedbacks(data.records || []);
          setSummary(data.summary || null);
          setLoading(false);
        }
      } catch {
        if (!ignore) setLoading(false);
      }
    };
    run();
    return () => {
      ignore = true;
    };
  }, [filterType]);

  const handleExportDPO = async () => {
    setExporting(true);
    const token = localStorage.getItem("clinical_token");
    if (!token) return;

    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/admin/feedback/export-preference", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setExportResult({
          count: data.total_preference_pairs,
          filename: data.filename,
          url: `http://127.0.0.1:8000${data.download_url}`
        });

        // Trigger direct browser download
        const dlRes = await fetch(`http://127.0.0.1:8000${data.download_url}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (dlRes.ok) {
          const blob = await dlRes.blob();
          const downloadUrl = window.URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = downloadUrl;
          a.download = data.filename;
          document.body.appendChild(a);
          a.click();
          a.remove();
        }
      } else {
        alert("Gagal mengekspor pasangan preferensi DPO.");
      }
    } catch (err: unknown) {
      alert(`Error export: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setExporting(false);
    }
  };

  const handleSaveNotes = async () => {
    if (!selectedFeedback) return;
    setSavingNote(true);
    const token = localStorage.getItem("clinical_token");
    if (!token) return;

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/admin/feedback/${selectedFeedback.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ notes: editNotes })
      });
      if (res.ok) {
        setSelectedFeedback(null);
        fetchFeedbackData();
      } else {
        alert("Gagal menyimpan catatan auditor.");
      }
    } catch (err: unknown) {
      alert(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setSavingNote(false);
    }
  };

  const filteredFeedbacks = feedbacks.filter((fb) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      fb.username.toLowerCase().includes(q) ||
      fb.user_prompt.toLowerCase().includes(q) ||
      fb.assistant_content.toLowerCase().includes(q) ||
      (fb.notes && fb.notes.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <ThumbsUp className="w-6 h-6 text-emerald-600" />
            <span>Tinjauan Umpan Balik Dokter & Reward Scoring</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Pengawasan kurasi kualitas klinis: formula reward Like (+1.75%) & Dislike (-0.74%) untuk pipeline preferensi offline (RLHF / DPO).
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchFeedbackData}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-xs text-slate-700 font-medium transition shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-emerald-600" : ""}`} />
            <span>Segarkan</span>
          </button>

          <button
            onClick={handleExportDPO}
            disabled={exporting || feedbacks.length === 0}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs text-white font-medium shadow-sm transition disabled:opacity-50"
          >
            <Download className="w-3.5 h-3.5" />
            <span>{exporting ? "Mengekspor..." : "Ekspor Pasangan Preferensi DPO (.jsonl)"}</span>
          </button>
        </div>
      </div>

      {/* Metrics Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-500 text-xs">
              <span>Total Umpan Balik</span>
              <MessageSquare className="w-4 h-4 text-sky-600" />
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-2">
              {summary.total_feedbacks}
            </div>
            <div className="text-[11px] text-slate-500 mt-1">
              {summary.likes} Like vs {summary.dislikes} Dislike
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-500 text-xs">
              <span>Tingkat Kepuasan (Like Ratio)</span>
              <ThumbsUp className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="text-2xl font-bold text-emerald-700 mt-2">
              {(summary.satisfaction_ratio * 100).toFixed(1)}%
            </div>
            <div className="text-[11px] text-slate-500 mt-1">
              Rasio respons positif dokter & pasien
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-500 text-xs">
              <span>Rata-rata Skor Reward</span>
              <Sparkles className="w-4 h-4 text-purple-600" />
            </div>
            <div className="text-2xl font-bold text-purple-700 mt-2">
              {summary.mean_adjusted_score.toFixed(4)}
            </div>
            <div className="text-[11px] text-slate-500 mt-1">
              Base score: 0.5000 (Skala 0.0 - 1.0)
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-500 text-xs">
              <span>Formula Penyesuaian</span>
              <CheckCircle2 className="w-4 h-4 text-amber-600" />
            </div>
            <div className="text-xs font-semibold text-amber-800 mt-2">
              Like: +1.75% | Dislike: -0.74%
            </div>
            <div className="text-[10px] text-slate-500 mt-1 font-mono">
              clamp(base * (1 + r), 0, 1)
            </div>
          </div>
        </div>
      )}

      {/* Export Success Notification Banner */}
      {exportResult && (
        <div className="p-3.5 rounded-xl border border-emerald-200 bg-emerald-50 text-emerald-800 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>
              Berhasil mengekspor <strong>{exportResult.count}</strong> pasangan preferensi DPO ke berkas <code>{exportResult.filename}</code>. File otomatis diunduh ke browser Anda.
            </span>
          </div>
          <button 
            onClick={() => setExportResult(null)}
            className="text-slate-400 hover:text-slate-600"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Filters and Search Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Cari prompt, respons, atau dokter..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-white border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-500 w-64 md:w-80 shadow-sm"
            />
          </div>

          <div className="flex items-center gap-1 bg-white border border-slate-200 p-0.5 rounded-lg text-xs shadow-sm">
            <button
              onClick={() => setFilterType("ALL")}
              className={`px-2.5 py-1 rounded-md transition ${filterType === "ALL" ? "bg-slate-100 text-slate-900 font-medium" : "text-slate-500 hover:text-slate-700"}`}
            >
              Semua
            </button>
            <button
              onClick={() => setFilterType("LIKE")}
              className={`px-2.5 py-1 rounded-md transition flex items-center gap-1 ${filterType === "LIKE" ? "bg-emerald-50 text-emerald-800 border border-emerald-200 font-medium" : "text-slate-500 hover:text-slate-700"}`}
            >
              <ThumbsUp className="w-3 h-3 text-emerald-600" />
              <span>Like (+1.75%)</span>
            </button>
            <button
              onClick={() => setFilterType("DISLIKE")}
              className={`px-2.5 py-1 rounded-md transition flex items-center gap-1 ${filterType === "DISLIKE" ? "bg-rose-50 text-rose-800 border border-rose-200 font-medium" : "text-slate-500 hover:text-slate-700"}`}
            >
              <ThumbsDown className="w-3 h-3 text-rose-600" />
              <span>Dislike (-0.74%)</span>
            </button>
          </div>
        </div>

        <div className="text-xs text-slate-500">
          Menampilkan {filteredFeedbacks.length} dari {feedbacks.length} riwayat feedback
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-16 text-center text-slate-500 text-xs flex flex-col items-center gap-2">
            <RefreshCw className="w-5 h-5 animate-spin text-emerald-600" />
            <span>Memuat basis data umpan balik klinis...</span>
          </div>
        ) : error ? (
          <div className="py-16 text-center text-rose-600 text-xs flex flex-col items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        ) : filteredFeedbacks.length === 0 ? (
          <div className="py-16 text-center text-slate-500 text-xs">
            Tidak ada riwayat umpan balik yang cocok dengan filter.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-[10px] tracking-wider">
                  <th className="py-3 px-4">Waktu</th>
                  <th className="py-3 px-4">Pengguna / Dokter</th>
                  <th className="py-3 px-4">Prompt Pasien</th>
                  <th className="py-3 px-4">Respons AI</th>
                  <th className="py-3 px-4">Tipe & Reward</th>
                  <th className="py-3 px-4">Skor Akhir</th>
                  <th className="py-3 px-4">Catatan Reviewer</th>
                  <th className="py-3 px-4 text-right">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredFeedbacks.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50 transition">
                    <td className="py-3 px-4 text-slate-500 whitespace-nowrap font-mono text-[11px]">
                      {new Date(item.created_at).toLocaleString("id-ID", {
                        day: "2-digit",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit"
                      })}
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-1.5 text-slate-900 font-medium">
                        <User className="w-3.5 h-3.5 text-slate-400" />
                        <span>{item.user_fullname}</span>
                      </div>
                      <div className="text-[10px] text-slate-500">@{item.username}</div>
                    </td>

                    <td className="py-3 px-4 max-w-xs">
                      <p className="line-clamp-2 text-slate-700 text-xs font-serif">
                        &quot;{item.user_prompt || "Konsultasi Klinis"}&quot;
                      </p>
                    </td>

                    <td className="py-3 px-4 max-w-sm">
                      <p className="line-clamp-2 text-slate-600 text-xs font-mono">
                        {item.assistant_content}
                      </p>
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap">
                      {item.feedback_type === "LIKE" ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <ThumbsUp className="w-3 h-3 text-emerald-600" />
                          <span>LIKE (+1.75%)</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                          <ThumbsDown className="w-3 h-3 text-rose-600" />
                          <span>DISLIKE (-0.74%)</span>
                        </span>
                      )}
                    </td>

                    <td className="py-3 px-4 font-mono font-bold whitespace-nowrap">
                      <span className={item.adjusted_score >= 0.5 ? "text-emerald-700" : "text-rose-700"}>
                        {item.adjusted_score.toFixed(4)}
                      </span>
                    </td>

                    <td className="py-3 px-4 max-w-xs">
                      {item.notes ? (
                        <span className="text-slate-700 text-[11px] bg-slate-50 px-2 py-1 rounded border border-slate-200 block truncate">
                          {item.notes}
                        </span>
                      ) : (
                        <span className="text-slate-400 italic text-[11px]">Belum ada catatan</span>
                      )}
                    </td>

                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <button
                        onClick={() => {
                          setSelectedFeedback(item);
                          setEditNotes(item.notes || "");
                        }}
                        className="p-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 shadow-sm transition"
                        title="Tinjau & Tambah Catatan Dokter"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Review & Notes Modal */}
      {selectedFeedback && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
                <Edit3 className="w-4 h-4 text-emerald-600" />
                <span>Review & Catatan Auditor Klinis</span>
              </h3>
              <button
                onClick={() => setSelectedFeedback(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-500 block mb-1 font-medium">Prompt Pertanyaan Pasien:</label>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-700">
                  {selectedFeedback.user_prompt || "Konsultasi Klinis"}
                </div>
              </div>

              <div>
                <label className="text-slate-500 block mb-1 font-medium">Respons Asisten AI:</label>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 max-h-32 overflow-y-auto">
                  {selectedFeedback.assistant_content}
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 flex-1">
                  <span className="text-slate-500 block text-[10px]">Tipe Feedback</span>
                  <span className={`font-bold ${selectedFeedback.feedback_type === "LIKE" ? "text-emerald-700" : "text-rose-700"}`}>
                    {selectedFeedback.feedback_type} ({selectedFeedback.reward_rate > 0 ? "+1.75%" : "-0.74%"})
                  </span>
                </div>

                <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 flex-1">
                  <span className="text-slate-500 block text-[10px]">Adjusted Score</span>
                  <span className="font-bold text-slate-900 font-mono">
                    {selectedFeedback.adjusted_score.toFixed(4)}
                  </span>
                </div>
              </div>

              <div>
                <label className="text-slate-700 block mb-1 font-medium">Catatan Koreksi / Justifikasi Klinis Dokter:</label>
                <textarea
                  rows={4}
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  placeholder="Contoh: Respons tepat, sitasi SPO Pulmonologi RSUKT akurat. Layak dijadikan sampel chosen preferensi DPO."
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-500 focus:bg-white transition"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setSelectedFeedback(null)}
                className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-xs text-slate-700 font-medium transition"
              >
                Batal
              </button>
              <button
                type="button"
                onClick={handleSaveNotes}
                disabled={savingNote}
                className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs text-white font-medium shadow-sm transition disabled:opacity-50"
              >
                {savingNote ? "Menyimpan..." : "Simpan Catatan Auditor"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
