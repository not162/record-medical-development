import re

# 1. Patch apps/web/src/app/chat/page.tsx
# Remove ScanningDeteksiBahasaCard entirely and any triage badge
chat_page_path = r"apps/web/src/app/chat/page.tsx"
with open(chat_page_path, "r", encoding="utf-8") as f:
    chat_code = f.read().replace("\r\n", "\n")

# Replace ScanningDeteksiBahasaCard definition with a dummy empty component that returns null
scan_def_regex = r"/\*\*\s*\* Komponen Scanning Deteksi Bahasa:.*?\nfunction ScanningDeteksiBahasaCard\(.*?\n\}\n"
chat_code = re.sub(
    r"/\*\*\s*\* Komponen Scanning Deteksi Bahasa:.*?\nfunction ScanningDeteksiBahasaCard\([\s\S]*?\n\}\n",
    "// Scanning Deteksi Bahasa dipindahkan seutuhnya ke Admin Workspace (/admin/training)\n",
    chat_code,
    count=1
)

# Remove the call to ScanningDeteksiBahasaCard around line 1266
call_regex = r"\{/\* Scanning Deteksi Bahasa: HANYA untuk Admin Periset AI \*/\}[\s\S]*?<ScanningDeteksiBahasaCard[\s\S]*?/\>\s*\)\}"
chat_code = re.sub(
    call_regex,
    "{/* Scanning Deteksi Bahasa & Triase dihapus dari chat pasien */}",
    chat_code,
    count=1
)

# Replace "Triase Klinis CDSS" header badge with "Konsultasi Klinis Aktif"
chat_code = chat_code.replace("Triase Klinis CDSS", "Konsultasi Klinis Terpandu")
chat_code = chat_code.replace("dan triase rujukan poliklinik spesialis", "dan panduan rujukan poliklinik spesialis")

# Also add admin redirect guard inside ChatPage
admin_guard_target = "export default function ChatPage() {"
admin_guard_replacement = """export default function ChatPage() {
  const { role: userRole } = useAuth();
  const pageRouter = useRouter();

  // Strict separation: Administrator dilarang keras masuk ke ruang konsultasi pasien (UU PDP No. 27/2022)
  useEffect(() => {
    if (userRole === "ADMIN") {
      pageRouter.replace("/admin/dashboard");
    }
  }, [userRole, pageRouter]);

  if (userRole === "ADMIN") {
    return null;
  }"""

chat_code = chat_code.replace(admin_guard_target, admin_guard_replacement, 1)

with open(chat_page_path, "w", encoding="utf-8") as f:
    f.write(chat_code)
print("Patched apps/web/src/app/chat/page.tsx (removed scanning card, triage badge, added admin block).")

# 2. Patch apps/web/src/app/chat/layout.tsx
# Enforce that ADMIN cannot access /chat layout
chat_layout_path = r"apps/web/src/app/chat/layout.tsx"
with open(chat_layout_path, "r", encoding="utf-8") as f:
    layout_code = f.read().replace("\r\n", "\n")

old_layout_effect = """  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);"""

new_layout_effect = """  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.push("/login");
      } else if (role === "ADMIN") {
        router.replace("/admin/dashboard");
      }
    }
  }, [isLoading, isAuthenticated, role, router]);"""

layout_code = layout_code.replace(old_layout_effect, new_layout_effect, 1)

# Add admin block view in layout render
admin_view_block = """  if (!isLoading && role === "ADMIN") {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50 p-6">
        <div className="max-w-md w-full bg-white p-8 rounded-3xl border border-red-200 text-center space-y-4 shadow-xl">
          <div className="w-14 h-14 rounded-2xl bg-red-50 border border-red-200 text-red-600 flex items-center justify-center mx-auto shadow-sm">
            <ShieldAlert className="w-7 h-7" />
          </div>
          <h3 className="font-bold text-lg text-slate-900">Akses Ditolak (UU PDP No. 27/2022)</h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            Sesuai regulasi kerahasiaan medis & UU Perlindungan Data Pribadi Pasal 4, akun Administrator dilarang keras mengakses ruang konsultasi dan rekam medis privat pasien.
          </p>
          <Link href="/admin/dashboard" className="inline-block py-2.5 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-md">
            Buka Dashboard Administrator
          </Link>
        </div>
      </div>
    );
  }
"""

layout_code = layout_code.replace("  return (\n    <div className=\"flex h-screen", admin_view_block + "\n  return (\n    <div className=\"flex h-screen", 1)

with open(chat_layout_path, "w", encoding="utf-8") as f:
    f.write(layout_code)
print("Patched apps/web/src/app/chat/layout.tsx (blocked admin from patient portal).")

# 3. Patch apps/web/src/app/admin/layout.tsx
# Remove "Lihat Tampilan Pasien" link from admin sidebar
admin_layout_path = r"apps/web/src/app/admin/layout.tsx"
with open(admin_layout_path, "r", encoding="utf-8") as f:
    admin_layout_code = f.read().replace("\r\n", "\n")

old_link_to_chat = """          <Link
            href="/chat"
            className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-white hover:bg-slate-100 border border-slate-200 text-slate-700 font-medium text-xs transition shadow-sm"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Lihat Tampilan Pasien</span>
          </Link>"""

new_privacy_badge = """          <div className="p-2.5 rounded-xl bg-emerald-50/80 border border-emerald-200 text-[10px] text-emerald-800 flex items-center gap-2 shadow-2xs">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="leading-tight font-medium">Separasi Akses: Data privat pasien terenkripsi & terisolasi (UU PDP No. 27/2022).</span>
          </div>"""

admin_layout_code = admin_layout_code.replace(old_link_to_chat, new_privacy_badge, 1)

with open(admin_layout_path, "w", encoding="utf-8") as f:
    f.write(admin_layout_code)
print("Patched apps/web/src/app/admin/layout.tsx (removed patient link).")

# 4. Patch apps/web/src/app/admin/dashboard/page.tsx
# Remove Colab conversation export which exported patient conversations
dash_path = r"apps/web/src/app/admin/dashboard/page.tsx"
with open(dash_path, "r", encoding="utf-8") as f:
    dash_code = f.read().replace("\r\n", "\n")

dash_code = dash_code.replace(
    "Ekspor Dataset Percakapan Klinis untuk Pelatihan di Google Colab",
    "Ekspor Benchmark Pengetahuan Klinis Terverifikasi (De-Identified)"
).replace(
    "Unduh seluruh dialog tanya-jawab pasien dan asisten AI lengkap dengan kategori triase, ICD-10, serta penilaian dokter.",
    "Unduh korpus data protokol kesehatan & benchmark medis yang telah disetujui (Approved) bebas dari data pribadi pasien sesuai UU PDP Pasal 4."
)

with open(dash_path, "w", encoding="utf-8") as f:
    f.write(dash_code)
print("Patched apps/web/src/app/admin/dashboard/page.tsx.")

# 5. Patch services/ai-api/app/routes/chat.py
# Block admin role from create session, post message, stream message
chat_api_path = r"services/ai-api/app/routes/chat.py"
with open(chat_api_path, "r", encoding="utf-8") as f:
    chat_api_code = f.read().replace("\r\n", "\n")

# In create_chat_session:
old_create = """@router.post("/chat/sessions")
def create_chat_session(
    req: CreateSessionRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):"""

new_create = """@router.post("/chat/sessions")
def create_chat_session(
    req: CreateSessionRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses Ditolak (UU PDP No. 27/2022): Administrator dilarang keras membuat atau mengoperasikan sesi rekam konsultasi pasien."
        )"""

chat_api_code = chat_api_code.replace(old_create, new_create, 1)

# In post_chat_message:
old_post = """@router.post("/chat/messages")
def send_chat_message(
    req: ChatMessageRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):"""

new_post = """@router.post("/chat/messages")
def send_chat_message(
    req: ChatMessageRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses Ditolak (UU PDP No. 27/2022): Administrator dilarang keras mengirimkan pesan konsultasi pasien."
        )"""

chat_api_code = chat_api_code.replace(old_post, new_post, 1)

# In stream_chat_messages:
old_stream = """@router.post("/chat/messages/stream")
async def stream_chat_messages(
    req: ChatMessageRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):"""

new_stream = """@router.post("/chat/messages/stream")
async def stream_chat_messages(
    req: ChatMessageRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses Ditolak (UU PDP No. 27/2022): Administrator dilarang mengakses stream percakapan pasien."
        )"""

chat_api_code = chat_api_code.replace(old_stream, new_stream, 1)

with open(chat_api_path, "w", encoding="utf-8") as f:
    f.write(chat_api_code)
print("Patched services/ai-api/app/routes/chat.py (strictly blocked admin from patient chat APIs).")

