with open("apps/web/src/app/chat/page.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove ScanningDeteksiBahasaCard definition
start_marker = "/**\n * Komponen Scanning Deteksi Bahasa: Bahasa Awam"
end_marker = "/**\n * Komponen pemformatan teks klinis untuk pasien:"

if start_marker in content and end_marker in content:
    idx1 = content.index(start_marker)
    idx2 = content.index(end_marker)
    content = content[:idx1] + content[idx2:]
    print("Removed ScanningDeteksiBahasaCard")
else:
    print("Markers not found for ScanningDeteksiBahasaCard")

# 2. Update loading streaming message
old_stream = "AI Real-Time memproses scanning bahasa & bukti klinis..."
new_stream = "AI sedang merumuskan penjelasan edukasi medis terverifikasi..."
if old_stream in content:
    content = content.replace(old_stream, new_stream)
    print("Updated streaming text")

# 3. Update header
lines = content.splitlines(True)
new_lines = []
skip = False
for i, line in enumerate(lines):
    if "{/* Tampilan Header: Pasien Awam (Hospital Native) vs Admin Workspace */}" in line:
        skip = True
        new_lines.append("""            {/* Mode Selector Pasien: Hanya Thinking Mode dan Fast Mode (Bebas dari jargon ML/DL) */}
            <div className="flex items-center gap-2 flex-wrap">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-cyan-50/70 border border-cyan-200 text-cyan-900 text-xs font-semibold shadow-2xs">
                <Stethoscope className="w-4 h-4 text-cyan-700 shrink-0" />
                <span className="hidden sm:inline">Asisten AI Medis</span>
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  Terpandu
                </span>
              </div>

              <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-xl border border-slate-200">
                <button
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
                </button>
              </div>
            </div>
""")
        continue
    if skip:
        if "{/* Daily Quota Counter Badge (Max 7 / 24 Hours) */}" in line:
            skip = False
            # Also need to make sure the closing </div> of previous wrapper is handled or if we replaced up to the closing tag
            new_lines.append(line)
        continue
    new_lines.append(line)

content = "".join(new_lines)

with open("apps/web/src/app/chat/page.tsx", "w", encoding="utf-8") as f:
    f.write(content)
print("Done writing apps/web/src/app/chat/page.tsx")
