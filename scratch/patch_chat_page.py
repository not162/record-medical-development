from pathlib import Path

file_path = Path(r"c:\Users\user\RAG-model-record\apps\web\src\app\chat\page.tsx")
content = file_path.read_text(encoding="utf-8")

# 1. Update New Session button label
content = content.replace("<span>Konsultasi Baru</span>", "<span>Anamnesis Klinis Baru</span>")

# 2. Update Header for patient
old_patient_header = """            {!isEffectiveAdmin ? (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-cyan-50/70 border border-cyan-200 text-cyan-900 text-xs font-semibold shadow-2xs">
                <Stethoscope className="w-4 h-4 text-cyan-700 shrink-0" />
                <span>Web Klinik RSUKT</span>
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  AI Real-Time
                </span>
              </div>"""

new_patient_header = """            {!isEffectiveAdmin ? (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-cyan-50/70 border border-cyan-200 text-cyan-900 text-xs font-semibold shadow-2xs">
                <Stethoscope className="w-4 h-4 text-cyan-700 shrink-0" />
                <span>Asisten AI Medis RSUKT</span>
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  Triase Klinis CDSS
                </span>
                <span className="hidden md:inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-cyan-100/70 text-cyan-800 text-[9px] font-mono">
                  🔒 UU PDP & ISO 27001
                </span>
              </div>"""

content = content.replace(old_patient_header.replace("\n", "\r\n"), new_patient_header.replace("\n", "\r\n"))
content = content.replace(old_patient_header, new_patient_header)

# 3. Add Empty State Quick Anamnesis Chips before messages.map
old_msg_area = """        {/* Messages List Area */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-1 mb-3">
          {messages.map((msg) => ("""

new_msg_area = """        {/* Messages List Area */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-1 mb-3">
          {messages.length === 0 && (
            <div className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6 text-center space-y-4 max-w-xl mx-auto my-auto animate-in fade-in duration-200">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-cyan-600 to-emerald-600 flex items-center justify-center text-white shadow-lg shadow-cyan-600/20">
                <Stethoscope className="w-7 h-7" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base sm:text-lg font-bold text-slate-900">
                  Asisten Kecerdasan Artifisial Medis Klinis RSUKT
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed max-w-md">
                  Pemeriksaan anamnesis terstruktur, penapisan tanda bahaya (*Red Flags*), dan triase rujukan poliklinik spesialis berbasis bukti protokol medis terverifikasi.
                </p>
              </div>

              {/* Quick Clinical Anamnesis Chips */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full pt-2 text-left">
                {[
                  {
                    title: "Anamnesis Kardiovaskular",
                    desc: "Nyeri dada retrosternal, penjalaran lengan kiri, diaphoresis",
                    prompt: "Saya merasakan nyeri dada substernal yang menjalar ke leher dan lengan kiri disertai keringat dingin sejak 30 menit yang lalu.",
                    icon: Activity,
                    color: "border-red-200 bg-red-50/70 text-red-950 hover:bg-red-100/80",
                  },
                  {
                    title: "Skrining Obstruksi Respirasi",
                    desc: "Sesak napas akut, mengi ekspiratoir, riwayat asma",
                    prompt: "Pasien mengeluhkan sesak napas akut berbunyi mengi ekspiratoir dan riwayat asma bronkial.",
                    icon: Stethoscope,
                    color: "border-cyan-200 bg-cyan-50/70 text-cyan-950 hover:bg-cyan-100/80",
                  },
                  {
                    title: "Evaluasi Nyeri Epigastrium",
                    desc: "Rasa terbakar retrosternal, dispepsia, dan begah",
                    prompt: "Keluhan nyeri ulu hati rasa terbakar yang diperberat makanan asam disertai mual dan begah.",
                    icon: FileText,
                    color: "border-amber-200 bg-amber-50/70 text-amber-950 hover:bg-amber-100/80",
                  },
                  {
                    title: "Verifikasi Kontraindikasi Obat",
                    desc: "Kontraindikasi Beta-blocker dan interaksi farmakologis",
                    prompt: "Apakah terdapat kontraindikasi pemberian Beta-blocker non-selektif pada pasien dengan riwayat asma bronkial?",
                    icon: ShieldCheck,
                    color: "border-emerald-200 bg-emerald-50/70 text-emerald-950 hover:bg-emerald-100/80",
                  },
                ].map((item, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setInputQuery(item.prompt)}
                    className={`p-3 rounded-2xl border transition-all text-xs flex flex-col gap-1 shadow-2xs ${item.color}`}
                  >
                    <span className="font-bold flex items-center gap-1.5 text-xs">
                      <item.icon className="w-3.5 h-3.5 shrink-0" />
                      {item.title}
                    </span>
                    <span className="text-[10px] opacity-80 line-clamp-2">{item.desc}</span>
                  </button>
                ))}
              </div>

              {/* Regulatory Trust Badge */}
              <div className="flex items-center justify-center gap-2 pt-2 text-[10px] text-slate-400">
                <Lock className="w-3 h-3 text-emerald-600" />
                <span>Kerahasiaan Medis Terenkripsi: UU No. 27/2022 (UU PDP) & ISO/IEC 27001:2022 ISMS</span>
              </div>
            </div>
          )}
          {messages.map((msg) => ("""

content = content.replace(old_msg_area.replace("\n", "\r\n"), new_msg_area.replace("\n", "\r\n"))
content = content.replace(old_msg_area, new_msg_area)

# 4. Update Placeholder and Send Button
old_placeholder = 'placeholder={\n                quotaStatus?.is_clinic_health_lock\n                  ? "Batas 7 keluaran AI tercapai. Sesi dialihkan ke Clinic Health Reset (24 Jam Penuh). Silakan hubungi IGD 119 atau kunjungi Poliklinik Fisik RSUKT..."\n                  : "Jelaskan keluhan Anda dalam bahasa awam (misal: \'Dada sakit dan sesak saat rebahan\')..."\n              }'
new_placeholder = 'placeholder={\n                quotaStatus?.is_clinic_health_lock\n                  ? "Batas 7 keluaran AI tercapai. Sesi dialihkan ke Clinic Health Reset (24 Jam Penuh). Silakan hubungi IGD 119 atau kunjungi Poliklinik Fisik RSUKT..."\n                  : "Sampaikan anamnesis keluhan utama & gejala klinis Anda (misal: \'Nyeri dada retrosternal onset 30 menit menjalar ke lengan kiri disertai dispnea dan diaphoresis\')..."\n              }'

content = content.replace(old_placeholder.replace("\n", "\r\n"), new_placeholder.replace("\n", "\r\n"))
content = content.replace(old_placeholder, new_placeholder)

old_send_btn = """              <button
                type="submit"
                disabled={!inputQuery.trim() || isGenerating || Boolean(quotaStatus?.is_clinic_health_lock)}
                className="py-2 px-4 rounded-xl bg-cyan-600 hover:bg-cyan-700 disabled:opacity-40 text-white font-semibold text-xs shadow-xs transition flex items-center gap-1.5 ml-auto"
              >
                {quotaStatus?.is_clinic_health_lock ? (
                  <>
                    <Lock className="w-3.5 h-3.5" />
                    <span>Terkunci</span>
                  </>
                ) : (
                  <>
                    <span>Kirim</span>
                    <Send className="w-3.5 h-3.5" />
                  </>
                )}
              </button>"""

new_send_btn = """              <button
                type="submit"
                disabled={!inputQuery.trim() || isGenerating || Boolean(quotaStatus?.is_clinic_health_lock)}
                className="py-2.5 px-4 rounded-xl bg-gradient-to-r from-cyan-600 to-emerald-600 hover:from-cyan-700 hover:to-emerald-700 disabled:opacity-40 text-white font-semibold text-xs shadow-xs transition flex items-center gap-1.5 ml-auto"
              >
                {quotaStatus?.is_clinic_health_lock ? (
                  <>
                    <Lock className="w-3.5 h-3.5" />
                    <span>Terkunci (24 Jam)</span>
                  </>
                ) : (
                  <>
                    <span className="hidden sm:inline">Konsultasikan Keluhan Klinis</span>
                    <span className="sm:hidden">Konsultasi</span>
                    <Send className="w-3.5 h-3.5" />
                  </>
                )}
              </button>"""

content = content.replace(old_send_btn.replace("\n", "\r\n"), new_send_btn.replace("\n", "\r\n"))
content = content.replace(old_send_btn, new_send_btn)

# 5. Update Patient Reasoning Selector label
content = content.replace(
    '<span className="text-[11px] text-slate-500">Tipe Jawaban:</span>',
    '<span className="text-[11px] text-slate-500 font-medium">Format Telaah:</span>'
)
content = content.replace(
    '<option value="thinking">Penjelasan Lengkap (Komprehensif)</option>',
    '<option value="thinking">Penjelasan Komprehensif (Protokol Lengkap)</option>'
)
content = content.replace(
    '<option value="fast">Penjelasan Ringkas (Praktis)</option>',
    '<option value="fast">Penjelasan Terfokus (Tindakan Cepat)</option>'
)

file_path.write_text(content, encoding="utf-8")
print("[OK] apps/web/src/app/chat/page.tsx updated with medical patient UI")

