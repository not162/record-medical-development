"use client";

import React, { useEffect, useState, useCallback } from "react";
import { ShieldAlert, RefreshCw, Filter, ShieldCheck, Lock, FileCheck } from "lucide-react";
import { api, AuditLog } from "@/lib/api";

const getComplianceTag = (action: string) => {
  const a = action.toUpperCase();
  if (a.includes("AUTH") || a.includes("LOGIN") || a.includes("ROLE") || a.includes("ADMIN")) {
    return { tag: "ISO 27001 (A.9)", color: "bg-cyan-50 text-cyan-800 border-cyan-200" };
  }
  if (a.includes("CHAT") || a.includes("MESSAGE") || a.includes("PATIENT") || a.includes("TRIAGE")) {
    return { tag: "HIPAA / Permenkes", color: "bg-emerald-50 text-emerald-800 border-emerald-200" };
  }
  if (a.includes("DELETE") || a.includes("ERASURE") || a.includes("EXPORT")) {
    return { tag: "GDPR (Art. 17/20)", color: "bg-amber-50 text-amber-800 border-amber-200" };
  }
  return { tag: "ISO 27001 (A.12)", color: "bg-slate-100 text-slate-700 border-slate-200" };
};

export default function AdminAuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState<string>("");
  const [limit, setLimit] = useState(50);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.admin.getAuditLogs(limit, 0);
      if (actionFilter) {
        setLogs(data.filter((l) => l.action.toLowerCase().includes(actionFilter.toLowerCase())));
      } else {
        setLogs(data);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [actionFilter, limit]);

  useEffect(() => {
    let ignore = false;
    const run = async () => {
      try {
        const data = await api.admin.getAuditLogs(limit, 0);
        if (!ignore) {
          if (actionFilter) {
            setLogs(data.filter((l) => l.action.toLowerCase().includes(actionFilter.toLowerCase())));
          } else {
            setLogs(data);
          }
          setLoading(false);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setError(err instanceof Error ? err.message : String(err));
          setLoading(false);
        }
      }
    };
    run();
    return () => {
      ignore = true;
    };
  }, [actionFilter, limit]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-emerald-600" />
            <span>Audit Trail & Log Keamanan Sistem</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Catatan permanen transaksi, otentikasi, perizinan, dan aktivitas administratif untuk kepatuhan ISO 27001, GDPR, HIPAA, dan Permenkes No. 12 Tahun 2025.
          </p>
        </div>

        <button
          onClick={fetchLogs}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-semibold shadow-xs transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-emerald-600 ${loading ? "animate-spin" : ""}`} />
          <span>Muat Ulang</span>
        </button>
      </div>

      {/* Compliance Standards Badges */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
        <div className="p-2.5 rounded-xl bg-white border border-slate-200 flex items-center gap-2 shadow-2xs">
          <Lock className="w-4 h-4 text-cyan-600 shrink-0" />
          <div>
            <div className="font-bold text-slate-800 text-[11px]">ISO/IEC 27001:2022</div>
            <div className="text-[9px] text-slate-500">Annex A.9 & A.12 Audit Trail</div>
          </div>
        </div>

        <div className="p-2.5 rounded-xl bg-white border border-slate-200 flex items-center gap-2 shadow-2xs">
          <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
          <div>
            <div className="font-bold text-slate-800 text-[11px]">HIPAA § 164.312(b)</div>
            <div className="text-[9px] text-slate-500">Audit Controls & PHI Safeguards</div>
          </div>
        </div>

        <div className="p-2.5 rounded-xl bg-white border border-slate-200 flex items-center gap-2 shadow-2xs">
          <FileCheck className="w-4 h-4 text-amber-600 shrink-0" />
          <div>
            <div className="font-bold text-slate-800 text-[11px]">GDPR Art. 30</div>
            <div className="text-[9px] text-slate-500">Records of Processing (ROPA)</div>
          </div>
        </div>

        <div className="p-2.5 rounded-xl bg-white border border-slate-200 flex items-center gap-2 shadow-2xs">
          <ShieldAlert className="w-4 h-4 text-violet-600 shrink-0" />
          <div>
            <div className="font-bold text-slate-800 text-[11px]">Permenkes No. 12/2025</div>
            <div className="text-[9px] text-slate-500">Standar Audit Trail RME Nasional</div>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700">
          {error}
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-4 text-xs">
        <div className="flex items-center gap-3">
          <Filter className="w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Cari aksi (misal: LOGIN, REGISTRATION)..."
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:outline-none focus:border-emerald-500 focus:bg-white"
          />
        </div>

        <div className="flex items-center gap-2 text-slate-600">
          <span>Batas Baris:</span>
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="px-2 py-1 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:outline-none"
          >
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
              <tr>
                <th className="py-3 px-4 font-semibold">ID</th>
                <th className="py-3 px-4 font-semibold">Waktu (WIB)</th>
                <th className="py-3 px-4 font-semibold">User ID</th>
                <th className="py-3 px-4 font-semibold">Aksi</th>
                <th className="py-3 px-4 font-semibold">Kepatuhan Regulasi</th>
                <th className="py-3 px-4 font-semibold">Resource</th>
                <th className="py-3 px-4 font-semibold">Status</th>
                <th className="py-3 px-4 font-semibold">IP Address</th>
                <th className="py-3 px-4 font-semibold">Rincian Peristiwa</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-slate-400 font-sans">
                    {loading ? "Memuat catatan audit log..." : "Tidak ada catatan audit yang cocok dengan filter."}
                  </td>
                </tr>
              ) : (
                logs.map((log) => {
                  const comp = getComplianceTag(log.action);
                  return (
                    <tr key={log.id} className="hover:bg-slate-50/80 transition">
                      <td className="py-2.5 px-4 text-slate-400 truncate max-w-[80px]">{log.id.substring(0, 8)}...</td>
                      <td className="py-2.5 px-4 text-slate-600 font-sans whitespace-nowrap">
                        {new Date(log.created_at).toLocaleString("id-ID")}
                      </td>
                      <td className="py-2.5 px-4 text-slate-600 truncate max-w-[90px]">
                        {log.user_id ? `${log.user_id.substring(0, 8)}...` : "ANONYMOUS"}
                      </td>
                      <td className="py-2.5 px-4 font-bold text-cyan-700">{log.action}</td>
                      <td className="py-2.5 px-4">
                        <span className={`px-2 py-0.5 rounded-md text-[9px] font-sans font-bold border ${comp.color}`}>
                          {comp.tag}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 text-slate-700 font-sans">{log.resource_type}</td>
                      <td className="py-2.5 px-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold font-sans ${
                            log.status === "SUCCESS"
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : "bg-red-50 text-red-700 border border-red-200"
                          }`}
                        >
                          {log.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 text-slate-500">{log.ip_address || "127.0.0.1"}</td>
                      <td className="py-2.5 px-4 text-slate-600 font-sans max-w-xs truncate">
                        {log.details || "-"}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
