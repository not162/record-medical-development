"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { History, MessageSquare, Trash2, ArrowRight, Loader2, AlertCircle, FileText, PlusCircle } from "lucide-react";
import { api, SessionItem } from "@/lib/api";

export default function ChatHistoryPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchInitialSessions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.chat.listSessions(20);
      setSessions(res.items || []);
      setHasMore(res.has_more);
      setNextCursor(res.next_cursor || null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Gagal memuat riwayat sesi konsultasi.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void Promise.resolve().then(() => {
      fetchInitialSessions();
    });
  }, [fetchInitialSessions]);

  const handleLoadMore = async () => {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const res = await api.chat.listSessions(20, nextCursor);
      setSessions((prev) => [...prev, ...(res.items || [])]);
      setHasMore(res.has_more);
      setNextCursor(res.next_cursor || null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Gagal memuat sesi tambahan.");
    } finally {
      setLoadingMore(false);
    }
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Apakah Anda yakin ingin menghapus arsip sesi percakapan ini?")) return;

    setDeletingId(sessionId);
    try {
      await api.chat.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Gagal menghapus sesi.");
    } finally {
      setDeletingId(null);
    }
  };

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString("id-ID", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="flex-1 p-4 sm:p-6 max-w-4xl w-full mx-auto space-y-6 bg-slate-50 min-h-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <History className="w-5 h-5 text-cyan-700" />
            <span>Riwayat Sesi Percakapan Klinis</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Daftar konsultasi sebelumnya yang tersimpan dengan aman pada database terisolasi pasien (UU PDP).
          </p>
        </div>

        <Link
          href="/chat"
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white font-semibold text-xs transition shadow-md shadow-cyan-600/20"
        >
          <PlusCircle className="w-4 h-4" />
          <span>Mulai Konsultasi Baru</span>
        </Link>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3 text-xs text-red-700">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span>{error}</span>
            <button
              onClick={fetchInitialSessions}
              className="ml-3 underline font-semibold hover:text-red-900"
            >
              Coba lagi
            </button>
          </div>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="p-4 rounded-2xl bg-white border border-slate-200 animate-pulse flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-slate-100 shrink-0" />
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-slate-100 rounded w-1/3" />
                <div className="h-3 bg-slate-100 rounded w-1/4" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && sessions.length === 0 && !error && (
        <div className="text-center py-16 px-4 bg-white border border-slate-200 rounded-2xl space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-cyan-50 text-cyan-600 flex items-center justify-center mx-auto">
            <MessageSquare className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-slate-800">Belum Ada Riwayat Percakapan</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Mulai sesi konsultasi medis pertama Anda untuk mendapatkan edukasi klinis yang dipandu asisten berdasar panduan resmi.
          </p>
          <div className="pt-2">
            <Link
              href="/chat"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white font-medium text-xs transition"
            >
              Mulai Konsultasi Sekarang
            </Link>
          </div>
        </div>
      )}

      {/* Session List */}
      {!loading && sessions.length > 0 && (
        <div className="space-y-3">
          {sessions.map((session) => (
            <div
              key={session.id}
              onClick={() => router.push(`/chat?session_id=${session.id}`)}
              className="p-4 rounded-2xl bg-white border border-slate-200 hover:border-cyan-400 hover:shadow-md transition cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="flex items-start gap-3.5 flex-1 min-w-0">
                <div className="w-10 h-10 rounded-xl bg-cyan-50 border border-cyan-200 flex items-center justify-center text-cyan-700 shrink-0 mt-0.5">
                  <MessageSquare className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-slate-900 truncate">{session.title}</h3>
                  {session.summary && (
                    <p className="text-xs text-slate-600 mt-1 line-clamp-2 leading-relaxed bg-slate-50 p-2 rounded-lg border border-slate-100 flex items-start gap-1.5">
                      <FileText className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                      <span>{session.summary}</span>
                    </p>
                  )}
                  <div className="flex flex-wrap items-center gap-2.5 text-[11px] text-slate-500 mt-2">
                    <span>{formatDate(session.updated_at || session.created_at)}</span>
                    <span>•</span>
                    <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 font-medium">
                      {session.message_count} pesan
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    router.push(`/chat?session_id=${session.id}`);
                  }}
                  className="p-2 rounded-xl bg-slate-50 hover:bg-cyan-50 border border-slate-200 text-slate-600 hover:text-cyan-700 transition"
                  title="Buka Sesi"
                >
                  <ArrowRight className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  disabled={deletingId === session.id}
                  onClick={(e) => handleDeleteSession(session.id, e)}
                  className="p-2 rounded-xl bg-slate-50 hover:bg-red-50 border border-slate-200 text-slate-400 hover:text-red-600 transition disabled:opacity-50"
                  title="Hapus Sesi"
                >
                  {deletingId === session.id ? (
                    <Loader2 className="w-4 h-4 animate-spin text-red-600" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>
          ))}

          {/* Load More Button */}
          {hasMore && (
            <div className="pt-2 text-center">
              <button
                type="button"
                disabled={loadingMore}
                onClick={handleLoadMore}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-300 text-xs font-semibold text-slate-700 transition shadow-xs disabled:opacity-50"
              >
                {loadingMore ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-600" />
                    <span>Memuat sesi sebelumnya...</span>
                  </>
                ) : (
                  <span>Muat Sesi Lainnya (20 per halaman)</span>
                )}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
