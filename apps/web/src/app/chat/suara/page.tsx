"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Video, VideoOff, Mic, ShieldCheck, Loader2, Send, AlertCircle, Smile, Activity, Timer, Waves, Cpu, Volume2, VolumeX, Gauge,
} from "lucide-react";
import { ProsodyAnalyzer, type ProsodySnapshot } from "@/lib/voice/prosody";
import {
  SentenceSpeaker, networkHint, preferredAsrTier, resetVoiceSession, streamReply,
} from "@/lib/voice/assistant";
import { FaceAnalyzer, createFaceLandmarker, type FaceSnapshot } from "@/lib/vision/face";
import {
  checkMediaPermissions, openMedia, permissionHelp, watchMediaPermissions, type MediaPermissions, type PermState,
} from "@/lib/media-permissions";

const PERM_LABEL: Record<PermState, { text: string; cls: string }> = {
  granted: { text: "diizinkan", cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  prompt: { text: "akan ditanyakan", cls: "bg-blue-50 text-blue-700 border-blue-200" },
  denied: { text: "diblokir", cls: "bg-red-50 text-red-700 border-red-200" },
  unsupported: { text: "ditanyakan saat mulai", cls: "bg-slate-100 text-slate-600 border-slate-200" },
};

function PermissionPanel({ perms, useCamera }: { perms: MediaPermissions | null; useCamera: boolean }) {
  if (!perms) return null;
  const blocked =
    (useCamera && perms.camera === "denied") || perms.microphone === "denied" ||
    !perms.secure || !perms.policyAllows.microphone || (useCamera && !perms.policyAllows.camera);
  return (
    <div className={`rounded-xl border p-3 text-xs space-y-2 ${blocked ? "border-red-200 bg-red-50" : "border-slate-200 bg-white"}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-slate-700">Izin perangkat:</span>
        {useCamera && (
          <span className={`px-2 py-0.5 rounded-full border ${PERM_LABEL[perms.camera].cls}`}>Kamera {PERM_LABEL[perms.camera].text}</span>
        )}
        <span className={`px-2 py-0.5 rounded-full border ${PERM_LABEL[perms.microphone].cls}`}>Mikrofon {PERM_LABEL[perms.microphone].text}</span>
      </div>
      {!perms.secure && <p className="text-red-700">Halaman harus dibuka lewat https:// agar kamera dapat diakses.</p>}
      {(!perms.policyAllows.camera || !perms.policyAllows.microphone) && (
        <p className="text-red-700">Kebijakan situs sedang memblokir kamera/mikrofon. Muat ulang halaman; bila tetap terblokir, hubungi admin.</p>
      )}
      {(perms.camera === "denied" || perms.microphone === "denied") && (
        <p className="text-red-700">
          <b>Akses diblokir sebelumnya.</b> {permissionHelp()}
        </p>
      )}
      {useCamera && !perms.hasDevices.camera && <p className="text-amber-700">Kamera tidak terdeteksi. Konsultasi tetap bisa dengan suara saja.</p>}
    </div>
  );
}

type AsrState = { status: "idle" | "loading" | "ready" | "error"; pct?: number; info?: string };
interface Line { id: number; text: string; pending: boolean }
interface Turn { id: string; role: "user" | "assistant"; text: string; pending?: boolean; error?: boolean; safety?: boolean }
interface Latency {
  asrMs: number | null; // akhir ucapan -> teks
  firstByteMs: number | null; // kirim -> byte pertama server
  firstTokenMs: number | null; // kirim -> token jawaban pertama
  totalMs: number | null; // kirim -> jawaban lengkap
  e2eMs: number | null; // akhir ucapan -> suara asisten pertama
  kbps: number | null; // throughput terukur
}
const NO_LAT: Latency = { asrMs: null, firstByteMs: null, firstTokenMs: null, totalMs: null, e2eMs: null, kbps: null };

// Whisper sering "berhalusinasi" teks pendek pada hening/derau -> jangan dikirim ke asisten
const isNoise = (t: string) =>
  t.length < 3 || /^(\(.*\)|\[.*\]|\.+|terima kasih\.?|thank you\.?|you)$/i.test(t.trim());

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
  const [perms, setPerms] = useState<MediaPermissions | null>(null);
  const [cameraLive, setCameraLive] = useState(false);
  const [faceStatus, setFaceStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [thinking, setThinking] = useState(false);
  const [ttsSpeaking, setTtsSpeaking] = useState(false);
  const [voiceReply, setVoiceReply] = useState(true);
  const [lat, setLat] = useState<Latency>(NO_LAT);
  const [net, setNet] = useState<ReturnType<typeof networkHint> | null>(null);

  // loop percakapan (ref agar callback worker selalu memakai versi terbaru)
  const segEndAt = useRef(new Map<number, number>());
  const queueRef = useRef<{ text: string; endAt: number }[]>([]);
  const busyRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);
  const speakerRef = useRef<SentenceSpeaker | null>(null);
  const respondRef = useRef<() => void>(() => undefined);

  const speaker = useCallback(() => {
    if (!speakerRef.current) {
      speakerRef.current = new SentenceSpeaker((on) => {
        setTtsSpeaking(on);
        // mic dijeda saat asisten bicara agar suara speaker tidak ditranskrip balik
        prosodyRef.current?.setPaused(on);
        if (!on) {
          prosodyRef.current?.markPrompt();
          respondRef.current();
        }
      });
    }
    return speakerRef.current;
  }, []);

  respondRef.current = async () => {
    if (busyRef.current || speakerRef.current?.speaking || !queueRef.current.length) return;
    const batch = queueRef.current.splice(0);
    const text = batch.map((b) => b.text).join(" ");
    const endAt = batch[batch.length - 1].endAt;
    busyRef.current = true;
    setThinking(true);
    const uid = `u-${Date.now()}`;
    const aid = `a-${Date.now()}`;
    setTurns((t) => [...t, { id: uid, role: "user", text }, { id: aid, role: "assistant", text: "", pending: true }]);
    const sp = speaker();
    sp.enabled = voiceReply;
    sp.reset();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      const out = await streamReply(
        text,
        (acc) => {
          setTurns((t) => t.map((x) => (x.id === aid ? { ...x, text: acc } : x)));
          sp.push(acc);
        },
        ctrl.signal,
      );
      sp.push(out.content, true);
      setTurns((t) => t.map((x) => (x.id === aid ? { ...x, text: out.content || "(jawaban kosong)", pending: false, safety: out.safetyAlert } : x)));
      setLat((l) => ({ ...l, ...out.timing, e2eMs: null }));
      // latency end-to-end diisi saat suara pertama benar-benar keluar
      const t0 = endAt;
      const poll = (n: number) => {
        const v = sp.firstAudioMs(t0);
        if (v !== null) setLat((l) => ({ ...l, e2eMs: v }));
        else if (n > 0) setTimeout(() => poll(n - 1), 150);
      };
      if (voiceReply) poll(60);
    } catch (e) {
      if ((e as DOMException)?.name !== "AbortError") {
        setTurns((t) => t.map((x) => (x.id === aid ? { ...x, text: `Asisten tidak dapat menjawab: ${(e as Error).message}`, pending: false, error: true } : x)));
      }
    } finally {
      busyRef.current = false;
      abortRef.current = null;
      setThinking(false);
      if (!speakerRef.current?.speaking) respondRef.current();
    }
  };

  const refreshPerms = useCallback(() => {
    checkMediaPermissions().then(setPerms).catch(() => undefined);
  }, []);

  // status izin dibaca saat halaman dibuka dan diperbarui otomatis saat pengguna mengubahnya di browser
  useEffect(() => {
    refreshPerms();
    return watchMediaPermissions(refreshPerms);
  }, [refreshPerms]);

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
      if (m.type === "result") {
        const endAt = segEndAt.current.get(m.id) ?? performance.now();
        segEndAt.current.delete(m.id);
        setLat((l) => ({ ...l, asrMs: Math.round(performance.now() - endAt) }));
        const text = (m.text || "").trim();
        setLines((ls) => ls.map((l) => (l.id === m.id ? { ...l, text: text || "(tidak terdengar jelas)", pending: false } : l)));
        if (!isNoise(text)) {
          queueRef.current.push({ text, endAt });
          respondRef.current();
        }
      }
      if (m.type === "error") setAsr({ status: "error", info: m.message });
    };
    setAsr({ status: "loading", pct: 0 });
    // bandwidth rendah / hemat data -> model kecil agar unduhan & inferensi cepat
    w.postMessage({ type: "load", prefer: preferredAsrTier() });
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
    abortRef.current?.abort();
    speakerRef.current?.cancel();
    queueRef.current = [];
    setCameraLive(false);
    setFaceStatus("idle");
    setRunning(false);
  }, []);

  useEffect(() => () => {
    stop();
    workerRef.current?.terminate();
    resetVoiceSession();
  }, [stop]);

  const [ttsSupported, setTtsSupported] = useState(true);
  useEffect(() => setTtsSupported(SentenceSpeaker.supported()), []);

  const start = async () => {
    setError(null);
    setStarting(true);
    try {
      // dipanggil langsung dari klik -> browser menampilkan dialog izin kamera & mikrofon
      const media = await openMedia(useCamera);
      const stream = media.stream;
      if (media.note) setError(media.note);
      refreshPerms();
      streamRef.current = stream;
      const worker = ensureWorker();
      setNet(networkHint());
      speaker(); // dibuat dari klik pengguna -> speechSynthesis diizinkan berbunyi
      const pa = new ProsodyAnalyzer((audio) => {
        const id = ++segId.current;
        segEndAt.current.set(id, performance.now());
        setLines((ls) => [...ls, { id, text: "", pending: true }]);
        worker.postMessage({ type: "segment", id, audio }, [audio.buffer]);
      });
      await pa.start(stream);
      prosodyRef.current = pa;

      if (media.video && videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setCameraLive(true);
        stream.getVideoTracks()[0]?.addEventListener("ended", () => setCameraLive(false));
        // model wajah (~4 MB) dimuat di latar: video & analisis suara tidak menunggu unduhan selesai
        setFaceStatus("loading");
        createFaceLandmarker()
          .then((lm) => {
            if (!streamRef.current) return lm.close();
            faceRef.current = new FaceAnalyzer(lm);
            setFaceStatus("ready");
          })
          .catch(() => {
            setFaceStatus("error");
            setError("Analisis wajah tidak dapat dimuat di perangkat ini. Analisis suara tetap berjalan.");
          });
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
        name === "InsecureContext"
          ? "Kamera hanya bisa dibuka lewat alamat aman (https://). Buka situs ini melalui https."
          : name === "NotAllowedError" || name === "SecurityError"
            ? `Izin mikrofon${useCamera ? "/kamera" : ""} ditolak. ${permissionHelp()}`
            : name === "NotFoundError"
              ? "Mikrofon tidak ditemukan. Sambungkan mikrofon atau headset lalu coba lagi."
              : name === "NotReadableError"
                ? "Mikrofon/kamera sedang dipakai aplikasi lain. Tutup aplikasi tersebut lalu coba lagi."
                : "Kamera atau mikrofon tidak dapat diakses di perangkat ini."
      );
      refreshPerms();
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
            <li className="flex gap-2"><ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />Yang dikirim ke asisten hanya <b>teks hasil pengenalan ucapan</b> Anda, secara otomatis setiap Anda selesai bicara, agar asisten bisa langsung menjawab dengan suara. Catatan nada/raut wajah hanya dikirim bila Anda menekan “Lanjutkan ke chat”.</li>
            <li className="flex gap-2"><ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />Hasil analisis wajah dan suara hanya indikasi, bukan diagnosis.</li>
            <li className="flex gap-2"><Cpu className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />Pada pemakaian pertama, model pengenal suara (±40–75 MB) diunduh sekali ke perangkat Anda.</li>
          </ul>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={useCamera} onChange={(e) => setUseCamera(e.target.checked)} className="accent-blue-600 h-4 w-4" />
            Aktifkan kamera untuk analisis raut wajah (opsional)
          </label>
          <PermissionPanel perms={perms} useCamera={useCamera} />
          <button
            onClick={() => {
              setConsent(true);
              ensureWorker(); // mulai unduh model suara sekarang agar siap saat pasien mulai bicara
            }}
            className="btn-primary w-full h-11 text-sm font-bold"
          >
            Saya mengerti dan setuju
          </button>
          <p className="text-[11px] text-slate-500">
            Setelah menekan “Mulai bicara”, browser akan meminta izin kamera dan mikrofon. Pilih <b>Izinkan</b>.
          </p>
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

        {!running && <PermissionPanel perms={perms} useCamera={useCamera} />}

        {error && (
          <div className="p-3 rounded-xl border border-amber-200 bg-amber-50 text-amber-800 text-xs flex gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" /> {error}
          </div>
        )}

        <div className="grid lg:grid-cols-[1.1fr_1fr] gap-4">
          <div className="space-y-3">
            <div className="relative aspect-video rounded-2xl overflow-hidden bg-slate-900 border border-slate-200">
              <video ref={videoRef} muted playsInline className="w-full h-full object-cover -scale-x-100" />
              {/* overlay hanya saat video benar-benar tidak tampil */}
              {!cameraLive && (
                <div className="absolute inset-0 flex items-center justify-center gap-2 text-slate-400 text-sm">
                  {starting && <Loader2 className="w-4 h-4 animate-spin" />}
                  {starting ? "Menyalakan kamera..." : running || !useCamera ? "Mode suara saja" : "Kamera mati"}
                </div>
              )}
              {running && (
                <span className="absolute top-3 left-3 inline-flex items-center gap-1.5 rounded-full bg-black/60 px-2.5 py-1 text-[11px] text-white">
                  <span className={`h-2 w-2 rounded-full ${ttsSpeaking ? "bg-cyan-400" : thinking ? "bg-amber-400" : prosody?.speaking ? "bg-emerald-400" : "bg-slate-400"}`} />
                  {ttsSpeaking ? "Asisten berbicara..." : thinking ? "Asisten menyiapkan jawaban..." : prosody?.speaking ? "Mendengarkan..." : "Silakan bicara"}
                </span>
              )}
              {cameraLive && faceStatus === "loading" && (
                <span className="absolute bottom-3 left-3 inline-flex items-center gap-1.5 rounded-full bg-black/60 px-2.5 py-1 text-[11px] text-white">
                  <Loader2 className="w-3 h-3 animate-spin" /> Memuat analisis wajah...
                </span>
              )}
            </div>
            <div className="text-[11px] text-slate-500 flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5" />
              Pengenal suara: {asr.status === "loading" ? `memuat model ${asr.pct ?? 0}%` : asr.status === "ready" ? asr.info : asr.status === "error" ? `gagal (${asr.info})` : "belum dimuat"}
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-3">
              <div className="text-[11px] font-semibold text-slate-700 flex items-center gap-1.5 mb-2">
                <Gauge className="w-3.5 h-3.5" /> Latency real-time
                {net && (
                  <span className="ml-auto font-normal text-slate-500">
                    jaringan {net.type ?? "?"}
                    {net.downlinkMbps != null ? ` · ${net.downlinkMbps} Mbps` : ""}
                    {net.rttMs != null ? ` · RTT ${net.rttMs} ms` : ""}
                  </span>
                )}
              </div>
              <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 text-center">
                {[
                  ["Kenali suara", ms(lat.asrMs)],
                  ["Respons server", ms(lat.firstByteMs)],
                  ["Kata pertama", ms(lat.firstTokenMs)],
                  ["Suara asisten", ms(lat.e2eMs)],
                  ["Bandwidth", lat.kbps != null ? `${lat.kbps} kbps` : "-"],
                ].map(([k, v]) => (
                  <div key={k} className="rounded-lg bg-slate-50 px-1.5 py-1.5">
                    <div className="text-[10px] text-slate-500">{k}</div>
                    <div className="text-xs font-bold text-slate-900 tabular-nums">{v}</div>
                  </div>
                ))}
              </div>
              <p className="text-[10px] text-slate-500 mt-1.5">
                &quot;Suara asisten&quot; = dari Anda selesai bicara sampai asisten mulai menjawab dengan suara.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 content-start">
            <Metric
              label="Raut wajah"
              value={face?.faceFound ? face.expression : "-"}
              hint={
                face?.faceFound
                  ? `senyum ${face.scores.senyum} · alis turun ${face.scores.alisTurun} · ${face.fps} fps`
                  : faceStatus === "loading"
                    ? "memuat model wajah..."
                    : faceStatus === "ready"
                      ? "arahkan wajah ke kamera"
                      : cameraLive || !useCamera ? "analisis wajah tidak aktif" : "wajah belum terdeteksi"
              }
            />
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
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
              <Mic className="w-4 h-4 text-blue-600" /> Percakapan dengan asisten
            </h2>
            <button
              onClick={() => {
                const next = !voiceReply;
                setVoiceReply(next);
                if (speakerRef.current) {
                  speakerRef.current.enabled = next;
                  if (!next) speakerRef.current.cancel();
                }
              }}
              aria-pressed={voiceReply}
              className="inline-flex items-center gap-1.5 px-2.5 h-8 rounded-lg border border-slate-200 text-[11px] font-semibold text-slate-700 hover:bg-slate-50"
            >
              {voiceReply ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
              {voiceReply ? "Jawaban bersuara" : "Suara dimatikan"}
            </button>
          </div>
          {!ttsSupported && (
            <p className="text-[11px] text-amber-700">Browser ini tidak mendukung pembacaan suara; jawaban tampil sebagai teks.</p>
          )}
          <div className="space-y-2 max-h-80 overflow-y-auto" aria-live="polite">
            {turns.length === 0 && (
              <p className="text-slate-500 text-xs">Setelah Anda selesai bicara (jeda ±1 detik), asisten akan langsung menjawab dengan suara.</p>
            )}
            {turns.map((t) => (
              <div key={t.id} className={`flex ${t.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap ${
                    t.role === "user"
                      ? "bg-cyan-600 text-white rounded-tr-sm"
                      : t.error
                        ? "bg-red-50 text-red-800 border border-red-200"
                        : t.safety
                          ? "bg-rose-50 text-rose-900 border border-rose-200"
                          : "bg-slate-100 text-slate-800 rounded-tl-sm"
                  }`}
                >
                  {t.pending && !t.text ? (
                    <span className="inline-flex items-center gap-1.5 text-slate-500 text-xs"><Loader2 className="w-3 h-3 animate-spin" /> menyiapkan jawaban...</span>
                  ) : (
                    t.text
                  )}
                </div>
              </div>
            ))}
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
