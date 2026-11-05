/**
 * Analisis pose & gestur on-device dengan Ultralytics YOLO11n-pose (lihat public/workers/pose-worker.js).
 * Inferensi berjalan di Web Worker pada ~6 fps; main thread hanya mengirim ImageBitmap & menghitung fitur ringan.
 *
 * Fitur (COCO 17 keypoint, koordinat ternormalisasi 0..1):
 *   - jumlah orang di frame (privasi: peringatan bila > 1)
 *   - framing: terlalu jauh / terlalu dekat / tidak di tengah, dari lebar bahu & posisi hidung
 *   - tangan di dada (bertahan >= 1 dtk) & tangan ke kepala  -> INDIKASI gestur nyeri/pusing
 *   - kemiringan bahu & kegelisahan (perpindahan bahu/hidung per detik, relatif lebar bahu)
 *
 * Hasil bersifat INDIKASI, bukan diagnosis.
 */

export type Keypoint = [number, number, number]; // x, y, visibilitas
export interface Person { score: number; box: [number, number, number, number]; kps: Keypoint[] }

export interface PoseSnapshot {
  ready: boolean;
  persons: number;
  framing: "pas" | "terlalu jauh" | "terlalu dekat" | "geser ke tengah" | "tidak terlihat";
  handOnChest: boolean;
  chestHoldSec: number;   // akumulasi detik tangan di dada selama sesi
  handToHead: boolean;
  headHoldSec: number;
  shoulderTiltDeg: number | null;
  restlessness: number;   // lebar-bahu per detik (EMA); > 0.6 cenderung gelisah
  inferMs: number;
  fps: number;
}

const NOSE = 0, L_SH = 5, R_SH = 6, L_WR = 9, R_WR = 10;
const VIS = 0.45;
const SEND_INTERVAL_MS = 120; // batas atas ~8 fps: cukup untuk gestur
const MAX_INTERVAL_MS = 500;  // perangkat lambat: turun ke >= 2 fps, tidak pernah menumpuk antrean
const MODEL_SIDE = 320;       // sisi input model; frame diperkecil sebelum dikirim ke worker

const EMPTY: PoseSnapshot = {
  ready: false, persons: 0, framing: "tidak terlihat", handOnChest: false, chestHoldSec: 0, handToHead: false,
  headHoldSec: 0, shoulderTiltDeg: null, restlessness: 0, inferMs: 0, fps: 0,
};

const vis = (k: Keypoint | undefined) => !!k && k[2] >= VIS;
const dist = (a: Keypoint, b: Keypoint) => Math.hypot(a[0] - b[0], a[1] - b[1]);

/** Fitur pose dari satu frame. Diekspor terpisah agar mudah diuji. */
export function poseFeatures(p: Person | undefined) {
  if (!p) return null;
  const k = p.kps;
  const ls = k[L_SH], rs = k[R_SH];
  if (!vis(ls) || !vis(rs)) return { shoulders: false as const };
  const sw = Math.max(dist(ls, rs), 1e-3);
  const left = Math.min(ls[0], rs[0]) - 0.2 * sw;
  const right = Math.max(ls[0], rs[0]) + 0.2 * sw;
  const top = Math.min(ls[1], rs[1]);
  const bottom = top + 1.3 * sw; // pinggul sering di luar frame webcam -> pakai lebar bahu
  const wrists = [k[L_WR], k[R_WR]].filter(vis);
  const onChest = wrists.some((w) => w[0] > left && w[0] < right && w[1] > top && w[1] < bottom);
  const nose = vis(k[NOSE]) ? k[NOSE] : null;
  const toHead = !!nose && wrists.some((w) => w[1] < top && dist(w, nose) < 0.9 * sw);
  const tilt = (Math.atan2(rs[1] - ls[1], rs[0] - ls[0]) * 180) / Math.PI;
  const tiltDeg = Math.round(Math.abs(Math.abs(tilt) > 90 ? 180 - Math.abs(tilt) : tilt));
  const cx = nose ? nose[0] : (ls[0] + rs[0]) / 2;
  const framing: PoseSnapshot["framing"] =
    sw < 0.14 ? "terlalu jauh" : sw > 0.75 ? "terlalu dekat" : cx < 0.25 || cx > 0.75 ? "geser ke tengah" : "pas";
  return { shoulders: true as const, sw, onChest, toHead, tiltDeg, framing, anchor: [(ls[0] + rs[0]) / 2, (ls[1] + rs[1]) / 2] };
}

export class PoseAnalyzer {
  private worker: Worker;
  private snap: PoseSnapshot = { ...EMPTY };
  private lastPersons: Person[] = [];
  private pending = false;
  private lastSend = 0;
  private lastT: number | null = null;
  private lastAnchor: number[] | null = null;
  private chestSince: number | null = null;
  private headSince: number | null = null;
  private frames: number[] = [];
  private seq = 0;
  onError?: (msg: string) => void;

  constructor() {
    this.worker = new Worker("/workers/pose-worker.js", { type: "module" });
    this.worker.onmessage = (e: MessageEvent) => this.onMessage(e.data);
    this.worker.postMessage({ type: "load" });
  }

  private onMessage(m: { type: string; persons?: Person[]; ms?: number; message?: string }) {
    if (m.type === "ready") this.snap = { ...this.snap, ready: true };
    if (m.type === "skip") this.pending = false;
    if (m.type === "error") {
      this.pending = false;
      this.onError?.(m.message || "pose error");
    }
    if (m.type === "result") {
      this.pending = false;
      this.update(m.persons || [], m.ms || 0, performance.now());
    }
  }

  /** Interval kirim adaptif: mengikuti waktu inferensi nyata agar antrean tidak menumpuk (tanpa lag). */
  private interval() {
    const ms = this.snap.inferMs || 0;
    return Math.min(MAX_INTERVAL_MS, Math.max(SEND_INTERVAL_MS, ms * 1.25));
  }

  /** Dipanggil dari loop rAF; hanya mengirim frame bila worker siap, tidak sibuk, dan interval terpenuhi. */
  tick(video: HTMLVideoElement, now: number) {
    if (!this.snap.ready || this.pending || video.readyState < 2) return;
    if (typeof document !== "undefined" && document.hidden) return; // tab tidak terlihat -> hemat CPU
    if (now - this.lastSend < this.interval()) return;
    this.pending = true;
    this.lastSend = now;
    // perkecil di GPU sebelum dikirim: frame 1280x720 (~3,7 MB RGBA) -> 320 px (~0,3 MB) per frame
    const vw = video.videoWidth || 640;
    const vh = video.videoHeight || 480;
    const s = MODEL_SIDE / Math.max(vw, vh);
    createImageBitmap(video, { resizeWidth: Math.round(vw * s), resizeHeight: Math.round(vh * s), resizeQuality: "low" })
      .then((bitmap) => this.worker.postMessage({ type: "frame", id: ++this.seq, bitmap }, [bitmap]))
      .catch(() => { this.pending = false; });
  }

  update(persons: Person[], ms: number, now: number) {
    this.lastPersons = persons;
    this.frames.push(now);
    while (this.frames.length && now - this.frames[0] > 1000) this.frames.shift();
    const main = [...persons].sort((a, b) => (b.box[2] - b.box[0]) * (b.box[3] - b.box[1]) - (a.box[2] - a.box[0]) * (a.box[3] - a.box[1]))[0];
    const f = poseFeatures(main);
    const dt = this.lastT == null ? 0 : (now - this.lastT) / 1000;
    this.lastT = now;
    const s = { ...this.snap, persons: persons.length, inferMs: ms, fps: this.frames.length };
    if (!f || !f.shoulders) {
      this.chestSince = this.headSince = null;
      this.lastAnchor = null;
      this.snap = { ...s, framing: main ? "terlalu dekat" : "tidak terlihat", handOnChest: false, handToHead: false, shoulderTiltDeg: null };
      return;
    }
    // gestur harus bertahan >= 1 dtk agar gerakan sekilas tidak dihitung
    this.chestSince = f.onChest ? this.chestSince ?? now : null;
    this.headSince = f.toHead ? this.headSince ?? now : null;
    const chestOn = this.chestSince != null && now - this.chestSince >= 1000;
    const headOn = this.headSince != null && now - this.headSince >= 1000;
    let restless = s.restlessness;
    if (this.lastAnchor && dt > 0 && dt < 2) {
      const v = Math.hypot(f.anchor[0] - this.lastAnchor[0], f.anchor[1] - this.lastAnchor[1]) / f.sw / dt;
      restless = 0.8 * restless + 0.2 * v;
    }
    this.lastAnchor = f.anchor;
    this.snap = {
      ...s, framing: f.framing, handOnChest: chestOn, handToHead: headOn, shoulderTiltDeg: f.tiltDeg,
      chestHoldSec: Math.round((s.chestHoldSec + (chestOn ? dt : 0)) * 10) / 10,
      headHoldSec: Math.round((s.headHoldSec + (headOn ? dt : 0)) * 10) / 10,
      restlessness: Math.round(restless * 100) / 100,
    };
  }

  current(): PoseSnapshot { return this.snap; }
  persons(): Person[] { return this.lastPersons; }
  close() { this.worker.terminate(); }
}

const EDGES: [number, number][] = [[5, 6], [5, 7], [7, 9], [6, 8], [8, 10], [5, 11], [6, 12], [11, 12], [0, 1], [0, 2], [1, 3], [2, 4]];

/** Gambar kerangka di atas video (kanvas ikut dicerminkan lewat CSS seperti videonya). */
export function drawPose(canvas: HTMLCanvasElement, persons: Person[], videoW = 0, videoH = 0) {
  const c = canvas.getContext("2d");
  if (!c) return;
  const cw = (canvas.width = canvas.clientWidth);
  const ch = (canvas.height = canvas.clientHeight);
  c.clearRect(0, 0, cw, ch);
  // video memakai object-cover: petakan koordinat frame -> kotak tampilan yang terpotong
  const scale = videoW && videoH ? Math.max(cw / videoW, ch / videoH) : 1;
  const w = videoW ? videoW * scale : cw;
  const h = videoH ? videoH * scale : ch;
  c.setTransform(1, 0, 0, 1, (cw - w) / 2, (ch - h) / 2);
  c.lineWidth = 2;
  for (const p of persons) {
    c.strokeStyle = "rgba(52,211,153,0.9)";
    for (const [a, b] of EDGES) {
      const ka = p.kps[a], kb = p.kps[b];
      if (ka[2] < VIS || kb[2] < VIS) continue;
      c.beginPath();
      c.moveTo(ka[0] * w, ka[1] * h);
      c.lineTo(kb[0] * w, kb[1] * h);
      c.stroke();
    }
    c.fillStyle = "rgba(255,255,255,0.9)";
    for (const k of p.kps) if (k[2] >= VIS) c.fillRect(k[0] * w - 2, k[1] * h - 2, 4, 4);
  }
}
