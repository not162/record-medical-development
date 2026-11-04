/**
 * Analisis raut & mimik wajah on-device dengan MediaPipe Face Landmarker (blendshape).
 * Video tidak pernah meninggalkan perangkat; hanya skor numerik yang dihitung.
 *
 * Hasil bersifat INDIKASI ekspresi, bukan diagnosis emosi atau kondisi medis.
 */

const MP_VERSION = "1.2.2";
const MP_BASE = `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${MP_VERSION}`;
const FACE_MODEL =
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";

type Category = { categoryName: string; score: number };
interface FaceLandmarkerLike {
  detectForVideo(video: HTMLVideoElement, ts: number): {
    faceBlendshapes?: { categories: Category[] }[];
    facialTransformationMatrixes?: { data: number[] }[];
  };
  close(): void;
}

export interface FaceSnapshot {
  faceFound: boolean;
  expression: "Netral" | "Tersenyum" | "Tegang" | "Sedih" | "Terkejut" | "Cemas" | "-";
  scores: { senyum: number; cemberut: number; alisTurun: number; alisNaik: number; mataLebar: number; mulutTerbuka: number };
  blinkPerMin: number;
  headYawDeg: number;
  headPitchDeg: number;
  movement: number; // rerata perubahan pose (derajat/frame) - gelisah vs tenang
  fps: number;
}

const EMPTY: FaceSnapshot = {
  faceFound: false,
  expression: "-",
  scores: { senyum: 0, cemberut: 0, alisTurun: 0, alisNaik: 0, mataLebar: 0, mulutTerbuka: 0 },
  blinkPerMin: 0,
  headYawDeg: 0,
  headPitchDeg: 0,
  movement: 0,
  fps: 0,
};

export async function createFaceLandmarker(): Promise<FaceLandmarkerLike> {
  const mod = await import(/* webpackIgnore: true */ /* turbopackIgnore: true */ `${MP_BASE}/vision_bundle.mjs`);
  const vision = await mod.FilesetResolver.forVisionTasks(`${MP_BASE}/wasm`);
  const opts = (delegate: "GPU" | "CPU") => ({
    baseOptions: { modelAssetPath: FACE_MODEL, delegate },
    runningMode: "VIDEO",
    numFaces: 1,
    outputFaceBlendshapes: true,
    outputFacialTransformationMatrixes: true,
  });
  try {
    return await mod.FaceLandmarker.createFromOptions(vision, opts("GPU"));
  } catch {
    return await mod.FaceLandmarker.createFromOptions(vision, opts("CPU"));
  }
}

export class FaceAnalyzer {
  private ema: FaceSnapshot["scores"] = { ...EMPTY.scores };
  private blinks: number[] = [];
  private eyesClosed = false;
  private lastPose: [number, number] | null = null;
  private moves: number[] = [];
  private frames: number[] = [];
  private snap: FaceSnapshot = { ...EMPTY };

  constructor(private landmarker: FaceLandmarkerLike) {}

  process(video: HTMLVideoElement, now: number): FaceSnapshot {
    if (video.readyState < 2) return this.snap;
    const res = this.landmarker.detectForVideo(video, now);
    this.frames.push(now);
    while (this.frames.length && now - this.frames[0] > 1000) this.frames.shift();
    const cats = res.faceBlendshapes?.[0]?.categories;
    if (!cats) {
      this.snap = { ...this.snap, faceFound: false, expression: "-", fps: this.frames.length };
      return this.snap;
    }
    const b = (name: string) => cats.find((c) => c.categoryName === name)?.score ?? 0;
    const raw = {
      senyum: (b("mouthSmileLeft") + b("mouthSmileRight")) / 2,
      cemberut: (b("mouthFrownLeft") + b("mouthFrownRight")) / 2,
      alisTurun: (b("browDownLeft") + b("browDownRight")) / 2,
      alisNaik: b("browInnerUp"),
      mataLebar: (b("eyeWideLeft") + b("eyeWideRight")) / 2,
      mulutTerbuka: b("jawOpen"),
    };
    const a = 0.3; // pemulusan EMA agar tidak berkedip-kedip
    (Object.keys(raw) as (keyof typeof raw)[]).forEach((k) => {
      this.ema[k] = a * raw[k] + (1 - a) * this.ema[k];
    });

    // kedipan: transisi mata tertutup -> terbuka
    const blink = (b("eyeBlinkLeft") + b("eyeBlinkRight")) / 2;
    if (blink > 0.55 && !this.eyesClosed) this.eyesClosed = true;
    if (blink < 0.3 && this.eyesClosed) {
      this.eyesClosed = false;
      this.blinks.push(now);
    }
    while (this.blinks.length && now - this.blinks[0] > 60000) this.blinks.shift();

    // pose kepala dari matriks transformasi (column-major 4x4)
    let yaw = 0;
    let pitch = 0;
    const m = res.facialTransformationMatrixes?.[0]?.data;
    if (m && m.length >= 16) {
      yaw = (Math.atan2(-m[8], Math.sqrt(m[9] * m[9] + m[10] * m[10])) * 180) / Math.PI;
      pitch = (Math.atan2(m[9], m[10]) * 180) / Math.PI;
      if (this.lastPose) this.moves.push(Math.abs(yaw - this.lastPose[0]) + Math.abs(pitch - this.lastPose[1]));
      this.lastPose = [yaw, pitch];
      if (this.moves.length > 90) this.moves.shift();
    }

    const s = this.ema;
    let expression: FaceSnapshot["expression"] = "Netral";
    if (s.senyum > 0.45) expression = "Tersenyum";
    else if (s.mataLebar > 0.35 && s.alisNaik > 0.4 && s.mulutTerbuka > 0.25) expression = "Terkejut";
    else if (s.cemberut > 0.25 && s.alisNaik > 0.3) expression = "Sedih";
    else if (s.alisTurun > 0.35) expression = "Tegang";
    else if (s.alisNaik > 0.45) expression = "Cemas";

    const round = (v: number) => Math.round(v * 100) / 100;
    this.snap = {
      faceFound: true,
      expression,
      scores: {
        senyum: round(s.senyum), cemberut: round(s.cemberut), alisTurun: round(s.alisTurun),
        alisNaik: round(s.alisNaik), mataLebar: round(s.mataLebar), mulutTerbuka: round(s.mulutTerbuka),
      },
      blinkPerMin: this.blinks.length,
      headYawDeg: Math.round(yaw),
      headPitchDeg: Math.round(pitch),
      movement: round(this.moves.length ? this.moves.reduce((x, y) => x + y, 0) / this.moves.length : 0),
      fps: this.frames.length,
    };
    return this.snap;
  }

  /** Snapshot terakhir tanpa menjalankan deteksi ulang. */
  current(): FaceSnapshot {
    return this.snap;
  }

  close() {
    this.landmarker.close();
  }
}
