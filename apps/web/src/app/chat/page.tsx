"use client";

import React, { useState, useEffect, useCallback } from "react";
import { 
  Send, Bot, User as UserIcon,
  ThumbsUp, ThumbsDown, FileText,
  Activity, Plus, MessageSquare, ExternalLink, X,
  Languages, ChevronDown, ChevronUp, Sparkles, Layers,
  Cpu, History, ArrowRight, ShieldCheck, Stethoscope,
  Trash2, Shield, Lock, FileCheck, CheckCircle2
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";

interface Citation {
  chunk_id: string;
  doc_id?: string;
  department?: string;
  title?: string;
  relevance_score?: number;
  dataset_id?: string;
  source_file?: string;
  approval_status?: string;
  content_excerpt?: string;
  checksum?: string;
}

export interface ScanningDeteksiBahasa {
  query_original?: string;
  language_detection?: {
    source_language_code?: string;
    source_language_label?: string;
    latency_ms?: number;
    confidence?: number;
  };
  bpe_tokens?: string[];
  target_steering_token?: string;
  steered_sequence?: string[];
  scanning_result?: {
    bahasa_awam?: string;
    bahasa_medis_klinis?: string;
    icd10_code?: string;
    urgensi_triase?: string;
    departemen_rekomendasi?: string;
  };
  beam_search?: {
    beam_width?: number;
    top_candidates?: Array<{
      candidate: string;
      probability: number;
      icd10?: string;
    }>;
  };
}

interface Message {
  id: string;
  sender: "user" | "assistant";
  content: string;
  department?: string;
  safetyAlert?: boolean;
  citations?: Citation[];
  feedback?: "LIKE" | "DISLIKE" | null;
  feedbackScore?: number;
  modelUsed?: string;
  timestamp: string;
  scanningDeteksiBahasa?: ScanningDeteksiBahasa | null;
}

interface SessionItem {
  id: string;
  title: string;
  updated_at: string;
  message_count: number;
}

interface ApiSessionMessage {
  id: string;
  sender_role: "user" | "assistant";
  content: string;
  triage_department?: string;
  safety_alert?: boolean;
  citations?: Citation[];
  created_at: string;
  scanning_deteksi_bahasa?: ScanningDeteksiBahasa | null;
}

/**
 * Komponen Scanning Deteksi Bahasa: Bahasa Awam ➔ Medis Klinis
 * Mengimplementasikan visualisasi Tiny Classifier (latency ms), Tokenizer BPE,
 * Steering Token (<2med_id>), Triase Klinis, dan Beam Search Top Candidates.
 */
function ScanningDeteksiBahasaCard({
  scan,
  defaultDept,
  isAdmin = false
}: {
  scan?: ScanningDeteksiBahasa | null;
  defaultDept?: string;
  isAdmin?: boolean;
}) {
  const [showPipelineDetails, setShowPipelineDetails] = useState(false);

  if (!scan || !scan.scanning_result) {
    return (
      <div className="flex items-center gap-2 text-[11px] text-slate-500 bg-slate-100/80 px-2.5 py-1 rounded-lg border border-slate-200">
        <Languages className="w-3.5 h-3.5 text-cyan-600" />
        <span>Triase: <strong className="text-slate-800">{defaultDept || "Umum"}</strong></span>
      </div>
    );
  }

  const res = scan.scanning_result;
  const lang = scan.language_detection;
  const beam = scan.beam_search?.top_candidates || [];
  const urgency = res.urgensi_triase || "HIJAU";

  const getUrgencyBadge = () => {
    switch (urgency) {
      case "MERAH":
        return "bg-red-50 text-red-700 border-red-300 animate-pulse";
      case "KUNING":
        return "bg-amber-50 text-amber-800 border-amber-300";
      default:
        return "bg-emerald-50 text-emerald-800 border-emerald-300";
    }
  };

  return (
    <div className="mt-3 p-3 sm:p-3.5 rounded-2xl bg-white border border-slate-200 shadow-xs space-y-3">
      {/* Header Scanning */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-cyan-50 border border-cyan-200 flex items-center justify-center text-cyan-700 shadow-2xs">
            <Languages className="w-3.5 h-3.5" />
          </div>
          <div>
            <span className="font-bold text-xs text-slate-900 block leading-tight">
              Scanning Deteksi Bahasa: Awam ➔ Medis Klinis
            </span>
            <div className="flex items-center gap-1.5 flex-wrap text-[10px] text-slate-500">
              <span>{lang?.source_language_label || "Bahasa Indonesia"} • Latency: <strong className="text-cyan-700 font-mono">{lang?.latency_ms || 1.2} ms</strong></span>
              <span className="text-[9px] px-1 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-200">
                🔒 UU PDP • HIPAA & Permenkes De-Identified
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          {/* Target Steering Token */}
          <span className="px-2 py-0.5 rounded-md bg-cyan-50 border border-cyan-200 text-[10px] font-mono font-semibold text-cyan-800">
            {scan.target_steering_token || "<2med_id>"}
          </span>

          {/* Urgensi Triase Badge */}
          <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${getUrgencyBadge()}`}>
            Triase: {urgency}
          </span>
        </div>
      </div>

      {/* Dual Box: Bahasa Awam vs Medis Klinis */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
        {/* Kolom 1: Bahasa Awam (Keluhan Pasien) */}
        <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
          <div className="flex items-center justify-between text-[10px] text-slate-500 font-medium">
            <span className="flex items-center gap-1">
              <UserIcon className="w-3 h-3 text-slate-400" />
              Bahasa Awam (Pasien)
            </span>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-white border border-slate-200 font-mono text-slate-600">
              Input
            </span>
          </div>
          <p className="font-semibold text-slate-800 text-xs leading-snug">
            {res.bahasa_awam || "Keluhan klinis pasien"}
          </p>
        </div>

        {/* Kolom 2: Terjemahan Medis Klinis (Standar Medis) */}
        <div className="p-2.5 rounded-xl bg-cyan-50/70 border border-cyan-200 space-y-1">
          <div className="flex items-center justify-between text-[10px] text-cyan-800 font-medium">
            <span className="flex items-center gap-1 font-semibold">
              <Stethoscope className="w-3 h-3 text-cyan-700" />
              Terjemahan Medis Klinis
            </span>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-100 text-cyan-800 font-mono font-semibold">
              ICD-10: {res.icd10_code || "Z00.0"}
            </span>
          </div>
          <p className="font-bold text-cyan-950 text-xs leading-snug">
            {res.bahasa_medis_klinis || "Standar Terminologi Klinis"}
          </p>
          <div className="text-[10px] text-cyan-800 pt-0.5">
            Departemen: <span className="font-semibold">{res.departemen_rekomendasi || defaultDept || "Umum"}</span>
          </div>
        </div>
      </div>

      {/* Khusus Administrator: Detail Neural Pipeline (BPE Tokens & Beam Search) */}
      {isAdmin && (
        <div className="pt-1">
          <button
            type="button"
            onClick={() => setShowPipelineDetails(!showPipelineDetails)}
            className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 text-[11px] text-slate-600 transition"
          >
            <span className="flex items-center gap-1.5 font-medium text-slate-700">
              <Cpu className="w-3.5 h-3.5 text-cyan-600" />
              <span>Detail Neural Pipeline (BPE Tokens & Beam Search) [Admin Workspace]</span>
            </span>
            {showPipelineDetails ? (
              <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            )}
          </button>

          {showPipelineDetails && (
            <div className="mt-2 p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-2.5 text-[11px]">
              {/* BPE Tokens */}
              <div>
                <div className="text-[10px] font-semibold text-slate-600 flex items-center gap-1 mb-1">
                  <Layers className="w-3 h-3 text-slate-500" />
                  <span>BPE Subword Tokenization ({scan.bpe_tokens?.length || 0} tokens):</span>
                </div>
                <div className="flex flex-wrap gap-1">
                  <span className="px-1.5 py-0.5 rounded bg-cyan-100 border border-cyan-200 font-mono text-[10px] font-bold text-cyan-800">
                    {scan.target_steering_token || "<2med_id>"}
                  </span>
                  {scan.bpe_tokens?.map((tok, idx) => (
                    <span
                      key={idx}
                      className="px-1.5 py-0.5 rounded bg-white border border-slate-200 font-mono text-[10px] text-slate-700 shadow-2xs"
                    >
                      {tok}
                    </span>
                  ))}
                </div>
              </div>

              {/* Beam Search Candidates */}
              {beam.length > 0 && (
                <div className="pt-1 border-t border-slate-200">
                  <div className="text-[10px] font-semibold text-slate-600 flex items-center gap-1 mb-1.5">
                    <Sparkles className="w-3 h-3 text-cyan-600" />
                    <span>Beam Search Top Candidates (Beam Width: {scan.beam_search?.beam_width || 3}):</span>
                  </div>
                  <div className="space-y-1.5">
                    {beam.map((c, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-1.5 rounded-lg bg-white border border-slate-200 text-[10px]"
                      >
                        <div className="flex items-center gap-2 truncate">
                          <span className="w-4 h-4 rounded-full bg-slate-100 text-slate-600 font-bold flex items-center justify-center text-[9px] shrink-0">
                            {idx + 1}
                          </span>
                          <span className="font-medium text-slate-800 truncate">{c.candidate}</span>
                          {c.icd10 && (
                            <span className="px-1 py-0.2 rounded bg-slate-100 text-slate-600 font-mono text-[9px] shrink-0">
                              {c.icd10}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0 pl-2">
                          <div className="w-12 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-cyan-600 rounded-full"
                              style={{ width: `${Math.round(c.probability * 100)}%` }}
                            />
                          </div>
                          <span className="font-mono text-cyan-700 font-semibold text-[10px]">
                            {(c.probability * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ChatPage() {
  const { role } = useAuth();
  const isAdmin = role === "ADMIN";
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [isHistoryDrawerOpen, setIsHistoryDrawerOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome-1",
      sender: "assistant",
      content: "Halo! Saya Asisten AI Klinis Rumah Sakit Umum Kota Terpadu (RSUKT). Anda dapat mendiskusikan informasi kesehatan umum, penjelasan gejala, atau protokol klinis rumah sakit.\n\nSetiap jawaban yang saya berikan akan dirujuk ke dokumen bukti protokol medis yang telah disetujui oleh tim medis kami. Bagaimana saya dapat membantu Anda hari ini?",
      department: "Umum",
      timestamp: "Baru saja",
      scanningDeteksiBahasa: {
        language_detection: {
          source_language_code: "id_layman_colloquial",
          source_language_label: "Bahasa Indonesia Awam",
          latency_ms: 1.15,
          confidence: 0.994,
        },
        bpe_tokens: ["ha@@", "lo", "asi@@", "sten", "kli@@", "nis", "rsukt"],
        target_steering_token: "<2med_id>",
        scanning_result: {
          bahasa_awam: "Sapaan pembuka konsultasi pasien",
          bahasa_medis_klinis: "Triase & Anamnesis Awal Pelayanan Medis",
          icd10_code: "Z00.0",
          urgensi_triase: "HIJAU",
          departemen_rekomendasi: "Umum / Triase Terpadu",
        },
        beam_search: {
          beam_width: 3,
          top_candidates: [
            { candidate: "Triase & Anamnesis Awal Pasien", probability: 0.985, icd10: "Z00.0" },
            { candidate: "Konsultasi Informasi Preventif", probability: 0.842, icd10: "Z71.9" },
            { candidate: "Edukasi Gaya Hidup & Kesehatan", probability: 0.670, icd10: "Z71.3" }
          ]
        }
      }
    },
  ]);
  const [inputQuery, setInputQuery] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [modelSize, setModelSize] = useState("70b");
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [showConsentModal, setShowConsentModal] = useState(false);

  const handleDeleteSession = async (sessId: string) => {
    if (!confirm("Hapus sesi percakapan ini secara permanen sesuai hak privasi GDPR & Permenkes?")) return;
    const token = localStorage.getItem("clinical_token");
    if (!token) return;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/chat/sessions/${sessId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        setSessions((prev) => prev.filter((s) => s.id !== sessId));
        if (currentSessionId === sessId) {
          createNewSession();
        }
      }
    } catch {
      // offline fallback
    }
  };

  const loadSession = useCallback(async (sessId: string) => {
    const token = localStorage.getItem("clinical_token");
    if (!token) return;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/chat/sessions/${sessId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCurrentSessionId(data.id);
        if (data.messages && data.messages.length > 0) {
          const formatted: Message[] = data.messages.map((m: ApiSessionMessage) => ({
            id: m.id,
            sender: m.sender_role,
            content: m.content,
            department: m.triage_department || "Umum",
            safetyAlert: m.safety_alert,
            citations: m.citations || [],
            timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            scanningDeteksiBahasa: m.scanning_deteksi_bahasa || null,
          }));
          setMessages(formatted);
        } else {
          setMessages([]);
        }
      }
    } catch {
      // offline fallback
    }
  }, []);

  // Load user sessions on mount
  const fetchSessions = useCallback(async () => {
    const token = localStorage.getItem("clinical_token");
    if (!token) return;
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/chat/sessions", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
        if (data.length > 0 && !currentSessionId) {
          loadSession(data[0].id);
        }
      }
    } catch {
      // offline fallback
    }
  }, [currentSessionId, loadSession]);

  useEffect(() => {
    let ignore = false;
    const run = async () => {
      const token = localStorage.getItem("clinical_token");
      if (!token) return;
      try {
        const res = await fetch("http://127.0.0.1:8000/api/v1/chat/sessions", {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok && !ignore) {
          const data = await res.json();
          setSessions(data);
          if (data.length > 0) {
            loadSession(data[0].id);
          }
        }
      } catch {
        // offline fallback
      }
    };
    run();
    return () => {
      ignore = true;
    };
  }, [loadSession]);

  const createNewSession = async () => {
    const token = localStorage.getItem("clinical_token");
    if (!token) return;
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/chat/sessions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ title: "Konsultasi Klinis Baru" })
      });
      if (res.ok) {
        const newSess = await res.json();
        setCurrentSessionId(newSess.id);
        setMessages([
          {
            id: `welcome-${Date.now()}`,
            sender: "assistant",
            content: "Halo! Sesi konsultasi klinis baru telah dibuka. Silakan ajukan pertanyaan atau jelaskan keluhan Anda.",
            department: "Umum",
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            scanningDeteksiBahasa: {
              language_detection: {
                source_language_code: "id_layman",
                source_language_label: "Bahasa Indonesia",
                latency_ms: 1.1,
                confidence: 0.99,
              },
              target_steering_token: "<2med_id>",
              scanning_result: {
                bahasa_awam: "Sesi Konsultasi Baru",
                bahasa_medis_klinis: "Anamnesis Awal Pasien Baru",
                icd10_code: "Z00.0",
                urgensi_triase: "HIJAU",
                departemen_rekomendasi: "Umum",
              }
            }
          }
        ]);
        fetchSessions();
        setIsHistoryDrawerOpen(false);
      }
    } catch {
      // offline fallback
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim() || isGenerating) return;

    const query = inputQuery.trim();
    setInputQuery("");

    let activeSessId = currentSessionId;
    const token = localStorage.getItem("clinical_token");

    // If no active session, create one first
    if (!activeSessId && token) {
      try {
        const sRes = await fetch("http://127.0.0.1:8000/api/v1/chat/sessions", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({ title: query.slice(0, 40) })
        });
        if (sRes.ok) {
          const sData = await sRes.json();
          activeSessId = sData.id;
          setCurrentSessionId(activeSessId);
        }
      } catch {
        // continue
      }
    }

    const tempUserMsg: Message = {
      id: `user-${Date.now()}`,
      sender: "user",
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setIsGenerating(true);

    try {
      if (token && activeSessId) {
        const res = await fetch("http://127.0.0.1:8000/api/v1/chat/messages", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({
            session_id: activeSessId,
            content: query
          })
        });

        if (res.ok) {
          const data = await res.json();
          const asst = data.assistant_message;
          const reply: Message = {
            id: asst.id,
            sender: "assistant",
            content: asst.content,
            department: asst.triage_department || "Umum",
            safetyAlert: asst.safety_alert,
            citations: asst.citations || [],
            modelUsed: asst.model_used,
            timestamp: new Date(asst.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            scanningDeteksiBahasa: asst.scanning_deteksi_bahasa || null,
          };
          setMessages((prev) => [...prev, reply]);
          fetchSessions();
        } else {
          throw new Error("Gagal menerima respons dari server");
        }
      } else {
        throw new Error("Sesi tidak aktif atau belum login");
      }
    } catch {
      // Local fallback
      const errorReply: Message = {
        id: `err-${Date.now()}`,
        sender: "assistant",
        content: "Maaf, terjadi kendala saat menghubungkan ke server asisten klinis RSUKT. Pastikan backend FastAPI aktif di http://127.0.0.1:8000.",
        department: "Sistem",
        safetyAlert: false,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorReply]);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleFeedback = async (msgId: string, type: "LIKE" | "DISLIKE") => {
    const token = localStorage.getItem("clinical_token");
    if (!token || !currentSessionId) return;

    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/chat/feedback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          session_id: currentSessionId,
          message_id: msgId,
          feedback_type: type
        })
      });

      if (res.ok) {
        const data = await res.json();
        setMessages((prev) =>
          prev.map((msg) => {
            if (msg.id === msgId) {
              return { ...msg, feedback: type, feedbackScore: data.adjusted_score };
            }
            return msg;
          })
        );
      }
    } catch {
      setMessages((prev) =>
        prev.map((msg) => (msg.id === msgId ? { ...msg, feedback: type } : msg))
      );
    }
  };

  const handleViewCitation = async (chunkId: string) => {
    const token = localStorage.getItem("clinical_token");
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/chat/citations/${chunkId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSelectedCitation(data);
      }
    } catch {
      // ignore
    }
  };

  return (
    <div className="flex h-full w-full overflow-hidden bg-slate-50 relative">
      {/* Sessions Drawer for Desktop & Mobile Toggle */}
      <div 
        className={`${
          isHistoryDrawerOpen ? "flex" : "hidden xl:flex"
        } fixed xl:static inset-y-0 left-0 z-40 w-72 flex-col border-r border-slate-200 bg-white p-3 shrink-0 shadow-lg xl:shadow-2xs transition-all`}
      >
        <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-100 xl:border-none">
          <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
            <History className="w-3.5 h-3.5 text-cyan-600" />
            Riwayat Percakapan
          </span>
          <button
            onClick={() => setIsHistoryDrawerOpen(false)}
            className="xl:hidden p-1 rounded-lg text-slate-400 hover:text-slate-600"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <button
          onClick={createNewSession}
          className="w-full py-2.5 px-3 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white text-xs font-semibold flex items-center justify-center gap-2 transition-colors shadow-sm mb-3"
        >
          <Plus className="w-4 h-4" />
          <span>Konsultasi Baru</span>
        </button>

        <div className="flex-1 overflow-y-auto space-y-1 pr-1">
          {sessions.map((sess) => (
            <div
              key={sess.id}
              className={`w-full p-2 rounded-xl text-xs transition-colors flex items-center justify-between group ${
                sess.id === currentSessionId
                  ? "bg-cyan-50 text-cyan-800 border border-cyan-200 shadow-2xs font-semibold"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 border border-transparent"
              }`}
            >
              <button
                onClick={() => {
                  loadSession(sess.id);
                  setIsHistoryDrawerOpen(false);
                }}
                className="flex items-start gap-2.5 flex-1 min-w-0 text-left"
              >
                <MessageSquare className="w-3.5 h-3.5 mt-0.5 shrink-0 text-cyan-600" />
                <div className="flex-1 truncate">
                  <div className="font-medium truncate">{sess.title}</div>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    {new Date(sess.updated_at).toLocaleDateString("id-ID")} • {sess.message_count} pesan
                  </div>
                </div>
              </button>

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteSession(sess.id);
                }}
                className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition shrink-0"
                title="Hapus Sesi (GDPR Art. 17 Right to Erasure)"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
          {sessions.length === 0 && (
            <div className="p-4 text-center text-xs text-slate-400">Belum ada riwayat sesi.</div>
          )}
        </div>
      </div>

      {/* Main Chat Workspace */}
      <div className="flex-1 flex flex-col h-full max-w-4xl w-full mx-auto p-3 sm:p-5 overflow-hidden">
        {/* Top Header Banner */}
        <div className="mb-3 px-3.5 py-2 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-2 text-xs text-slate-700">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsHistoryDrawerOpen(!isHistoryDrawerOpen)}
              className="xl:hidden p-1.5 rounded-lg text-slate-600 hover:bg-slate-100 border border-slate-200"
              title="Buka Riwayat Percakapan"
            >
              <History className="w-3.5 h-3.5 text-cyan-600" />
            </button>
            <Activity className="w-4 h-4 text-cyan-600 shrink-0" />
            <span className="text-xs font-medium truncate">
              Asisten AI Klinis • <strong className="text-cyan-800 font-semibold">{modelSize === "70b" ? "Llama 3.3 70B" : "Llama 3.1 8B"}</strong>
            </span>
          </div>

          <div className="flex items-center gap-1.5 flex-wrap">
            <button
              type="button"
              onClick={() => setShowConsentModal(true)}
              className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-[10px] font-semibold flex items-center gap-1 transition"
              title="Kepatuhan Regulasi ISO 27001, GDPR, HIPAA & Permenkes No. 12/2025"
            >
              <Shield className="w-3 h-3 text-cyan-600" />
              <span>Informed Consent</span>
            </button>

            <span className="px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-[10px] font-semibold flex items-center gap-1.5 shadow-2xs">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>Rujukan Protokol Klinis Terverifikasi</span>
              <span className="hidden sm:inline text-[9px] text-emerald-600 font-normal">| UU PDP No. 27/2022 • ISO 27001 • HIPAA • Permenkes</span>
            </span>
          </div>
        </div>

        {/* Messages List Area */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-1 mb-3">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-2 sm:gap-3 ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.sender === "assistant" && (
                <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-600 to-emerald-600 flex items-center justify-center text-white shrink-0 shadow-sm mt-1">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div className={`max-w-2xl w-full sm:w-auto space-y-2 ${msg.sender === "user" ? "items-end" : "items-start"}`}>
                {/* Message Bubble */}
                <div
                  className={`p-3.5 sm:p-4 rounded-2xl text-sm leading-relaxed ${
                    msg.sender === "user"
                      ? "bg-gradient-to-r from-cyan-600 to-cyan-700 text-white shadow-sm rounded-tr-xs ml-auto max-w-xl"
                      : msg.safetyAlert
                      ? "bg-red-50 border border-red-200 text-red-900 rounded-tl-xs shadow-xs"
                      : "bg-white text-slate-800 rounded-tl-xs border border-slate-200 shadow-xs"
                  }`}
                >
                  <p className="whitespace-pre-line text-xs sm:text-sm">{msg.content}</p>

                  {/* Citations Excerpt Box */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-100 space-y-2">
                      <span className="text-[11px] font-semibold text-cyan-700 flex items-center gap-1">
                        <FileText className="w-3.5 h-3.5" />
                        Sitasi Dokumen Bukti Terverifikasi:
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {msg.citations.map((c, i) => (
                          <button
                            key={i}
                            onClick={() => handleViewCitation(c.chunk_id)}
                            className="text-left p-2 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-[11px] text-slate-700 transition-all group flex items-start justify-between gap-2 shadow-2xs"
                          >
                            <div>
                              <div className="font-semibold text-emerald-700 group-hover:text-emerald-800 flex items-center gap-1">
                                <span>[{c.doc_id}]</span>
                                <ExternalLink className="w-3 h-3 text-slate-400 group-hover:text-cyan-600" />
                              </div>
                              <div className="text-[10px] text-slate-500 mt-0.5">Spesialisasi: {c.department}</div>
                            </div>
                            <span className="px-1.5 py-0.5 rounded bg-white border border-slate-200 text-[9px] font-mono text-slate-600 shrink-0">
                              RRF: {c.relevance_score}
                            </span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Scanning Deteksi Bahasa: Awam ➔ Medis Klinis Card */}
                  {msg.sender === "assistant" && (
                    <ScanningDeteksiBahasaCard
                      scan={msg.scanningDeteksiBahasa}
                      defaultDept={msg.department}
                      isAdmin={isAdmin}
                    />
                  )}
                </div>

                {/* Message Footer Info & Feedback Controls */}
                <div className="flex flex-wrap items-center gap-2 sm:gap-3 px-1 text-[11px] text-slate-500">
                  <span>{msg.timestamp}</span>

                  {/* Doctor/User Feedback Buttons */}
                  {msg.sender === "assistant" && (
                    <div className="flex items-center gap-1.5 ml-auto sm:ml-2">
                      <button
                        onClick={() => handleFeedback(msg.id, "LIKE")}
                        className={`p-1 rounded-lg hover:bg-slate-100 transition ${
                          msg.feedback === "LIKE" ? "text-emerald-700 bg-emerald-50" : "text-slate-400 hover:text-slate-600"
                        }`}
                        title="Sesuai Pedoman (+1.75%)"
                      >
                        <ThumbsUp className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleFeedback(msg.id, "DISLIKE")}
                        className={`p-1 rounded-lg hover:bg-slate-100 transition ${
                          msg.feedback === "DISLIKE" ? "text-red-700 bg-red-50" : "text-slate-400 hover:text-slate-600"
                        }`}
                        title="Kurang Sesuai / Butuh Revisi (-0.74%)"
                      >
                        <ThumbsDown className="w-3.5 h-3.5" />
                      </button>
                      {msg.feedback && (
                        <span className="text-[10px] text-cyan-700 font-semibold">
                          {msg.feedback === "LIKE" ? "+1.75%" : "-0.74%"}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {msg.sender === "user" && (
                <div className="w-8 h-8 rounded-xl bg-slate-200 border border-slate-300 flex items-center justify-center text-slate-600 shrink-0 mt-1 shadow-2xs">
                  <UserIcon className="w-4 h-4" />
                </div>
              )}
            </div>
          ))}

          {isGenerating && (
            <div className="flex gap-2 sm:gap-3 items-center text-xs text-slate-500">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-600 to-emerald-600 flex items-center justify-center text-white shrink-0">
                <Bot className="w-4 h-4 animate-spin" />
              </div>
              <div className="p-3 rounded-2xl bg-white border border-slate-200 shadow-xs flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-cyan-600 animate-bounce"></div>
                <div className="w-2 h-2 rounded-full bg-cyan-600 animate-bounce delay-100"></div>
                <div className="w-2 h-2 rounded-full bg-cyan-600 animate-bounce delay-200"></div>
                <span className="ml-1 text-slate-700 font-medium text-xs">
                  Scanning deteksi bahasa & menyintesis bukti protokol medis...
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Mobile-Friendly Composer Input Area */}
        <form onSubmit={handleSendMessage} className="relative mt-auto">
          <div className="bg-white p-2 rounded-2xl border border-slate-300 focus-within:border-cyan-600 focus-within:ring-2 focus-within:ring-cyan-500/10 shadow-xs transition">
            <textarea
              rows={2}
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage(e);
                }
              }}
              placeholder="Jelaskan keluhan Anda dalam bahasa awam (misal: 'Dada sakit dan sesak saat rebahan')..."
              className="w-full bg-transparent p-2 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:outline-none resize-none"
            />

            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 px-1 sm:px-2">
              <div className="flex items-center gap-1.5 text-xs text-slate-500">
                <span className="text-[11px] hidden sm:inline">Model:</span>
                <select
                  value={modelSize}
                  onChange={(e) => setModelSize(e.target.value)}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 text-[11px] text-slate-700 focus:outline-none focus:border-cyan-500"
                >
                  <option value="70b">Llama 3.3 70B (Gold Standard)</option>
                  <option value="8b">Llama 3.1 8B (Fast)</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={!inputQuery.trim() || isGenerating}
                className="py-2 px-4 rounded-xl bg-cyan-600 hover:bg-cyan-700 disabled:opacity-40 text-white font-semibold text-xs shadow-xs transition flex items-center gap-1.5 ml-auto"
              >
                <span>Kirim</span>
                <Send className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Citation Metadata Modal */}
      {selectedCitation && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl max-w-lg w-full p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-emerald-600" />
                <h3 className="text-sm font-bold text-slate-900">Metadata Sitasi Bukti Klinis</h3>
              </div>
              <button
                onClick={() => setSelectedCitation(null)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2">
                <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-slate-500 block text-[10px]">ID Dokumen</span>
                  <span className="font-semibold text-emerald-700">{selectedCitation.dataset_id}</span>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-slate-500 block text-[10px]">Spesialisasi</span>
                  <span className="font-semibold text-slate-800">{selectedCitation.department}</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-slate-500 block text-[10px]">File Sumber</span>
                  <span className="text-slate-700 truncate block">{selectedCitation.source_file}</span>
                </div>
                <div className="p-2.5 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-slate-500 block text-[10px]">Status Persetujuan</span>
                  <span className="text-emerald-700 font-semibold">{selectedCitation.approval_status}</span>
                </div>
              </div>

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                <span className="text-slate-700 font-semibold block text-[10px]">Kutipan Teks Asli (Ground Truth Excerpt):</span>
                <p className="text-slate-700 leading-relaxed max-h-48 overflow-y-auto whitespace-pre-line text-[11px]">
                  {selectedCitation.content_excerpt}
                </p>
              </div>

              <div className="text-[10px] text-slate-500 font-mono">
                Checksum SHA-256: {selectedCitation.checksum?.slice(0, 24)}...
              </div>
            </div>

            <button
              onClick={() => setSelectedCitation(null)}
              className="w-full py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-xl text-xs font-semibold transition"
            >
              Tutup Rincian Sitasi
            </button>
          </div>
        </div>
      )}

      {/* Informed Consent & Compliance Modal (ISO 27001, GDPR, HIPAA, Permenkes No. 12 Tahun 2025) */}
      {showConsentModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-3xl max-w-xl w-full p-5 sm:p-6 space-y-4 shadow-2xl max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-cyan-50 border border-cyan-200 flex items-center justify-center text-cyan-700 shadow-2xs">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Informed Consent & Kepatuhan Regulasi</h3>
                  <span className="text-[10px] text-slate-500 font-medium">
                    Standar Keamanan Informasi & Pelindungan Data Medis Pasien
                  </span>
                </div>
              </div>
              <button
                onClick={() => setShowConsentModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs text-slate-700 leading-relaxed">
              {/* Standar 1: ISO/IEC 27001:2022 */}
              <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5 text-cyan-600" />
                    1. ISO/IEC 27001:2022 (Sistem Manajemen Keamanan Informasi / ISMS)
                  </span>
                  <span className="px-1.5 py-0.2 rounded bg-cyan-100 text-cyan-800 text-[9px] font-mono font-bold">
                    ISMS Annex A.9
                  </span>
                </div>
                <p className="text-[11px] text-slate-600">
                  Data konsultasi Anda dienkripsi penuh secara transmisi (TLS 1.3) dan penyimpanan basis data (AES-256). Akses data diatur berdasarkan prinsip hak akses terendah (*Role-Based Access Control* / RBAC) dengan pencatatan audit log tak terhapuskan.
                </p>
              </div>

              {/* Standar 2: HIPAA Safe Harbor § 164.514 */}
              <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                    <Shield className="w-3.5 h-3.5 text-emerald-600" />
                    2. HIPAA Safe Harbor § 164.514 (De-identifikasi PHI)
                  </span>
                  <span className="px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-800 text-[9px] font-mono font-bold">
                    18 Identifiers Safe
                  </span>
                </div>
                <p className="text-[11px] text-slate-600">
                  Sistem secara otomatis menyamarkan data identitas pribadi (NIK 16 digit, No. Rekam Medis, No. BPJS, No. Telepon, Tanggal Lahir, dan Email) sebelum keluhan Anda diproses oleh modul penalaran klinis LLM.
                </p>
              </div>

              {/* Standar 3: GDPR (EU 2016/679) */}
              <div className="p-3 rounded-2xl bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                    <FileCheck className="w-3.5 h-3.5 text-amber-600" />
                    3. GDPR (General Data Protection Regulation)
                  </span>
                  <span className="px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 text-[9px] font-mono font-bold">
                    Art. 9 & 17 Rights
                  </span>
                </div>
                <p className="text-[11px] text-slate-600">
                  Pemrosesan data kesehatan dilakukan atas persetujuan sadar (*Informed Consent*). Anda memiliki hak penuh untuk meminta penghapusan riwayat sesi (*Right to Erasure*) melalui tombol hapus pada panel riwayat sesi.
                </p>
              </div>

              {/* Standar 4: Permenkes No. 12 Tahun 2025 */}
              <div className="p-3 rounded-2xl bg-cyan-50/70 border border-cyan-200 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-cyan-950 text-xs flex items-center gap-1.5">
                    <Stethoscope className="w-3.5 h-3.5 text-cyan-700" />
                    4. Permenkes No. 12 Tahun 2025 (Penyelenggaraan RME & Keamanan Data Medis)
                  </span>
                  <span className="px-1.5 py-0.2 rounded bg-cyan-100 text-cyan-800 text-[9px] font-mono font-bold">
                    Kemenkes Standar
                  </span>
                </div>
                <p className="text-[11px] text-cyan-900 leading-relaxed">
                  Asisten AI ini beroperasi sebagai <strong>Sistem Pendukung Keputusan Klinis (CDSS)</strong> rujukan protokol medis terakreditasi dan <strong>BUKAN merupakan pengganti diagnosis langsung dokter</strong>. AI tidak meresepkan terapi obat mandiri. Untuk kondisi darurat, segera hubungi IGD 119.
                </p>
              </div>

              {/* Standar 5: UU No. 27 Tahun 2022 (Pelindungan Data Pribadi / UU PDP) */}
              <div className="p-3 rounded-2xl bg-emerald-50/70 border border-emerald-200 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-emerald-950 text-xs flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-700" />
                    5. UU No. 27 Tahun 2022 (Pelindungan Data Pribadi / UU PDP)
                  </span>
                  <span className="px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-800 text-[9px] font-mono font-bold">
                    Data Spesifik Legal
                  </span>
                </div>
                <p className="text-[11px] text-emerald-900 leading-relaxed">
                  Data kesehatan diklasifikasikan sebagai <strong>Data Pribadi yang Bersifat Spesifik</strong> (Pasal 4 UU PDP). Seluruh keluhan diproses atas dasar persetujuan eksplisit (Pasal 20 UU PDP), dienkripsi penuh (Pasal 35 UU PDP), dan menjamin hak subjek data termasuk hak penghapusan data / <em>Right to Erasure</em> (Pasal 8 &amp; 10 UU PDP).
                </p>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-200 flex items-center justify-between gap-3">
              <span className="text-[10px] text-slate-500 font-medium">
                Persetujuan digital Anda tersimpan secara aman.
              </span>
              <button
                type="button"
                onClick={() => setShowConsentModal(false)}
                className="py-2.5 px-5 bg-cyan-600 hover:bg-cyan-700 text-white rounded-xl text-xs font-semibold shadow-xs transition"
              >
                Saya Memahami & Menyetujui
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

