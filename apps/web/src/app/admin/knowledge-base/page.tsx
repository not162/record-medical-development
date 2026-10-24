"use client";

import React, { useState, useEffect } from "react";
import { BookOpen, Search, RefreshCw, BarChart2, ShieldCheck, Database, Layers, CheckCircle2 } from "lucide-react";

interface RAGStatus {
  status: string;
  approved_dataset_records: number;
  pending_dataset_records: number;
  fts5_indexed_chunks: number;
  sqlite_vec_indexed_chunks: number;
  embedding_dimensions: number;
  retrieval_method: string;
}

interface EvidenceChunk {
  chunk_id: string;
  doc_id: string;
  title: string;
  department: string;
  excerpt: string;
  relevance_score: number;
  approval_status: string;
}

interface EvalResult {
  mean_metrics: {
    "Precision@3": number;
    "Recall@3": number;
    "MRR": number;
    "nDCG@3": number;
  };
  benchmark_cases_evaluated: number;
}

export default function AdminKnowledgeBasePage() {
  const [statusData, setStatusData] = useState<RAGStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [evalResult, setEvalResult] = useState<EvalResult | null>(null);
  const [searchQuery, setSearchQuery] = useState("terapi lini pertama asma akut sesak napas");
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<EvidenceChunk[]>([]);
  const [notification, setNotification] = useState<string | null>(null);

  const fetchStatus = async () => {
    setLoadingStatus(true);
    const token = localStorage.getItem("clinical_token");
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/admin/rag/status", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setStatusData(data);
      }
    } catch {
      // offline / mock fallback display
    } finally {
      setLoadingStatus(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleTriggerIndex = async () => {
    setIndexing(true);
    setNotification(null);
    const token = localStorage.getItem("clinical_token");
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/admin/rag/index", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setNotification(`Berhasil mengindeks ${data.indexed_chunks_count} potongan dokumen ke FTS5 & sqlite-vec!`);
        fetchStatus();
      }
    } catch {
      setNotification("Gagal menghubungi backend indexing.");
    } finally {
      setIndexing(false);
    }
  };

  const handleEvaluate = async () => {
    setEvaluating(true);
    const token = localStorage.getItem("clinical_token");
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/admin/rag/evaluate", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setEvalResult(data);
      }
    } catch {
      // ignore
    } finally {
      setEvaluating(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    const token = localStorage.getItem("clinical_token");
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/rag/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ query: searchQuery, top_k: 4 })
      });
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data.evidence_context || []);
      }
    } catch {
      // ignore
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="pb-4 border-b border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <BookOpen className="w-6 h-6 text-emerald-600" />
            <span>Indeks Pengetahuan Medis (RAG Engine)</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Mesin pencarian semantik hibrida FTS5 (BM25) + sqlite-vec (Dense 384-d) dengan fusi Reciprocal Rank Fusion (RRF).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchStatus}
            disabled={loadingStatus}
            className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium flex items-center gap-1.5 transition-colors shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingStatus ? "animate-spin text-emerald-600" : ""}`} />
            <span>Segarkan</span>
          </button>
          <button
            onClick={handleTriggerIndex}
            disabled={indexing}
            className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-sm"
          >
            <Database className="w-3.5 h-3.5" />
            <span>{indexing ? "Mengindeks..." : "Picu Re-Indexing RAG"}</span>
          </button>
        </div>
      </div>

      {notification && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          <span>{notification}</span>
        </div>
      )}

      {/* RAG Status Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-2">
            <span>Rekam Disetujui (Approved)</span>
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900">{statusData?.approved_dataset_records ?? 0}</div>
          <div className="text-[10px] text-slate-500 mt-1">Hanya dokumen disetujui yang dapat diindeks</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-2">
            <span>FTS5 BM25 Sparse Chunks</span>
            <Search className="w-4 h-4 text-cyan-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900">{statusData?.fts5_indexed_chunks ?? 0}</div>
          <div className="text-[10px] text-slate-500 mt-1">Tokenizer unicode61 remove_diacritics</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-2">
            <span>sqlite-vec Dense Chunks</span>
            <Layers className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900">{statusData?.sqlite_vec_indexed_chunks ?? 0}</div>
          <div className="text-[10px] text-slate-500 mt-1">Vektor 384 Dimensi, L2 Normalized</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 text-xs mb-2">
            <span>Metode Fusi RAG</span>
            <BarChart2 className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-sm font-semibold text-slate-900">RRF (k=60)</div>
          <div className="text-[10px] text-slate-500 mt-1">Fusi peringkat Sparse + Dense</div>
        </div>
      </div>

      {/* Retrieval Evaluation Benchmarking */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-emerald-600" />
              <span>Evaluasi Kualitas Pencarian (Retrieval Benchmark)</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">Uji coba terstandarisasi menghitung Recall@3, Precision@3, MRR, dan nDCG@3.</p>
          </div>
          <button
            onClick={handleEvaluate}
            disabled={evaluating}
            className="px-3.5 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium transition-colors shadow-sm"
          >
            {evaluating ? "Mengevaluasi..." : "Jalankan Benchmark"}
          </button>
        </div>

        {evalResult && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t border-slate-100">
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-center">
              <span className="text-slate-500 text-xs block">Precision@3</span>
              <span className="text-lg font-bold text-emerald-700">{evalResult.mean_metrics["Precision@3"]}</span>
            </div>
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-center">
              <span className="text-slate-500 text-xs block">Recall@3</span>
              <span className="text-lg font-bold text-cyan-700">{evalResult.mean_metrics["Recall@3"]}</span>
            </div>
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-center">
              <span className="text-slate-500 text-xs block">MRR</span>
              <span className="text-lg font-bold text-indigo-700">{evalResult.mean_metrics["MRR"]}</span>
            </div>
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-center">
              <span className="text-slate-500 text-xs block">nDCG@3</span>
              <span className="text-lg font-bold text-amber-700">{evalResult.mean_metrics["nDCG@3"]}</span>
            </div>
          </div>
        )}
      </div>

      {/* Interactive RAG Search Sandbox */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
            <Search className="w-4 h-4 text-cyan-600" />
            <span>Uji Coba Sandbox Pencarian Semantik</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">Uji pengambilan potongan bukti (evidence chunks) secara real-time.</p>
        </div>

        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Masukkan pertanyaan klinis (contoh: tatalaksana infark miokard akut)..."
            className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-500 focus:bg-white transition"
          />
          <button
            type="submit"
            disabled={searching}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 transition-colors shadow-sm"
          >
            <Search className="w-3.5 h-3.5" />
            <span>{searching ? "Mencari..." : "Cari Bukti"}</span>
          </button>
        </form>

        {searchResults.length > 0 && (
          <div className="space-y-3 pt-2">
            <div className="text-xs font-semibold text-slate-700">Hasil Potongan Bukti Terverifikasi ({searchResults.length}):</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {searchResults.map((chunk, idx) => (
                <div key={idx} className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-semibold text-emerald-700">{chunk.doc_id}</span>
                    <span className="px-2 py-0.5 rounded-full bg-white border border-slate-200 text-slate-700 text-[10px] font-mono shadow-sm">
                      Skor RRF: {chunk.relevance_score}
                    </span>
                  </div>
                  <div className="text-xs text-slate-700 line-clamp-3 leading-relaxed">{chunk.excerpt}</div>
                  <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-200">
                    <span>Spesialisasi: {chunk.department}</span>
                    <span className="text-emerald-700 font-semibold">Status: {chunk.approval_status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
