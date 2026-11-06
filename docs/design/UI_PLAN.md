# UI and Sitemap Plan

## Core Philosophy

- **Mobile-first, PWA-first:** semua halaman nyaman di lebar 375 px tanpa scroll horizontal, bisa dipasang sebagai aplikasi, dan punya halaman offline.
- **Satu peran, satu ruang:** pasien, Admin Operasional, dan Admin Riset masing-masing punya tata letak sendiri dan tidak bisa saling masuk.
- **Data selalu segar:** halaman CRUD menampilkan indikator "Live dari database".
- **Jujur soal batasan:** disclaimer medis dan label "indikasi" selalu terlihat.

## Sitemap

### Public
| Rute | Isi |
|---|---|
| `/` | Beranda: cara pakai, yang bisa & tidak bisa, layanan, privasi |
| `/login` | Masuk (username/email, sandi + tampilkan, Ingat saya, lupa sandi) |
| `/register` | Daftar pasien (2 kolom, pengukur kekuatan sandi, persetujuan ketentuan) |
| `/forgot-password` | Pemulihan sandi dengan kode 6 digit |
| `/privacy`, `/terms` | Kebijakan privasi, ketentuan |
| `/offline.html` | Halaman cadangan saat offline (service worker) |

### Patient Dashboard (Requires Auth, `USER`)
| Rute | Isi |
|---|---|
| `/chat` | Konsultasi (Thinking/Fast, sitasi, kuota, umpan balik) |
| `/chat/history` | Riwayat sesi |
| `/chat/tips` | Tips Hidup Sehat & rekomendasi dari biodata |
| `/profile`, `/settings` | Profil kesehatan, pengaturan akun |

### Staff & Admin Dashboard (Requires Role)
| Rute | `ADMIN` | `RESEARCHER` |
|---|---|---|
| `/admin/dashboard`, `/admin/feedback`, `/admin/audit-logs`, `/admin/settings` | ✓ | ✓ |
| `/admin/training`, `/admin/models`, `/admin/evaluation` | — | ✓ |
| `/admin/datasets`, `/admin/datasets/imports`, `/admin/annotations` | — | ✓ |
| `/admin/knowledge-base` (CRUD live), `/admin/graph` | — | ✓ |
| `/admin/users` (live) | — | ✓ |
| `/admin/insights` (Insight Pasien & RLHF) | — | ✓ |

## Architecture

```
apps/web/src/
├── app/                    # App Router: halaman per rute di atas
├── components/
│   ├── auth/AuthShell.tsx  # header ringkas + glow + kartu auth (gaya PRISMA)
│   ├── auth/PasswordInput.tsx
│   ├── BrandMark.tsx, ThemeToggle.tsx, InstallAppButton.tsx
│   ├── PwaRegistration.tsx # registrasi SW, banner versi baru & offline
│   └── BrandLoader.tsx     # layar pembuka 1,2 dtk (sekali per sesi)
└── lib/
    ├── api.ts              # klien API + token (getToken/setToken)
    ├── auth-context.tsx    # login(remember), logout, refreshUser
    ├── realtime.tsx        # useLiveQuery, useLiveMutation, LiveIndicator
    ├── roles.ts            # canAccess, homePathForRole
```
