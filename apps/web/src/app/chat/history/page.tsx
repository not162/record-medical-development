"use client";

import React from "react";
import Link from "next/link";
import { History, MessageSquare, Trash2, ArrowRight } from "lucide-react";

export default function ChatHistoryPage() {
  const mockSessions = [
    {
      id: "sess-001",
      title: "Konsultasi Palpitasi Jantung & Nyeri Dada",
      date: "23 Oktober 2026, 14:20",
      department: "Kardiologi",
      messageCount: 6,
    },
    {
      id: "sess-002",
      title: "Gejala Batuk Berdahak & Mengi Akut",
      date: "21 Oktober 2026, 09:45",
      department: "Pulmonologi",
      messageCount: 4,
    },
    {
      id: "sess-003",
      title: "Pemeriksaan Pola Diet & Gula Darah Tinggi",
      date: "18 Oktober 2026, 16:10",
      department: "Endokrinologi",
      messageCount: 8,
    },
  ];

  return (
    <div className="flex-1 p-6 max-w-4xl w-full mx-auto space-y-6 bg-slate-50 min-h-full">
      <div className="flex items-center justify-between pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <History className="w-5 h-5 text-cyan-700" />
            <span>Riwayat Sesi Percakapan Klinis</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Daftar konsultasi sebelumnya yang tersimpan dengan aman pada database pasien.
          </p>
        </div>

        <Link
          href="/chat"
          className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white font-semibold text-xs transition shadow-md shadow-cyan-600/20"
        >
          Mulai Percakapan Baru
        </Link>
      </div>

      <div className="space-y-3">
        {mockSessions.map((session) => (
          <div
            key={session.id}
            className="p-4 rounded-2xl bg-white border border-slate-200 hover:border-cyan-400 hover:shadow-md transition shadow-xs flex items-center justify-between gap-4"
          >
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-cyan-50 border border-cyan-200 flex items-center justify-center text-cyan-700 shrink-0 mt-0.5">
                <MessageSquare className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-900">{session.title}</h3>
                <div className="flex items-center gap-3 text-xs text-slate-500 mt-1">
                  <span>{session.date}</span>
                  <span>•</span>
                  <span className="px-2 py-0.5 rounded bg-cyan-50 text-cyan-800 border border-cyan-200 text-[11px] font-medium">
                    {session.department}
                  </span>
                  <span>•</span>
                  <span>{session.messageCount} pesan</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Link
                href="/chat"
                className="p-2 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 text-cyan-700 hover:text-cyan-800 transition shadow-xs"
                title="Buka Sesi"
              >
                <ArrowRight className="w-4 h-4" />
              </Link>
              <button
                className="p-2 rounded-lg bg-slate-50 hover:bg-red-50 border border-slate-200 text-slate-400 hover:text-red-600 transition shadow-xs"
                title="Hapus Sesi"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
