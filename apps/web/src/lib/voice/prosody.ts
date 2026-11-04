/**
 * Analisis suara on-device (Web Audio, 16 kHz). Tidak ada audio yang dikirim ke server.
 *
 * Per frame (~32 ms): energi (dB), pitch F0 (autokorelasi 70-400 Hz), deteksi suara (VAD) dengan
 * ambang yang dikalibrasi otomatis dari derau latar (auto-tuning). Dari situ dihitung:
 *   - latency respons  : jeda dari tombol "mulai bicara" ke onset suara pertama
 *   - jeda             : jumlah, rata-rata, dan terpanjang (>= 250 ms di antara segmen bicara)
 *   - intonasi         : rerata/rentang/variasi F0 dan arah akhir kalimat (naik/turun/datar)
 *   - tone up          : kenaikan energi (dB) relatif terhadap awal bicara
 *   - laju bicara      : segmen bersuara per detik bicara (proksi suku kata)
 * Segmen ucapan (dipisah jeda >= 700 ms) diserahkan ke ASR on-device.
 */

export const SAMPLE_RATE = 16000;
const FRAME = 512; // 32 ms
const MIN_PAUSE_MS = 250;
const SEGMENT_PAUSE_MS = 700;
const CALIBRATION_MS = 800;

export interface ProsodySnapshot {
  speaking: boolean;
  levelDb: number;
  noiseFloorDb: number;
  pitchHz: number | null;
  responseLatencyMs: number | null;
  pauses: { count: number; meanMs: number; maxMs: number };
  intonation: { meanHz: number | null; rangeHz: number | null; stdHz: number | null; endContour: "naik" | "turun" | "datar" | null };
  toneUpDb: number | null;
  speechRate: number | null;
  speechMs: number;
}

export function detectPitch(buf: Float32Array, sr = SAMPLE_RATE): number | null {
  // autokorelasi ternormalisasi (cukup ringan untuk real-time di main thread)
  const minLag = Math.floor(sr / 400);
  const maxLag = Math.floor(sr / 70);
  let rms = 0;
  for (let i = 0; i < buf.length; i++) rms += buf[i] * buf[i];
  rms = Math.sqrt(rms / buf.length);
  if (rms < 0.01) return null;
  const corr: number[] = [];
  let best = 0;
  for (let lag = minLag; lag <= maxLag && lag < buf.length; lag++) {
    let num = 0;
    let e1 = 0;
    let e2 = 0;
    for (let i = 0; i + lag < buf.length; i++) {
      num += buf[i] * buf[i + lag];
      e1 += buf[i] * buf[i];
      e2 += buf[i + lag] * buf[i + lag];
    }
    const r = num / Math.sqrt(e1 * e2 + 1e-12);
    corr.push(r);
    if (r > best) best = r;
  }
  if (best <= 0.5) return null;
  // ambil puncak lokal PERTAMA yang mendekati maksimum -> menghindari kesalahan oktaf (lag 2T, 3T, ...)
  for (let k = 1; k < corr.length - 1; k++) {
    if (corr[k] >= 0.9 * best && corr[k] >= corr[k - 1] && corr[k] >= corr[k + 1]) {
      // interpolasi parabola untuk presisi sub-sampel
      const a = corr[k - 1], b = corr[k], c = corr[k + 1];
      const shift = (a - c) / (2 * (a - 2 * b + c) || 1);
      return sr / (minLag + k + shift);
    }
  }
  return null;
}

const mean = (a: number[]) => (a.length ? a.reduce((s, v) => s + v, 0) / a.length : 0);
const std = (a: number[]) => {
  if (a.length < 2) return 0;
  const m = mean(a);
  return Math.sqrt(mean(a.map((v) => (v - m) ** 2)));
};

export class ProsodyAnalyzer {
  private ctx: AudioContext | null = null;
  private node: ScriptProcessorNode | null = null;
  private src: MediaStreamAudioSourceNode | null = null;
  private carry = new Float32Array(0);
  private elapsedMs = 0;
  private calib: number[] = [];
  private noiseFloorDb = -60;
  private threshDb = -45;
  private speaking = false;
  private silenceMs = 0;
  private hangMs = 0;
  private promptAt = 0;
  private firstOnset: number | null = null;
  private pauses: number[] = [];
  private pitches: number[] = [];
  private utterancePitch: number[] = [];
  private lastContour: ProsodySnapshot["intonation"]["endContour"] = null;
  private energies: number[] = [];
  private voicedRuns = 0;
  private wasVoiced = false;
  private speechMs = 0;
  private segment: Float32Array[] = [];
  private last: { db: number; pitch: number | null } = { db: -90, pitch: null };

  constructor(private onSegment: (audio: Float32Array) => void) {}

  async start(stream: MediaStream) {
    // 16 kHz langsung = format masukan Whisper; tanpa resampling tambahan
    this.ctx = new AudioContext({ sampleRate: SAMPLE_RATE });
    // iOS/Safari & Chrome memulai AudioContext dalam keadaan "suspended" sampai ada aksi pengguna
    if (this.ctx.state === "suspended") await this.ctx.resume().catch(() => undefined);
    this.src = this.ctx.createMediaStreamSource(stream);
    this.node = this.ctx.createScriptProcessor(2048, 1, 1);
    this.node.onaudioprocess = (e) => this.ingest(e.inputBuffer.getChannelData(0));
    this.src.connect(this.node);
    this.node.connect(this.ctx.destination);
    this.markPrompt();
  }

  private paused = false;

  /**
   * Jeda pengambilan segmen (mis. saat asisten sedang membacakan jawaban) agar suara speaker
   * tidak ikut ditranskrip. Metrik level/derau tetap berjalan.
   */
  setPaused(p: boolean) {
    this.paused = p;
    if (p) {
      this.segment = [];
      this.speaking = false;
      this.utterancePitch = [];
    }
  }

  /** Dipanggil saat pasien diminta bicara (mulai hitung latency respons). */
  markPrompt() {
    this.promptAt = this.elapsedMs;
    this.firstOnset = null;
  }

  async stop() {
    this.flushSegment();
    this.node?.disconnect();
    this.src?.disconnect();
    await this.ctx?.close().catch(() => undefined);
    this.ctx = null;
  }

  private ingest(input: Float32Array) {
    const joined = new Float32Array(this.carry.length + input.length);
    joined.set(this.carry);
    joined.set(input, this.carry.length);
    let off = 0;
    for (; off + FRAME <= joined.length; off += FRAME) this.frame(joined.subarray(off, off + FRAME));
    this.carry = joined.slice(off);
  }

  private frame(f: Float32Array) {
    const frameMs = (FRAME / SAMPLE_RATE) * 1000;
    this.elapsedMs += frameMs;
    let sum = 0;
    for (let i = 0; i < f.length; i++) sum += f[i] * f[i];
    const db = 10 * Math.log10(sum / f.length + 1e-10);

    // auto-tuning VAD: kalibrasi derau awal, lalu lantai derau mengikuti perlahan saat hening
    if (this.elapsedMs <= CALIBRATION_MS) {
      this.calib.push(db);
      this.noiseFloorDb = mean(this.calib);
      this.threshDb = Math.max(this.noiseFloorDb + 10, -55);
      this.last = { db, pitch: null };
      return;
    }
    if (this.paused) {
      this.last = { db, pitch: null };
      return;
    }
    const voiced = db > this.threshDb;
    if (!voiced && !this.speaking) {
      this.noiseFloorDb = 0.98 * this.noiseFloorDb + 0.02 * db;
      this.threshDb = Math.max(this.noiseFloorDb + 10, -55);
    }
    const pitch = voiced ? detectPitch(f) : null;
    this.last = { db, pitch };

    if (voiced) {
      // jeda dihitung setiap kali suara kembali setelah hening >= 250 ms, termasuk jeda di dalam satu segmen
      if (this.silenceMs >= MIN_PAUSE_MS && this.speechMs > 0) this.pauses.push(this.silenceMs);
      if (!this.speaking) {
        if (this.firstOnset === null) this.firstOnset = this.elapsedMs;
        this.speaking = true;
      }
      this.silenceMs = 0;
      this.hangMs = 0;
      this.speechMs += frameMs;
      this.energies.push(db);
      if (pitch) {
        this.pitches.push(pitch);
        this.utterancePitch.push(pitch);
      }
      if (!this.wasVoiced) this.voicedRuns += 1;
      this.segment.push(f.slice());
    } else {
      this.silenceMs += frameMs;
      if (this.speaking) {
        this.hangMs += frameMs;
        this.segment.push(f.slice()); // sisakan ekor agar kata terakhir tidak terpotong
        if (this.hangMs >= SEGMENT_PAUSE_MS) {
          this.speaking = false;
          this.lastContour = this.contour(this.utterancePitch);
          this.utterancePitch = [];
          this.flushSegment();
        }
      }
    }
    this.wasVoiced = voiced;
  }

  private contour(p: number[]): ProsodySnapshot["intonation"]["endContour"] {
    if (p.length < 6) return null;
    const tail = p.slice(-Math.min(12, Math.floor(p.length / 2)));
    const head = p.slice(-2 * tail.length, -tail.length);
    if (!head.length) return null;
    const d = mean(tail) - mean(head);
    return d > 12 ? "naik" : d < -12 ? "turun" : "datar";
  }

  private flushSegment() {
    if (!this.segment.length) return;
    const n = this.segment.reduce((s, f) => s + f.length, 0);
    if (n >= SAMPLE_RATE * 0.4) {
      const out = new Float32Array(n);
      let o = 0;
      for (const f of this.segment) {
        out.set(f, o);
        o += f.length;
      }
      this.onSegment(out);
    }
    this.segment = [];
  }

  snapshot(): ProsodySnapshot {
    const p = this.pitches;
    const e = this.energies;
    const base = e.length >= 10 ? mean(e.slice(0, 10)) : null;
    const recent = e.length >= 10 ? mean(e.slice(-10)) : null;
    return {
      speaking: this.speaking,
      levelDb: Math.round(this.last.db),
      noiseFloorDb: Math.round(this.noiseFloorDb),
      pitchHz: this.last.pitch ? Math.round(this.last.pitch) : null,
      responseLatencyMs: this.firstOnset !== null ? Math.round(this.firstOnset - this.promptAt) : null,
      pauses: {
        count: this.pauses.length,
        meanMs: Math.round(mean(this.pauses)),
        maxMs: Math.round(this.pauses.length ? Math.max(...this.pauses) : 0),
      },
      intonation: {
        meanHz: p.length ? Math.round(mean(p)) : null,
        rangeHz: p.length ? Math.round(Math.max(...p) - Math.min(...p)) : null,
        stdHz: p.length ? Math.round(std(p)) : null,
        endContour: this.lastContour,
      },
      toneUpDb: base !== null && recent !== null ? Math.round((recent - base) * 10) / 10 : null,
      speechRate: this.speechMs > 1000 ? Math.round((this.voicedRuns / (this.speechMs / 1000)) * 10) / 10 : null,
      speechMs: Math.round(this.speechMs),
    };
  }
}
