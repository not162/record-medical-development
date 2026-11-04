"use client";

import { useEffect, useState } from "react";
import { RefreshCw, WifiOff } from "lucide-react";

/**
 * Mendaftarkan service worker, memberi tahu bila ada versi baru,
 * dan menampilkan banner saat koneksi terputus.
 */
export function PwaRegistration() {
  const [waiting, setWaiting] = useState<ServiceWorker | null>(null);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const syncOnline = () => setOffline(!navigator.onLine);
    syncOnline();
    window.addEventListener("online", syncOnline);
    window.addEventListener("offline", syncOnline);

    if (!("serviceWorker" in navigator) || process.env.NODE_ENV !== "production") {
      return () => {
        window.removeEventListener("online", syncOnline);
        window.removeEventListener("offline", syncOnline);
      };
    }

    let reloading = false;
    const onControllerChange = () => {
      if (reloading) return;
      reloading = true;
      window.location.reload();
    };

    const register = async () => {
      try {
        const reg = await navigator.serviceWorker.register("/sw.js", { scope: "/" });
        const hadController = !!navigator.serviceWorker.controller;
        if (reg.waiting && hadController) setWaiting(reg.waiting);
        reg.addEventListener("updatefound", () => {
          const sw = reg.installing;
          sw?.addEventListener("statechange", () => {
            if (sw.state === "installed" && navigator.serviceWorker.controller) setWaiting(sw);
          });
        });
        if (hadController) navigator.serviceWorker.addEventListener("controllerchange", onControllerChange);
      } catch (err) {
        console.warn("Registrasi service worker gagal:", err);
      }
    };

    // Bug lama: listener "load" tidak pernah terpanggil bila halaman sudah selesai dimuat.
    if (document.readyState === "complete") register();
    else window.addEventListener("load", register, { once: true });

    return () => {
      window.removeEventListener("online", syncOnline);
      window.removeEventListener("offline", syncOnline);
      navigator.serviceWorker.removeEventListener("controllerchange", onControllerChange);
    };
  }, []);

  if (!waiting && !offline) return null;

  return (
    <div className="fixed inset-x-0 bottom-4 z-[60] flex justify-center px-4 pointer-events-none">
      {offline ? (
        <div role="status" className="pointer-events-auto flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs font-semibold text-amber-800 shadow-lg">
          <WifiOff className="h-4 w-4" />
          Anda sedang offline. Perubahan akan dimuat ulang saat tersambung kembali.
        </div>
      ) : (
        <div role="status" className="pointer-events-auto flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs text-slate-700 shadow-lg">
          <span>Versi baru Web Klinik tersedia.</span>
          <button
            type="button"
            onClick={() => waiting?.postMessage("SKIP_WAITING")}
            className="btn-primary inline-flex h-8 items-center gap-1.5 px-3 font-bold"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Muat ulang
          </button>
        </div>
      )}
    </div>
  );
}
