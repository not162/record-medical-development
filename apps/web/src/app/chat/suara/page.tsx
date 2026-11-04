"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Video, VideoOff, Mic, ShieldCheck, Loader2, Send, AlertCircle, Smile, Activity, Timer, Waves, Cpu,
} from "lucide-react";
import { ProsodyAnalyzer, type ProsodySnapshot } from "@/lib/voice/prosody";
import { FaceAnalyzer, createFaceLandmarker, type FaceSnapshot } from "@/lib/vision/face";

type AsrState = { status: "idle" | "loading" | "ready" | "error"; pct?: number; info?: string };
interface Line { id: number; text: string; pending: boolean }

function Metric({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3">
      <div className="text-[11px] text-slate-500">{label}</div>
      <div className="text-base font-bold text-slate-900 mt-0.5">{value}</div>
      {hint && <div className="text-[10px] text-slate-500">{hint}</div>}
    </div>
  );
}

const ms = (v: number | null | undefined) => (v == null ? "-" : v >= 1000 ? `${(v / 1000).toFixed(1)} dtk` : `${v} ms`);

export default function VoiceCameraPage() {
  const router = useRouter();
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const prosodyRef = useRef<ProsodyAnalyzer | null>(null);
  const faceRef = useRef<FaceAnalyzer | null>(null);
  const workerRef = useRef<Worker | null>(null);
  const rafRef = useRef<number | null>(null);
  const segId = useRef(0);

  const [consent, setConsent] = useState(false);
  const [useCamera, setUseCamera] = useState(true);
  const [running, setRunning] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [prosody, setProsody] = useState<ProsodySnapshot | null>(null);
  const [face, setFace] = useState<FaceSnapshot | null>(null);
  const [asr, setAsr] = useState<AsrState>({ status: "idle" });
  const [lines, setLines] = useState<Line[]>([]);
  const [attachSummary, setAttachSummary] = useState(true);

  const ensureWorker = useCallback(() => {
    if (workerRef.current) return workerRef.current;
    const w = new Worker("/workers/asr-worker.js", { type: "module" });
    w.onmessage = (e: MessageEvent) => {
      const m = e.data;
      if (m.type === "progress") setAsr({ status: "loading", pct: m.pct, info: m.file });
      if (m.type === "ready")
        setAsr({
          status: "ready",
          info: `${m.model.split("/")[1]} · ${m.device} · RTF ${m.rtf} · batch ${m.maxBatch}${m.kvCache ? " · KV cache" : ""}`,
        });
      if (m.type === "result")
        setLines((ls) => ls.map((l) => (l.id === m.id ? { ...l, text: m.text || "(tidak terdengar jelas)", pending: false } : l)));
      if (m.type === "error") setAsr({ status: "error", info: m.message });
    };
    setAsr({ status: "loading", pct: 0 });
    w.postMessage({ type: "load" });
    workerRef.current = w;
    return w;
  }, []);

  const stop = useCallback(async () => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
    await prosodyRef.current?.stop();
    prosodyRef.current = null;
    faceRef.current?.close();
    faceRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setRunning(false);
  }, []);

  useEffect(() => () => {
    stop();
    workerRef.current?.terminate();
  }, [stop]);

  const start = async () => {
    setError(null);
    setStarting(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
        video: useCamera ? { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" } : false,
      });
      streamRef.current = stream;
      const worker = ensureWorker();
      const pa = new ProsodyAnalyzer((audio) => {
        const id = ++segId.current;
        setLines((ls) => [...ls, { id, text: "", pending: true }]);
        worker.postMessage({ type: "segment", id, audio }, [audio.buffer]);
      });
      await pa.start(stream);
      prosodyRef.current = pa;

      if (useCamera && videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        try {
          faceRef.current = new FaceAnalyzer(await createFaceLandmarker());
        } catch {
          setError("Analisis wajah tidak dapat dimuat di perangkat ini. Analisis suara tetap berjalan.");
        }
      }
      setRunning(true);
      let lastUi = 0;
      const loop = (now: number) => {
        if (faceRef.current && videoRef.current) faceRef.current.process(videoRef.current, now);
        if (now - lastUi > 250) {
          lastUi = now;
          setProsody(prosodyRef.current?.snapshot() ?? null);
          if (faceRef.current) setFace(faceRef.current.current());
        }
        rafRef.current = requestAnimationFrame(loop);
      };
      rafRef.current = requestAnimationFrame(loop);
    } catch (e) {
      const name = (e as DOMException)?.name;
      setError(
        name === "NotAllowedError"
          ? "Izin kamera/mikrofon ditolak. Aktifkan izin di pengaturan browser lalu coba lagi."
          : "Kamera atau mikrofon tidak dapat diakses di perangkat ini."
      );
      await stop();
    } finally {
      setStarting(false);
    }
  };

  const transcript = lines.filter((l) => !l.pending).map((l) => l.text).join(" ").trim();

  const summary = (): string => {
    const parts: string[] = [];
    if (prosody) {
      if (prosody.responseLatencyMs != null) parts.push(`mulai bicara setelah ${ms(prosody.responseLatencyMs)}`);
      parts.push(`${prosody.pauses.count} jeda (rata-rata ${ms(prosody.pauses.meanMs)})`);
      if (prosody.intonation.endContour) parts.push(`intonasi akhir ${prosody.intonation.endContour}`);
    }
    if (face?.faceFound) parts.push(`raut wajah cenderung ${face.expression.toLowerCase()}`);
    return parts.length ? `\n\n[Catatan otomatis dari perangkat saya: ${parts.join(", ")}. Ini hanya indikasi, bukan diagnosis.]` : "";
  };

  const sendToChat = () => {
    const text = transcript + (attachSummary ? summary() : "");
    try {
      sessionStorage.setItem("chat_prefill", text);
    } catch {
      // abaikan
    }
    stop();
    router.push("/chat");
  };

  if (!consent) {
    return (
      <div className="flex-1 overflow-y-auto p-4 sm:p-8">
        <div className="max-w-xl mx-auto bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
          <h1 className="text-xl font-extrabold text-slate-900 flex items-center gap-2">
            <Video className="w-5 h-5 text-blue-600" /> Konsultasi Suara & Kamera
          </h1>
          <p className="text-sm text-slate-600">
            Ceritakan keluhan Anda dengan berbicara. Ucapan Anda diubah menjadi teks, lalu nada suara, jeda bicara,
            dan raut wajah dianalisis sebagai catatan tambahan untuk asisten.
          </p>
          <ul className="text-[13px] text-slate-600 space-y-2">
            <li className="flex gap-2"><ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />Semua proses berjalan di perangkat Anda. Video dan rekaman suara <b>tidak dikirim atau disimpan</b> di server.</li>
            <li className="flex gap-2"><ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />Yang dikirim ke asisten hanya teks yang Anda setujui sendiri sebelum menekan Kirim.</li>
            <li className="flex gap-2"><ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />Hasil analisis wajah dan suara hanya indikasi, bukan diagnosis.</li>
            <li className="flex gap-2"><Cpu className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />Pada pemakaian pertama, model pengenal suara (±40–75 MB) diunduh sekali ke perangkat Anda.</li>
          </ul>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={useCamera} onChange={(e) => setUseCamera(e.target.checked)} className="accent-blue-600 h-4 w-4" />
            Aktifkan kamera untuk analisis raut wajah (opsional)
          </label>
          <button onClick={() => setConsent(true)} className="btn-primary w-full h-11 text-sm font-bold">
            Saya mengerti dan setuju
          </button>
          <p className="text-[11px] text-slate-500">Keadaan darurat? Segera hubungi 119 atau IGD terdekat.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6">
      <div className="max-w-5xl mx-auto space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-lg font-extrabold text-slate-900 flex items-center gap-2">
            <Video className="w-5 h-5 text-blue-600" /> Konsultasi Suara & Kamera
          </h1>
          <div className="flex items-center gap-2">
            {!running ? (
              <button onClick={start} disabled={starting} className="btn-primary inline-flex items-center gap-2 px-4 h-10 text-sm font-bold">
                {starting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mic className="w-4 h-4" />}
                Mulai bicara
              </button>
            ) : (
              <>
                <button onClick={() => prosodyRef.current?.markPrompt()} className="px-3 h-10 rounded-xl border border-slate-200 bg-white text-xs font-semibold text-slate-700">
                  Pertanyaan baru
                </button>
                <button onClick={stop} className="inline-flex items-center gap-2 px-4 h-10 rounded-xl bg-red-600 text-white text-sm font-bold">
                  <VideoOff className="w-4 h-4" /> Berhenti
                </button>
              </>
            )}
          </div>
        </div>

        {error && (
          <div className="p-3 rounded-xl border border-amber-200 bg-amber-50 text-amber-800 text-xs flex gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" /> {error}
          </div>
        )}

        <div className="grid lg:grid-cols-[1.1fr_1fr] gap-4">
          <div className="space-y-3">
            <div className="relative aspect-video rounded-2xl overflow-hidden bg-slate-900 border border-slate-200">
              <video ref={videoRef} muted playsInline className="w-full h-full object-cover -scale-x-100" />
              {!running && (
                <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm">
                  {useCamera ? "Kamera mati" : "Mode suara saja"}
                </div>
              )}
              {running && (
                <span className="absolute top-3 left-3 inline-flex items-center gap-1.5 rounded-full bg-black/60 px-2.5 py-1 text-[11px] text-white">
                  <span className={`h-2 w-2 rounded-full ${prosody?.speaking ? "bg-emerald-400" : "bg-slate-400"}`} />
                  {prosody?.speaking ? "Mendengarkan..." : "Menunggu suara"}
                </span>
              )}
            </div>
            <div className="text-[11px] text-slate-500 flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5" />
              Pengenal suara: {asr.status === "loading" ? `memuat model ${asr.pct ?? 0}%` : asr.status === "ready" ? asr.info : asr.status === "error" ? `gagal (${asr.info})` : "belum dimuat"}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 content-start">
            <Metric label="Raut wajah" value={face?.faceFound ? face.expression : "-"} hint={face?.faceFound ? `senyum ${face.scores.senyum} · alis turun ${face.scores.alisTurun}` : "wajah belum terdeteksi"} />
            <Metric label="Kedipan / menit" value={face?.faceFound ? face.blinkPerMin : "-"} hint={face ? `gerak kepala ${face.movement}°/frame` : undefined} />
            <Metric label="Latency respons" value={ms(prosody?.responseLatencyMs)} hint="dari mulai sampai Anda bicara" />
            <Metric label="Jeda bicara" value={prosody ? `${prosody.pauses.count}×` : "-"} hint={prosody ? `rata ${ms(prosody.pauses.meanMs)} · terlama ${ms(prosody.pauses.maxMs)}` : undefined} />
            <Metric label="Intonasi" value={prosody?.intonation.meanHz ? `${prosody.intonation.meanHz} Hz` : "-"} hint={prosody?.intonation.rangeHz != null ? `rentang ${prosody.intonation.rangeHz} Hz · akhir ${prosody.intonation.endContour ?? "-"}` : undefined} />
            <Metric label="Tone up (energi)" value={prosody?.toneUpDb != null ? `${prosody.toneUpDb > 0 ? "+" : ""}${prosody.toneUpDb} dB` : "-"} hint={prosody ? `level ${prosody.levelDb} dB · derau ${prosody.noiseFloorDb} dB` : undefined} />
            <Metric label="Laju bicara" value={prosody?.speechRate ?? "-"} hint="segmen bersuara per detik" />
            <Metric label="Durasi bicara" value={ms(prosody?.speechMs)} />
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-4 space-y-3">
          <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
            <Waves className="w-4 h-4 text-blue-600" /> Transkrip (dikenali di perangkat)
          </h2>
          <div className="min-h-16 text-sm text-slate-800 space-y-1">
            {lines.length === 0 && <p className="text-slate-400 text-xs">Tekan “Mulai bicara”, lalu ceritakan keluhan Anda.</p>}
            {lines.map((l) => (
              <p key={l.id} className={l.pending ? "text-slate-400 italic" : ""}>
                {l.pending ? "mengenali ucapan..." : l.text}
              </p>
            ))}
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100">
            <label className="flex items-center gap-2 text-xs text-slate-600">
              <input type="checkbox" checked={attachSummary} onChange={(e) => setAttachSummary(e.target.checked)} className="accent-blue-600" />
              Sertakan catatan nada, jeda, dan raut wajah
            </label>
            <button onClick={sendToChat} disabled={!transcript} className="btn-primary inline-flex items-center gap-2 px-4 h-10 text-sm font-bold">
              <Send className="w-4 h-4" /> Lanjutkan ke chat
            </button>
          </div>
          {transcript && attachSummary && (
            <p className="text-[11px] text-slate-500 whitespace-pre-wrap">Pratinjau catatan: {summary().trim() || "-"}</p>
          )}
        </div>
        <p className="text-[11px] text-slate-500 flex items-center gap-1.5">
          <Smile className="w-3.5 h-3.5" /> <Activity className="w-3.5 h-3.5" /> <Timer className="w-3.5 h-3.5" />
          Analisis ekspresi dan suara bersifat indikatif dan dapat keliru karena cahaya, kamera, logat, atau derau.
        </p>
      </div>
    </div>
  );
}
