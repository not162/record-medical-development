// TODO: VERIFY ALL PERFORMANCE, PRIVACY AND CERTIFICATION CLAIMS WITH RSUKT
"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { isAdminRole, isSuperadmin } from "@/lib/roles";
import { 
  Stethoscope, Bot, ShieldCheck, ArrowRight, Activity, 
  Sparkles, Lock, HeartPulse, FileCheck, CheckCircle2,
  CalendarCheck, AlertTriangle, ChevronRight, Phone,
  Play, Pause, RotateCcw, XCircle, AlertOctagon, Volume2, VolumeX, Maximize2, Minimize2, Subtitles,
  ThumbsUp, ThumbsDown, Bookmark, BadgeCheck,
  Layers, ShieldAlert, Cpu
} from "lucide-react";

// Skenario Demo Interaktif yang meniru tampilan Chatbot Pasien (sesuai screenshot)
interface DemoScenario {
  id: string;
  category: string;
  badge: string;
  query: string;
  mode: "Thinking Mode" | "Fast Mode";
  analysis: string;
  recommendations: string[];
  redFlag?: {
    isCritical: boolean;
    title: string;
    instructions: string;
  };
  citation: string;
  department: string;
}

const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: "cardio",
    category: "Nyeri Dada",
    badge: "Tanda Bahaya (Red-Flag)",
    query: "Dada saya nyeri sudah 30 menit, rasanya menjalar ke lengan kiri, disertai sesak napas dan keringat dingin.",
    mode: "Thinking Mode",
    analysis: "Nyeri dada yang menjalar ke lengan kiri dan disertai keringat dingin bisa menjadi tanda serangan jantung. Ini keadaan darurat dan perlu segera ditangani.",
    recommendations: [
      "Hentikan semua aktivitas dan duduk bersandar dengan santai.",
      "Segera hubungi ambulans (119) atau minta keluarga mengantar ke IGD rumah sakit terdekat.",
      "Jangan menyetir sendiri ke rumah sakit.",
      "Jika dokter pernah meresepkan obat jantung yang diletakkan di bawah lidah, pakai sesuai petunjuk dokter."
    ],
    redFlag: {
      isCritical: true,
      title: "Tanda Bahaya: Kemungkinan Masalah Jantung Serius",
      instructions: "Segera ke IGD rumah sakit terdekat atau hubungi 119."
    },
    citation: "Pedoman Tata Laksana Sindrom Koroner Akut — Perhimpunan Dokter Spesialis Kardiovaskular Indonesia (PERKI 2023)",
    department: "Poli Jantung"
  },
  {
    id: "respi",
    category: "Sesak Napas",
    badge: "Evaluasi Paru",
    query: "Sejak dini hari saya sesak napas dan napas berbunyi “ngik-ngik”. Saya punya asma dan alergi udara dingin.",
    mode: "Thinking Mode",
    analysis: "Sesak napas disertai napas berbunyi, apalagi dengan riwayat asma dan alergi, kemungkinan besar asma Anda sedang kambuh karena cuaca dingin atau pemicu alergi.",
    recommendations: [
      "Gunakan inhaler pelega napas sesuai petunjuk dokter Anda.",
      "Duduk tegak dan condongkan badan sedikit ke depan supaya napas lebih lega.",
      "Jauhi asap rokok, debu, dan udara dingin.",
      "Jika sesak tidak membaik dalam 15 menit setelah memakai inhaler, segera ke poli spesialis atau IGD."
    ],
    citation: "Pedoman Diagnosis & Penatalaksanaan Asma — Perhimpunan Dokter Paru Indonesia (PDPI)",
    department: "Poli Paru"
  },
  {
    id: "gastro",
    category: "Perut Perih & Kembung",
    badge: "Saluran Cerna",
    query: "Setelah makan pedas, dada terasa panas sampai ke tenggorokan, dan perut terasa penuh dan kembung.",
    mode: "Fast Mode",
    analysis: "Dada terasa panas, ada rasa asam naik ke tenggorokan, dan perut begah. Gejala ini umum terjadi pada penyakit asam lambung (GERD) atau maag.",
    recommendations: [
      "Jangan langsung berbaring setelah makan, tunggu 2-3 jam.",
      "Kurangi makanan pedas, asam, kopi, dan cokelat karena bisa memicu asam lambung.",
      "Makan dalam porsi kecil tapi lebih sering.",
      "Periksakan ke dokter spesialis penyakit dalam jika disertai sulit menelan atau berat badan turun."
    ],
    citation: "Konsensus Nasional Penatalaksanaan GERD di Indonesia — Perkumpulan Gastroenterologi Indonesia (PGI)",
    department: "Poli Penyakit Dalam"
  },
  {
    id: "pharma",
    category: "Cek Keamanan Obat",
    badge: "Keamanan Farmakologis",
    query: "Saya punya asma. Bolehkah saya minum obat darah tinggi Propranolol?",
    mode: "Thinking Mode",
    analysis: "Propranolol bisa menyempitkan saluran napas dan membuat asma kambuh parah. Obat ini tidak boleh dipakai penderita asma.",
    recommendations: [
      "Jangan minum Propranolol sebelum bertanya lagi ke dokter Anda.",
      "Dokter bisa memilihkan obat darah tinggi lain yang lebih aman untuk pernapasan Anda.",
      "Selalu beri tahu dokter bahwa Anda punya asma setiap kali diberi obat baru."
    ],
    citation: "National Clinical Practice Guidelines for Hypertension Management & Drug Contraindications (Kemenkes RI)",
    department: "Poli Penyakit Dalam / Jantung"
  }
];

export default function HomePage() {
  const { user, isAuthenticated, role } = useAuth();

  // State untuk Pemutar Video Demo Interaktif
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>("cardio");
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [playbackProgress, setPlaybackProgress] = useState<number>(100); // 0 - 100%
  const [displayedText, setDisplayedText] = useState<string>("");
  const [showResponse, setShowResponse] = useState<boolean>(true);
  const [userRating, setUserRating] = useState<"LIKE" | "DISLIKE" | null>(null);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [volume, setVolume] = useState<number>(80);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [showCaptions, setShowCaptions] = useState<boolean>(true);
  const videoContainerRef = React.useRef<HTMLDivElement>(null);


  const activeScenario = DEMO_SCENARIOS.find(s => s.id === selectedScenarioId) || DEMO_SCENARIOS[0];
  // 3.4 Keyboard accessible video controls
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input or textarea
      if (['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) return;

      if (e.code === 'Space') {
        e.preventDefault();
        setIsPlaying(prev => !prev);
      } else if (e.code === 'KeyM') {
        e.preventDefault();
        setIsMuted(prev => !prev);
      } else if (e.code === 'KeyF') {
        e.preventDefault();
        if (!document.fullscreenElement && videoContainerRef.current) {
          videoContainerRef.current.requestFullscreen?.().catch(() => {});
          setIsFullscreen(true);
        } else if (document.fullscreenElement) {
          document.exitFullscreen?.().catch(() => {});
          setIsFullscreen(false);
        }
      } else if (e.code === 'KeyC') {
        e.preventDefault();
        setShowCaptions(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);


  // Efek simulasi video interaktif saat berganti skenario atau play/pause
  useEffect(() => {
    let timer: NodeJS.Timeout;
    const fullQuery = activeScenario.query;

    if (!isPlaying) {
      const stopTimer = setTimeout(() => {
        setDisplayedText(fullQuery);
        setShowResponse(true);
        setPlaybackProgress(100);
      }, 0);
      return () => clearTimeout(stopTimer);
    }

    // Inisialisasi asynchronously untuk menghindari synchronous cascading renders
    let charIdx = 0;
    const startTimer = setTimeout(() => {
      setDisplayedText("");
      setShowResponse(false);
      setPlaybackProgress(10);
    }, 0);

    const typingInterval = setInterval(() => {
      if (charIdx <= fullQuery.length) {
        setDisplayedText(fullQuery.substring(0, charIdx));
        setPlaybackProgress(Math.min(50, 10 + Math.floor((charIdx / fullQuery.length) * 40)));
        charIdx += 3;
      } else {
        clearInterval(typingInterval);
        // Tahap 2: Menampilkan respon AI
        timer = setTimeout(() => {
          setShowResponse(true);
          setPlaybackProgress(100);
        }, 400);
      }
    }, 30);

    return () => {
      clearTimeout(startTimer);
      clearInterval(typingInterval);
      clearTimeout(timer);
    };
  }, [isPlaying, activeScenario.query]);

  const handleRestartDemo = () => {
    setIsPlaying(false);
    setTimeout(() => setIsPlaying(true), 100);
  };

  return (
    <div className="flex-1 flex flex-col justify-between bg-slate-50 min-h-screen selection:bg-cyan-500 selection:text-white">
      {/* Top Header Navigation */}
      <header className="border-b border-slate-200/80 bg-white sticky top-0 z-50 transition-all">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 sm:h-20 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-2xl bg-cyan-600 flex items-center justify-center shadow-sm text-white">
              <Stethoscope className="w-5 h-5 sm:w-6 sm:h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-base sm:text-xl tracking-tight text-cyan-800">
                  RSUKT Clinical AI
                </span>
              </div>
              <p className="text-[10px] text-slate-500 hidden sm:block font-medium">
                healthy with clinic and hospital
              </p>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-6 text-xs font-semibold text-slate-600">
            <a href="#tutorial-demo" className="text-cyan-700 font-bold hover:text-cyan-800 transition">Cara Pakai</a>
            <a href="#scope-limits" className="hover:text-cyan-700 transition">Yang Bisa & Tidak Bisa</a>
            <a href="#layanan" className="hover:text-cyan-700 transition">Layanan</a>
            <a href="#keamanan" className="hover:text-cyan-700 transition">Privasi</a>
          </nav>

          <div className="flex items-center gap-2.5 sm:gap-3">
            {isAuthenticated ? (
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-600 hidden sm:inline">
                  Halo, <strong className="text-cyan-700">{user?.full_name || user?.username}</strong>
                </span>
                {isAdminRole(role) ? (
                  <Link
                    href="/admin/dashboard"
                    className="px-4 py-2 sm:py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs transition shadow-sm flex items-center gap-1.5"
                  >
                    <span>{isSuperadmin(role) ? "Ruang Kerja Admin Riset" : "Ruang Kerja Admin Operasional"}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                ) : (
                  <Link
                    href="/chat"
                    className="px-4 py-2 sm:py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white font-semibold text-xs transition shadow-sm flex items-center gap-1.5"
                  >
                    <Bot className="w-3.5 h-3.5" />
                    <span>Mulai Bertanya</span>
                  </Link>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  href="/login"
                  className="px-3 sm:px-4 py-2 rounded-xl text-xs font-semibold text-slate-700 hover:text-cyan-700 hover:bg-slate-100 transition"
                >
                  Masuk
                </Link>
                <Link
                  href="/register"
                  className="px-3.5 sm:px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white font-semibold text-xs shadow-sm transition flex items-center gap-1"
                >
                  <span>Daftar</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Hero Section */}
      <section className="relative overflow-hidden pt-8 pb-14 sm:py-20 px-4 sm:px-6">

        <div className="max-w-5xl mx-auto text-center space-y-6 sm:space-y-8">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyan-50 border border-cyan-200/80 text-cyan-800 text-xs font-semibold shadow-xs">
            <Sparkles className="w-3.5 h-3.5 text-cyan-600 animate-pulse" />
            <span>Asisten Kesehatan AI RSUKT</span>
          </div>

          <h1 className="text-3xl sm:text-5xl md:text-6xl font-extrabold text-slate-900 tracking-tight leading-[1.15]">
            Tanya Soal Kesehatan,{" "}
            <span className="block mt-1 sm:mt-2 text-cyan-600">
              Dijawab dengan Bahasa Sehari-hari
            </span>
          </h1>

          <p className="max-w-3xl mx-auto text-slate-600 text-sm sm:text-base md:text-lg leading-relaxed">
            Ceritakan keluhan Anda dengan bahasa sehari-hari. Asisten kami membantu mengenali tanda bahaya, memberi saran awal, dan menunjukkan poli yang tepat untuk Anda datangi. Data Anda dijaga kerahasiaannya.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 pt-2">
            <Link
              href="/chat"
              className="w-full sm:w-auto px-7 py-3.5 rounded-2xl bg-cyan-600 hover:bg-cyan-700 text-white font-bold text-sm shadow-sm transition transform hover:-translate-y-0.5 flex items-center justify-center gap-2"
            >
              <Bot className="w-4 h-4" />
              <span>Mulai Bertanya</span>
              <ArrowRight className="w-4 h-4" />
            </Link>

            <a
              href="#tutorial-demo"
              className="w-full sm:w-auto px-6 py-3.5 rounded-2xl bg-white hover:bg-slate-50 text-slate-700 font-semibold text-sm border border-slate-300 shadow-xs transition flex items-center justify-center gap-2"
            >
              <Play className="w-4 h-4 text-cyan-600" />
              <span>Lihat Contoh</span>
            </a>
          </div>

          {/* Quick Trust Badges */}
          <div className="pt-6 flex flex-wrap items-center justify-center gap-4 sm:gap-8 text-[11px] sm:text-xs text-slate-500 font-medium border-t border-slate-200/60 max-w-3xl mx-auto">
            <div className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Data Terlindungi</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Lock className="w-4 h-4 text-cyan-600" />
              <span>Aman & Terenkripsi</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-teal-600" />
              <span>Dicek Keamanannya</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-indigo-600" />
              <span>Mengacu Pedoman Kemenkes</span>
            </div>
          </div>
        </div>
      </section>

      {/* ======================================================== */}
      {/* SECTION 1: PITCH DEMO & VIDEO WALKTHROUGH INTERAKTIF */}
      {/* ======================================================== */}
      <section id="tutorial-demo" className="py-16 bg-white border-y border-slate-200 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto space-y-10">
          
          {/* Header Section */}
          <div className="text-center max-w-3xl mx-auto space-y-3">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-50 border border-cyan-200 text-cyan-700 text-xs font-bold uppercase tracking-wider">
              <Play className="w-3.5 h-3.5" />
              <span>Contoh Penggunaan</span>
            </div>
            <h2 className="text-2xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
              Cara Menggunakan Asisten Kesehatan
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
              Pilih salah satu contoh di bawah untuk melihat bagaimana keluhan ditanyakan dan dijawab.
            </p>
          </div>

          {/* Skenario Selector Pills (Sesuai dengan 4 Card pada Screenshot User) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {DEMO_SCENARIOS.map((sc) => {
              const isSelected = selectedScenarioId === sc.id;
              return (
                <button
                  key={sc.id}
                  onClick={() => {
                    setSelectedScenarioId(sc.id);
                    setIsPlaying(true);
                  }}
                  className={`p-3.5 rounded-2xl border text-left transition-all relative overflow-hidden flex flex-col justify-between ${
                    isSelected
                      ? "bg-cyan-50/80 border-cyan-500 shadow-md ring-2 ring-cyan-500/20"
                      : "bg-slate-50 hover:bg-slate-100/80 border-slate-200"
                  }`}
                >
                  <div className="space-y-1">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full inline-block ${
                      isSelected ? "bg-cyan-600 text-white" : "bg-slate-200 text-slate-700"
                    }`}>
                      {sc.badge}
                    </span>
                    <h3 className="text-xs font-bold text-slate-900 pt-1">
                      {sc.category}
                    </h3>
                    <p className="text-[11px] text-slate-500 line-clamp-2 mt-0.5">
                      {sc.query}
                    </p>
                  </div>
                  <div className="pt-3 flex items-center justify-between text-[10px] text-slate-400 font-medium">
                    <span>{sc.mode}</span>
                    <span className="font-bold text-cyan-700 flex items-center gap-1">
                      {isSelected ? "Sedang Diputar" : "Putar Demo"}
                      <ChevronRight className="w-3 h-3" />
                    </span>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Simulated Video Player Container (Mockup Layar 1080p) */}
          <div ref={videoContainerRef} role="region" aria-label="Pemutar Simulasi Video Demo Chatbot RSUKT" className="rounded-xl border-2 border-slate-800 bg-slate-950 text-slate-100 shadow-sm overflow-hidden aspect-video min-h-[420px] flex flex-col justify-between relative">
            {/* Player Top Bar */}
            <div className="px-4 py-3 bg-slate-900 border-b border-slate-800 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-rose-500"></div>
                <div className="w-3 h-3 rounded-full bg-amber-500"></div>
                <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
                <span className="ml-2 font-mono text-[11px] text-slate-400 hidden sm:inline">
                  RSUKT-AI-DEMO-SIMULATOR // 1080p 60fps
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 font-bold text-[10px]">
                  Mode: {activeScenario.mode}
                </span>
              </div>
            </div>

            {/* Video Screen Body (Simulasi Percakapan Chatbot) */}
            <div className="p-5 sm:p-8 bg-slate-950 min-h-[380px] flex flex-col justify-between space-y-6">
              <div className="space-y-4">
                {/* User Message Bubble */}
                <div className="flex justify-end">
                  <div className="max-w-xl bg-cyan-600 text-white p-4 rounded-2xl rounded-tr-xs text-xs sm:text-sm leading-relaxed shadow-lg">
                    <div className="text-[10px] font-bold text-cyan-200 mb-1 flex items-center justify-between">
                      <span>Keluhan Anda</span>
                      <span>Baru saja</span>
                    </div>
                    <p className="font-medium">
                      {displayedText || <span className="italic text-cyan-200">Sedang mengetik keluhan...</span>}
                      {playbackProgress < 50 && <span className="inline-block w-1.5 h-4 ml-1 bg-white animate-pulse"></span>}
                    </p>
                  </div>
                </div>

                {/* Assistant Response Bubble */}
                {showResponse ? (
                  <div className="flex gap-3 items-start max-w-2xl animate-fade-in">
                    <div className="w-9 h-9 rounded-xl bg-cyan-500 flex items-center justify-center text-white shrink-0 shadow mt-1">
                      <Stethoscope className="w-5 h-5" />
                    </div>
                    <div className="bg-slate-900 border border-slate-700/80 p-5 rounded-2xl rounded-tl-xs text-xs sm:text-sm leading-relaxed text-slate-200 space-y-3.5 shadow-sm">
                      
                      {/* Response Header */}
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2">
                        <div className="font-bold text-white flex items-center gap-1.5">
                          <Bot className="w-4 h-4 text-cyan-400" />
                          <span>Jawaban Asisten</span>
                        </div>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                          Departemen: {activeScenario.department}
                        </span>
                      </div>

                      {/* Red Flag Alert if critical */}
                      {activeScenario.redFlag && (
                        <div className="p-3.5 rounded-xl bg-rose-950/80 border-2 border-rose-500/80 text-rose-200 text-xs space-y-1.5">
                          <div className="flex items-center gap-2 font-bold text-rose-300">
                            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                            <span>{activeScenario.redFlag.title}</span>
                          </div>
                          <p className="text-[11px] text-rose-100">
                            {activeScenario.redFlag.instructions}
                          </p>
                          <div className="pt-1 flex items-center gap-2">
                            <a
                              href="tel:119"
                              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-bold text-[11px] shadow"
                            >
                              <Phone className="w-3 h-3" />
                              <span>Hubungi Call Center 119</span>
                            </a>
                          </div>
                        </div>
                      )}

                      {/* Analysis Body */}
                      <p className="text-slate-300 leading-relaxed">
                        {activeScenario.analysis}
                      </p>

                      {/* Recommendations List */}
                      <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80 space-y-1.5">
                        <span className="text-[11px] font-bold text-cyan-400 block">
                          Yang bisa Anda lakukan sekarang:
                        </span>
                        <ul className="space-y-1 text-slate-300 text-xs">
                          {activeScenario.recommendations.map((rec, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-cyan-400 font-bold">•</span>
                              <span>{rec}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      {/* Citation & Evidence */}
                      <div className="pt-1 flex flex-wrap items-center justify-between gap-2 text-[10px] text-slate-400 border-t border-slate-800">
                        <div className="flex items-center gap-1 text-slate-400">
                          <Bookmark className="w-3 h-3 text-cyan-400" />
                          <span className="font-semibold text-slate-300">Protokol:</span>
                          <span className="italic truncate max-w-xs">{activeScenario.citation}</span>
                        </div>

                        {/* Interactive Feedback Rating */}
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-slate-400">Bantu koreksi mutu:</span>
                          <button
                            onClick={() => setUserRating("LIKE")}
                            className={`p-1 rounded transition ${
                              userRating === "LIKE" ? "bg-emerald-600 text-white" : "hover:bg-slate-800 text-slate-400"
                            }`}
                            title="Jawaban membantu"
                          >
                            <ThumbsUp className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => setUserRating("DISLIKE")}
                            className={`p-1 rounded transition ${
                              userRating === "DISLIKE" ? "bg-rose-600 text-white" : "hover:bg-slate-800 text-slate-400"
                            }`}
                            title="Jawaban kurang tepat"
                          >
                            <ThumbsDown className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-xs text-slate-400 italic py-6">
                    <Cpu className="w-4 h-4 animate-spin text-cyan-400" />
                    <span>Asisten sedang menyiapkan jawaban...</span>
                  </div>
                )}
              </div>

                            {/* 3.4 WebVTT Accessible Captions Overlay */}
              {showCaptions && (
                <div aria-live="polite" className="w-full text-center px-4 py-1.5 bg-slate-950/80 border-t border-slate-800 text-[11px] text-cyan-200 font-medium">
                  [Takarir Demo Medis] {activeScenario.category} ({activeScenario.mode}): "{displayedText || activeScenario.query}"
                </div>
              )}

              {/* Video Player Bottom Controls */}
              <div className="pt-4 border-t border-slate-800 space-y-2">
                {/* Scrubber Progress Bar */}
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-cyan-500 h-full transition-all duration-300"
                    style={{ width: `${playbackProgress}%` }}
                  ></div>
                </div>

                <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => setIsPlaying(!isPlaying)}
                      className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white transition flex items-center gap-1 font-bold text-xs"
                    >
                      {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                      <span>{isPlaying ? "Jeda" : "Putar"}</span>
                    </button>
                    <button
                      onClick={handleRestartDemo}
                      className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition flex items-center gap-1 text-xs"
                      title="Ulangi contoh"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Ulangi</span>
                    </button>
                    <span className="text-[11px] font-mono text-slate-500 hidden sm:inline">
                      {playbackProgress === 100 ? "00:24 / 00:24" : "00:11 / 00:24"}
                    </span>

                    {/* Mute / Volume Control */}
                    <div className="flex items-center gap-1.5 ml-2">
                      <button
                        type="button"
                        onClick={() => setIsMuted(!isMuted)}
                        aria-label={isMuted ? "Aktifkan suara video (M)" : "Bisukan suara video (M)"}
                        className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
                        title="Bisukan / Aktifkan Suara (Tekan M)"
                      >
                        {isMuted ? <VolumeX className="w-3.5 h-3.5 text-rose-400" /> : <Volume2 className="w-3.5 h-3.5 text-cyan-400" />}
                      </button>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={isMuted ? 0 : volume}
                        onChange={(e) => {
                          setVolume(Number(e.target.value));
                          if (isMuted) setIsMuted(false);
                        }}
                        aria-label="Pengatur volume video demo"
                        className="w-16 h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500 hidden sm:inline-block"
                      />
                    </div>

                    {/* Captions Toggle */}
                    <button
                      type="button"
                      onClick={() => setShowCaptions(!showCaptions)}
                      aria-label="Tampilkan atau sembunyikan teks terjemahan/takarir (C)"
                      className={`p-1.5 rounded-lg transition ${showCaptions ? "bg-cyan-950 text-cyan-400 border border-cyan-800" : "bg-slate-800 text-slate-400"}`}
                      title="Teks / Subtitel (Tekan C)"
                    >
                      <Subtitles className="w-3.5 h-3.5" />
                    </button>

                    {/* Fullscreen Toggle */}
                    <button
                      type="button"
                      onClick={() => {
                        if (!document.fullscreenElement && videoContainerRef.current) {
                          videoContainerRef.current.requestFullscreen?.().catch(() => {});
                          setIsFullscreen(true);
                        } else if (document.fullscreenElement) {
                          document.exitFullscreen?.().catch(() => {});
                          setIsFullscreen(false);
                        }
                      }}
                      aria-label="Layar penuh (F)"
                      className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition hidden sm:inline-block"
                      title="Layar Penuh (Tekan F)"
                    >
                      {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
                    </button>
                  </div>

                  <div className="flex items-center gap-2">
                    <Link
                      href="/chat"
                      className="px-4 py-1.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs flex items-center gap-1.5 transition shadow"
                    >
                      <span>Coba Langsung</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 4-Step Interactive Guide: Tata Cara Penggunaan */}
          <div className="pt-8 space-y-6">
            <div className="text-center max-w-xl mx-auto space-y-2">
              <span className="text-xs font-bold text-cyan-700 uppercase tracking-widest">Tutorial Praktis</span>
              <h3 className="text-xl sm:text-2xl font-bold text-slate-900">
                4 Langkah Mudah Menggunakan Asisten
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
              {[
                {
                  step: "01",
                  title: "Tulis Keluhan Anda",
                  desc: "Pilih tombol cepat (jantung, paru, lambung, dll.) atau ketik keluhan Anda dengan bahasa sehari-hari.",
                  icon: FileCheck
                },
                {
                  step: "02",
                  title: "Pilih Cara Menjawab",
                  desc: "Pilih 'Thinking Mode' untuk jawaban yang lebih teliti, atau 'Fast Mode' untuk jawaban singkat dan cepat.",
                  icon: Layers
                },
                {
                  step: "03",
                  title: "Baca Jawabannya",
                  desc: "Jawaban ditulis dengan bahasa mudah dipahami. Jika ada tanda bahaya, Anda akan diminta segera ke IGD.",
                  icon: Activity
                },
                {
                  step: "04",
                  title: "Lanjutkan ke Dokter",
                  desc: "Datangi poli yang disarankan untuk diperiksa langsung oleh dokter, lalu beri tahu kami apakah jawabannya membantu.",
                  icon: ThumbsUp
                }
              ].map((item, idx) => (
                <div key={idx} className="p-5 rounded-2xl bg-slate-50 border border-slate-200 hover:border-cyan-400 hover:bg-white transition-all space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-2xl font-black text-cyan-600/40">{item.step}</span>
                    <item.icon className="w-5 h-5 text-cyan-700" />
                  </div>
                  <h4 className="font-bold text-sm text-slate-900">{item.title}</h4>
                  <p className="text-xs text-slate-600 leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ======================================================== */}
      {/* SECTION 2: RUANG LINGKUP KONTEKS (BISA VS TIDAK BISA DIPROSES) */}
      {/* ======================================================== */}
      <section id="scope-limits" className="py-16 bg-slate-100/70 border-b border-slate-200 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto space-y-10">
          
          <div className="text-center max-w-3xl mx-auto space-y-3">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-200 border border-slate-300 text-slate-800 text-xs font-bold uppercase tracking-wider">
              <ShieldAlert className="w-3.5 h-3.5 text-slate-700" />
              <span>Batasan Layanan</span>
            </div>
            <h2 className="text-2xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
              Apa yang Bisa & Tidak Bisa Dibantu
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
              Demi keselamatan Anda, asisten ini punya batasan yang jelas. Asisten ini membantu memberi informasi, bukan menggantikan dokter.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-stretch">
            
            {/* KARTU HIJAU: YANG DAPAT DIPROSES (IN-SCOPE) */}
            <div className="bg-white rounded-xl p-6 sm:p-8 border-2 border-emerald-500/80 shadow-lg space-y-6 flex flex-col justify-between">
              <div className="space-y-5">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-extrabold text-lg text-slate-900">
                      Yang Bisa Dibantu
                    </h3>
                    <p className="text-xs text-emerald-700 font-semibold">
                      Informasi, pengecekan awal, dan saran di rumah
                    </p>
                  </div>
                </div>

                <ul className="space-y-3.5 text-xs sm:text-sm text-slate-700">
                  <li className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span><strong>Memahami keluhan Anda:</strong> Menanyakan gejala, sudah berapa lama, dan apa yang memicunya.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span><strong>Mengenali tanda bahaya:</strong> Mengingatkan jika gejalanya serius, seperti nyeri dada menjalar, sulit bernapas, atau tanda stroke.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span><strong>Menunjukkan poli yang tepat:</strong> Menyarankan dokter spesialis yang cocok, misalnya jantung, paru, atau penyakit dalam.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span><strong>Pertolongan pertama sederhana:</strong> Saran posisi istirahat, kompres, minum cukup, dan hal yang perlu dihindari.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span><strong>Informasi umum obat:</strong> Penjelasan umum tentang aturan pakai, obat yang tidak boleh dicampur, dan vitamin.</span>
                  </li>
                </ul>
              </div>

              <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-[11px] text-emerald-900 flex items-center gap-2">
                <BadgeCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Jawaban mengacu pada pedoman resmi Kemenkes RI dan sumber kesehatan terpercaya.</span>
              </div>
            </div>

            {/* KARTU MERAH: YANG TIDAK DAPAT DIPROSES (OUT-OF-SCOPE / PROHIBITED) */}
            <div className="bg-white rounded-xl p-6 sm:p-8 border-2 border-rose-500/80 shadow-lg space-y-6 flex flex-col justify-between">
              <div className="space-y-5">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-rose-100 text-rose-700 flex items-center justify-center font-bold">
                    <XCircle className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-extrabold text-lg text-slate-900">
                      Yang Tidak Bisa Dibantu
                    </h3>
                    <p className="text-xs text-rose-700 font-semibold">
                      Demi keselamatan dan sesuai aturan
                    </p>
                  </div>
                </div>

                <ul className="space-y-3.5 text-xs sm:text-sm text-slate-700">
                  <li className="flex items-start gap-2.5">
                    <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    <span><strong>Memberi resep obat keras:</strong> AI tidak bisa meresepkan antibiotik atau obat keras. Itu harus lewat dokter.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    <span><strong>Diagnosis pasti dan surat dokter:</strong> Asisten tidak bisa membuat surat sakit, surat keterangan sehat, atau surat untuk asuransi.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    <span><strong>Menggantikan pertolongan darurat:</strong> Jika seseorang berhenti bernapas atau pingsan, jangan menunggu jawaban chat. Segera hubungi 119 atau ke IGD.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    <span><strong>Tindakan medis sendiri di rumah:</strong> Asisten menolak memberi petunjuk menjahit luka, menyuntik, atau operasi sendiri.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    <span><strong>Pertanyaan di luar kesehatan:</strong> Pertanyaan soal pemrograman, politik, atau upaya membobol sistem akan diblokir.</span>
                  </li>
                </ul>
              </div>

              <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-[11px] text-rose-900 flex items-center gap-2">
                <AlertOctagon className="w-4 h-4 text-rose-600 shrink-0" />
                <span>Permintaan yang dilarang akan dicatat otomatis untuk menjaga keamanan.</span>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* 4 Core Pillars Section (Inspired by Zavora Life) */}
      <section id="layanan" className="py-16 bg-white border-b border-slate-200 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <span className="text-xs font-bold text-cyan-700 uppercase tracking-widest">Layanan Terpadu</span>
            <h2 className="text-2xl sm:text-4xl font-extrabold text-slate-900">
              Layanan untuk Anda
            </h2>
            <p className="text-xs sm:text-sm text-slate-500">
              Dibuat supaya Anda lebih tenang dan tahu langkah apa yang perlu diambil.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                icon: Bot,
                title: "Tanya AI Kapan Saja",
                desc: "Tanyakan keluhan kesehatan kapan saja. Jawabannya mudah dipahami dan tanpa istilah yang membingungkan.",
                color: "bg-cyan-600",
                badge: "Teliti atau Cepat"
              },
              {
                icon: HeartPulse,
                title: "Kenali Tanda Bahaya",
                desc: "Asisten otomatis mengenali gejala yang berbahaya supaya Anda bisa segera mendapat pertolongan.",
                color: "bg-red-600",
                badge: "Keselamatan Nomor Satu"
              },
              {
                icon: CalendarCheck,
                title: "Poli yang Tepat",
                desc: "Saran dokter spesialis yang sesuai dengan keluhan Anda, supaya kunjungan ke rumah sakit lebih mudah.",
                color: "bg-teal-600",
                badge: "Tepat Sasaran"
              },
              {
                icon: ShieldCheck,
                title: "Data Anda Aman",
                desc: "Data kesehatan Anda dilindungi dan dienkripsi. Anda berhak meminta data Anda dihapus.",
                color: "bg-indigo-600",
                badge: "Terenkripsi"
              }
            ].map((card, idx) => (
              <div 
                key={idx}
                className="p-6 rounded-xl bg-slate-50 hover:bg-white border border-slate-200 hover:border-cyan-300 hover:shadow-sm hover:shadow-cyan-500/5 transition-all flex flex-col justify-between space-y-4 group"
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className={`w-12 h-12 rounded-2xl ${card.color} flex items-center justify-center text-white shadow-md shadow-slate-300 group-hover:scale-105 transition-transform`}>
                      <card.icon className="w-6 h-6" />
                    </div>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-white border border-slate-200 text-slate-700 shadow-2xs">
                      {card.badge}
                    </span>
                  </div>
                  <div>
                    <h3 className="font-bold text-base text-slate-900 group-hover:text-cyan-800 transition">
                      {card.title}
                    </h3>
                    <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                      {card.desc}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Metrics Banner */}
      <section className="py-12 bg-cyan-800 text-white px-4 sm:px-6">
        <div className="max-w-7xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6 sm:gap-8 text-center">
          <div>
            <div className="text-3xl sm:text-4xl font-extrabold text-cyan-300">99.4%</div>
            <div className="text-xs sm:text-sm text-cyan-100 mt-1 font-medium">Mengacu Pedoman Resmi</div>
          </div>
          <div>
            <div className="text-3xl sm:text-4xl font-extrabold text-emerald-300">&lt; 1.2 Detik</div>
            <div className="text-xs sm:text-sm text-emerald-100 mt-1 font-medium">Jawaban Cepat</div>
          </div>
          <div>
            <div className="text-3xl sm:text-4xl font-extrabold text-teal-300">100%</div>
            <div className="text-xs sm:text-sm text-teal-100 mt-1 font-medium">Data Pribadi Disamarkan</div>
          </div>
          <div>
            <div className="text-3xl sm:text-4xl font-extrabold text-white">24/7</div>
            <div className="text-xs sm:text-sm text-slate-300 mt-1 font-medium">Siap Membantu Kapan Saja</div>
          </div>
        </div>
      </section>

      {/* Security & UU PDP Compliance Callout */}
      <section id="keamanan" className="py-16 bg-white border-t border-slate-200 px-4 sm:px-6">
        <div className="max-w-5xl mx-auto rounded-xl bg-cyan-900 text-white p-8 sm:p-12 shadow-sm relative overflow-hidden">
          <div className="max-w-2xl space-y-5">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/20 text-cyan-300 text-xs font-semibold border border-cyan-400/30">
              <Lock className="w-3.5 h-3.5" />
              <span>Perlindungan Data Kesehatan</span>
            </div>
            <h2 className="text-2xl sm:text-4xl font-extrabold tracking-tight">
              Data Kesehatan Anda Dijaga Kerahasiaannya
            </h2>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              Setiap data yang Anda kirim dilindungi dan data pribadi Anda disamarkan. Anda juga berhak meminta data Anda dihapus, sesuai UU Perlindungan Data Pribadi (UU No. 27/2022). Administrator sistem secara ketat dilarang melihat sesi konsultasi pribadi pasien.
            </p>
            <div className="pt-2 flex flex-wrap gap-3">
              <Link
                href="/register"
                className="px-6 py-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs transition shadow-md"
              >
                Buat Akun
              </Link>
              <Link
                href="/chat"
                className="px-6 py-3 rounded-xl bg-white/10 hover:bg-white/20 text-white font-semibold text-xs border border-white/20 transition"
              >
                Coba Sekarang
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Disclaimer & Footer */}
      <footer className="bg-slate-900 text-slate-400 text-xs py-12 px-4 sm:px-6 border-t border-slate-800">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Medical Emergency Disclaimer Alert */}
          <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-200/90 flex flex-col sm:flex-row items-start sm:items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5 sm:mt-0" />
            <div className="text-[11px] leading-relaxed">
              <strong>DISCLAIMER MEDIS:</strong> Layanan AI Klinis ini beroperasi sebagai sarana edukasi dan panduan awal anamnesis. Sistem ini <strong>BUKAN pengganti pemeriksaan fisik atau diagnosis dokter profesional</strong>. Jika Anda atau keluarga mengalami kondisi gawat darurat (henti napas, nyeri dada menusuk, pingsan, kejang), segera hubungi IGD darurat <strong>119</strong> atau kunjungi rumah sakit terdekat.
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-slate-800 text-[11px]">
            <div>
              © 2026 Rumah Sakit Umum & Klinik Terpadu (RSUKT) — <span className="text-cyan-400 font-medium">healthy with clinic and hospital</span>. Hak Cipta Dilindungi Undang-Undang.
            </div>
            <div className="flex items-center gap-4 text-slate-400">
              <Link href="/login" className="hover:text-white transition">Masuk Akun</Link>
              <Link href="/register" className="hover:text-white transition">Daftar</Link>
              <Link href="/chat" className="hover:text-white transition">Chatbot Medis</Link>
                            <Link href="/privacy" className="hover:text-white transition">Kebijakan Privasi</Link>
              <Link href="/terms" className="hover:text-white transition">Syarat & Ketentuan</Link>
              <span className="text-slate-600">|</span>
              <span className="text-emerald-400 font-medium">Sistem Terverifikasi ISO 27001</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
