# Dokumentasi Optimasi Web Performa, Core Web Vitals, SEO & GEO

## 1. Core Web Vitals & Optimasi Performa

### 1.1 Largest Contentful Paint (LCP) & Priority Hints
- Font Plus Jakarta Sans dimuat lewat `next/font` dengan `display: swap` (di-*self-host* saat build, tanpa permintaan ke Google Fonts saat runtime).
- Halaman publik dan auth dirender statis (`○ Static` pada `next build`).
- Layar pembuka `BrandLoader` dipersingkat dari 4 detik menjadi 1,2 detik dan hanya muncul sekali per sesi browser.
- Library berat (MediaPipe, transformers.js) **hanya dimuat di `/chat/suara`** lewat `import()` dinamis atau Web Worker, sehingga tidak membebani bundle halaman lain.

### 1.2 Cumulative Layout Shift (CLS)
- Skrip tema inline di `<head>` menerapkan kelas `dark` sebelum render pertama, sehingga tidak ada kedipan terang → gelap.
- Kolom isian berukuran tetap (44 px) dan pesan error dirender di slot yang sudah tersedia.

## 2. Adaptasi Dimensi & Responsivitas Perangkat

- Diverifikasi di lebar 375 px (mobile): `scrollWidth === innerWidth`, tanpa scroll horizontal.
- Form register memakai 2 kolom di `sm:` ke atas dan 1 kolom di bawahnya.
- `viewport-fit=cover` dan `theme-color` ganda (terang `#2563EB`, gelap `#070B16`).

## 3. Struktur Navigasi Prioritas & Drawer

- Header publik: logo, navigasi (Beranda, Privasi, Ketentuan), Pasang Aplikasi, toggle tema, dan tombol utama (Daftar/Masuk).
- Chat: sidebar desktop dan menu drawer di mobile (Tanya Asisten, Riwayat, Konsultasi Suara & Kamera, Profil, Pengaturan).
- Admin: sidebar dikelompokkan Operasional vs Riset; menu riset disembunyikan untuk `ADMIN`.

## 4. Metadata SEO (Search Engine Optimization)

- `metadataBase` dan `robots.ts`/`sitemap.ts` memakai `NEXT_PUBLIC_SITE_URL`, dengan fallback `https://klinik-terpadu.vercel.app`.
- Judul bertemplat `%s | Web Klinik RSUKT`, deskripsi, Open Graph `id_ID`.
- **PWA (`public/manifest.json`):** `id: "/"`, `start_url: /chat?source=pwa`, `display: standalone` (+ `window-controls-overlay`), ikon `any` + `maskable` 192/512, `apple-touch-icon`, dan tiga *shortcut* (Konsultasi Baru, Riwayat, Profil).
- **Service worker v3 (`public/sw.js`):** halaman offline dipra-cache; navigasi memakai *network-first* dengan fallback `offline.html`; aset `/_next/static`, ikon, dan font memakai *cache-first*. **API, SSE, dan HTML tidak pernah dicache** karena bisa berisi data pribadi. SW disajikan dengan `Cache-Control: no-cache` dan menampilkan banner "Versi baru tersedia" saat ada pembaruan.

## 5. Metadata GEO (Geolokasi & Wilayah Layanan)

Aplikasi tidak meminta lokasi pengguna (`Permissions-Policy: geolocation=()`). Wilayah layanan dinyatakan sebagai `addressCountry: ID` pada JSON-LD. Belum ada koordinat fasilitas fisik; tambahkan bila klinik mitra sudah ditetapkan.

## 6. Schema.org JSON-LD (Structured Data)

```json
{
  "@context": "https://schema.org",
  "@type": "MedicalOrganization",
  "name": "Web Klinik RSUKT",
  "url": "https://klinik-terpadu.vercel.app",
  "logo": "https://klinik-terpadu.vercel.app/icons/icon-512.png",
  "address": { "@type": "PostalAddress", "addressCountry": "ID" },
  "medicalSpecialty": ["EmergencyMedicine", "Cardiovascular", "InternalMedicine"]
}
```
Disisipkan di `apps/web/src/app/layout.tsx`.
