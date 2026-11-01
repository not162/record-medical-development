"use client";

import React, { useEffect, useState } from "react";
import { Stethoscope } from "lucide-react";

export default function BrandLoader() {
  const [visible, setVisible] = useState(false);
  const [fading, setFading] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // Only run on client
    if (typeof window === "undefined") return;

    // Check if prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Check if already displayed this browser session
    const alreadyShown = sessionStorage.getItem("rsukt_brand_loaded");
    if (alreadyShown || prefersReducedMotion) {
      return;
    }

    const rId = requestAnimationFrame(() => setVisible(true));

    const DURATION = 4000; // 4.0 seconds
    const FADEOUT = 400;   // 400ms transition
    const INTERVAL = 40;   // update every 40ms

    const startTime = Date.now();
    const intervalId = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const pct = Math.min(100, Math.round((elapsed / DURATION) * 100));
      setProgress(pct);

      if (elapsed >= DURATION) {
        clearInterval(intervalId);
        setFading(true);
        setTimeout(() => {
          setVisible(false);
          sessionStorage.setItem("rsukt_brand_loaded", "true");
        }, FADEOUT);
      }
    }, INTERVAL);

    return () => {
      cancelAnimationFrame(rId);
      clearInterval(intervalId);
    };
  }, []);

  if (!visible) return null;

  return (
    <div
      aria-hidden="true"
      role="progressbar"
      aria-valuenow={progress}
      aria-valuemin={0}
      aria-valuemax={100}
      className={`fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-slate-900 transition-opacity duration-400 select-none ${
        fading ? "opacity-0 pointer-events-none" : "opacity-100"
      }`}
    >
      <div className="relative flex flex-col items-center space-y-6 max-w-sm px-6 text-center">
        {/* Glow behind icon */}
        <div className="absolute -inset-4 bg-[#0891b2]/20 rounded-full blur-2xl pointer-events-none"></div>

        {/* Stethoscope Icon with Pulse */}
        <div className="relative w-20 h-20 rounded-2xl bg-gradient-to-tr from-[#0891b2] to-emerald-500 flex items-center justify-center shadow-lg shadow-[#0891b2]/30 animate-pulse">
          <Stethoscope className="w-10 h-10 text-white" />
        </div>

        {/* Brand Name & Slogan */}
        <div className="space-y-2">
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Web Klinik RSUKT
          </h1>
          <p className="text-xs uppercase tracking-widest font-semibold text-cyan-400">
            healthy with clinic and hospital
          </p>
        </div>

        {/* Progress Bar (4 seconds) */}
        <div className="w-48 h-1.5 bg-slate-800 rounded-full overflow-hidden border border-slate-700/60">
          <div
            className="h-full bg-gradient-to-r from-[#0891b2] to-emerald-400 transition-all duration-75 ease-linear rounded-full"
            style={{ width: `${progress}%` }}
          />
        </div>

        <p className="text-[11px] text-slate-400">
          Menyiapkan sistem klinis & rekam medis elektronik terverifikasi...
        </p>
      </div>
    </div>
  );
}
