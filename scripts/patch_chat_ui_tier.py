path = r"apps/web/src/app/chat/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add maxLength to textarea
text = text.replace(
    'rows={2}\n              disabled={Boolean(quotaStatus?.is_clinic_health_lock)}',
    'rows={2}\n              maxLength={currentTier.maxChars}\n              disabled={Boolean(quotaStatus?.is_clinic_health_lock)}'
)

# 2. Add Character Counter and Guest Selector Mode
old_mode_block = """                <span className="text-[11px] text-slate-500 font-medium">Mode:</span>
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
                </select>"""

new_mode_block = """                <span className="text-[11px] text-slate-500 font-medium">Mode:</span>
                <select
                  value={currentTier.tier === "GUEST" ? "fast" : reasoningMode}
                  disabled={currentTier.tier === "GUEST"}
                  onChange={(e) => {
                    const m = e.target.value as "thinking" | "fast";
                    setReasoningMode(m);
                    setModelSize(m === "thinking" ? "70b" : "8b");
                  }}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 text-[11px] text-slate-700 focus:outline-none focus:border-cyan-500 font-semibold disabled:opacity-80"
                >
                  {currentTier.tier === "AUTHENTICATED" && (
                    <option value="thinking">Thinking Mode</option>
                  )}
                  <option value="fast">Fast Mode</option>
                </select>
                {currentTier.tier === "GUEST" ? (
                  <span className="text-[10px] text-slate-400 hidden sm:inline">(Masuk akun untuk Thinking Mode)</span>
                ) : null}
                <span className="text-[10px] text-slate-400 ml-1">
                  {inputQuery.length}/{currentTier.maxChars}
                </span>"""

text = text.replace(old_mode_block, new_mode_block)

# 3. Add Guest Consent Banner right above the form
banner_code = """      {/* 2.2 Guest Consent Banner (UU No. 27/2022) */}
      {currentTier.tier === "GUEST" && !guestConsentDismissed && (
        <div className="mb-2 p-2.5 rounded-xl bg-cyan-50/90 border border-cyan-200 flex items-center justify-between text-xs text-cyan-900 shadow-xs">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-cyan-600 shrink-0" />
            <span className="text-[11px]">
              <strong>Mode Tamu (Anonim):</strong> Dengan melanjutkan konsultasi, Anda menyetujui pemrosesan data anamnesis secara anonim sesuai UU No. 27/2022 (UU PDP).
            </span>
          </div>
          <button
            type="button"
            onClick={() => setGuestConsentDismissed(true)}
            className="text-cyan-700 hover:text-cyan-900 text-[11px] font-semibold px-2 py-0.5 rounded hover:bg-cyan-100/70 ml-2 shrink-0 transition"
          >
            Saya Setuju
          </button>
        </div>
      )}
"""

if "{/* 2.2 Guest Consent Banner" not in text:
    text = text.replace(
        '<form onSubmit={handleSendMessage} className="relative mt-auto">',
        banner_code + '        <form onSubmit={handleSendMessage} className="relative mt-auto">'
    )

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("UI Tier elements and consent banner added!")
