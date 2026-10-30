# Patching UI files to use medical terminology and strengthen PDP / ISO compliance

# 1. Patch apps/web/src/app/login/page.tsx
login_path = r"apps/web/src/app/login/page.tsx"
with open(login_path, "r", encoding="utf-8") as f:
    login_code = f.read().replace("\r\n", "\n")

login_code = login_code.replace(
    'Masuk ke Sistem Klinis',
    'Portal Masuk Sistem Medis & Anamnesis Klinis'
).replace(
    'Akses Chatbot Edukasi Pasien atau Workspace Riset Administrator',
    'Layanan Konsultasi Triase Pasien Berbasis AI & Workspace Peneliti Medis RSUKT'
).replace(
    'Username atau Email',
    'Identitas Pasien / Username / Surel Klinis'
).replace(
    'placeholder="nama_pengguna atau email@rsukt.go.id"',
    'placeholder="No. Rekam Medis / nama_pasien / email@rsukt.go.id"'
).replace(
    '<label className="block text-xs font-semibold text-slate-700">\n                Kata Sandi\n              </label>',
    '<label className="block text-xs font-semibold text-slate-700">\n                Kata Sandi Kredensial Medis\n              </label>'
).replace(
    '<span>Memproses Verifikasi...</span>',
    '<span>Memverifikasi Otorisasi Kredensial Medis...</span>'
).replace(
    '<span>Masuk Sekarang</span>',
    '<span>Autentikasi Akses Klinis</span>'
).replace(
    'Daftar Akun Baru (User)',
    'Registrasi Pasien Baru (Peran: Pasien / User)'
)

with open(login_path, "w", encoding="utf-8") as f:
    f.write(login_code)
print("Patched login page.")

# 2. Patch apps/web/src/app/register/page.tsx
reg_path = r"apps/web/src/app/register/page.tsx"
with open(reg_path, "r", encoding="utf-8") as f:
    reg_code = f.read().replace("\r\n", "\n")

reg_code = reg_code.replace(
    'Pendaftaran Pengguna Baru',
    'Registrasi Pasien & Rekam Medis Elektronik'
).replace(
    'Daftar untuk berkonsultasi dengan Asisten AI Klinis RSUKT',
    'Pendaftaran Pasien untuk Konsultasi Anamnesis Terpandu AI & Rekam Medis Terenkripsi'
).replace(
    'Username <span className="text-red-500">*</span>',
    'ID Pengguna Pasien / Rekam Medis <span className="text-red-500">*</span>'
).replace(
    'placeholder="misal: pasien_andi"',
    'placeholder="misal: pasien_anamnesis_01"'
).replace(
    'Email Valid <span className="text-red-500">*</span>',
    'Alamat Surel Pasien Terdaftar <span className="text-red-500">*</span>'
).replace(
    'placeholder="andi@gmail.com"',
    'placeholder="pasien@rsukt.go.id"'
).replace(
    'Nama Lengkap (Opsional)',
    'Nama Lengkap Pasien Sesuai Identitas Resmi (KTP/KIA)'
).replace(
    'placeholder="Andi Pratama"',
    'placeholder="misal: Siti Rahmawati / Budi Santoso"'
).replace(
    'Kata Sandi (Minimal 8 karakter) <span className="text-red-500">*</span>',
    'Kata Sandi Kredensial Medis (Min. 8 karakter) <span className="text-red-500">*</span>'
).replace(
    'Konfirmasi Kata Sandi <span className="text-red-500">*</span>',
    'Konfirmasi Kata Sandi Kredensial Medis <span className="text-red-500">*</span>'
).replace(
    '<span>Mendaftarkan Akun...</span>',
    '<span>Mendaftarkan Subjek Klinis ke Basis Data...</span>'
).replace(
    '<span>Daftar Sekarang (Role: USER)</span>',
    '<span>Daftarkan Pasien (Peran: Pasien / User Klinis)</span>'
).replace(
    '<span>Pendaftaran publik hanya menetapkan peran Pengguna Standar (USER)</span>',
    '<span>Registrasi publik secara otomatis menetapkan hak akses Pasien / Pengguna Klinis (USER)</span>'
).replace(
    '<span>Keamanan data terjamin sesuai UU PDP No. 27/2022 & ISO 27001 ISMS</span>',
    '<span>Data kesehatan sensitif dilindungi sesuai UU PDP No. 27/2022 (Pasal 4) & ISO/IEC 27001 ISMS</span>'
)

with open(reg_path, "w", encoding="utf-8") as f:
    f.write(reg_code)
print("Patched register page.")

# 3. Patch apps/web/src/app/profile/page.tsx
prof_path = r"apps/web/src/app/profile/page.tsx"
with open(prof_path, "r", encoding="utf-8") as f:
    prof_code = f.read().replace("\r\n", "\n")

prof_code = prof_code.replace(
    '<span>Profil Rekam Medis Pasien</span>',
    '<span>Profil Rekam Medis & Anamnesis Pasien</span>'
).replace(
    'Informasi rekam medis terlindungi yang digunakan secara personal untuk grounding respons chatbot.',
    'Parameter klinis dan riwayat komorbiditas yang digunakan secara personal untuk kalibrasi penalaran AI dan deteksi kontraindikasi farmakologis.'
).replace(
    '<span>Status Otorisasi Identitas Pasien</span>',
    '<span>Status Otorisasi Identitas Pasien (UU PDP No. 27/2022 Pasal 4)</span>'
).replace(
    '<label className="block text-slate-700 font-medium mb-1.5">Nama Lengkap</label>',
    '<label className="block text-slate-700 font-medium mb-1.5">Nama Lengkap Pasien Sesuai Identitas Resmi</label>'
).replace(
    '<label className="block text-slate-700 font-medium mb-1.5">Usia (Tahun)</label>',
    '<label className="block text-slate-700 font-medium mb-1.5">Usia Kronologis (Tahun)</label>'
).replace(
    '<label className="block text-slate-700 font-medium mb-1.5">Jenis Kelamin</label>',
    '<label className="block text-slate-700 font-medium mb-1.5">Fenotipe Jenis Kelamin Biologis</label>'
).replace(
    '<label className="block text-slate-700 font-medium mb-1.5">Golongan Darah</label>',
    '<label className="block text-slate-700 font-medium mb-1.5">Golongan Darah & Sistem Rhesus (ABO)</label>'
).replace(
    'Ringkasan Riwayat Alergi, Obat, & Penyakit Kronis',
    'Anamnesis Riwayat Penyakit Kronis, Alergi Farmakologis, & Pengobatan Berjalan'
).replace(
    'Contoh: Riwayat asma sejak anak-anak, alergi debu, riwayat hipertensi ringan terkontrol.',
    'Contoh: Hipertensi Grade 1 terkontrol Amlodipine 5mg; Riwayat alergi obat golongan Penisilin (urtikaria); Riwayat Asma Bronkial intermiten.'
).replace(
    '<span>{saving ? "Menyimpan..." : "Simpan Profil Medis"}</span>',
    '<span>{saving ? "Sinkronisasi..." : "Simpan & Sinkronisasi Rekam Medis"}</span>'
)

with open(prof_path, "w", encoding="utf-8") as f:
    f.write(prof_code)
print("Patched profile page.")

# 4. Patch apps/web/src/app/settings/page.tsx
sett_path = r"apps/web/src/app/settings/page.tsx"
with open(sett_path, "r", encoding="utf-8") as f:
    sett_code = f.read().replace("\r\n", "\n")

sett_code = sett_code.replace(
    '<span>Tata Kelola Privasi Data Klinis</span>',
    '<span>Tata Kelola Privasi & Kepatuhan UU PDP No. 27/2022</span>'
).replace(
    '<span>Izinkan model AI merujuk riwayat kesehatan pribadi saat menjawab pertanyaan (Hanya sesi aktif)</span>',
    '<span>Informed Consent (Pasal 20): Izinkan agen AI merujuk riwayat medis pribadi untuk kalibrasi diagnosis diferensial</span>'
).replace(
    '<span>Sensor otomatis data pengenal (NIK, nama dokter, nomor resep) sebelum diproses oleh model LLM</span>',
    '<span>Purifikasi PII Otomatis (Pasal 35): Anonimisasi NIK, nama faskes, dan data pengenal sebelum evaluasi model AI</span>'
).replace(
    '<span>Area Tindakan Sensitif (Data Pasien)</span>',
    '<span>Hak Penghapusan Data (Right to Erasure - UU PDP Pasal 8 & 10)</span>'
).replace(
    'Sesuai regulasi privasi kesehatan, Anda berhak menghapus seluruh riwayat percakapan Anda dari server RS RSUKT secara permanen.',
    'Sesuai UU PDP No. 27/2022 Pasal 8 dan ISO/IEC 27001 Annex A.12, subjek data berhak menarik persetujuan dan meminta penghapusan permanen seluruh jejak rekam konsultasi klinis.'
).replace(
    'Hapus Seluruh Riwayat Konsultasi',
    'Hapus Permanen Seluruh Riwayat Anamnesis Klinis'
)

with open(sett_path, "w", encoding="utf-8") as f:
    f.write(sett_code)
print("Patched settings page.")

