import React from "react";
import Link from "next/link";
import { AlertTriangle, ArrowLeft, ShieldAlert } from "lucide-react";

export const metadata = {
  title: "Syarat & Ketentuan Konsultasi Medis Digital | Clinic with Agent Healthy",
  description: "Syarat dan Ketentuan Penggunaan Sistem CDSS Asisten AI Medis RSUKT & Batasan Tanggung Jawab Medis.",
};

export default function TermsPage() {
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
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-800 text-xs font-semibold">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <span>Batasan Tanggung Jawab Medis & Standar CDSS</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Syarat & Ketentuan Konsultasi Medis Digital
          </h1>
          <p className="text-xs text-slate-500">
            healthy with clinic and hospital | Rumah Sakit Umum Kota Terpadu (RSUKT)
          </p>
        </div>

        <div className="space-y-6 text-xs sm:text-sm text-slate-700 leading-relaxed">
          <div className="p-4 rounded-2xl bg-amber-50/80 border border-amber-200 text-amber-900 space-y-2">
            <h3 className="font-bold text-xs uppercase tracking-wider flex items-center gap-1.5 text-amber-800">
              <ShieldAlert className="w-4 h-4 text-amber-600" />
              Peringatan Kegawatdaruratan Medis
            </h3>
            <p className="text-xs leading-relaxed">
              Layanan AI ini BUKAN pengganti penanganan gawat darurat. Jika Anda mengalami nyeri dada hebat menjalar, sesak napas akut, penurunan kesadaran, kejang, perdarahan masif, atau gejala stroke, segera hubungi <strong>119</strong> atau langsung menuju <strong>Instalasi Gawat Darurat (IGD)</strong> rumah sakit terdekat.
            </p>
          </div>

          <section className="space-y-2">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <span className="w-1.5 h-4 bg-cyan-600 rounded-full"></span>
              1. Sifat Layanan CDSS (Bukan Diagnosis Definitif)
            </h2>
            <p>
              Asisten Kecerdasan Artifisial Medis Klinis RSUKT beroperasi sebagai *Clinical Decision Support System* (CDSS) dan media edukasi penapisan gejala awal. Rekomendasi, estimasi ICD-10, atau saran poliklinik spesialis yang diberikan tidak dapat diposisikan sebagai diagnosis medis final, resep obat mandiri, atau rencana terapi definitif tanpa pemeriksaan langsung oleh dokter ber-SIP.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <span className="w-1.5 h-4 bg-cyan-600 rounded-full"></span>
              2. Kewajiban & Integritas Data Pasien
            </h2>
            <p>
              Pengguna berkewajiban menyampaikan deskripsi keluhan dan riwayat medis secara jujur dan akurat. Sistem tidak bertanggung jawab atas ketidaktepatan analisis AI yang diakibatkan oleh pemberian informasi klinis yang tidak lengkap, keliru, atau sengaja dimanipulasi oleh pengguna.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <span className="w-1.5 h-4 bg-cyan-600 rounded-full"></span>
              3. Larangan Penggunaan (Adversarial & Abuse)
            </h2>
            <p>
              Pengguna dilarang melakukan upaya rekayasa instruksi (*prompt injection*), memintas filter keselamatan medis, memasukkan skrip berbahaya, meminta resep narkotika/psikotropika ilegal, atau mengeksploitasi antarmuka sistem untuk tujuan di luar konsultasi kesehatan wajar.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <span className="w-1.5 h-4 bg-cyan-600 rounded-full"></span>
              4. Batasan Tanggung Jawab Hukum
            </h2>
            <p>
              RSUKT dan para pengembang perangkat lunak dibebaskan dari segala tuntutan hukum atau kerugian yang timbul akibat keterlambatan pasien mencari pertolongan medis langsung di fasilitas pelayanan kesehatan, penggunaan mandiri obat-obatan tanpa pengawasan dokter, atau interpretasi sepihak atas rekomendasi edukatif sistem.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <span className="w-1.5 h-4 bg-cyan-600 rounded-full"></span>
              5. Persetujuan atas Syarat & Ketentuan
            </h2>
            <p>
              Dengan mengakses dan menggunakan Clinic with Agent Healthy, baik melalui Mode Tamu maupun akun terdaftar, Anda menyatakan telah membaca, memahami, dan menyetujui seluruh ketentuan ini tanpa syarat.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
