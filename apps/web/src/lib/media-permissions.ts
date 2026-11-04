/**
 * Izin kamera & mikrofon real-time.
 *
 * Browser hanya menampilkan dialog izin bila:
 *   1. halaman berjalan di secure context (HTTPS atau localhost),
 *   2. header Permissions-Policy mengizinkan (camera=(self), microphone=(self)),
 *   3. getUserMedia dipanggil dari aksi pengguna (klik),
 *   4. pengguna belum memblokir situs ini sebelumnya (status "denied" harus dibuka manual).
 */

export type PermState = "granted" | "denied" | "prompt" | "unsupported";

export interface MediaPermissions {
  camera: PermState;
  microphone: PermState;
  secure: boolean;
  policyAllows: { camera: boolean; microphone: boolean };
  hasDevices: { camera: boolean; microphone: boolean };
}

type FeaturePolicyDoc = Document & { featurePolicy?: { allowsFeature(f: string): boolean } };

async function query(name: "camera" | "microphone"): Promise<PermState> {
  try {
    const st = await navigator.permissions.query({ name: name as PermissionName });
    return st.state as PermState;
  } catch {
    return "unsupported"; // Firefox/Safari lama tidak mendukung query kamera
  }
}

export async function checkMediaPermissions(): Promise<MediaPermissions> {
  const fp = (document as FeaturePolicyDoc).featurePolicy;
  let devices: MediaDeviceInfo[] = [];
  try {
    devices = (await navigator.mediaDevices?.enumerateDevices?.()) ?? [];
  } catch {
    devices = [];
  }
  return {
    camera: await query("camera"),
    microphone: await query("microphone"),
    secure: window.isSecureContext,
    policyAllows: {
      camera: fp ? fp.allowsFeature("camera") : true,
      microphone: fp ? fp.allowsFeature("microphone") : true,
    },
    // label perangkat kosong sebelum izin diberikan, tapi jenisnya tetap terlihat
    hasDevices: {
      camera: devices.length === 0 || devices.some((d) => d.kind === "videoinput"),
      microphone: devices.length === 0 || devices.some((d) => d.kind === "audioinput"),
    },
  };
}

/** Pantau perubahan izin (mis. pengguna membuka blokir lewat ikon gembok) tanpa reload. */
export function watchMediaPermissions(onChange: () => void): () => void {
  const subs: PermissionStatus[] = [];
  (["camera", "microphone"] as const).forEach((n) => {
    navigator.permissions
      ?.query({ name: n as PermissionName })
      .then((st) => {
        st.addEventListener("change", onChange);
        subs.push(st);
      })
      .catch(() => undefined);
  });
  return () => subs.forEach((s) => s.removeEventListener("change", onChange));
}

const AUDIO: MediaTrackConstraints = { echoCancellation: true, noiseSuppression: true, channelCount: 1 };
const VIDEO: MediaTrackConstraints = { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" };

export interface MediaResult {
  stream: MediaStream;
  video: boolean;
  note?: string;
}

/**
 * Minta izin & buka stream. Bila kamera ditolak/tidak ada, otomatis lanjut ke mode suara saja
 * agar konsultasi tetap bisa berjalan. Wajib dipanggil langsung dari handler klik.
 */
export async function openMedia(wantVideo: boolean): Promise<MediaResult> {
  if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
    throw Object.assign(new Error("insecure"), { name: "InsecureContext" });
  }
  if (wantVideo) {
    try {
      return { stream: await navigator.mediaDevices.getUserMedia({ audio: AUDIO, video: VIDEO }), video: true };
    } catch (e) {
      const name = (e as DOMException).name;
      if (!["NotAllowedError", "NotFoundError", "NotReadableError", "OverconstrainedError"].includes(name)) throw e;
      // coba lagi hanya mikrofon (kamera ditolak/sedang dipakai aplikasi lain/tidak ada)
      const stream = await navigator.mediaDevices.getUserMedia({ audio: AUDIO });
      return {
        stream,
        video: false,
        note:
          name === "NotReadableError"
            ? "Kamera sedang dipakai aplikasi lain (mis. Zoom/WhatsApp). Lanjut dengan suara saja."
            : name === "NotFoundError"
              ? "Kamera tidak ditemukan. Lanjut dengan suara saja."
              : "Akses kamera ditolak. Lanjut dengan suara saja.",
      };
    }
  }
  return { stream: await navigator.mediaDevices.getUserMedia({ audio: AUDIO }), video: false };
}

export function permissionHelp(): string {
  const ua = navigator.userAgent;
  if (/Android/i.test(ua)) return "Ketuk ikon gembok di samping alamat situs → Izin → aktifkan Kamera dan Mikrofon, lalu muat ulang halaman.";
  if (/iPhone|iPad/i.test(ua)) return "Buka Pengaturan iPhone → Safari → Kamera & Mikrofon → pilih Izinkan/Tanya, lalu muat ulang halaman.";
  if (/Firefox/i.test(ua)) return "Klik ikon kamera/gembok di kiri alamat situs → hapus blokir Kamera dan Mikrofon, lalu muat ulang.";
  if (/Safari/i.test(ua) && !/Chrome/i.test(ua)) return "Safari → Pengaturan untuk situs ini → Kamera & Mikrofon: Izinkan, lalu muat ulang.";
  return "Klik ikon gembok/pengaturan situs di kiri alamat → Kamera & Mikrofon: Izinkan, lalu muat ulang halaman. Pastikan juga izin kamera untuk browser aktif di pengaturan privasi Windows/macOS.";
}
