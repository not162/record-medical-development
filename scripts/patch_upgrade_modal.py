path = r"apps/web/src/app/chat/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Replace separate modelSize state with derived const
text = text.replace(
    'const [modelSize, setModelSize] = useState("70b");\n  const [reasoningMode, setReasoningMode] = useState<"thinking" | "fast">("thinking");',
    'const [reasoningMode, setReasoningMode] = useState<"thinking" | "fast">("thinking");\n  const modelSize = reasoningMode === "thinking" ? "70b" : "8b";'
)
text = text.replace('setModelSize("70b");\n', '')
text = text.replace('setModelSize("8b");\n', '')
text = text.replace('setModelSize(m === "thinking" ? "70b" : "8b");\n', '')

# 2. Add Upgrade Button in header banner next to Consent button
upgrade_btn = """            {currentTier.tier === "GUEST" && messages.length > 1 && (
              <button
                type="button"
                onClick={() => setShowUpgradeModal(true)}
                className="px-2.5 py-1 rounded-xl bg-cyan-600 hover:bg-cyan-700 text-white text-[11px] font-semibold flex items-center gap-1 transition shadow-2xs"
                title="Simpan percakapan ke akun terdaftar"
              >
                <span>Simpan ke Akun</span>
              </button>
            )}"""

text = text.replace(
    '<button\n              type="button"\n              onClick={() => setShowConsentModal(true)}',
    upgrade_btn + '\n\n            <button\n              type="button"\n              onClick={() => setShowConsentModal(true)}'
)

# 3. Add Upgrade Modal near bottom of ChatPage
upgrade_modal_code = """      {/* 2.2 Upgrade Session Modal */}
      {showUpgradeModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl">
            <h3 className="text-sm font-bold text-slate-900">Simpan Riwayat Konsultasi ke Akun</h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              {user
                ? "Apakah Anda ingin menyimpan seluruh riwayat percakapan sesi tamu ini ke akun rekam medis terdaftar Anda?"
                : "Untuk menyimpan dan mensinkronkan riwayat percakapan ini ke semua perangkat, silakan masuk atau daftar akun pasien RSUKT."}
            </p>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowUpgradeModal(false)}
                className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg transition"
              >
                Batal
              </button>
              {user ? (
                <button
                  type="button"
                  disabled={isUpgrading}
                  onClick={async () => {
                    setIsUpgrading(true);
                    try {
                      const token = localStorage.getItem("clinical_token");
                      const res = await fetch(`${API_BASE_URL}/chat/sessions/upgrade`, {
                        method: "POST",
                        headers: {
                          "Content-Type": "application/json",
                          Authorization: `Bearer ${token}`
                        },
                        body: JSON.stringify({
                          guest_session_id: currentSessionId || "guest",
                          messages: messages.map(m => ({ sender: m.sender, content: m.content }))
                        })
                      });
                      if (res.ok) {
                        const data = await res.json();
                        alert(data.message);
                        setShowUpgradeModal(false);
                        fetchSessions();
                      }
                    } catch {
                      alert("Gagal menyimpan riwayat.");
                    } finally {
                      setIsUpgrading(false);
                    }
                  }}
                  className="px-3.5 py-1.5 text-xs bg-cyan-600 hover:bg-cyan-700 text-white font-semibold rounded-lg transition"
                >
                  {isUpgrading ? "Menyimpan..." : "Ya, Simpan ke Akun"}
                </button>
              ) : (
                <a
                  href="/login"
                  className="px-3.5 py-1.5 text-xs bg-cyan-600 hover:bg-cyan-700 text-white font-semibold rounded-lg transition inline-block"
                >
                  Masuk / Daftar
                </a>
              )}
            </div>
          </div>
        </div>
      )}
"""

if "{/* 2.2 Upgrade Session Modal */}" not in text:
    text = text.replace(
        '{/* Citation Metadata Modal */}',
        upgrade_modal_code + '\n      {/* Citation Metadata Modal */}'
    )

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("apps/web/src/app/chat/page.tsx upgraded cleanly with upgrade modal!")
