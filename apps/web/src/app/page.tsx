"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { 
  Stethoscope, Bot, ShieldCheck, ArrowRight, Activity, 
  Sparkles, Lock, HeartPulse, Clock, FileCheck, CheckCircle2,
  CalendarCheck, UserCheck, AlertTriangle, ChevronRight, Phone
} from "lucide-react";

export default function HomePage() {
  const { user, isAuthenticated, role } = useAuth();

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
              <p className="text-[10px] text-slate-500 hidden sm:block">
                All-in-One Health AI & Rekam Medis Terpadu
              </p>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-6 text-xs font-semibold text-slate-600">
            <a href="#layanan" className="hover:text-cyan-700 transition">Layanan Klinis</a>
            <a href="#keunggulan" className="hover:text-cyan-700 transition">Keunggulan</a>
            <a href="#alur" className="hover:text-cyan-700 transition">Cara Kerja</a>
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
      <section className="relative overflow-hidden pt-8 pb-16 sm:py-24 px-4 sm:px-6">
        {/* Glow ambient backdrops */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[30rem] sm:w-[45rem] h-[25rem] bg-gradient-to-tr from-cyan-400/20 via-teal-300/20 to-emerald-400/20 rounded-full blur-3xl pointer-events-none -z-10"></div>

        <div className="max-w-5xl mx-auto text-center space-y-6 sm:space-y-8">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyan-50 border border-cyan-200/80 text-cyan-800 text-xs font-semibold shadow-xs">
            <Sparkles className="w-3.5 h-3.5 text-cyan-600 animate-pulse" />
            <span>All-in-One Health, Better Living — RSUKT Clinical Suite</span>
          </div>

          <h1 className="text-3xl sm:text-5xl md:text-6xl font-extrabold text-slate-900 tracking-tight leading-[1.15]">
            Layanan Kesehatan Digital Terpadu{" "}
            <span className="block mt-1 sm:mt-2 bg-gradient-to-r from-cyan-600 via-teal-600 to-emerald-600 bg-clip-text text-transparent">
              Lebih Cepat, Tepat, dan Tepercaya
            </span>
          </h1>

          <p className="max-w-2xl mx-auto text-slate-600 text-sm sm:text-base md:text-lg leading-relaxed">
            Platform kecerdasan buatan medis terintegrasi: anamnesis keluhan mandiri berbasis protokol klinis terverifikasi, penapisan tanda bahaya dini, serta penjadwalan poliklinik terpadu yang aman sesuai regulasi kesehatan nasional.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 pt-2">
            <Link
              href="/chat"
              className="w-full sm:w-auto px-7 py-3.5 rounded-2xl bg-gradient-to-r from-cyan-600 via-teal-600 to-emerald-600 hover:from-cyan-700 hover:to-emerald-700 text-white font-bold text-sm shadow-xl shadow-cyan-600/25 transition transform hover:-translate-y-0.5 flex items-center justify-center gap-2"
            >
              <Bot className="w-4 h-4" />
              <span>Mulai Anamnesis Klinis Sekarang</span>
              <ArrowRight className="w-4 h-4" />
            </Link>

            <Link
              href="/login"
              className="w-full sm:w-auto px-6 py-3.5 rounded-2xl bg-white hover:bg-slate-50 text-slate-700 font-semibold text-sm border border-slate-300 shadow-xs transition flex items-center justify-center gap-2"
            >
              <span>Akses Workspace Riset Medis</span>
              <ChevronRight className="w-4 h-4 text-slate-400" />
            </Link>
          </div>

          {/* Trust Badges */}
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
              <FileCheck className="w-4 h-4 text-indigo-600" />
              <span>Standar Permenkes No. 12/2025</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-teal-600" />
              <span>Verifikasi Keamanan OWASP Top 10</span>
            </div>
          </div>
        </div>

        {/* Live Interface Preview Mockup */}
        <div className="max-w-4xl mx-auto mt-12 sm:mt-16 bg-white rounded-3xl border border-slate-200/90 shadow-2xl shadow-slate-200/60 overflow-hidden">
          <div className="p-3 sm:p-4 bg-slate-100/80 border-b border-slate-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-400"></div>
              <div className="w-3 h-3 rounded-full bg-amber-400"></div>
              <div className="w-3 h-3 rounded-full bg-emerald-400"></div>
              <span className="text-[11px] text-slate-500 font-medium ml-2">Simulasi Konsultasi Asisten AI Klinis RSUKT</span>
            </div>
            <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
              Sistem Aktif 24/7
            </span>
          </div>

          <div className="p-5 sm:p-8 space-y-4 text-left">
            {/* User message */}
            <div className="flex justify-end">
              <div className="max-w-lg bg-cyan-600 text-white p-3.5 rounded-2xl rounded-tr-xs text-xs sm:text-sm leading-relaxed shadow-sm">
                Pasien mengeluhkan tensi 145/90 mmHg, pusing berputar, dan rasa berat di tengkuk leher sejak kemarin malam.
              </div>
            </div>

            {/* AI Assistant response */}
            <div className="flex gap-3 items-start max-w-2xl">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-600 to-emerald-600 flex items-center justify-center text-white shrink-0 shadow-sm mt-1">
                <Bot className="w-4 h-4" />
              </div>
              <div className="bg-slate-50 border border-slate-200 p-4 rounded-2xl rounded-tl-xs text-xs sm:text-sm leading-relaxed text-slate-800 space-y-2.5 shadow-xs">
                <div className="font-bold text-slate-900 border-b border-slate-200 pb-1.5 flex items-center justify-between">
                  <span>Telaah Anamnesis Klinis Awal</span>
                  <span className="text-[10px] font-normal px-2 py-0.5 rounded bg-cyan-100 text-cyan-800 font-medium">Thinking Mode</span>
                </div>
                <p>
                  Berdasarkan tanda vital yang disampaikan, tekanan darah 145/90 mmHg tergolong <strong>Hipertensi Derajat 1</strong>. Sensasi pusing berputar disertai rasa tegang pada tengkuk dapat berkaitan dengan respon vaskular maupun gangguan keseimbangan perifer (seperti vertigo posisi).
                </p>
                <div className="bg-amber-50 border border-amber-200 p-2.5 rounded-xl text-amber-900 text-[11px] space-y-1">
                  <div className="font-bold flex items-center gap-1 text-amber-800">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                    <span>Langkah Rekomendasi Pertama:</span>
                  </div>
                  <ul className="list-disc list-inside space-y-0.5">
                    <li>Istirahat tenang selama 10-15 menit dalam posisi duduk santai dan ukur ulang tekanan darah.</li>
                    <li>Batasi asupan garam, hindari konsumsi kafein atau rokok saat ini.</li>
                    <li>Segera periksakan diri ke Instalasi Gawat Darurat jika muncul nyeri dada, sesak napas, atau kelemahan satu sisi tubuh.</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4 Core Pillars Section (Inspired by Zavora Life) */}
      <section id="layanan" className="py-16 bg-white border-y border-slate-200 px-4 sm:px-6">
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

      {/* Step by Step Workflow */}
      <section id="alur" className="py-16 bg-slate-50 px-4 sm:px-6">
        <div className="max-w-5xl mx-auto space-y-12 text-center">
          <div className="space-y-3">
            <span className="text-xs font-bold text-teal-700 uppercase tracking-widest">Alur Pelayanan</span>
            <h2 className="text-2xl sm:text-4xl font-extrabold text-slate-900">
              3 Langkah Mudah Konsultasi Pasien
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 max-w-lg mx-auto">
              Proses interaksi yang intuitif dan nyaman untuk membantu kebutuhan informasi kesehatan Anda.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-left">
            {[
              {
                step: "01",
                title: "Sampaikan Keluhan",
                desc: "Tuliskan gejala yang Anda rasakan seperti pusing, batuk, tensi tinggi, atau durasi keluhan dalam bahasa sehari-hari."
              },
              {
                step: "02",
                title: "Telaah AI Klinis",
                desc: "Model AI menganalisis gejala dengan panduan protokol medis terverifikasi, mengevaluasi tanda bahaya, dan menyusun saran awal."
              },
              {
                step: "03",
                title: "Tindakan & Rujukan",
                desc: "Dapatkan petunjuk pertolongan mandiri yang aman dan informasi poliklinik spesialis rujukan untuk evaluasi dokter langsung."
              }
            ].map((item, idx) => (
              <div key={idx} className="bg-white p-6 rounded-3xl border border-slate-200/90 shadow-sm space-y-4 relative">
                <span className="text-4xl font-black text-cyan-100 block">{item.step}</span>
                <h3 className="font-bold text-base text-slate-900">{item.title}</h3>
                <p className="text-xs text-slate-600 leading-relaxed">{item.desc}</p>
              </div>
            ))}
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
              © 2026 Rumah Sakit Umum & Klinik Terpadu (RSUKT). Hak Cipta Dilindungi Undang-Undang.
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
