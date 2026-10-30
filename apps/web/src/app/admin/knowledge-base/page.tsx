"use client";

import React, { useState, useEffect } from "react";
import { BookOpen, Search, RefreshCw, BarChart2, ShieldCheck, Database, Layers, CheckCircle2, AlertCircle, Plus, Pencil, Trash2, X } from "lucide-react";
import { API_BASE_URL, api, type KnowledgeDoc, type KnowledgeInput } from "@/lib/api";

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

const EMPTY_FORM: KnowledgeInput = {
  title: "",
  department: "",
  content: "",
  source: "",
  approval_status: "APPROVED",
};

export default function AdminKnowledgeBasePage() {
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [docsLoading, setDocsLoading] = useState(true);
  const [crudError, setCrudError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<KnowledgeInput>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [reindexing, setReindexing] = useState(false);
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
      const res = await fetch(`${API_BASE_URL}/admin/rag/status`, {
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
    let ignore = false;
    const run = async () => {
      const token = localStorage.getItem("clinical_token");
      try {
        const res = await fetch(`${API_BASE_URL}/admin/rag/status`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok && !ignore) {
          const data = await res.json();
          setStatusData(data);
        }
      } catch {
        // offline / mock fallback display
      }
    };
    run();
    return () => {
      ignore = true;
    };
  }, []);

  const loadDocs = async () => {
    setDocsLoading(true);
    try {
      const data = await api.admin.listKnowledge();
      setDocs(Array.isArray(data) ? data : data.items || []);
      setCrudError(null);
    } catch (err: unknown) {
      setCrudError(err instanceof Error ? err.message : "Gagal memuat dokumen pengetahuan.");
    } finally {
      setDocsLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    api.admin
      .listKnowledge()
      .then((data) => {
        if (!ignore) setDocs(Array.isArray(data) ? data : data.items || []);
      })
      .catch((err: unknown) => {
        if (!ignore) setCrudError(err instanceof Error ? err.message : "Gagal memuat dokumen pengetahuan.");
      })
      .finally(() => {
        if (!ignore) setDocsLoading(false);
      });
    return () => {
      ignore = true;
    };
  }, []);

  const openCreate = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setCrudError(null);
    setShowForm(true);
  };

  const openEdit = (d: KnowledgeDoc) => {
    setEditingId(d.id);
    setForm({
      title: d.title,
      department: d.department,
      content: d.content,
      source: d.source || "",
      approval_status: d.approval_status,
    });
    setCrudError(null);
    setShowForm(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setCrudError(null);
    try {
      const payload: KnowledgeInput = { ...form, source: form.source?.trim() || null };
      if (editingId) {
        await api.admin.updateKnowledge(editingId, payload);
        setNotification("Dokumen pengetahuan berhasil diperbarui.");
      } else {
        await api.admin.createKnowledge(payload);
        setNotification("Dokumen pengetahuan berhasil ditambahkan.");
      }
      setShowForm(false);
      await loadDocs();
      fetchStatus();
    } catch (err: unknown) {
      setCrudError(err instanceof Error ? err.message : "Gagal menyimpan dokumen.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (d: KnowledgeDoc) => {
    if (!window.confirm(`Hapus dokumen "${d.title}"? Tindakan ini tidak dapat dibatalkan.`)) return;
    setCrudError(null);
    try {
      await api.admin.deleteKnowledge(d.id);
      setNotification("Dokumen pengetahuan dihapus.");
      await loadDocs();
      fetchStatus();
    } catch (err: unknown) {
      setCrudError(err instanceof Error ? err.message : "Gagal menghapus dokumen.");
    }
  };

  const handleReindexDocs = async () => {
    setReindexing(true);
    setCrudError(null);
    try {
      await api.admin.reindexKnowledge();
      setNotification("Re-indexing dokumen pengetahuan selesai.");
      fetchStatus();
    } catch (err: unknown) {
      setCrudError(err instanceof Error ? err.message : "Gagal melakukan re-indexing.");
    } finally {
      setReindexing(false);
    }
  };

  const handleTriggerIndex = async () => {
    setIndexing(true);
    setNotification(null);
    const token = localStorage.getItem("clinical_token");
    try {
      const res = await fetch(`${API_BASE_URL}/admin/rag/index`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setNotification(`Berhasil mengindeks ${data.indexed_chunks_count} potongan dokumen ke indeks RAG!`);
        fetchStatus();
      } else {
        setNotification(`Indexing gagal (HTTP ${res.status}).`);
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
      const res = await fetch(`${API_BASE_URL}/admin/rag/evaluate`, {
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
      const res = await fetch(`${API_BASE_URL}/rag/search`, {
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

      {crudError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
          <span>{crudError}</span>
        </div>
      )}

      {/* Knowledge Documents CRUD */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-emerald-600" />
              <span>Dokumen Pengetahuan ({docs.length})</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">Tambah, ubah, atau hapus dokumen. Hanya status APPROVED yang diindeks.</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleReindexDocs}
              disabled={reindexing}
              className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium flex items-center gap-1.5 shadow-sm disabled:opacity-50"
            >
              <Database className="w-3.5 h-3.5" />
              <span>{reindexing ? "Mengindeks..." : "Reindex Dokumen"}</span>
            </button>
            <button
              onClick={openCreate}
              className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Tambah Dokumen</span>
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="pb-2 font-semibold">Judul</th>
                <th className="pb-2 font-semibold">Departemen</th>
                <th className="pb-2 font-semibold">Sumber</th>
                <th className="pb-2 font-semibold">Status</th>
                <th className="pb-2 font-semibold text-right">Aksi</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {docs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-slate-500">
                    {docsLoading ? "Memuat dokumen..." : "Belum ada dokumen pengetahuan."}
                  </td>
                </tr>
              ) : (
                docs.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50">
                    <td className="py-2.5 font-medium text-slate-900 max-w-xs truncate">{d.title}</td>
                    <td className="py-2.5 text-slate-700">{d.department}</td>
                    <td className="py-2.5 text-slate-500">{d.source || "-"}</td>
                    <td className="py-2.5">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                          d.approval_status === "APPROVED"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : "bg-amber-50 text-amber-700 border-amber-200"
                        }`}
                      >
                        {d.approval_status}
                      </span>
                    </td>
                    <td className="py-2.5 text-right whitespace-nowrap">
                      <button
                        onClick={() => openEdit(d)}
                        className="p-1.5 rounded-lg text-slate-600 hover:bg-slate-100"
                        title="Ubah"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDelete(d)}
                        className="p-1.5 rounded-lg text-red-600 hover:bg-red-50"
                        title="Hapus"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showForm && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 flex items-center justify-center p-4">
          <form
            onSubmit={handleSave}
            className="w-full max-w-lg rounded-2xl border border-slate-200 p-6 space-y-3 bg-white shadow-xl text-xs max-h-[90vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900">
                {editingId ? "Ubah Dokumen Pengetahuan" : "Tambah Dokumen Pengetahuan"}
              </h3>
              <button type="button" onClick={() => setShowForm(false)} className="text-slate-400 hover:text-slate-600 p-1">
                <X className="w-4 h-4" />
              </button>
            </div>
            {crudError && <div className="p-2 rounded-lg bg-red-50 border border-red-200 text-red-800">{crudError}</div>}
            <label className="block space-y-1">
              <span className="font-medium text-slate-700">Judul</span>
              <input
                required
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                className="w-full p-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-emerald-500"
              />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="block space-y-1">
                <span className="font-medium text-slate-700">Departemen</span>
                <input
                  required
                  value={form.department}
                  onChange={(e) => setForm({ ...form, department: e.target.value })}
                  placeholder="mis: Pulmonologi"
                  className="w-full p-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </label>
              <label className="block space-y-1">
                <span className="font-medium text-slate-700">Status</span>
                <select
                  value={form.approval_status}
                  onChange={(e) => setForm({ ...form, approval_status: e.target.value })}
                  className="w-full p-2.5 rounded-xl border border-slate-200 bg-white focus:outline-none focus:border-emerald-500"
                >
                  <option value="APPROVED">APPROVED</option>
                  <option value="PENDING">PENDING</option>
                  <option value="REJECTED">REJECTED</option>
                </select>
              </label>
            </div>
            <label className="block space-y-1">
              <span className="font-medium text-slate-700">Sumber</span>
              <input
                value={form.source || ""}
                onChange={(e) => setForm({ ...form, source: e.target.value })}
                placeholder="mis: PNPK Kemenkes 2023"
                className="w-full p-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-emerald-500"
              />
            </label>
            <label className="block space-y-1">
              <span className="font-medium text-slate-700">Isi Dokumen</span>
              <textarea
                required
                rows={8}
                value={form.content}
                onChange={(e) => setForm({ ...form, content: e.target.value })}
                className="w-full p-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-emerald-500"
              />
            </label>
            <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-4 py-2 rounded-xl bg-white hover:bg-slate-50 text-slate-700 border border-slate-200"
              >
                Batal
              </button>
              <button
                type="submit"
                disabled={saving}
                className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold disabled:opacity-50"
              >
                {saving ? "Menyimpan..." : "Simpan"}
              </button>
            </div>
          </form>
        </div>
      )}

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
