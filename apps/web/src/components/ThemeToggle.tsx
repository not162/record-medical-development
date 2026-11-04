"use client";

import { useCallback, useSyncExternalStore } from "react";
import { Moon, Sun } from "lucide-react";

const STORAGE_KEY = "klinik_theme";
type Theme = "light" | "dark";

/** Dijalankan inline di <head> sebelum hidrasi: pilihan tersimpan > preferensi sistem. */
export const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem("${STORAGE_KEY}");if(!t){t=window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}var d=document.documentElement;d.classList.toggle("dark",t==="dark");d.style.colorScheme=t}catch(e){}})();`;

const listeners = new Set<() => void>();

function readTheme(): Theme {
  if (typeof document === "undefined") return "light";
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

export function setTheme(theme: Theme) {
  const root = document.documentElement;
  root.classList.toggle("dark", theme === "dark");
  root.style.colorScheme = theme;
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // storage diblokir - tema tetap berlaku untuk halaman ini
  }
  listeners.forEach((l) => l());
}

export function useTheme() {
  const theme = useSyncExternalStore(subscribe, readTheme, () => "light" as Theme);
  const toggle = useCallback(() => setTheme(readTheme() === "dark" ? "light" : "dark"), []);
  return { theme, toggle };
}

export function ThemeToggle({ className = "", small = false }: { className?: string; small?: boolean }) {
  const { theme, toggle } = useTheme();
  const isDark = theme === "dark";
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={isDark ? "Ganti ke tema terang" : "Ganti ke tema gelap"}
      title={isDark ? "Tema terang" : "Tema gelap"}
      className={`inline-flex ${small ? "h-7 w-7 rounded-lg" : "h-9 w-9 rounded-xl"} shrink-0 items-center justify-center border border-slate-200 bg-white text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition ${className}`}
    >
      {isDark ? <Sun className={small ? "h-3.5 w-3.5" : "h-4 w-4"} /> : <Moon className={small ? "h-3.5 w-3.5" : "h-4 w-4"} />}
    </button>
  );
}
