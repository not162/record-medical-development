"use client";

/**
 * Lapisan real-time untuk CRUD.
 *
 * Backend berjalan sebagai fungsi serverless (Vercel, maks 30 dtk) sehingga koneksi
 * WebSocket/SSE yang panjang tidak andal. Maka "real-time" diwujudkan dengan:
 *   1. Polling ringan (default 5 dtk) hanya saat tab terlihat + refetch saat fokus/online.
 *   2. Sinkron antar-tab/jendela lewat BroadcastChannel: setiap POST/PUT/DELETE langsung
 *      memicu refetch di semua tab yang membuka data yang sama (tanpa menunggu polling).
 *   3. Optimistic update pada mutasi agar UI langsung berubah, lalu dikonfirmasi server.
 */

import { useEffect, useState } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryKey,
  type UseQueryOptions,
} from "@tanstack/react-query";

export const LIVE_INTERVAL_MS = 5000;
const CHANNEL = "klinik-live";

let channel: BroadcastChannel | null = null;
function getChannel(): BroadcastChannel | null {
  if (typeof window === "undefined" || typeof BroadcastChannel === "undefined") return null;
  if (!channel) channel = new BroadcastChannel(CHANNEL);
  return channel;
}

/** Beri tahu tab lain bahwa data dengan key ini berubah. */
export function broadcastChange(key: QueryKey) {
  getChannel()?.postMessage({ type: "invalidate", key });
}

/** Dipasang sekali di Providers: menerima sinyal perubahan dari tab lain. */
export function useLiveSync() {
  const qc = useQueryClient();
  useEffect(() => {
    const ch = getChannel();
    if (!ch) return;
    const onMsg = (e: MessageEvent) => {
      if (e.data?.type === "invalidate" && Array.isArray(e.data.key)) {
        qc.invalidateQueries({ queryKey: e.data.key });
      }
    };
    ch.addEventListener("message", onMsg);
    return () => ch.removeEventListener("message", onMsg);
  }, [qc]);
}

/** useQuery yang selalu segar: polling saat terlihat, refetch saat fokus & online. */
export function useLiveQuery<T>(
  key: QueryKey,
  fetcher: () => Promise<T>,
  options: Partial<UseQueryOptions<T>> & { intervalMs?: number } = {}
) {
  const { intervalMs = LIVE_INTERVAL_MS, ...rest } = options;
  return useQuery<T>({
    queryKey: key,
    queryFn: fetcher,
    refetchInterval: intervalMs,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
    staleTime: 0,
    retry: 1,
    ...rest,
  });
}

type ListUpdater<TItem, TVars> = (list: TItem[], vars: TVars) => TItem[];

/**
 * Mutasi CRUD dengan optimistic update + rollback + sinkron antar-tab.
 * `optimistic` menerima list saat ini dan mengembalikan list baru sebelum server menjawab.
 */
export function useLiveMutation<TItem, TVars, TResult = unknown>(
  key: QueryKey,
  mutationFn: (vars: TVars) => Promise<TResult>,
  optimistic?: ListUpdater<TItem, TVars>
) {
  const qc = useQueryClient();
  return useMutation<TResult, Error, TVars, { prev?: TItem[] }>({
    mutationFn,
    onMutate: async (vars) => {
      if (!optimistic) return {};
      await qc.cancelQueries({ queryKey: key });
      const prev = qc.getQueryData<TItem[]>(key);
      if (prev) qc.setQueryData<TItem[]>(key, optimistic(prev, vars));
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(key, ctx.prev);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: key });
      broadcastChange(key);
    },
  });
}

function useNow(intervalMs = 1000) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}

/** Badge "Live · diperbarui HH.MM.SS" seperti indikator data langsung dari database. */
export function LiveIndicator({
  updatedAt,
  isFetching,
  isError,
  className = "",
}: {
  updatedAt: number;
  isFetching?: boolean;
  isError?: boolean;
  className?: string;
}) {
  const now = useNow();
  const stale = updatedAt > 0 && now - updatedAt > LIVE_INTERVAL_MS * 4;
  const tone = isError || stale ? "bg-amber-500" : "bg-emerald-500";
  const time = updatedAt
    ? new Date(updatedAt).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    : "-";
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-600 ${className}`}
      aria-live="polite"
    >
      <span className={`live-dot h-2 w-2 rounded-full ${tone}`} />
      {isError ? "Koneksi terganggu, mencoba lagi" : "Live dari database"}
      <span className="text-slate-400">· diperbarui {time}</span>
      {isFetching && <span className="sr-only">memuat</span>}
    </span>
  );
}
