/**
 * Loop percakapan suara: teks hasil ASR -> jawaban asisten (streaming SSE) -> dibacakan (TTS).
 *
 * - Jawaban diambil dari endpoint chat yang sama (`/chat/messages/stream`, mode "fast" = model
 *   ringan bergaya GPT di backend) agar pagar keselamatan klinis & kuota tetap berlaku.
 * - TTS memakai Web Speech API di perangkat; kalimat dibacakan begitu selesai di-stream,
 *   tidak menunggu jawaban lengkap -> latency suara pertama lebih rendah.
 */
import { API_BASE_URL, api, getToken } from "@/lib/api";

export interface ReplyTiming {
  /** kirim -> byte pertama dari server (jaringan + antrean + LLM) */
  firstByteMs: number | null;
  /** kirim -> token pertama */
  firstTokenMs: number | null;
  /** kirim -> jawaban lengkap */
  totalMs: number | null;
  /** throughput unduh terukur (kbit/dtk) dari respons ini */
  kbps: number | null;
}

let sessionId: string | null = null;

async function ensureSession(): Promise<string> {
  if (sessionId) return sessionId;
  const s = await api.chat.createSession("Konsultasi Suara");
  sessionId = s.id;
  return sessionId;
}

export function resetVoiceSession() {
  sessionId = null;
}

export async function streamReply(
  text: string,
  onToken: (accumulated: string, delta: string) => void,
  signal?: AbortSignal,
): Promise<{ content: string; timing: ReplyTiming; safetyAlert: boolean }> {
  const sid = await ensureSession();
  const token = getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;

  const t0 = performance.now();
  const timing: ReplyTiming = { firstByteMs: null, firstTokenMs: null, totalMs: null, kbps: null };
  const res = await fetch(`${API_BASE_URL}/chat/messages/stream`, {
    method: "POST",
    headers,
    credentials: "include",
    signal,
    body: JSON.stringify({ session_id: sid, content: text, reasoning_mode: "fast", model_size: "8b" }),
  });
  if (!res.ok || !res.body) {
    let detail = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      detail = typeof j.detail === "string" ? j.detail : j.detail?.message || detail;
    } catch {
      // abaikan
    }
    if (res.status === 404) resetVoiceSession();
    throw new Error(detail);
  }

  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  let content = "";
  let bytes = 0;
  let safetyAlert = false;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    if (timing.firstByteMs === null) timing.firstByteMs = Math.round(performance.now() - t0);
    bytes += value.byteLength;
    buf += dec.decode(value, { stream: true });
    const events = buf.split("\n\n");
    buf = events.pop() || "";
    for (const ev of events) {
      const line = ev.trim();
      if (!line.startsWith("data: ")) continue;
      try {
        const p = JSON.parse(line.slice(6));
        if (p.type === "token") {
          if (timing.firstTokenMs === null) timing.firstTokenMs = Math.round(performance.now() - t0);
          content += p.token;
          onToken(content, p.token);
        } else if (p.type === "done") {
          const a = p.assistant_message;
          if (a?.content) content = a.content;
          safetyAlert = Boolean(a?.safety_alert);
        }
      } catch {
        // potongan JSON belum lengkap
      }
    }
  }
  timing.totalMs = Math.round(performance.now() - t0);
  const secs = timing.totalMs / 1000;
  timing.kbps = secs > 0 ? Math.round((bytes * 8) / 1000 / secs) : null;
  return { content, timing, safetyAlert };
}

/** Bersihkan markdown, sitasi, dan blok disclaimer agar enak didengar. */
export function speakable(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/\[(\d+|[A-Z]{1,4}-?\d*)\]/g, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/[*_#>`|]+/g, "")
    .replace(/^\s*[-•]\s+/gm, "")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Pembaca kalimat bertahap. `push()` menerima teks akumulasi yang terus bertambah; setiap kalimat
 * yang sudah lengkap langsung diantrikan ke speechSynthesis.
 */
export class SentenceSpeaker {
  private spoken = 0;
  private pending = 0;
  private voice: SpeechSynthesisVoice | null = null;
  private onStateChange: (speaking: boolean) => void;
  private firstAudioAt: number | null = null;
  enabled = true;

  constructor(onStateChange: (speaking: boolean) => void) {
    this.onStateChange = onStateChange;
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      const pick = () => {
        const vs = window.speechSynthesis.getVoices();
        this.voice = vs.find((v) => v.lang?.toLowerCase().startsWith("id")) ?? null;
      };
      pick();
      window.speechSynthesis.addEventListener?.("voiceschanged", pick);
    }
  }

  static supported() {
    return typeof window !== "undefined" && "speechSynthesis" in window;
  }

  get speaking() {
    return this.pending > 0;
  }

  /** ms dari reset() ke awal suara pertama (latency end-to-end yang dirasakan pasien) */
  firstAudioMs(since: number) {
    return this.firstAudioAt === null ? null : Math.round(this.firstAudioAt - since);
  }

  reset() {
    this.spoken = 0;
    this.firstAudioAt = null;
  }

  push(accumulated: string, final = false) {
    const clean = speakable(accumulated);
    if (clean.length <= this.spoken) return;
    const rest = clean.slice(this.spoken);
    let cut = -1;
    const re = /[.!?…](\s|$)/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(rest))) cut = m.index + 1;
    if (final) cut = rest.length;
    if (cut <= 0) return;
    const sentence = rest.slice(0, cut).trim();
    this.spoken += cut;
    if (sentence) this.say(sentence);
  }

  private say(text: string) {
    if (!this.enabled || !SentenceSpeaker.supported()) return;
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "id-ID";
    if (this.voice) u.voice = this.voice;
    u.rate = 1.05;
    this.pending += 1;
    this.onStateChange(true);
    u.onstart = () => {
      if (this.firstAudioAt === null) this.firstAudioAt = performance.now();
    };
    const end = () => {
      this.pending = Math.max(0, this.pending - 1);
      if (this.pending === 0) this.onStateChange(false);
    };
    u.onend = end;
    u.onerror = end;
    window.speechSynthesis.speak(u);
  }

  cancel() {
    if (SentenceSpeaker.supported()) window.speechSynthesis.cancel();
    this.pending = 0;
    this.onStateChange(false);
  }
}

/** Perkiraan bandwidth dari Network Information API (Chrome/Android); null bila tidak tersedia. */
export function networkHint(): { downlinkMbps: number | null; rttMs: number | null; type: string | null; saveData: boolean } {
  const c = (typeof navigator !== "undefined" ? (navigator as Navigator & { connection?: { downlink?: number; rtt?: number; effectiveType?: string; saveData?: boolean } }).connection : undefined);
  return {
    downlinkMbps: c?.downlink ?? null,
    rttMs: c?.rtt ?? null,
    type: c?.effectiveType ?? null,
    saveData: Boolean(c?.saveData),
  };
}

/** Pilih ukuran model ASR dari bandwidth: jaringan lambat/hemat data -> whisper-tiny (unduhan ~40 MB). */
export function preferredAsrTier(): "tiny" | "base" {
  const n = networkHint();
  if (n.saveData) return "tiny";
  if (n.type && /(^|-)2g|3g/.test(n.type)) return "tiny";
  if (n.downlinkMbps !== null && n.downlinkMbps < 2) return "tiny";
  return "base";
}
