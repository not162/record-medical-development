# Dokumentasi Desain Sistem & Rekayasa Perangkat Lunak (`docs/design/`)

Subfolder ini memuat pemodelan arsitektur perangkat lunak, perancangan antarmuka (UI/UX), diagram UML, dan pemodelan data relasional untuk **Klinik Terpadu**.

---

## Berkas Dokumentasi dalam Subfolder Ini

1. **[SYSTEM_MODELING_5_ELEMENTS.md](SYSTEM_MODELING_5_ELEMENTS.md)** *(dokumen induk)*:
   - Pemetaan **5 unsur pemodelan** (ERD, LRS, Use Case, Activity, UML) ke fase **Waterfall**, penelusuran ke kode Next.js/FastAPI dan tes, serta aturan pemeliharaan diagram.
2. **[LRS.md](LRS.md)**:
   - Logical Record Structure per modul, aturan transformasi ERD → LRS, matriks FK beserta `ON DELETE`, dan catatan normalisasi.
   - Pasangannya, [ERD.md](ERD.md): 13 tabel dalam lima modul, dibangkitkan dari model SQLAlchemy.
3. **[DIAGRAMS.md](DIAGRAMS.md)**:
   - Use case, activity, class, dan sequence (Mermaid). Gambar ERD/LRS ada di `diagrams/`.
4. **[BRAND_GUIDE.md](BRAND_GUIDE.md)**:
   - Identitas visual: gradien biru `#2563EB` → cyan `#06B6D4`, navy gelap `#070B16`, Plus Jakarta Sans, logo palang medis.
5. **[UI_PLAN.md](UI_PLAN.md)**:
   - Peta situs per peran dan arsitektur komponen (AuthShell, ThemeToggle, LiveIndicator, InstallAppButton).
6. **[WEB_PERFORMANCE_SEO_GEO.md](WEB_PERFORMANCE_SEO_GEO.md)**:
   - PWA (manifest, service worker v3, offline), Core Web Vitals, metadata SEO, dan JSON-LD `MedicalOrganization`.
7. **[TECHNOLOGY_ARCHITECTURE.md](TECHNOLOGY_ARCHITECTURE.md)**:
   - Diagram deployment Vercel (web + API) + Neon, serta komponen on-device (MediaPipe, Whisper).
8. **[CIRCULAR_FRAMEWORK_METHODS_AND_ALGORITHMS.md](CIRCULAR_FRAMEWORK_METHODS_AND_ALGORITHMS.md)**:
   - Kerangka lingkaran sistem dan rumus algoritma inti: RAG hibrida RRF, reweighing Kamiran–Calders, RLHF reward-weighted, self-improvement bergerbang, temperature scaling, VAD/pitch, KV cache dan continuous batching.

---

## 5 Unsur Pemodelan dan Fase Waterfall

| No | Unsur | Fase Waterfall | Dokumen |
|---|---|---|---|
| 1 | ERD | Perancangan | [ERD.md](ERD.md) |
| 2 | LRS | Perancangan | [LRS.md](LRS.md) |
| 3 | Use Case | Analisis kebutuhan | [DIAGRAMS.md](DIAGRAMS.md) bagian 3 |
| 4 | Activity | Perancangan | [DIAGRAMS.md](DIAGRAMS.md) bagian 4 |
| 5 | UML (Class, Sequence) | Perancangan | [DIAGRAMS.md](DIAGRAMS.md) bagian 5 |

Penelusuran lengkap ke implementasi, pengujian, dan pemeliharaan: [SYSTEM_MODELING_5_ELEMENTS.md](SYSTEM_MODELING_5_ELEMENTS.md).
