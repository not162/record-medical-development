chat_path = r"apps/web/src/app/chat/page.tsx"
with open(chat_path, "r", encoding="utf-8") as f:
    code = f.read().replace("\r\n", "\n")

# 1. Update ScanningDeteksiBahasaCard to return null when !isAdmin
old_card_check = """  if (!isAdmin) {
    // Tampilan native untuk pasien klinis:
    // Tidak mengekspos token teknis (<2med_id>), latency ms, atau struktur machine learning
    return (
      <div className="mt-2.5 pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-600">
        <div className="flex items-center gap-1.5">
          <Stethoscope className="w-3.5 h-3.5 text-cyan-700 shrink-0" />
          <span>Rujukan Layanan: <strong className="text-slate-800">{res.departemen_rekomendasi || defaultDept || "Poliklinik Terpadu"}</strong></span>
        </div>
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${getUrgencyBadge()}`}>
          Triase: {urgency}
        </span>
      </div>
    );
  }"""

new_card_check = """  if (!isAdmin) {
    // Sesuai aturan: Dashboard scanning bahasa dan badge triase TIDAK DITAMPILKAN pada role user/pasien
    // Seluruh visualisasi scanning & triase hanya aktif pada role Admin / Periset AI
    return null;
  }"""

if old_card_check in code:
    code = code.replace(old_card_check, new_card_check, 1)
    print("Patched ScanningDeteksiBahasaCard !isAdmin")
else:
    print("Could not find old_card_check")

# 2. Add CleanClinicalMarkdown and renderFormattedInline helper
clean_renderer_code = """
/**
 * Komponen pemformatan teks klinis untuk pasien:
 * Menghilangkan simbol teknis (*, '', ##, ###) dan merender judul, list, dan penekanan secara bersih.
 */
function CleanClinicalMarkdown({ content, isAdmin = false }: { content: string; isAdmin?: boolean }) {
  if (!content) return null;

  const lines = content.split("\\n");

  return (
    <div className="space-y-2 text-xs sm:text-sm text-slate-800 leading-relaxed">
      {lines.map((line, idx) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={idx} className="h-1.5" />;
        }

        // 1. Heading check (###, ##, #)
        if (trimmed.startsWith("#")) {
          const cleanHeading = trimmed.replace(/^#+\\s*/, "").replace(/[*'"]/g, "").trim();
          return (
            <h4 key={idx} className="font-bold text-slate-900 text-xs sm:text-sm pt-2 pb-0.5 border-b border-slate-100 flex items-center gap-1.5 text-cyan-950">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-600 shrink-0"></span>
              <span>{cleanHeading}</span>
            </h4>
          );
        }

        // 2. List item check (*, -, •)
        if (trimmed.startsWith("* ") || trimmed.startsWith("- ") || trimmed.startsWith("• ")) {
          const innerText = trimmed.replace(/^(\\*|-|•)\\s+/, "");
          return (
            <div key={idx} className="flex items-start gap-2 pl-1.5 my-1 text-slate-700">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-600 mt-1.5 shrink-0"></span>
              <span className="flex-1">{renderFormattedInline(innerText)}</span>
            </div>
          );
        }

        // 3. Regular paragraph
        return (
          <p key={idx} className="text-slate-700">
            {renderFormattedInline(trimmed)}
          </p>
        );
      })}
    </div>
  );
}

function renderFormattedInline(text: string): React.ReactNode {
  const parts = text.split(/(\\*\\*[^*]+\\*\\*|__[^_]+__)/g);

  return parts.map((part, i) => {
    if ((part.startsWith("**") && part.endsWith("**")) || (part.startsWith("__") && part.endsWith("__"))) {
      const cleanBold = part.slice(2, -2).replace(/[*'"]/g, "").trim();
      return <strong key={i} className="font-semibold text-slate-900">{cleanBold}</strong>;
    }
    const cleanText = part
      .replace(/[*#]/g, "")
      .replace(/''/g, '"')
      .replace(/\\s{2,}/g, " ");
    return cleanText;
  });
}
"""

# Place CleanClinicalMarkdown before export default function ChatPage()
chat_page_marker = "export default function ChatPage() {"
if chat_page_marker in code:
    code = code.replace(chat_page_marker, clean_renderer_code + "\n" + chat_page_marker, 1)
    print("Added CleanClinicalMarkdown component")

# 3. Replace <p className="whitespace-pre-line text-xs sm:text-sm">{msg.content}</p>
old_p = '<p className="whitespace-pre-line text-xs sm:text-sm">{msg.content}</p>'
new_p = '<CleanClinicalMarkdown content={msg.content} isAdmin={isEffectiveAdmin} />'

if old_p in code:
    code = code.replace(old_p, new_p, 1)
    print("Replaced raw <p> with <CleanClinicalMarkdown>")
else:
    print("Could not find old_p")

# 4. Hide scanning card when !isEffectiveAdmin
old_scan_call = """                  {/* Scanning Deteksi Bahasa: Awam ➔ Medis Klinis Card (hanya jika ada hasil deteksi asli) */}
                  {msg.sender === "assistant" && Boolean(msg.scanningDeteksiBahasa?.scanning_result) && (
                    <ScanningDeteksiBahasaCard
                      scan={msg.scanningDeteksiBahasa}
                      defaultDept={msg.department}
                      isAdmin={isEffectiveAdmin}
                    />
                  )}"""

new_scan_call = """                  {/* Scanning Deteksi Bahasa: HANYA untuk Admin Periset AI */}
                  {isEffectiveAdmin && msg.sender === "assistant" && Boolean(msg.scanningDeteksiBahasa?.scanning_result) && (
                    <ScanningDeteksiBahasaCard
                      scan={msg.scanningDeteksiBahasa}
                      defaultDept={msg.department}
                      isAdmin={isEffectiveAdmin}
                    />
                  )}"""

if old_scan_call in code:
    code = code.replace(old_scan_call, new_scan_call, 1)
    print("Enforced isEffectiveAdmin on scanning card call")

# 5. Simplify Thinking / Fast mode buttons to remove "17 ML & 8 DL", "5 ML & 2 DL"
old_buttons_block = """                  <button
                    type="button"
                    onClick={() => {
                      setReasoningMode("thinking");
                      setModelSize("70b");
                    }}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold flex items-center gap-1.5 transition ${
                      reasoningMode === "thinking"
                        ? "bg-white text-indigo-700 shadow-2xs border border-indigo-200"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                    title="Llama 3.3 70B Gold Standard: 17 Algoritma ML & 8 Deep Learning"
                  >
                    <Brain className="w-3.5 h-3.5 text-indigo-600" />
                    <span>Thinking Mode</span>
                    <span className="hidden sm:inline px-1 py-0.2 rounded bg-indigo-50 text-indigo-700 text-[9px] font-mono">
                      17 ML & 8 DL
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setReasoningMode("fast");
                      setModelSize("8b");
                    }}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold flex items-center gap-1.5 transition ${
                      reasoningMode === "fast"
                        ? "bg-white text-amber-700 shadow-2xs border border-amber-200"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                    title="Llama 3.1 8B Fast: 5 Algoritma ML & 2 Deep Learning"
                  >
                    <Zap className="w-3.5 h-3.5 text-amber-600" />
                    <span>Fast Mode</span>
                    <span className="hidden sm:inline px-1 py-0.2 rounded bg-amber-50 text-amber-700 text-[9px] font-mono">
                      5 ML & 2 DL
                    </span>
                  </button>"""

new_buttons_block = """                  <button
                    type="button"
                    onClick={() => {
                      setReasoningMode("thinking");
                      setModelSize("70b");
                    }}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold flex items-center gap-1.5 transition ${
                      reasoningMode === "thinking"
                        ? "bg-white text-indigo-700 shadow-2xs border border-indigo-200"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                    title="Thinking Mode"
                  >
                    <Brain className="w-3.5 h-3.5 text-indigo-600" />
                    <span>Thinking Mode</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setReasoningMode("fast");
                      setModelSize("8b");
                    }}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold flex items-center gap-1.5 transition ${
                      reasoningMode === "fast"
                        ? "bg-white text-amber-700 shadow-2xs border border-amber-200"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                    title="Fast Mode"
                  >
                    <Zap className="w-3.5 h-3.5 text-amber-600" />
                    <span>Fast Mode</span>
                  </button>"""

if old_buttons_block in code:
    code = code.replace(old_buttons_block, new_buttons_block, 1)
    print("Simplified Thinking / Fast buttons header")

# 6. Simplify bottom input select dropdown to remove "17 ML & 8 DL", "5 ML & 2 DL"
old_select_block = """              {isEffectiveAdmin ? (
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <span className="text-[11px] hidden sm:inline">Mode Penalaran:</span>
                  <select
                    value={reasoningMode}
                    onChange={(e) => {
                      const m = e.target.value as "thinking" | "fast";
                      setReasoningMode(m);
                      setModelSize(m === "thinking" ? "70b" : "8b");
                    }}
                    className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 text-[11px] text-slate-700 focus:outline-none focus:border-cyan-500 font-medium"
                  >
                    <option value="thinking">Thinking Mode (Llama Gold Standard: 17 ML & 8 DL)</option>
                    <option value="fast">Fast Mode (Llama Fast: 5 ML & 2 DL)</option>
                  </select>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 text-xs text-slate-500">
                  <span className="text-[11px] text-slate-500 font-medium">Format Telaah:</span>
                  <select
                    value={reasoningMode}
                    onChange={(e) => {
                      const m = e.target.value as "thinking" | "fast";
                      setReasoningMode(m);
                      setModelSize(m === "thinking" ? "70b" : "8b");
                    }}
                    className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 text-[11px] text-slate-700 focus:outline-none focus:border-cyan-500 font-medium"
                  >
                    <option value="thinking">Penjelasan Komprehensif (Protokol Lengkap)</option>
                    <option value="fast">Penjelasan Terfokus (Tindakan Cepat)</option>
                  </select>
                </div>
              )}"""

new_select_block = """              <div className="flex items-center gap-1.5 text-xs text-slate-500">
                <span className="text-[11px] text-slate-500 font-medium">Mode:</span>
                <select
                  value={reasoningMode}
                  onChange={(e) => {
                    const m = e.target.value as "thinking" | "fast";
                    setReasoningMode(m);
                    setModelSize(m === "thinking" ? "70b" : "8b");
                  }}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 text-[11px] text-slate-700 focus:outline-none focus:border-cyan-500 font-semibold"
                >
                  <option value="thinking">Thinking Mode</option>
                  <option value="fast">Fast Mode</option>
                </select>
              </div>"""

if old_select_block in code:
    code = code.replace(old_select_block, new_select_block, 1)
    print("Simplified input dropdown to clean Thinking / Fast Mode")

with open(chat_path, "w", encoding="utf-8") as f:
    f.write(code)

print("Finished updating apps/web/src/app/chat/page.tsx.")

