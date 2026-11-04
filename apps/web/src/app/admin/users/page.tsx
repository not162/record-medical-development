"use client";

import React, { useMemo, useState } from "react";
import { useLiveQuery, useLiveMutation, LiveIndicator } from "@/lib/realtime";
import { Users, RefreshCw, AlertTriangle, Search } from "lucide-react";
import { api, ManagedUser, UserRole } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { roleLabel } from "@/lib/roles";

const USERS_KEY = ["admin", "users"] as const;

const ROLE_OPTIONS: UserRole[] = ["USER", "ADMIN", "RESEARCHER"];

const BADGE: Record<UserRole, string> = {
  USER: "bg-slate-100 text-slate-700 border-slate-200",
  ADMIN: "bg-emerald-50 text-emerald-700 border-emerald-200",
  RESEARCHER: "bg-sky-50 text-sky-700 border-sky-200",
};

function friendlyError(err: unknown, fallback: string): string {
  const msg = err instanceof Error ? err.message : "";
  if (/403|izin|forbidden/i.test(msg)) return "Anda tidak punya izin untuk aksi ini. Hanya Admin Riset yang boleh.";
  if (/404|tidak ditemukan/i.test(msg)) return "Data pengguna tidak ditemukan. Muat ulang daftar lalu coba lagi.";
  if (/Failed to fetch|NetworkError/i.test(msg)) return "Tidak bisa terhubung ke server. Cek koneksi internet Anda.";
  return msg || fallback;
}

export default function ManageUsersPage() {
  const { user: me } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  // Real-time: daftar pengguna dipoll tiap 5 dtk + sinkron antar-tab; PATCH optimistik.
  const usersQuery = useLiveQuery<ManagedUser[]>(USERS_KEY, () => api.admin.users.list());
  const users = useMemo(() => usersQuery.data ?? [], [usersQuery.data]);
  const loading = usersQuery.isFetching;
  const loadError = usersQuery.error ? friendlyError(usersQuery.error, "Gagal memuat daftar pengguna.") : null;
  const load = () => usersQuery.refetch();

  const patchUser = useLiveMutation<ManagedUser, { id: string; patch: { role?: UserRole; is_active?: boolean } }, ManagedUser>(
    USERS_KEY,
    ({ id, patch }) => api.admin.users.update(id, patch),
    (list, { id, patch }) => list.map((x) => (x.id === id ? { ...x, ...patch } : x))
  );

  const update = async (u: ManagedUser, patch: { role?: UserRole; is_active?: boolean }, okMsg: string) => {
    setBusyId(u.id);
    setError(null);
    setNotice(null);
    try {
      await patchUser.mutateAsync({ id: u.id, patch });
      setNotice(okMsg);
    } catch (err) {
      setError(friendlyError(err, "Perubahan gagal disimpan."));
    } finally {
      setBusyId(null);
    }
  };

  const onChangeRole = (u: ManagedUser, role: UserRole) => {
    if (role === u.role) return;
    if (u.id === me?.id) {
      setError("Anda tidak bisa mengubah peran akun Anda sendiri.");
      return;
    }
    const ok = window.confirm(`Ubah peran ${u.username} menjadi ${roleLabel(role)}?`);
    if (!ok) return;
    update(u, { role }, `Peran ${u.username} sekarang ${roleLabel(role)}.`);
  };

  const onToggleActive = (u: ManagedUser) => {
    if (u.id === me?.id) {
      setError("Anda tidak bisa menonaktifkan akun Anda sendiri.");
      return;
    }
    const next = !u.is_active;
    update(u, { is_active: next }, `Akun ${u.username} ${next ? "diaktifkan" : "dinonaktifkan"}.`);
  };

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return users;
    return users.filter((u) =>
      [u.username, u.email, u.full_name ?? ""].some((v) => v.toLowerCase().includes(q))
    );
  }, [users, query]);

  return (
    <div className="space-y-5 max-w-6xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Users className="w-5 h-5 text-sky-600" />
            Kelola Pengguna
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Atur peran dan status akun. Halaman ini hanya untuk Admin Riset (Superadmin).
          </p>
          <LiveIndicator
            className="mt-2"
            updatedAt={usersQuery.dataUpdatedAt}
            isFetching={usersQuery.isFetching}
            isError={usersQuery.isError}
          />
        </div>
        <button
          onClick={() => load()}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 text-xs font-semibold text-slate-700 disabled:opacity-50 self-start"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Muat ulang
        </button>
      </div>

      {(error || loadError) && (
        <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error || loadError}</span>
        </div>
      )}
      {notice && (
        <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800">{notice}</div>
      )}

      <div className="relative max-w-sm">
        <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Cari nama, username, atau email"
          className="w-full pl-9 pr-3 py-2 text-xs bg-white border border-slate-200 rounded-xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-200"
        />
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-x-auto">
        <table className="w-full text-xs text-left">
          <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
            <tr>
              <th className="px-4 py-3 font-semibold">Pengguna</th>
              <th className="px-4 py-3 font-semibold">Email</th>
              <th className="px-4 py-3 font-semibold">Peran</th>
              <th className="px-4 py-3 font-semibold">Ganti peran</th>
              <th className="px-4 py-3 font-semibold">Aktif</th>
              <th className="px-4 py-3 font-semibold">Dibuat</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && users.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-500">Memuat data...</td>
              </tr>
            )}
            {!loading && filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                  {users.length === 0 ? "Belum ada pengguna." : "Tidak ada pengguna yang cocok."}
                </td>
              </tr>
            )}
            {filtered.map((u) => {
              const isMe = u.id === me?.id;
              const busy = busyId === u.id;
              return (
                <tr key={u.id} className="hover:bg-slate-50/60">
                  <td className="px-4 py-3">
                    <p className="font-semibold text-slate-900">{u.full_name || u.username}</p>
                    <p className="text-slate-500">@{u.username}{isMe ? " (Anda)" : ""}</p>
                  </td>
                  <td className="px-4 py-3 text-slate-700">{u.email}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2 py-0.5 rounded border font-semibold ${BADGE[u.role]}`}>
                      {roleLabel(u.role)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <select
                      value={u.role}
                      disabled={busy || isMe}
                      onChange={(e) => onChangeRole(u, e.target.value as UserRole)}
                      aria-label={`Ganti peran ${u.username}`}
                      className="px-2 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-800 disabled:opacity-50"
                    >
                      {ROLE_OPTIONS.map((r) => (
                        <option key={r} value={r}>{roleLabel(r)}</option>
                      ))}
                    </select>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      role="switch"
                      aria-checked={u.is_active}
                      aria-label={`${u.is_active ? "Nonaktifkan" : "Aktifkan"} ${u.username}`}
                      disabled={busy || isMe}
                      onClick={() => onToggleActive(u)}
                      className={`relative inline-flex h-5 w-9 items-center rounded-full transition disabled:opacity-50 ${
                        u.is_active ? "bg-emerald-500" : "bg-slate-300"
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${
                          u.is_active ? "translate-x-4" : "translate-x-0.5"
                        }`}
                      />
                    </button>
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {u.created_at ? new Date(u.created_at).toLocaleDateString("id-ID") : "-"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
