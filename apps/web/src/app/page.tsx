"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { 
  Stethoscope, Bot, ShieldCheck, ArrowRight, Activity, 
  Sparkles, Lock, HeartPulse, Clock, FileCheck, CheckCircle2,
  CalendarCheck, UserCheck, AlertTriangle, ChevronRight, Phone,
  Play, Pause, RotateCcw, XCircle, AlertOctagon, HelpCircle,
  ThumbsUp, ThumbsDown, Bookmark, ExternalLink, BadgeCheck,
  Send, Layers, ShieldAlert, Cpu
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
    category: "Anamnesis Kardiovaskular",
    badge: "Tanda Bahaya (Red-Flag)",
    query: "Nyeri dada retrosternal onset 30 menit menjalar ke lengan kiri, disertai sesak napas dan keringat dingin (diaphoresis).",
    mode: "Thinking Mode",
    analysis: "Pola keluhan nyeri dada retrosternal dengan penjalaran ke lengan kiri dan keringat dingin memiliki karakteristik khas Sindrom Koroner Akut (SKA) atau iskemia miokard. Ini merupakan kondisi darurat medis yang memerlukan penanganan segera.",
    recommendations: [
      "Hentikan seluruh aktivitas fisik dan istirahatkan diri dalam posisi setengah duduk santai.",
      "Segera hubungi ambulans darurat (119) atau minta keluarga mengantar ke Instalasi Gawat Darurat (IGD) rumah sakit terdekat.",
      "Jangan mengemudi kendaraan sendiri menuju rumah sakit.",
      "Jika memiliki riwayat penyakit jantung dan telah diresepkan Nitrat sublingual oleh dokter, konsumsi sesuai petunjuk medis."
    ],
    redFlag: {
      isCritical: true,
      title: "Triase Merah: Potensi Kegawatdaruratan Kardiovaskular",
      instructions: "Segera menuju IGD Rumah Sakit Terdekat atau hubungi Hotline Darurat RSUKT / 119."
    },
    citation: "Pedoman Tata Laksana Sindrom Koroner Akut — Perhimpunan Dokter Spesialis Kardiovaskular Indonesia (PERKI 2023)",
    department: "Kardiologi & Vaskular"
  },
  {
    id: "respi",
    category: "Skrining Obstruksi Respirasi",
    badge: "Evaluasi Paru",
    query: "Sesak napas akut berulang disertai bunyi mengi ekspiratoir sejak dini hari, riwayat alergi dingin dan asma bronkial.",
    mode: "Thinking Mode",
    analysis: "Kombinasi sesak napas akut dengan mengi ekspiratoir dan riwayat atopi sangat mengarah pada eksaserbasi asma bronkial atau bronkospasme akut akibat pemicu cuaca/alergen.",
    recommendations: [
      "Gunakan inhaler bronkodilator pelega (SABA) sesuai instruksi dokter yang pernah merawat Anda.",
      "Posisikan tubuh tegak dan condongkan sedikit ke depan (posisi tripod) untuk mempermudah ekspansi paru.",
      "Jauhkan diri dari paparan asap rokok, debu, atau udara dingin.",
      "Jika sesak napas tidak membaik dalam 15 menit setelah pemakaian inhaler, segera ke poliklinik spesialis atau IGD."
    ],
    citation: "Pedoman Diagnosis & Penatalaksanaan Asma — Perhimpunan Dokter Paru Indonesia (PDPI)",
    department: "Pulmonologi & Kedokteran Respirasi"
  },
  {
    id: "gastro",
    category: "Evaluasi Nyeri Epigastrium",
    badge: "Saluran Cerna",
    query: "Rasa terbakar retrosternal menjalar ke tenggorokan setelah makan pedas, dispepsia, dan perut terasa kembung begah.",
    mode: "Fast Mode",
    analysis: "Gejala rasa panas terbakar di dada (heartburn) disertai regurgitasi asam dan begah merupakan manifestasi tipikal Gastroesophageal Reflux Disease (GERD) dan sindrom dispepsia fungsional.",
    recommendations: [
      "Hindari langsung berbaring minimal 2-3 jam setelah makan.",
      "Batasi makanan yang merangsang asam lambung seperti makanan pedas, asam, kafein, dan cokelat.",
      "Konsumsi makanan dalam porsi kecil namun lebih sering (small frequent meals).",
      "Konsultasikan ke Dokter Spesialis Penyakit Dalam jika keluhan disertai sulit menelan atau penurunan berat badan."
    ],
    citation: "Konsensus Nasional Penatalaksanaan GERD di Indonesia — Perkumpulan Gastroenterologi Indonesia (PGI)",
    department: "Penyakit Dalam (Gastroenterohepatologi)"
  },
  {
    id: "pharma",
    category: "Verifikasi Kontraindikasi Obat",
    badge: "Keamanan Farmakologis",
    query: "Apakah pasien dengan riwayat asma bronkial boleh mengonsumsi obat antihipertensi golongan Propranolol?",
    mode: "Thinking Mode",
    analysis: "Propranolol adalah penyekat beta non-selektif (Beta-Blocker) yang dapat memblokade reseptor beta-2 pada saluran napas, sehingga memicu bronkospasme berat pada penderita asma. Obat ini KONTRAINDIKASI bagi pasien asma.",
    recommendations: [
      "JANGAN mengonsumsi Propranolol tanpa konsultasi ulang dengan dokter penanggung jawab Anda.",
      "Dokter dapat mempertimbangkan alternatif obat antihipertensi lain yang lebih aman bagi saluran napas (misal: CCB seperti Amlodipin atau ARB).",
      "Selalu sampaikan riwayat asma kepada setiap dokter yang meresepkan obat baru."
    ],
    citation: "National Clinical Practice Guidelines for Hypertension Management & Drug Contraindications (Kemenkes RI)",
    department: "Farmakologi Klinis & Kardiologi"
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

  const activeScenario = DEMO_SCENARIOS.find(s => s.id === selectedScenarioId) || DEMO_SCENARIOS[0];

  // Efek simulasi video interaktif saat berganti skenario atau play/pause
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isPlaying) {
      setDisplayedText("");
      setShowResponse(false);
      setPlaybackProgress(10);

      // Tahap 1: Mengetik kueri pasien
      let charIdx = 0;
      const fullQuery = activeScenario.query;
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
        clearInterval(typingInterval);
        clearTimeout(timer);
      };
    } else {
      setDisplayedText(activeScenario.query);
      setShowResponse(true);
      setPlaybackProgress(100);
    }
  }, [selectedScenarioId, isPlaying]);

  const handleRestartDemo = () => {
    setIsPlaying(false);
    setTimeout(() => setIsPlaying(true), 100);
  };

  return (
    <div className="flex-1 flex flex-col justify-between bg-slate-50 min-h-screen selection:bg-cyan-500 selection:text-white">
      {/* Top Header Navigation */}
      <header className="border-b border-slate-200/80 bg-white/90 backdrop-blur-md sticky top-0 z-50 transition-all">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 sm:h-20 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-2xl bg-gradient-to-tr from-cyan-600 via-teal-600 to-emerald-600 flex items-center justify-center shadow-md shadow-cyan-600/20 text-white">
              <Stethoscope className="w-5 h-5 sm:w-6 sm:h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-base sm:text-xl tracking-tight bg-gradient-to-r from-cyan-800 to-teal-800 bg-clip-text text-transparent">
                  RSUKT Clinical AI
                </span>
                <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full bg-cyan-50 text-cyan-700 border border-cyan-200 tracking-wider">
                  Live
                </span>
              </div>
              <p className="text-[10px] text-slate-500 hidden sm:block font-medium">
                healthy with clinic and hospital
              </p>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-6 text-xs font-semibold text-slate-600">
            <a href="#tutorial-demo" className="text-cyan-700 font-bold hover:text-cyan-800 transition">Tutorial & Video Demo</a>
            <a href="#scope-limits" className="hover:text-cyan-700 transition">Batas Konteks Medis</a>
            <a href="#layanan" className="hover:text-cyan-700 transition">Layanan Klinis</a>
            <a href="#keamanan" className="hover:text-cyan-700 transition">Privasi & UU PDP</a>
          </nav>

          <div className="flex items-center gap-2.5 sm:gap-3">
            {isAuthenticated ? (
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-600 hidden sm:inline">
                  Halo, <strong className="text-cyan-700">{user?.full_name || user?.username}</strong>
                </span>
                {role === "ADMIN" ? (
                  <Link
                    href="/admin/dashboard"
                    className="px-4 py-2 sm:py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs transition shadow-md shadow-emerald-600/20 flex items-center gap-1.5"
                  >
                    <span>Workspace Riset</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                ) : (
                  <Link
                    href="/chat"
                    className="px-4 py-2 sm:py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white font-semibold text-xs transition shadow-md shadow-cyan-600/20 flex items-center gap-1.5"
                  >
                    <Bot className="w-3.5 h-3.5" />
                    <span>Konsultasi Klinis</span>
                  </Link>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  href="/login"
                  className="px-3 sm:px-4 py-2 rounded-xl text-xs font-semibold text-slate-700 hover:text-cyan-700 hover:bg-slate-100 transition"
                >
                  Masuk (Login)
                </Link>
                <Link
                  href="/register"
                  className="px-3.5 sm:px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-700 hover:to-teal-700 text-white font-semibold text-xs shadow-md shadow-cyan-600/20 transition flex items-center gap-1"
                >
                  <span>Daftar Pasien</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Hero Section */}
      <section className="relative overflow-hidden pt-8 pb-14 sm:py-20 px-4 sm:px-6">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[30rem] sm:w-[45rem] h-[25rem] bg-gradient-to-tr from-cyan-400/20 via-teal-300/20 to-emerald-400/20 rounded-full blur-3xl pointer-events-none -z-10"></div>

        <div className="max-w-5xl mx-auto text-center space-y-6 sm:space-y-8">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyan-50 border border-cyan-200/80 text-cyan-800 text-xs font-semibold shadow-xs">
            <Sparkles className="w-3.5 h-3.5 text-cyan-600 animate-pulse" />
            <span>Asisten Kecerdasan Artifisial Medis Klinis RSUKT</span>
          </div>

          <h1 className="text-3xl sm:text-5xl md:text-6xl font-extrabold text-slate-900 tracking-tight leading-[1.15]">
            Anamnesis Cerdas & Penapisan Bahaya{" "}
            <span className="block mt-1 sm:mt-2 bg-gradient-to-r from-cyan-600 via-teal-600 to-emerald-600 bg-clip-text text-transparent">
              Cepat, Tepat, dan Berbasis Bukti
            </span>
          </h1>

          <p className="max-w-3xl mx-auto text-slate-600 text-sm sm:text-base md:text-lg leading-relaxed">
            Pemeriksaan anamnesis terstruktur, penapisan tanda bahaya dini (*Red Flags*), dan panduan rujukan poliklinik spesialis berbasis bukti protokol medis terverifikasi. Terlindungi UU PDP No. 27/2022 dan standar ISO/IEC 27001:2022.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 pt-2">
            <Link
              href="/chat"
              className="w-full sm:w-auto px-7 py-3.5 rounded-2xl bg-gradient-to-r from-cyan-600 via-teal-600 to-emerald-600 hover:from-cyan-700 hover:to-emerald-700 text-white font-bold text-sm shadow-xl shadow-cyan-600/25 transition transform hover:-translate-y-0.5 flex items-center justify-center gap-2"
            >
              <Bot className="w-4 h-4" />
              <span>Mulai Konsultasi Chatbot</span>
              <ArrowRight className="w-4 h-4" />
            </Link>

            <a
              href="#tutorial-demo"
              className="w-full sm:w-auto px-6 py-3.5 rounded-2xl bg-white hover:bg-slate-50 text-slate-700 font-semibold text-sm border border-slate-300 shadow-xs transition flex items-center justify-center gap-2"
            >
              <Play className="w-4 h-4 text-cyan-600" />
              <span>Tonton Video Demo Interaktif</span>
            </a>
          </div>

          {/* Quick Trust Badges */}
          <div className="pt-6 flex flex-wrap items-center justify-center gap-4 sm:gap-8 text-[11px] sm:text-xs text-slate-500 font-medium border-t border-slate-200/60 max-w-3xl mx-auto">
            <div className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Kepatuhan UU PDP No. 27/2022</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Lock className="w-4 h-4 text-cyan-600" />
              <span>Enkripsi ISO/IEC 27001 ISMS</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-teal-600" />
              <span>Sanitasi OWASP Top 10</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-indigo-600" />
              <span>Protokol Klinis Kemenkes</span>
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
              <span>Simulasi Video Demo Interaktif</span>
            </div>
            <h2 className="text-2xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
              Tata Cara & Alur Penggunaan Chatbot Klinis
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
              Pilih skenario klinis di bawah untuk melihat simulasi interaktif pengetikan keluhan, analisis mode inferensi medis, penapisan red-flag, hingga sitasi protokol klinis.
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
          <div className="rounded-3xl border-2 border-slate-800 bg-slate-950 text-slate-100 shadow-2xl overflow-hidden">
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
                <span className="text-[11px] text-emerald-400 flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                  Live AI Engine
                </span>
              </div>
            </div>

            {/* Video Screen Body (Simulasi Percakapan Chatbot) */}
            <div className="p-5 sm:p-8 bg-gradient-to-b from-slate-950 to-slate-900 min-h-[380px] flex flex-col justify-between space-y-6">
              <div className="space-y-4">
                {/* User Message Bubble */}
                <div className="flex justify-end">
                  <div className="max-w-xl bg-cyan-600 text-white p-4 rounded-2xl rounded-tr-xs text-xs sm:text-sm leading-relaxed shadow-lg">
                    <div className="text-[10px] font-bold text-cyan-200 mb-1 flex items-center justify-between">
                      <span>Keluhan Klinis Pasien (Input Awam)</span>
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
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-teal-500 flex items-center justify-center text-white shrink-0 shadow mt-1">
                      <Stethoscope className="w-5 h-5" />
                    </div>
                    <div className="bg-slate-900 border border-slate-700/80 p-5 rounded-2xl rounded-tl-xs text-xs sm:text-sm leading-relaxed text-slate-200 space-y-3.5 shadow-xl">
                      
                      {/* Response Header */}
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2">
                        <div className="font-bold text-white flex items-center gap-1.5">
                          <Bot className="w-4 h-4 text-cyan-400" />
                          <span>Telaah Asisten Edukasi Medis RSUKT</span>
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
                          Panduan Pertolongan Awal & Tindakan Mandiri:
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
                            title="Jawaban Tepat & Edukatif"
                          >
                            <ThumbsUp className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => setUserRating("DISLIKE")}
                            className={`p-1 rounded transition ${
                              userRating === "DISLIKE" ? "bg-rose-600 text-white" : "hover:bg-slate-800 text-slate-400"
                            }`}
                            title="Perlu Koreksi Dokter"
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
                    <span>AI Engine sedang menelaah protokol medis & tanda bahaya...</span>
                  </div>
                )}
              </div>

              {/* Video Player Bottom Controls */}
              <div className="pt-4 border-t border-slate-800 space-y-2">
                {/* Scrubber Progress Bar */}
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-cyan-500 to-teal-400 h-full transition-all duration-300"
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
                      title="Ulangi Simulasi Skenario"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Ulangi</span>
                    </button>
                    <span className="text-[11px] font-mono text-slate-500 hidden sm:inline">
                      {playbackProgress === 100 ? "00:24 / 00:24" : "00:11 / 00:24"}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Link
                      href="/chat"
                      className="px-4 py-1.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs flex items-center gap-1.5 transition shadow"
                    >
                      <span>Coba Chatbot Langsung</span>
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
                4 Langkah Mudah Menggunakan Chatbot Klinis
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
              {[
                {
                  step: "01",
                  title: "Pilih / Tuliskan Keluhan",
                  desc: "Gunakan tombol cepat (Kardiovaskular, Paru, Lambung, dsb.) atau ketikkan gejala Anda dalam bahasa awam sehari-hari.",
                  icon: FileCheck
                },
                {
                  step: "02",
                  title: "Tentukan Mode Analisis",
                  desc: "Pilih 'Thinking Mode' untuk penelusuran protokol mendalam & rujukan spesialis, atau 'Fast Mode' untuk informasi kilat.",
                  icon: Layers
                },
                {
                  step: "03",
                  title: "Simak Telaah & Red-Flag",
                  desc: "Baca penjelasan ramah awam tanpa jargon teknis membingungkan, serta perhatikan arahan darurat jika terdeteksi gejala kritis.",
                  icon: Activity
                },
                {
                  step: "04",
                  title: "Tindak Lanjut & Evaluasi",
                  desc: "Gunakan informasi rujukan poliklinik rumah sakit untuk periksa langsung ke dokter dan berikan rating suka/tidak suka.",
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
              <span>Etika Medis & Kebijakan Batasan Sistem</span>
            </div>
            <h2 className="text-2xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
              Konteks Layanan: Apa yang Dapat & TIDAK DAPAT Diproses
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
              Demi keselamatan pasien dan kepatuhan terhadap standar Konsil Kedokteran Indonesia (KKI) serta Permenkes No. 24/2022, sistem memiliki batasan operasional yang tegas.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-stretch">
            
            {/* KARTU HIJAU: YANG DAPAT DIPROSES (IN-SCOPE) */}
            <div className="bg-white rounded-3xl p-6 sm:p-8 border-2 border-emerald-500/80 shadow-lg space-y-6 flex flex-col justify-between">
              <div className="space-y-5">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-extrabold text-lg text-slate-900">
                      Konteks yang DAPAT Diproses
                    </h3>
                    <p className="text-xs text-emerald-700 font-semibold">
                      Fokus Edukasi, Skrining & Panduan Mandiri
                    </p>
                  </div>
                </div>

                <ul className="space-y-3.5 text-xs sm:text-sm text-slate-700">
                  <li className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span><strong>Anamnesis Gejala Terstruktur:</strong> Analisis kemungkinan sindrom klinis berdasarkan keluhan awam, durasi sakit, dan faktor pencetus.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span><strong>Penapisan Tanda Bahaya (*Red-Flags*):</strong> Deteksi dini gejala kritis seperti nyeri dada menjalar, apnea, henti napas, dan stroke akut.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span><strong>Rekomendasi Poliklinik Rujukan:</strong> Membimbing pasien ke spesialisasi rumah sakit yang tepat (Kardiologi, Paru, Penyakit Dalam, dsb.).</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span><strong>Panduan Pertolongan Pertama Non-Invasif:</strong> Instruksi posisi istirahat, kompres, cairan hidrasi, dan pencegahan komplikasi.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span><strong>Edukasi Informasi Umum Obat:</strong> Informasi umum interaksi farmakologis, kontraindikasi, dan aturan pakai suplemen/vitamin.</span>
                  </li>
                </ul>
              </div>

              <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-[11px] text-emerald-900 flex items-center gap-2">
                <BadgeCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Seluruh jawaban grounded pada basis data pedoman klinis resmi Kemenkes RI & jurnal terverifikasi.</span>
              </div>
            </div>

            {/* KARTU MERAH: YANG TIDAK DAPAT DIPROSES (OUT-OF-SCOPE / PROHIBITED) */}
            <div className="bg-white rounded-3xl p-6 sm:p-8 border-2 border-rose-500/80 shadow-lg space-y-6 flex flex-col justify-between">
              <div className="space-y-5">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-rose-100 text-rose-700 flex items-center justify-center font-bold">
                    <XCircle className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-extrabold text-lg text-slate-900">
                      Yang TIDAK DAPAT Diproses
                    </h3>
                    <p className="text-xs text-rose-700 font-semibold">
                      Batasan Etika Hukum & Keamanan Medis Mutlak
                    </p>
                  </div>
                </div>

                <ul className="space-y-3.5 text-xs sm:text-sm text-slate-700">
                  <li className="flex items-start gap-2.5">
                    <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    <span><strong>Peresepan Obat Keras & Narkotika:</strong> AI TIDAK BERWENANG mengeluarkan resep antibiotik, psikotropika, atau obat daftar G tanpa tatap muka dokter.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    <span><strong>Vonis Diagnosis Definitif & Surat Medis:</strong> Sistem tidak menerbitkan surat sakit resmi, surat bebas narkoba, atau sertifikat legal asuransi.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    <span><strong>Pengganti Tindakan Gawat Darurat Fisik:</strong> Pasien henti napas/jantung tidak boleh menunggu respons teks; wajib segera ke IGD 119.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    <span><strong>Instruksi Prosedur Bedah Mandiri:</strong> Permintaan petunjuk penjahitan luka, injeksi cairan berbahaya, atau bedah mandiri DITOLAK KERAS.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                    <span><strong>Kueri Non-Medis & Injeksi Sistem:</strong> Pertanyaan coding, politik, atau percobaan SQL/Prompt Injection otomatis diblokir filter OWASP.</span>
                  </li>
                </ul>
              </div>

              <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-[11px] text-rose-900 flex items-center gap-2">
                <AlertOctagon className="w-4 h-4 text-rose-600 shrink-0" />
                <span>Pelanggaran kueri terlarang akan dicatat dalam Audit Trail Kepatuhan ISO 27001 secara otomatis.</span>
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
              Solusi Lengkap Kesehatan Digital Pasien
            </h2>
            <p className="text-xs sm:text-sm text-slate-500">
              Dirancang untuk memberikan ketenangan pikiran dengan panduan medis berbasis bukti protokol kesehatan terverifikasi.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                icon: Bot,
                title: "Anamnesis AI 24/7",
                desc: "Konsultasi keluhan kesehatan kapan saja dengan penjelasan ramah awam, akurat, dan tanpa jargon teknis membingungkan.",
                color: "from-cyan-500 to-teal-500",
                badge: "Thinking & Fast"
              },
              {
                icon: HeartPulse,
                title: "Deteksi Red Flags",
                desc: "Penapisan tanda bahaya dini otomatis untuk mendeteksi kegawatan klinis sebelum terjadi komplikasi lebih lanjut.",
                color: "from-red-500 to-rose-500",
                badge: "Keselamatan Prioritas"
              },
              {
                icon: CalendarCheck,
                title: "Rujukan Spesialis",
                desc: "Rekomendasi poliklinik spesialis yang sesuai dengan pola gejala pasien untuk mempermudah kunjungan rumah sakit.",
                color: "from-teal-500 to-emerald-500",
                badge: "Terarah & Tepat"
              },
              {
                icon: ShieldCheck,
                title: "Privasi Rekam Medis",
                desc: "Data kesehatan bersifat spesifik dilindungi enkripsi penuh. Hak penghapusan permanen sesuai UU PDP No. 27/2022.",
                color: "from-indigo-500 to-cyan-500",
                badge: "Enkripsi AES-256"
              }
            ].map((card, idx) => (
              <div 
                key={idx}
                className="p-6 rounded-3xl bg-slate-50 hover:bg-white border border-slate-200 hover:border-cyan-300 hover:shadow-xl hover:shadow-cyan-500/5 transition-all flex flex-col justify-between space-y-4 group"
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className={`w-12 h-12 rounded-2xl bg-gradient-to-tr ${card.color} flex items-center justify-center text-white shadow-md shadow-slate-300 group-hover:scale-105 transition-transform`}>
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
      <section className="py-12 bg-gradient-to-r from-cyan-800 via-teal-800 to-slate-900 text-white px-4 sm:px-6">
        <div className="max-w-7xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6 sm:gap-8 text-center">
          <div>
            <div className="text-3xl sm:text-4xl font-extrabold text-cyan-300">99.4%</div>
            <div className="text-xs sm:text-sm text-cyan-100 mt-1 font-medium">Akurasi Protokol Klinis</div>
          </div>
          <div>
            <div className="text-3xl sm:text-4xl font-extrabold text-emerald-300">&lt; 1.2 Detik</div>
            <div className="text-xs sm:text-sm text-emerald-100 mt-1 font-medium">Latensi Respons Cepat</div>
          </div>
          <div>
            <div className="text-3xl sm:text-4xl font-extrabold text-teal-300">100%</div>
            <div className="text-xs sm:text-sm text-teal-100 mt-1 font-medium">PII Teranonimkan (UU PDP)</div>
          </div>
          <div>
            <div className="text-3xl sm:text-4xl font-extrabold text-white">24/7</div>
            <div className="text-xs sm:text-sm text-slate-300 mt-1 font-medium">Kesiagaan Konsultasi Digital</div>
          </div>
        </div>
      </section>

      {/* Security & UU PDP Compliance Callout */}
      <section id="keamanan" className="py-16 bg-white border-t border-slate-200 px-4 sm:px-6">
        <div className="max-w-5xl mx-auto rounded-3xl bg-gradient-to-tr from-cyan-900 via-teal-900 to-slate-900 text-white p-8 sm:p-12 shadow-xl relative overflow-hidden">
          <div className="max-w-2xl space-y-5">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/20 text-cyan-300 text-xs font-semibold border border-cyan-400/30">
              <Lock className="w-3.5 h-3.5" />
              <span>Standar Perlindungan Data Kesehatan Indonesia</span>
            </div>
            <h2 className="text-2xl sm:text-4xl font-extrabold tracking-tight">
              Kerahasiaan Medis Anda Terjamin Secara Mutlak
            </h2>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              Setiap pertukaran data dilindungi oleh pemindaian keamanan OWASP Top 10, sanitasi data pengenal (PII De-identification), dan pemenuhan hak subjek data (Right to Erasure) sesuai UU No. 27/2022 Pasal 4, 8, dan 10. Administrator sistem secara ketat dilarang melihat sesi konsultasi pribadi pasien.
            </p>
            <div className="pt-2 flex flex-wrap gap-3">
              <Link
                href="/register"
                className="px-6 py-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs transition shadow-md"
              >
                Daftar Akun Terlindungi
              </Link>
              <Link
                href="/chat"
                className="px-6 py-3 rounded-xl bg-white/10 hover:bg-white/20 text-white font-semibold text-xs border border-white/20 transition"
              >
                Coba Anamnesis Sekarang
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
              <Link href="/register" className="hover:text-white transition">Daftar Pasien</Link>
              <Link href="/chat" className="hover:text-white transition">Chatbot Medis</Link>
              <span className="text-slate-600">|</span>
              <span className="text-emerald-400 font-medium">Sistem Terverifikasi ISO 27001</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
