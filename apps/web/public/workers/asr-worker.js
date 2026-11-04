// ASR on-device (Whisper via transformers.js) - Web Worker (module).
// Audio pasien tidak pernah dikirim ke server: model diunduh sekali dari Hugging Face Hub,
// lalu semua inferensi berjalan di perangkat (WebGPU bila ada, selain itu WASM).
//
// - KV cache      : dekoder Whisper memakai past_key_values (config use_cache=true) - token lama
//                   tidak dihitung ulang tiap langkah.
// - Continuous batching : segmen ucapan masuk ke antrean; saat model selesai satu batch, SEMUA segmen
//                   yang menunggu (maks MAX_BATCH) langsung didekode bersama - segmen baru tidak
//                   menunggu batch berikutnya penuh.
// - Auto-tuning   : saat load, real-time factor (RTF) diukur pada audio uji 2 dtk; bila terlalu lambat,
//                   otomatis turun dari whisper-base ke whisper-tiny dan ukuran batch disesuaikan.

// +esm: jsDelivr me-resolve dependensi (onnxruntime-web) menjadi URL absolut
const TRANSFORMERS = "https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.3.2/+esm";
const MODELS = { base: "onnx-community/whisper-base", tiny: "onnx-community/whisper-tiny" };
// Revisi dikunci ke commit tertentu (supply-chain): perubahan di repo model tidak otomatis masuk ke perangkat pasien.
const REVISIONS = {
  base: "1846881b6b3a3024392c1eea3ad983695bc23925",
  tiny: "ff4177021cc41f7db950912b73ea4fdf7d01d8e7",
};

let transcriber = null;
let tier = null;
let maxBatch = 4;
let busy = false;
const queue = [];

const post = (msg) => self.postMessage(msg);

async function build(lib, name, device) {
  return lib.pipeline("automatic-speech-recognition", MODELS[name], {
    device,
    revision: REVISIONS[name],
    dtype: device === "webgpu" ? "fp32" : "q8",
    progress_callback: (p) => {
      if (p.status === "progress" && p.total) post({ type: "progress", file: p.file, pct: Math.round((p.loaded / p.total) * 100) });
    },
  });
}

async function measureRtf(t) {
  const audio = new Float32Array(16000 * 2);
  for (let i = 0; i < audio.length; i++) audio[i] = 0.02 * Math.sin((2 * Math.PI * 180 * i) / 16000);
  // pemanasan dulu: inferensi pertama ikut menghitung kompilasi shader/WASM dan akan melebih-lebihkan RTF
  await t(audio.subarray(0, 8000), { language: "indonesian", task: "transcribe" });
  const t0 = performance.now();
  await t(audio, { language: "indonesian", task: "transcribe" });
  return (performance.now() - t0) / 2000; // detik proses per detik audio
}

async function load(prefer) {
  const lib = await import(TRANSFORMERS);
  lib.env.allowLocalModels = false;
  const device = self.navigator && "gpu" in self.navigator ? "webgpu" : "wasm";
  let name = prefer === "tiny" ? "tiny" : "base";
  let t;
  try {
    t = await build(lib, name, device);
  } catch (e) {
    if (device !== "webgpu") throw e;
    t = await build(lib, name, "wasm");
  }
  let rtf = await measureRtf(t);
  if (name === "base" && rtf > 0.9) {
    // auto-tune: perangkat terlalu lambat untuk base -> pakai tiny
    await t.dispose?.();
    name = "tiny";
    t = await build(lib, name, device);
    rtf = await measureRtf(t);
  }
  maxBatch = rtf < 0.3 ? 6 : rtf < 0.7 ? 3 : 1;
  transcriber = t;
  tier = name;
  const kv = Boolean(t.model?.config?.use_cache ?? true);
  post({ type: "ready", model: MODELS[name], device, rtf: Math.round(rtf * 100) / 100, maxBatch, kvCache: kv });
}

async function drain() {
  if (busy || !transcriber) return;
  busy = true;
  try {
    while (queue.length) {
      const batch = queue.splice(0, maxBatch);
      const t0 = performance.now();
      const out = await transcriber(batch.map((b) => b.audio), { language: "indonesian", task: "transcribe" });
      const arr = Array.isArray(out) ? out : [out];
      const ms = Math.round(performance.now() - t0);
      batch.forEach((b, i) =>
        post({ type: "result", id: b.id, text: (arr[i]?.text || "").trim(), batchSize: batch.length, decodeMs: ms, queued: queue.length })
      );
    }
  } catch (e) {
    post({ type: "error", message: String(e?.message || e) });
  } finally {
    busy = false;
  }
}

self.onmessage = async (e) => {
  const msg = e.data || {};
  try {
    if (msg.type === "load") await load(msg.prefer);
    if (msg.type === "segment") {
      queue.push({ id: msg.id, audio: msg.audio });
      drain();
    }
  } catch (err) {
    post({ type: "error", message: String(err?.message || err), tier });
  }
};
