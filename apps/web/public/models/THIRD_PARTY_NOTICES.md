# Model pihak ketiga

## yolo11n-pose-320-q8.onnx
- Sumber: Ultralytics YOLO11n-pose (`yolo11n-pose.pt`, ultralytics 8.3.253)
- Lisensi: **AGPL-3.0** — https://github.com/ultralytics/ultralytics/blob/main/LICENSE
  Menyajikan model ini ke pengguna lewat jaringan mewajibkan kode sumber aplikasi tersedia di bawah AGPL-3.0,
  kecuali memakai Ultralytics Enterprise License.
- Ekspor: `YOLO("yolo11n-pose.pt").export(format="onnx", imgsz=320, opset=17, simplify=True)`,
  lalu `onnxruntime.quantization.quantize_dynamic(weight_type=QUInt8)` (11,6 MB -> 3,2 MB;
  selisih kotak < 1 px, keypoint rata-rata 0,7 px vs fp32 pada gambar uji `bus.jpg`).
- SHA-256: e21997e9199789a704c23fb92e627203136d1c4bda6bd19a9ffceb54a3b45313
- Runtime: onnxruntime-web 1.22.0 (MIT) dari jsDelivr, di Web Worker `public/workers/pose-worker.js`.
