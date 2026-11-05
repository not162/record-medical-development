// Deteksi pose on-device: Ultralytics YOLO11n-pose (ONNX 320 px, kuantisasi uint8, ~3,2 MB) via onnxruntime-web.
// Berjalan di Web Worker agar main thread (video, UI, analisis suara) tetap ringan.
// Frame kamera TIDAK pernah meninggalkan perangkat: hanya kotak + 17 keypoint (ternormalisasi) yang dikirim balik.
//
// Model: Ultralytics YOLO11n-pose, lisensi AGPL-3.0 (https://github.com/ultralytics/ultralytics).
// Diekspor: YOLO("yolo11n-pose.pt").export(format="onnx", imgsz=320, opset=17, simplify=True)
//           lalu onnxruntime.quantization.quantize_dynamic(weight_type=QUInt8).

const ORT_VERSION = "1.22.0";
const ORT_BASE = `https://cdn.jsdelivr.net/npm/onnxruntime-web@${ORT_VERSION}/dist/`;
const MODEL_URL = "/models/yolo11n-pose-320-q8.onnx";
const SIZE = 320;
const CONF = 0.4;
const IOU = 0.45;
const MAX_PERSONS = 5;

let ort = null;
let session = null;
let canvas = null;
let ctx = null;
let busy = false;

const post = (m) => self.postMessage(m);

async function load() {
  ort = await import(`${ORT_BASE}ort.wasm.min.mjs`);
  ort.env.wasm.wasmPaths = ORT_BASE;
  // multi-thread butuh crossOriginIsolated; tanpa itu pakai 1 thread (tetap SIMD)
  ort.env.wasm.numThreads = self.crossOriginIsolated ? Math.min(4, self.navigator?.hardwareConcurrency || 2) : 1;
  const t0 = performance.now();
  session = await ort.InferenceSession.create(MODEL_URL, { executionProviders: ["wasm"], graphOptimizationLevel: "all" });
  canvas = new OffscreenCanvas(SIZE, SIZE);
  ctx = canvas.getContext("2d", { willReadFrequently: true });
  // pemanasan: inferensi pertama ikut menghitung inisialisasi WASM
  await session.run({ [session.inputNames[0]]: new ort.Tensor("float32", new Float32Array(3 * SIZE * SIZE), [1, 3, SIZE, SIZE]) });
  post({ type: "ready", loadMs: Math.round(performance.now() - t0), threads: ort.env.wasm.numThreads });
}

function preprocess(bitmap) {
  const w = bitmap.width;
  const h = bitmap.height;
  const r = SIZE / Math.max(w, h);
  const nw = Math.round(w * r);
  const nh = Math.round(h * r);
  ctx.fillStyle = "rgb(114,114,114)";
  ctx.fillRect(0, 0, SIZE, SIZE);
  ctx.drawImage(bitmap, 0, 0, nw, nh); // letterbox kiri-atas
  const px = ctx.getImageData(0, 0, SIZE, SIZE).data;
  const n = SIZE * SIZE;
  const x = new Float32Array(3 * n);
  for (let i = 0; i < n; i++) {
    x[i] = px[i * 4] / 255;
    x[n + i] = px[i * 4 + 1] / 255;
    x[2 * n + i] = px[i * 4 + 2] / 255;
  }
  return { x, r, w, h };
}

function iou(a, b) {
  const x1 = Math.max(a[0], b[0]);
  const y1 = Math.max(a[1], b[1]);
  const x2 = Math.min(a[2], b[2]);
  const y2 = Math.min(a[3], b[3]);
  const inter = Math.max(0, x2 - x1) * Math.max(0, y2 - y1);
  return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter + 1e-9);
}

// output0: [1, 56, N] -> per kandidat: cx, cy, w, h, conf, lalu 17 x (x, y, visibilitas)
function decode(out, N, r, w, h) {
  const cands = [];
  for (let j = 0; j < N; j++) {
    const conf = out[4 * N + j];
    if (conf < CONF) continue;
    const cx = out[j];
    const cy = out[N + j];
    const bw = out[2 * N + j];
    const bh = out[3 * N + j];
    cands.push({ conf, j, box: [cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2] });
  }
  cands.sort((a, b) => b.conf - a.conf);
  const kept = [];
  for (const c of cands) {
    if (kept.every((k) => iou(k.box, c.box) < IOU)) kept.push(c);
    if (kept.length >= MAX_PERSONS) break;
  }
  // kembalikan ke koordinat ternormalisasi frame asli (0..1)
  const nx = (v) => Math.min(1, Math.max(0, v / r / w));
  const ny = (v) => Math.min(1, Math.max(0, v / r / h));
  return kept.map((c) => {
    const kps = [];
    for (let k = 0; k < 17; k++) {
      const base = (5 + k * 3) * N + c.j;
      kps.push([nx(out[base]), ny(out[base + N]), out[base + 2 * N]]);
    }
    return { score: Math.round(c.conf * 100) / 100, box: [nx(c.box[0]), ny(c.box[1]), nx(c.box[2]), ny(c.box[3])], kps };
  });
}

async function infer(id, bitmap) {
  if (!session || busy) {
    bitmap.close?.();
    post({ type: "skip", id });
    return;
  }
  busy = true;
  try {
    const t0 = performance.now();
    const { x, r, w, h } = preprocess(bitmap);
    bitmap.close?.();
    const res = await session.run({ [session.inputNames[0]]: new ort.Tensor("float32", x, [1, 3, SIZE, SIZE]) });
    const t = res[session.outputNames[0]];
    const persons = decode(t.data, t.dims[2], r, w, h);
    post({ type: "result", id, persons, ms: Math.round(performance.now() - t0) });
  } finally {
    busy = false;
  }
}

self.onmessage = async (e) => {
  const m = e.data || {};
  try {
    if (m.type === "load") await load();
    if (m.type === "frame") await infer(m.id, m.bitmap);
  } catch (err) {
    post({ type: "error", message: String(err?.message || err) });
  }
};
