# Pemodelan 5 Unsur dengan Metode Waterfall: Klinik Terpadu

## 1. Metode dan lima unsur

Proyek memakai **Waterfall terkendali dengan sprint inkremental**: setiap sprint melewati analisis → perancangan → implementasi → pengujian → penyebaran, dan berakhir dengan gerbang audit (lihat [plan_project](../plan_project/README.md)). Lima unsur pemodelan:

1. **ERD**: struktur data konseptual.
2. **LRS**: struktur record logis dan FK.
3. **Use Case**: kebutuhan dari sudut aktor.
4. **Activity**: alur proses bisnis.
5. **UML (Class, Sequence)**: struktur dan interaksi perangkat lunak.

## 2. Peta unsur ke fase Waterfall

| Fase | Unsur | Artefak |
|---|---|---|
| Analisis kebutuhan | Use Case (3) | [SRS.md](../business/SRS.md), [DIAGRAMS.md](DIAGRAMS.md) §3 |
| Perancangan proses | Activity (4) | [DIAGRAMS.md](DIAGRAMS.md) §4 |
| Perancangan data | ERD (1), LRS (2) | [ERD.md](ERD.md), [LRS.md](LRS.md) |
| Perancangan perangkat lunak | UML (5) | [DIAGRAMS.md](DIAGRAMS.md) §5 |
| Implementasi | — | `apps/web`, `services/ai-api` |
| Pengujian | — | `services/ai-api/tests`, `tests/` |
| Penyebaran & pemeliharaan | — | Vercel, [runbook](../plan_project/PRODUCTION_RUNBOOK_AND_ROLLBACK.md) |

## 3. Fase 1: Analisis kebutuhan (Unsur 3)

Aktor dan use case diturunkan dari kebutuhan FR-01–FR-09 di SRS. Batasan penting yang dimodelkan sejak awal: admin tidak boleh membaca chat pasien, dan media biometrik tidak boleh meninggalkan perangkat.

## 4. Fase 2: Perancangan (Unsur 4, 1, 2, 5)

### 4.1. Perancangan proses: Activity Diagram (Unsur 4)
Tiga alur utama: konsultasi teks, konsultasi suara & kamera, dan pipeline insight. Setiap keputusan (kuota, tanda bahaya, gerbang validasi) menjadi percabangan eksplisit.

### 4.2. Perancangan data: ERD lalu LRS (Unsur 1 dan 2)
ERD dirancang per modul, lalu diturunkan ke LRS dengan aturan di [LRS.md §2](LRS.md). Keputusan khusus: dokumen pengetahuan memakai ulang `dataset_records`, dan tidak ada tabel media.

### 4.3. Perancangan perangkat lunak: UML (Unsur 5)
Class diagram memisahkan `TextInsightModel` (server) dari `ProsodyAnalyzer`/`FaceAnalyzer`/worker ASR (browser). Sequence diagram memperjelas batas kepercayaan: proxy same-origin, JWT, dan BroadcastChannel.

## 5. Fase 3: Implementasi (penerjemahan ke kode)

| Rancangan | Kode |
|---|---|
| Entitas ERD | `services/ai-api/app/models*.py`, `database/migrations/` |
| Use case pasien | `apps/web/src/app/chat/*`, `routes/chat.py` |
| Use case riset | `apps/web/src/app/admin/*`, `routes/admin.py`, `knowledge.py`, `graph_crud.py`, `insights.py` |
| Activity insight | `ml/patient_insights.run_pipeline()` |
| Activity suara/kamera | `lib/voice/prosody.ts`, `lib/vision/face.ts`, `public/workers/asr-worker.js` |
| Sequence real-time | `lib/realtime.tsx` |

## 6. Fase 4: Pengujian (penelusuran dari desain)

| Desain | Tes |
|---|---|
| Matriks RBAC (use case per aktor) | `services/ai-api/tests/test_rbac_matrix.py` |
| Privasi insight & ekspor | `services/ai-api/tests/test_patient_insights.py` |
| Graf CRUD | `services/ai-api/tests/test_sprint21_graph_crud.py` |
| RAG portabel | `services/ai-api/tests/test_sprint21_rag_portable.py` |
| Penyesuaian adaptif | `services/ai-api/tests/test_adaptive_update.py` |
| Tipe & lint web | `npx tsc --noEmit`, `npx eslint` |

## 7. Fase 5: Penyebaran dan pemeliharaan

Push ke `main` memicu deploy Vercel untuk proyek `web` (Root Directory `apps/web`) dan `ai-api`. Prosedur rilis, pemulihan, dan rollback: [PRODUCTION_RUNBOOK_AND_ROLLBACK.md](../plan_project/PRODUCTION_RUNBOOK_AND_ROLLBACK.md).

## 8. Kualitas diagram: tidak ada garis yang bertabrakan

SVG ERD/LRS dibangkitkan otomatis: kotak disusun berjajar, dan setiap relasi dirutekan lewat jalur horizontal tersendiri di bawah semua kotak. Dengan begitu garis tidak memotong kotak dan tidak saling menumpuk. Diagram Mermaid dirender oleh GitHub.

## 9. Berkas diagram

```
docs/design/diagrams/
├── erd-1-akun-akses.svg        lrs-1-akun-akses.svg
├── erd-2-percakapan-klinis.svg lrs-2-percakapan-klinis.svg
├── erd-3-data-pengetahuan.svg  lrs-3-data-pengetahuan.svg
├── erd-4-model-training.svg    lrs-4-model-training.svg
└── erd-5-graf-pengetahuan.svg  lrs-5-graf-pengetahuan.svg
```
Use case, activity, class, dan sequence ditulis sebagai Mermaid di [DIAGRAMS.md](DIAGRAMS.md) agar selalu bisa di-*diff* bersama kode.
