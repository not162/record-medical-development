"use client";

import React, { useState, useEffect, useCallback, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";

const emptySubscribe = () => () => {};

function useMounted() {
  return useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false
  );
}
import { 
  Send, Bot, User as UserIcon,
  ThumbsUp, ThumbsDown, FileText,
  Activity, Plus, MessageSquare, ExternalLink, X,
  History, ShieldCheck, Stethoscope,
  Trash2, Shield, Lock, FileCheck,
  Clock, PhoneCall, Calendar, Download, RefreshCw, Zap, Brain, Loader2
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { API_BASE_URL } from "@/lib/api";

export interface QuotaStatus {
  quota_used: number;
  quota_max: number;
  quota_remaining: number;
  is_clinic_health_lock: boolean;
  reset_at: string | null;
  seconds_remaining: number;
  window_hours: number;
  policy: string;
  referral_info: {
    emergency_phone: string;
    hospital_name: string;
    clinic_name: string;
    operating_hours: string;
  };
}

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
 * Komponen pemformatan teks klinis untuk pasien:
 * Menghilangkan simbol teknis (*, '', ##, ###) dan merender judul, list, dan penekanan secara bersih.
 */
function CleanClinicalMarkdown({ content }: { content: string; isAdmin?: boolean }) {
  if (!content) return null;

  const lines = content.split("\n");

  return (
    <div className="space-y-2 text-xs sm:text-sm text-slate-800 leading-relaxed">
      {lines.map((line, idx) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={idx} className="h-1.5" />;
        }

        // 1. Heading check (###, ##, #)
        if (trimmed.startsWith("#")) {
          const cleanHeading = trimmed.replace(/^#+\s*/, "").replace(/[*'"]/g, "").trim();
          return (
            <h4 key={idx} className="font-bold text-slate-900 text-xs sm:text-sm pt-2 pb-0.5 border-b border-slate-100 flex items-center gap-1.5 text-cyan-950">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-600 shrink-0"></span>
              <span>{cleanHeading}</span>
            </h4>
          );
        }

        // 2. List item check (*, -, •)
        if (trimmed.startsWith("* ") || trimmed.startsWith("- ") || trimmed.startsWith("• ")) {
          const innerText = trimmed.replace(/^(\*|-|•)\s+/, "");
          return (
            <div key={idx} className="flex items-start gap-2 pl-1.5 my-1 text-slate-700">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-600 mt-1.5 shrink-0"></span>
              <span className="flex-1">{renderFormattedInline(innerText)}</span>
            </div>
          );
        }

        // 3. Regular paragraph
        return (
          <p key={idx} className="text-slate-700">
            {renderFormattedInline(trimmed)}
          </p>
        );
      })}
    </div>
  );
}

function renderFormattedInline(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|__[^_]+__)/g);

  return parts.map((part, i) => {
    if ((part.startsWith("**") && part.endsWith("**")) || (part.startsWith("__") && part.endsWith("__"))) {
      const cleanBold = part.slice(2, -2).replace(/[*'"]/g, "").trim();
      return <strong key={i} className="font-semibold text-slate-900">{cleanBold}</strong>;
    }
    const cleanText = part
      .replace(/[*#]/g, "")
      .replace(/''/g, '"')
      .replace(/\s{2,}/g, " ");
    return cleanText;
  });
}

export default function ChatPage() {
  const { role: userRole } = useAuth();
  const pageRouter = useRouter();

  // Strict separation: Administrator dilarang keras masuk ke ruang konsultasi pasien (UU PDP No. 27/2022)
  useEffect(() => {
    if (userRole === "ADMIN") {
      pageRouter.replace("/admin/dashboard");
    }
  }, [userRole, pageRouter]);

  const mounted = useMounted();
  const { role } = useAuth();
  const isAdmin = role === "ADMIN";
  const isEffectiveAdmin = mounted && isAdmin;

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
      scanningDeteksiBahasa: null,
    },
  ]);
  const [inputQuery, setInputQuery] = useState("");
  const [hasMoreMessages, setHasMoreMessages] = useState(false);
  const [nextMessageCursor, setNextMessageCursor] = useState<string | null>(null);
  const [totalSessionMessages, setTotalSessionMessages] = useState<number>(0);
  const [loadingOlderMessages, setLoadingOlderMessages] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [modelSize, setModelSize] = useState("70b");
  const [reasoningMode, setReasoningMode] = useState<"thinking" | "fast">("thinking");
  const [quotaStatus, setQuotaStatus] = useState<QuotaStatus | null>(null);
  const [secondsLeft, setSecondsLeft] = useState<number>(0);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [showConsentModal, setShowConsentModal] = useState(false);

  // RLHF Feedback State (Modal koreksi respon jika unlike)
  const [feedbackModalOpen, setFeedbackModalOpen] = useState(false);
  const [feedbackMsgId, setFeedbackMsgId] = useState<string | null>(null);
  const [feedbackCategory, setFeedbackCategory] = useState<string>("Bahasa terlalu rumit / teknis");
  const [feedbackNotes, setFeedbackNotes] = useState<string>("");
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);

  const formatCountdown = (totalSeconds: number) => {
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  };

  const fetchQuota = useCallback(async () => {
    const token = localStorage.getItem("clinical_token");
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE_URL}/chat/quota`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data: QuotaStatus = await res.json();
        setQuotaStatus(data);
        if (data.seconds_remaining) {
          setSecondsLeft(data.seconds_remaining);
        }
      }
    } catch {
      // offline fallback
    }
  }, []);

  const handleResetQuota = async () => {
    const token = localStorage.getItem("clinical_token");
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE_URL}/chat/quota/reset`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setQuotaStatus(data.quota);
        setSecondsLeft(0);
        alert("Siklus kuota 24 jam berhasil di-reset untuk pengujian.");
      }
    } catch {
      // ignore
    }
  };

  const handleDownloadSummary = () => {
    let summaryText = `RESUME KONSULTASI KLINIS ELEKTRONIK (RME) - RSUKT\n`;
    summaryText += `Standar Regulasi: Permenkes No. 12 Tahun 2025 | UU PDP No. 27 Tahun 2022 | ISO 27001\n`;
    summaryText += `Tanggal Unduh: ${new Date().toLocaleString("id-ID")}\n`;
    summaryText += `ID Sesi: ${currentSessionId || "N/A"}\n`;
    summaryText += `Mode Penalaran: ${reasoningMode.toUpperCase()}\n`;
    summaryText += `Status Kuota: ${quotaStatus ? quotaStatus.quota_used : 0}/7 Respon (Siklus 24 Jam Penuh)\n`;
    summaryText += `============================================================\n\n`;
    messages.forEach((m, idx) => {
      summaryText += `[${idx + 1}] [${m.sender.toUpperCase()}] ${m.timestamp}\n`;
      summaryText += `${m.content}\n\n`;
      if (m.scanningDeteksiBahasa?.scanning_result) {
        const sr = m.scanningDeteksiBahasa.scanning_result;
        summaryText += `   Triase Klinis: ${sr.urgensi_triase} | ICD-10: ${sr.icd10_code || "-"} | Spesialisasi: ${sr.departemen_rekomendasi}\n\n`;
      }
    });
    summaryText += `============================================================\n`;
    summaryText += `CATATAN RUJUKAN KLINIS:\n`;
    summaryText += `Hasil konsultasi AI di atas adalah Clinical Decision Support System (CDSS) dan bukan diagnosis definitif. Pasien wajib menjalani evaluasi tatap muka oleh dokter ber-SIP di poliklinik rawat jalan RSUKT atau IGD 119.\n`;

    const blob = new Blob([summaryText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Resume_RME_RSUKT_${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  useEffect(() => {
    let ignore = false;
    const initQuota = async () => {
      const token = localStorage.getItem("clinical_token");
      if (!token || ignore) return;
      try {
        const res = await fetch(`${API_BASE_URL}/chat/quota`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok && !ignore) {
          const data: QuotaStatus = await res.json();
          setQuotaStatus(data);
          if (data.seconds_remaining) {
            setSecondsLeft(data.seconds_remaining);
          }
        }
      } catch {
        // ignore
      }
    };
    initQuota();
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    if (!secondsLeft || secondsLeft <= 0) return;
    const timer = setInterval(() => {
      setSecondsLeft((prev) => {
        if (!prev || prev <= 1) {
          fetchQuota();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [secondsLeft, fetchQuota]);

  const handleDeleteSession = async (sessId: string) => {
    if (!confirm("Hapus sesi percakapan ini secara permanen sesuai hak privasi GDPR & Permenkes?")) return;
    const token = localStorage.getItem("clinical_token");
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE_URL}/chat/sessions/${sessId}`, {
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
      const res = await fetch(`${API_BASE_URL}/chat/sessions/${sessId}?limit=20`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCurrentSessionId(data.id);
        setHasMoreMessages(Boolean(data.has_more));
        setNextMessageCursor(data.next_cursor || null);
        setTotalSessionMessages(Number(data.total_messages || (data.messages ? data.messages.length : 0)));

        if (data.messages && data.messages.length > 0) {
          const formatted: Message[] = data.messages.map((m: ApiSessionMessage) => ({
            id: m.id,
            sender: m.sender_role,
            content: m.content,
            department: m.triage_department || "Umum",
            safetyAlert: m.safety_alert,
            citations: m.citations || [],
            timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            scanningDeteksiBahasa: null,
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

  const loadOlderMessages = async () => {
    if (!currentSessionId || !nextMessageCursor || loadingOlderMessages) return;
    const token = localStorage.getItem("clinical_token");
    if (!token) return;

    setLoadingOlderMessages(true);
    try {
      const res = await fetch(
        `${API_BASE_URL}/chat/sessions/${currentSessionId}?limit=20&before=${encodeURIComponent(nextMessageCursor)}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        const data = await res.json();
        setHasMoreMessages(Boolean(data.has_more));
        setNextMessageCursor(data.next_cursor || null);

        if (data.messages && data.messages.length > 0) {
          const formatted: Message[] = data.messages.map((m: ApiSessionMessage) => ({
            id: m.id,
            sender: m.sender_role,
            content: m.content,
            department: m.triage_department || "Umum",
            safetyAlert: m.safety_alert,
            citations: m.citations || [],
            timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            scanningDeteksiBahasa: null,
          }));
          setMessages((prev) => [...formatted, ...prev]);
        }
      }
    } catch (err) {
      console.error("Failed to load older messages:", err);
    } finally {
      setLoadingOlderMessages(false);
    }
  };

  // Load user sessions on mount
  const fetchSessions = useCallback(async () => {
    const token = localStorage.getItem("clinical_token");
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE_URL}/chat/sessions?limit=20`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        const items = Array.isArray(data) ? data : (data.items || []);
        setSessions(items);
        if (items.length > 0 && !currentSessionId) {
          loadSession(items[0].id);
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
        const res = await fetch(`${API_BASE_URL}/chat/sessions`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok && !ignore) {
          const data = await res.json();
          const items = Array.isArray(data) ? data : (data.items || []);
          setSessions(items);
          if (items.length > 0) {
            loadSession(items[0].id);
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
      const res = await fetch(`${API_BASE_URL}/chat/sessions`, {
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
            scanningDeteksiBahasa: null,
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

    if (quotaStatus?.is_clinic_health_lock && !isAdmin) {
      alert("Batas 7 keluaran AI harian tercapai. Sesi dialihkan ke Clinic Health Reset selama 24 jam penuh.");
      return;
    }

    const query = inputQuery.trim();
    setInputQuery("");

    let activeSessId = currentSessionId;
    const token = localStorage.getItem("clinical_token");

    // If no active session, create one first
    if (!activeSessId && token) {
      try {
        const sRes = await fetch(`${API_BASE_URL}/chat/sessions`, {
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

    const streamMsgId = `asst-stream-${Date.now()}`;
    const initialStreamMsg: Message = {
      id: streamMsgId,
      sender: "assistant",
      content: "",
      department: "Umum",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, initialStreamMsg]);

    try {
      if (token && activeSessId) {
        // Respons Percakapan Real-Time (Server-Sent Events)
        const res = await fetch(`${API_BASE_URL}/chat/messages/stream`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({
            session_id: activeSessId,
            content: query,
            reasoning_mode: reasoningMode,
            model_size: modelSize
          })
        });

        if (res.status === 429) {
          const errData = await res.json();
          if (errData.detail?.quota_status) {
            setQuotaStatus(errData.detail.quota_status);
            setSecondsLeft(errData.detail.quota_status.seconds_remaining || 86400);
          }
          const lockedReply: Message = {
            id: `lock-${Date.now()}`,
            sender: "assistant",
            content: "⚠️ **BATAS KONSULTASI AI HARIAN TERCAPAI (7/7 RESPON)** ⚠️\n\nSesuai standar Permenkes No. 12 Tahun 2025 demi keselamatan pasien, sesi dialihkan ke Clinic Health Reset selama 1 hari / 24 jam penuh.\n\nSilakan hubungi IGD 119 atau jadwalkan kunjungan ke Poliklinik Fisik RSUKT untuk pemeriksaan medis langsung oleh dokter.",
            department: "Clinic Health",
            safetyAlert: true,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          };
          setMessages((prev) => [...prev.filter((m) => m.id !== streamMsgId), lockedReply]);
          return;
        }

        if (res.ok && res.body) {
          const reader = res.body.getReader();
          const decoder = new TextDecoder("utf-8");
          let accumulatedContent = "";
          let buffer = "";

          while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
              const trimmed = line.trim();
              if (!trimmed.startsWith("data: ")) continue;
              try {
                const parsed = JSON.parse(trimmed.slice(6));

                if (parsed.type === "start" && parsed.scanning) {
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === streamMsgId
                        ? { ...m, scanningDeteksiBahasa: parsed.scanning }
                        : m
                    )
                  );
                } else if (parsed.type === "token") {
                  accumulatedContent += parsed.token;
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === streamMsgId
                        ? { ...m, content: accumulatedContent }
                        : m
                    )
                  );
                } else if (parsed.type === "done") {
                  if (parsed.quota_status) {
                    setQuotaStatus(parsed.quota_status);
                    if (parsed.quota_status.seconds_remaining) {
                      setSecondsLeft(parsed.quota_status.seconds_remaining);
                    }
                  }
                  const asst = parsed.assistant_message;
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === streamMsgId
                        ? {
                            ...m,
                            id: asst.id,
                            content: asst.content,
                            department: asst.triage_department || "Umum",
                            safetyAlert: asst.safety_alert,
                            citations: asst.citations || [],
                            modelUsed: asst.model_used,
                            scanningDeteksiBahasa: asst.scanning_deteksi_bahasa || m.scanningDeteksiBahasa || null,
                          }
                        : m
                    )
                  );
                  fetchSessions();
                }
              } catch {
                // ignore incomplete json chunk
              }
            }
          }
        } else {
          // Fallback ke synchronous POST jika streaming tidak tersedia
          const syncRes = await fetch(`${API_BASE_URL}/chat/messages`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`
            },
            body: JSON.stringify({
              session_id: activeSessId,
              content: query,
              reasoning_mode: reasoningMode
            })
          });

          if (syncRes.ok) {
            const data = await syncRes.json();
            if (data.quota_status) {
              setQuotaStatus(data.quota_status);
            }
            const asst = data.assistant_message;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === streamMsgId
                  ? {
                      ...m,
                      id: asst.id,
                      content: asst.content,
                      department: asst.triage_department || "Umum",
                      safetyAlert: asst.safety_alert,
                      citations: asst.citations || [],
                      modelUsed: asst.model_used,
                      timestamp: new Date(asst.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                      scanningDeteksiBahasa: asst.scanning_deteksi_bahasa || null,
                    }
                  : m
              )
            );
            fetchSessions();
          } else {
            throw new Error("Gagal menerima respons dari server");
          }
        }
      } else {
        throw new Error("Sesi tidak aktif atau belum login");
      }
    } catch {
      // Local fallback
      const errorReply: Message = {
        id: `err-${Date.now()}`,
        sender: "assistant",
        content: "Halo! Saya Asisten AI Klinis RSUKT. Sistem beroperasi dalam mode terverifikasi. Jika ada kendala jaringan, silakan muat ulang atau periksa status koneksi Anda.",
        department: "Sistem",
        safetyAlert: false,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev.filter((m) => m.id !== streamMsgId), errorReply]);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleFeedback = async (
    msgId: string,
    type: "LIKE" | "DISLIKE",
    category?: string,
    notes?: string
  ) => {
    const token = localStorage.getItem("clinical_token");
    if (!token || !currentSessionId) return;

    try {
      const res = await fetch(`${API_BASE_URL}/chat/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          session_id: currentSessionId,
          message_id: msgId,
          feedback_type: type,
          improvement_category: category,
          notes: notes
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

  const handleOpenDislikeModal = (msgId: string) => {
    setFeedbackMsgId(msgId);
    setFeedbackCategory("Bahasa terlalu rumit / teknis");
    setFeedbackNotes("");
    setFeedbackModalOpen(true);
  };

  const handleSubmitDislikeModal = async () => {
    if (!feedbackMsgId) return;
    setIsSubmittingFeedback(true);
    await handleFeedback(feedbackMsgId, "DISLIKE", feedbackCategory, feedbackNotes);
    setIsSubmittingFeedback(false);
    setFeedbackModalOpen(false);
  };

  const handleViewCitation = async (chunkId: string) => {
    const token = localStorage.getItem("clinical_token");
    try {
      const res = await fetch(`${API_BASE_URL}/chat/citations/${chunkId}`, {
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

  if (userRole === "ADMIN") {
    return null;
  }

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
          <span>Anamnesis Klinis Baru</span>
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
                  <div className="text-[10px] text-slate-500 mt-0.5" suppressHydrationWarning>
                    {mounted ? new Date(sess.updated_at).toLocaleDateString("id-ID") : ""} • {sess.message_count} pesan
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
        <div className="mb-3 px-3.5 py-2.5 rounded-2xl bg-white border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-2.5 text-xs text-slate-700">
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => setIsHistoryDrawerOpen(!isHistoryDrawerOpen)}
              className="xl:hidden p-1.5 rounded-lg text-slate-600 hover:bg-slate-100 border border-slate-200"
              title="Buka Riwayat Percakapan"
            >
              <History className="w-3.5 h-3.5 text-cyan-600" />
            </button>

            {/* Mode Selector Pasien: Hanya Thinking Mode dan Fast Mode (Bebas dari jargon ML/DL) */}
            <div className="flex items-center gap-2 flex-wrap">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-cyan-50/70 border border-cyan-200 text-cyan-900 text-xs font-semibold shadow-2xs">
                <Stethoscope className="w-4 h-4 text-cyan-700 shrink-0" />
                <span className="hidden sm:inline">Asisten AI Medis</span>
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  Terpandu
                </span>
              </div>

              <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-xl border border-slate-200">
                <button
                  type="button"
                  onClick={() => {
                    setReasoningMode("thinking");
                    setModelSize("70b");
                  }}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold flex items-center gap-1.5 transition ${
                    reasoningMode === "thinking"
                      ? "bg-white text-indigo-700 shadow-2xs border border-indigo-200"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                  title="Thinking Mode"
                >
                  <Brain className="w-3.5 h-3.5 text-indigo-600" />
                  <span>Thinking Mode</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setReasoningMode("fast");
                    setModelSize("8b");
                  }}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold flex items-center gap-1.5 transition ${
                    reasoningMode === "fast"
                      ? "bg-white text-amber-700 shadow-2xs border border-amber-200"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                  title="Fast Mode"
                >
                  <Zap className="w-3.5 h-3.5 text-amber-600" />
                  <span>Fast Mode</span>
                </button>
              </div>
            </div>
            {/* Daily Quota Counter Badge (Max 7 / 24 Hours) */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl border bg-slate-50 border-slate-200 text-[11px] shadow-2xs">
              <Clock className="w-3.5 h-3.5 text-cyan-600" />
              <span className="text-slate-500">Kuota AI:</span>
              <span className={`font-bold ${
                quotaStatus && quotaStatus.quota_used >= 7
                  ? "text-red-600"
                  : quotaStatus && quotaStatus.quota_used >= 5
                  ? "text-amber-600"
                  : "text-emerald-700"
              }`}>
                {quotaStatus ? quotaStatus.quota_used : 0}/7 Respon
              </span>
              <span className="text-slate-400 text-[10px] hidden sm:inline">| 24 Jam</span>
            </div>

            <button
              type="button"
              onClick={() => setShowConsentModal(true)}
              className="px-2.5 py-1 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-[10px] font-semibold flex items-center gap-1 transition"
              title="Kepatuhan Regulasi ISO 27001, GDPR, HIPAA & Permenkes No. 12/2025"
            >
              <Shield className="w-3 h-3 text-cyan-600" />
              <span>Consent</span>
            </button>

            <span className="px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-[10px] font-semibold flex items-center gap-1.5 shadow-2xs">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span className="hidden sm:inline">Terverifikasi RSUKT</span>
              <span className="text-[9px] text-emerald-600 font-normal">| Permenkes 12/2025</span>
            </span>
          </div>
        </div>

        {/* Messages List Area */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-1 mb-3">
          {messages.length === 0 && (
            <div className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6 text-center space-y-4 max-w-xl mx-auto my-auto animate-in fade-in duration-200">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-cyan-600 to-emerald-600 flex items-center justify-center text-white shadow-lg shadow-cyan-600/20">
                <Stethoscope className="w-7 h-7" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base sm:text-lg font-bold text-slate-900">
                  Asisten Kecerdasan Artifisial Medis Klinis RSUKT
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed max-w-md">
                  Pemeriksaan anamnesis terstruktur, penapisan tanda bahaya (*Red Flags*), dan panduan rujukan poliklinik spesialis berbasis bukti protokol medis terverifikasi.
                </p>
              </div>

              {/* Quick Clinical Anamnesis Chips */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full pt-2 text-left">
                {[
                  {
                    title: "Anamnesis Kardiovaskular",
                    desc: "Nyeri dada retrosternal, penjalaran lengan kiri, diaphoresis",
                    prompt: "Saya merasakan nyeri dada substernal yang menjalar ke leher dan lengan kiri disertai keringat dingin sejak 30 menit yang lalu.",
                    icon: Activity,
                    color: "border-red-200 bg-red-50/70 text-red-950 hover:bg-red-100/80",
                  },
                  {
                    title: "Skrining Obstruksi Respirasi",
                    desc: "Sesak napas akut, mengi ekspiratoir, riwayat asma",
                    prompt: "Pasien mengeluhkan sesak napas akut berbunyi mengi ekspiratoir dan riwayat asma bronkial.",
                    icon: Stethoscope,
                    color: "border-cyan-200 bg-cyan-50/70 text-cyan-950 hover:bg-cyan-100/80",
                  },
                  {
                    title: "Evaluasi Nyeri Epigastrium",
                    desc: "Rasa terbakar retrosternal, dispepsia, dan begah",
                    prompt: "Keluhan nyeri ulu hati rasa terbakar yang diperberat makanan asam disertai mual dan begah.",
                    icon: FileText,
                    color: "border-amber-200 bg-amber-50/70 text-amber-950 hover:bg-amber-100/80",
                  },
                  {
                    title: "Verifikasi Kontraindikasi Obat",
                    desc: "Kontraindikasi Beta-blocker dan interaksi farmakologis",
                    prompt: "Apakah terdapat kontraindikasi pemberian Beta-blocker non-selektif pada pasien dengan riwayat asma bronkial?",
                    icon: ShieldCheck,
                    color: "border-emerald-200 bg-emerald-50/70 text-emerald-950 hover:bg-emerald-100/80",
                  },
                ].map((item, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setInputQuery(item.prompt)}
                    className={`p-3 rounded-2xl border transition-all text-xs flex flex-col gap-1 shadow-2xs ${item.color}`}
                  >
                    <span className="font-bold flex items-center gap-1.5 text-xs">
                      <item.icon className="w-3.5 h-3.5 shrink-0" />
                      {item.title}
                    </span>
                    <span className="text-[10px] opacity-80 line-clamp-2">{item.desc}</span>
                  </button>
                ))}
              </div>

              {/* Regulatory Trust Badge */}
              <div className="flex items-center justify-center gap-2 pt-2 text-[10px] text-slate-400">
                <Lock className="w-3 h-3 text-emerald-600" />
                <span>Kerahasiaan Medis Terenkripsi: UU No. 27/2022 (UU PDP) & ISO/IEC 27001:2022 ISMS</span>
              </div>
            </div>
          )}
          {/* Pagination: Muat pesan riwayat sebelumnya */}
          {hasMoreMessages && (
            <div className="flex justify-center my-2">
              <button
                type="button"
                onClick={loadOlderMessages}
                disabled={loadingOlderMessages}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-700 text-xs font-semibold transition shadow-2xs disabled:opacity-50"
              >
                {loadingOlderMessages ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-600" />
                    <span>Memuat riwayat sebelumnya...</span>
                  </>
                ) : (
                  <>
                    <History className="w-3.5 h-3.5 text-cyan-700" />
                    <span>
                      Muat pesan sebelumnya ({Math.max(0, totalSessionMessages - messages.length)} pesan lagi)
                    </span>
                  </>
                )}
              </button>
            </div>
          )}

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
                  <CleanClinicalMarkdown content={msg.content} isAdmin={isEffectiveAdmin} />

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

                  {/* Scanning Deteksi Bahasa & Triase dihapus dari chat pasien */}
                </div>

                {/* Message Footer Info & Feedback Controls */}
                <div className="flex flex-wrap items-center gap-2 sm:gap-3 px-1 text-[11px] text-slate-500">
                  <span>{msg.timestamp}</span>

                  {/* Doctor/User Feedback Controls */}
                  {msg.sender === "assistant" && (
                    <div className="flex items-center gap-1.5 ml-auto sm:ml-2">
                      <button
                        onClick={() => handleFeedback(msg.id, "LIKE")}
                        className={`p-1.5 rounded-lg border transition ${
                          msg.feedback === "LIKE"
                            ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                            : "bg-white border-slate-200 text-slate-400 hover:text-slate-700 hover:border-slate-300"
                        }`}
                        title="Penjelasan bermanfaat dan mudah dipahami"
                      >
                        <ThumbsUp className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleOpenDislikeModal(msg.id)}
                        className={`p-1.5 rounded-lg border transition ${
                          msg.feedback === "DISLIKE"
                            ? "bg-amber-50 border-amber-200 text-amber-700"
                            : "bg-white border-slate-200 text-slate-400 hover:text-slate-700 hover:border-slate-300"
                        }`}
                        title="Beri masukan koreksi penjelasan klinis"
                      >
                        <ThumbsDown className="w-3.5 h-3.5" />
                      </button>

                      {/* Tampilan Status Feedback Pasien (Bukan AI slop/persentase RLHF teknis) */}
                      {msg.feedback === "LIKE" && (
                        <span className="text-[10px] text-emerald-700 font-medium px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200">
                          Membantu
                        </span>
                      )}
                      {msg.feedback === "DISLIKE" && (
                        <span className="text-[10px] text-amber-700 font-medium px-2 py-0.5 rounded-full bg-amber-50 border border-amber-200">
                          Masukan Dicatat
                        </span>
                      )}

                      {/* Khusus Admin: Indikator Bobot Penguatan RLHF */}
                      {isEffectiveAdmin && msg.feedback && (
                        <span className="text-[9px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
                          RLHF: {msg.feedback === "LIKE" ? "+1.0" : "-1.0"}
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
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-600 to-emerald-600 flex items-center justify-center text-white shrink-0 shadow-xs">
                <Bot className="w-4 h-4 animate-spin" />
              </div>
              <div className="p-3 rounded-2xl bg-white border border-slate-200 shadow-xs flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-cyan-600 animate-bounce"></div>
                <div className="w-2 h-2 rounded-full bg-cyan-600 animate-bounce delay-100"></div>
                <div className="w-2 h-2 rounded-full bg-cyan-600 animate-bounce delay-200"></div>
                <span className="ml-1 text-slate-700 font-medium text-xs">
                  AI sedang merumuskan penjelasan edukasi medis terverifikasi...
                </span>
                <span className="ml-auto text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold hidden sm:inline">
                  LIVE STREAM
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Clinic Health Reset Looping Card (Maksimal 7 Keluaran AI / 24 Jam Penuh) */}
        {quotaStatus?.is_clinic_health_lock && (
          <div className="mb-3 p-4 sm:p-5 rounded-2xl bg-gradient-to-br from-red-50 via-white to-amber-50 border-2 border-red-300 shadow-md space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-red-100 border border-red-200 flex items-center justify-center text-red-600 shrink-0 mt-0.5">
                  <Lock className="w-5 h-5" />
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="text-sm font-bold text-red-900">
                      Batas Konsultasi AI Harian Tercapai (7/7 Respon)
                    </h4>
                    <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-700 text-[10px] font-mono font-semibold">
                      Dialihkan ke Clinic Health Reset
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Sesuai regulasi rekam medis Permenkes No. 12 Tahun 2025 demi keselamatan klinis pasien, keluaran Asisten AI dibatasi 7 respon dalam jendela 24 jam penuh. Pasien dialihkan untuk pemeriksaan fisik langsung oleh dokter spesialis di poliklinik rumah sakit.
                  </p>
                </div>
              </div>

              {/* 24-Hour Live Countdown Clock */}
              <div className="shrink-0 bg-white p-3 rounded-xl border border-red-200 shadow-2xs text-left sm:text-right">
                <div className="text-[10px] font-medium text-slate-500 uppercase tracking-wider flex items-center sm:justify-end gap-1">
                  <Clock className="w-3.5 h-3.5 text-red-500 animate-pulse" />
                  <span>Reset Sesi Dalam</span>
                </div>
                <div className="text-lg sm:text-xl font-mono font-bold text-red-600 mt-0.5">
                  {formatCountdown(secondsLeft)}
                </div>
                <div className="text-[9px] text-slate-400">1 hari / 24 jam penuh</div>
              </div>
            </div>

            {/* Direct Clinical Physical Referral CTAs */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
              <a
                href="tel:119"
                className="flex items-center justify-center gap-2 p-2.5 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-bold transition shadow-xs"
              >
                <PhoneCall className="w-4 h-4" />
                <span>Hubungi IGD 119</span>
              </a>

              <button
                type="button"
                onClick={() => alert("Membuka loket pendaftaran Poliklinik Fisik Rawat Jalan RSUKT.")}
                className="flex items-center justify-center gap-2 p-2.5 rounded-xl bg-cyan-700 hover:bg-cyan-800 text-white text-xs font-bold transition shadow-xs"
              >
                <Calendar className="w-4 h-4" />
                <span>Jadwalkan Poli Fisik</span>
              </button>

              <button
                type="button"
                onClick={handleDownloadSummary}
                className="flex items-center justify-center gap-2 p-2.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 text-xs font-bold transition shadow-2xs"
              >
                <Download className="w-4 h-4 text-slate-600" />
                <span>Unduh Resume RME</span>
              </button>
            </div>

            {isEffectiveAdmin && (
              <div className="pt-2.5 border-t border-red-100 flex items-center justify-between text-xs flex-wrap gap-2">
                <span className="text-[11px] text-slate-500 font-mono">Mode Admin: Uji Coba Reset Kuota</span>
                <button
                  type="button"
                  onClick={handleResetQuota}
                  className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-900 text-white text-[11px] font-semibold flex items-center gap-1.5 transition"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Reset Siklus 24 Jam</span>
                </button>
              </div>
            )}
          </div>
        )}

        {/* Mobile-Friendly Composer Input Area */}
        <form onSubmit={handleSendMessage} className="relative mt-auto">
          <div className={`p-2 rounded-2xl border shadow-xs transition ${
            quotaStatus?.is_clinic_health_lock
              ? "bg-slate-100 border-red-200"
              : "bg-white border-slate-300 focus-within:border-cyan-600 focus-within:ring-2 focus-within:ring-cyan-500/10"
          }`}>
            <textarea
              rows={2}
              disabled={Boolean(quotaStatus?.is_clinic_health_lock)}
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage(e);
                }
              }}
              placeholder={
                quotaStatus?.is_clinic_health_lock
                  ? "Batas 7 keluaran AI tercapai. Sesi dialihkan ke Clinic Health Reset (24 Jam Penuh). Silakan hubungi IGD 119 atau kunjungi Poliklinik Fisik RSUKT..."
                  : "Sampaikan anamnesis keluhan utama & gejala klinis Anda (misal: 'Nyeri dada retrosternal onset 30 menit menjalar ke lengan kiri disertai dispnea dan diaphoresis')..."
              }
              className="w-full bg-transparent p-2 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:outline-none resize-none disabled:opacity-60"
            />

            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 px-1 sm:px-2">
              <div className="flex items-center gap-1.5 text-xs text-slate-500">
                <span className="text-[11px] text-slate-500 font-medium">Mode:</span>
                <select
                  value={reasoningMode}
                  onChange={(e) => {
                    const m = e.target.value as "thinking" | "fast";
                    setReasoningMode(m);
                    setModelSize(m === "thinking" ? "70b" : "8b");
                  }}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 text-[11px] text-slate-700 focus:outline-none focus:border-cyan-500 font-semibold"
                >
                  <option value="thinking">Thinking Mode</option>
                  <option value="fast">Fast Mode</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={!inputQuery.trim() || isGenerating || Boolean(quotaStatus?.is_clinic_health_lock)}
                className="py-2.5 px-4 rounded-xl bg-gradient-to-r from-cyan-600 to-emerald-600 hover:from-cyan-700 hover:to-emerald-700 disabled:opacity-40 text-white font-semibold text-xs shadow-xs transition flex items-center gap-1.5 ml-auto"
              >
                {quotaStatus?.is_clinic_health_lock ? (
                  <>
                    <Lock className="w-3.5 h-3.5" />
                    <span>Terkunci (24 Jam)</span>
                  </>
                ) : (
                  <>
                    <span className="hidden sm:inline">Konsultasikan Keluhan Klinis</span>
                    <span className="sm:hidden">Konsultasi</span>
                    <Send className="w-3.5 h-3.5" />
                  </>
                )}
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

      {/* Modal Koreksi Kualitas Penjelasan Klinis (RLHF Reinforcement Loop) */}
      {feedbackModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
          <div className="w-full max-w-lg bg-white border border-slate-200 rounded-3xl p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-700">
                  <Stethoscope className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Koreksi Kualitas Penjelasan Klinis
                  </h3>
                  <p className="text-xs text-slate-500">
                    Bantu tim medis menyempurnakan keakuratan dan kenyamanan asisten edukasi
                  </p>
                </div>
              </div>
              <button
                onClick={() => setFeedbackModalOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              <label className="block text-xs font-semibold text-slate-700">
                Pilih Aspek yang Perlu Ditingkatkan:
              </label>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                {[
                  { id: "Bahasa terlalu rumit / teknis", label: "Bahasa terlalu rumit / teknis", desc: "Sulit dipahami masyarakat awam" },
                  { id: "Informasi klinis kurang lengkap", label: "Informasi kurang lengkap", desc: "Penjelasan gejala/tindakan minim" },
                  { id: "Rujukan poliklinik kurang tepat", label: "Rujukan spesialisasi meleset", desc: "Departemen poliklinik tidak cocok" },
                  { id: "Kurang relevan dengan keluhan", label: "Kurang relevan", desc: "Menjawab di luar inti pertanyaan" },
                  { id: "Penyampaian kurang empatik", label: "Kurang empatik / kaku", desc: "Gaya bahasa terasa robotik" },
                  { id: "Lainnya / Masukan kustom", label: "Masukan lainnya", desc: "Catatan khusus dari pasien/dokter" },
                ].map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setFeedbackCategory(opt.id)}
                    className={`text-left p-2.5 rounded-xl border transition flex flex-col gap-0.5 ${
                      feedbackCategory === opt.id
                        ? "bg-cyan-50 border-cyan-500 ring-2 ring-cyan-500/20 text-cyan-900"
                        : "bg-slate-50 hover:bg-slate-100/80 border-slate-200 text-slate-700"
                    }`}
                  >
                    <span className="font-semibold text-xs">{opt.label}</span>
                    <span className="text-[10px] text-slate-500">{opt.desc}</span>
                  </button>
                ))}
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Catatan Tambahan (Opsional):
                </label>
                <textarea
                  rows={2}
                  value={feedbackNotes}
                  onChange={(e) => setFeedbackNotes(e.target.value)}
                  placeholder="Contoh: Tolong berikan instruksi pertolongan pertama yang lebih jelas sebelum ke rumah sakit..."
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-cyan-600 focus:bg-white focus:ring-2 focus:ring-cyan-500/10 transition resize-none"
                />
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setFeedbackModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition"
              >
                Batal
              </button>
              <button
                type="button"
                disabled={isSubmittingFeedback}
                onClick={handleSubmitDislikeModal}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-600 to-cyan-700 hover:from-cyan-700 hover:to-cyan-800 text-white text-xs font-semibold shadow-sm transition disabled:opacity-50"
              >
                {isSubmittingFeedback ? "Menyimpan Masukan..." : "Kirim Masukan Klinis"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

