"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { 
  Bot, ShieldCheck, Database, Stethoscope, ArrowRight, 
  Activity, Sparkles, BrainCircuit
} from "lucide-react";

export default function HomePage() {
  const { user, isAuthenticated, role } = useAuth();

  return (
    <div className="flex-1 flex flex-col justify-between bg-slate-50 min-h-screen">
      {/* Top Navigation */}
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-emerald-600 flex items-center justify-center shadow-md shadow-cyan-600/20">
              <Stethoscope className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-cyan-700 to-teal-700 bg-clip-text text-transparent">
                RSUKT Clinical AI
              </span>
              <span className="ml-2 text-xs uppercase px-2 py-0.5 rounded-full bg-cyan-50 text-cyan-700 border border-cyan-200 font-semibold tracking-wider">
                v2.0
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {isAuthenticated ? (
              <div className="flex items-center space-x-3">
                <span className="text-sm text-slate-600">
                  Login sebagai: <strong className="text-cyan-700">{user?.username}</strong> ({role})
                </span>
                {role === "ADMIN" ? (
                  <Link
                    href="/admin/dashboard"
                    className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm transition shadow-md shadow-emerald-600/20"
                  >
                    Buka Admin Console
                  </Link>
                ) : (
                  <Link
                    href="/chat"
                    className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white font-medium text-sm transition shadow-md shadow-cyan-600/20"
                  >
                    Buka Chatbot Klinis
                  </Link>
                )}
              </div>
            ) : (
              <div className="flex items-center space-x-3">
                <Link
                  href="/login"
                  className="px-4 py-2 rounded-xl text-sm font-medium text-slate-600 hover:text-slate-900 transition"
                >
                  Masuk (Login)
                </Link>
                <Link
                  href="/register"
                  className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white font-medium text-sm transition shadow-md shadow-cyan-600/20"
                >
                  Daftar Akun
                </Link>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="max-w-7xl mx-auto px-6 py-16 flex-1 flex flex-col justify-center">
        <div className="text-center max-w-3xl mx-auto space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-50 border border-cyan-200 text-cyan-800 text-xs font-semibold tracking-wide shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-cyan-600" />
            <span>Sistem Asisten Klinis Berbasis Bukti & Audit-Gated</span>
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-slate-900 leading-tight">
            Kecerdasan Buatan Medis Terpadu{" "}
            <span className="bg-gradient-to-r from-cyan-600 via-teal-600 to-emerald-600 bg-clip-text text-transparent">
              RS RSUKT
            </span>
          </h1>

          <p className="text-slate-600 text-base sm:text-lg leading-relaxed">
            Platform AI klinis dual-workspace: Chatbot edukasi kesehatan pasien dengan sitasi bukti protokol terverifikasi, serta Workspace Riset Data untuk kurasi dataset, pelatihan model IndoBERT & random forest, dan evaluasi akurasi sistematis.
          </p>

          <div className="pt-4 flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/chat"
              className="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-700 hover:to-teal-700 text-white font-semibold text-sm shadow-lg shadow-cyan-600/20 transition transform hover:-translate-y-0.5"
            >
              <Bot className="w-5 h-5" />
              <span>Mulai Chatbot Klinis</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </Link>

            <Link
              href="/admin/dashboard"
              className="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl bg-white hover:bg-slate-100 border border-slate-300 text-slate-700 font-semibold text-sm transition shadow-sm transform hover:-translate-y-0.5"
            >
              <Database className="w-5 h-5 text-emerald-600" />
              <span>Workspace Admin & Riset</span>
            </Link>
          </div>
        </div>

        {/* Feature Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-20">
          <div className="glass-card p-6 rounded-2xl hover:border-cyan-300 hover:shadow-md transition">
            <div className="w-12 h-12 rounded-xl bg-cyan-50 border border-cyan-200 flex items-center justify-center text-cyan-600 mb-4 shadow-sm">
              <Bot className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 mb-2">Evidence-Grounded RAG</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Setiap respons jawaban didukung kutipan protokol medis resmi RS RSUKT. Tidak ada halusinasi data dan disertai disclaimer batasan klinis.
            </p>
          </div>

          <div className="glass-card p-6 rounded-2xl hover:border-emerald-300 hover:shadow-md transition">
            <div className="w-12 h-12 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 mb-4 shadow-sm">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 mb-2">Safety Guardrail & Triase</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Mendeteksi kontraindikasi fatal (misal Beta-blocker pada asma) dan kalkulasi risiko serangan jantung berbasis populasi 15.000 pasien Indonesia.
            </p>
          </div>

          <div className="glass-card p-6 rounded-2xl hover:border-indigo-300 hover:shadow-md transition">
            <div className="w-12 h-12 rounded-xl bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600 mb-4 shadow-sm">
              <BrainCircuit className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 mb-2">Laboratorium Riset ML</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Ruang kerja administrator untuk mengunggah CSV, TXT, dan JSONL, mengelola anotasi penalaran klinis, serta melatih model terverifikasi.
            </p>
          </div>
        </div>

        {/* Clinical Disclaimer Notice */}
        <div className="mt-16 p-4 rounded-xl bg-amber-50 border border-amber-200 flex items-start gap-3 shadow-sm">
          <Activity className="w-5 h-5 text-amber-600 mt-0.5 shrink-0" />
          <div className="text-xs text-amber-900 leading-relaxed">
            <strong>Pemberitahuan Keselamatan Klinis:</strong> Asisten AI ini dirancang untuk tujuan pemberian informasi kesehatan berbasis bukti dan riset evaluatif. Sistem ini <strong>bukan pengganti diagnosis medis resmi</strong>, tidak dapat meresepkan obat secara mandiri, dan tidak membuat keputusan tata laksana pasien darurat. Bila Anda mengalami kegawatdaruratan medis, segera kunjungi Instalasi Gawat Darurat (IGD) rumah sakit terdekat.
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <span>&copy; 2026 RS RSUKT. All rights reserved. Clinical AI Research Platform.</span>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5 text-emerald-600 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              FastAPI + SQLite Engine Online
            </span>
            <span className="text-slate-300">•</span>
            <span>Groq LLM Verified</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
