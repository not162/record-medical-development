import React from "react";
import Link from "next/link";
import { ShieldCheck, ArrowLeft } from "lucide-react";

export const metadata = {
  title: "Kebijakan Privasi Rekam Medis & Perlindungan Data Pribadi | Web Klinik RSUKT",
  description: "Kebijakan Privasi Rekam Medis Elektronik Terpadu RSUKT sesuai UU No. 27 Tahun 2022 (UU PDP) dan ISO/IEC 27001:2022.",
};

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto space-y-8 bg-white border border-slate-200 p-8 sm:p-12 rounded-xl shadow-sm">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-700 hover:text-cyan-800 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Kembali ke Beranda</span>
        </Link>

        <div className="space-y-3 border-b border-slate-100 pb-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-50 border border-cyan-200 text-cyan-800 text-xs font-semibold">
            <ShieldCheck className="w-4 h-4 text-cyan-600" />
            <span>Kepatuhan UU No. 27/2022 (UU PDP) & ISO 27001</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Kebijakan Privasi Rekam Medis & Perlindungan Data Pribadi
          </h1>
          <p className="text-xs text-slate-500">
            Terakhir diperbarui: 1 November 2026 | Rumah Sakit Umum Kota Terpadu (RSUKT)
          </p>
        </div>

        <div className="space-y-6 text-xs sm:text-sm text-slate-700 leading-relaxed">
          <section className="space-y-2">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <span className="w-1.5 h-4 bg-cyan-600 rounded-full"></span>
              1. Prinsip Kerahasiaan Medis & Landasan Hukum
            </h2>
            <p>
              Web Klinik RSUKT berkomitmen melindungi privasi pasien dan integritas data medis klinis. Seluruh pemrosesan informasi kesehatan elektronik mematuhi Undang-Undang No. 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP), Peraturan Menteri Kesehatan No. 24 Tahun 2022 tentang Rekam Medis, serta standar keamanan ISO/IEC 27001:2022.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <span className="w-1.5 h-4 bg-cyan-600 rounded-full"></span>
              2. Kategori Data yang Diproses
            </h2>
            <ul className="list-disc pl-5 space-y-1 text-slate-600">
              <li><strong>Mode Tamu (Anonim):</strong> Teks keluhan gejala yang dimasukkan tanpa akun dianonimkan seketika. Riwayat sesi tamu bersifat efemeral (in-memory) dan tidak disimpan ke basis data permanen.</li>
              <li><strong>Pasien Terdaftar:</strong> Identitas pasien (nama, username, email), riwayat anamnesis konsultasi AI, dan resume konsultasi terenkripsi yang terasosiasi dengan ID pasien.</li>
              <li><strong>Data Teknis:</strong> Alamat IP tersamar, waktu akses, dan audit log keamanan untuk mencegah serangan siber dan memastikan ketersediaan layanan.</li>
            </ul>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <span className="w-1.5 h-4 bg-cyan-600 rounded-full"></span>
              3. Isolasi Akses Administrator (UU PDP Pasal 4)
            </h2>
            <p>
              Sistem menerapkan prinsip pemisahan tugas (*Segregation of Duties*) yang ketat. Administrator sistem, pengembang, maupun staf non-klinis secara teknis <strong>DILARANG KERAS</strong> dan dicegah oleh otorisasi server untuk melihat, membaca, atau mengoperasikan sesi percakapan konsultasi pribadi pasien.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <span className="w-1.5 h-4 bg-cyan-600 rounded-full"></span>
              4. Keamanan & Enkripsi Data
            </h2>
            <p>
              Seluruh komunikasi data antara peramban pengguna dan server dienkripsi menggunakan protokol TLS 1.3 (HTTPS). Kredensial akun diamankan menggunakan algoritma hashing bcrypt 12-round salt. Data medis sensitif yang disimpan pada basis data diproteksi dengan enkripsi at-rest.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <span className="w-1.5 h-4 bg-cyan-600 rounded-full"></span>
              5. Hak Pasien atas Data Pribadi
            </h2>
            <p>
              Pasien memiliki hak untuk mengakses riwayat konsultasi medis miliknya, mengunduh salinan ringkasan resume rekam medis (format teks/PDF), memperbarui profil data, atau mengajukan penghapusan riwayat sesi (*soft-delete* atau *hard-delete*) melalui fitur dalam dashboard akun.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <span className="w-1.5 h-4 bg-cyan-600 rounded-full"></span>
              6. Kontak Tim Perlindungan Data (DPO)
            </h2>
            <p>
              Untuk pertanyaan, keluhan, atau pelaksanaan hak pelindungan data pribadi, silakan hubungi Pejabat Pelindung Data Pribadi RSUKT melalui surel resmi: <span className="font-semibold text-cyan-800">dpo@rsukt.go.id</span> atau kunjungi Pusat Layanan Terpadu RSUKT.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
