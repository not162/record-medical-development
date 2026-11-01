import os
from pathlib import Path

training_file = Path("apps/web/src/app/admin/training/page.tsx")
with open(training_file, "r", encoding="utf-8") as f:
    code = f.read().replace("\r\n", "\n")

# 1. Add useAuth import
if 'import { useAuth } from "@/lib/auth-context";' not in code:
    code = code.replace(
        'import { API_BASE_URL, getToken, api, formatErrorDetail } from "@/lib/api";',
        'import { API_BASE_URL, getToken, api, formatErrorDetail } from "@/lib/api";\nimport { useAuth } from "@/lib/auth-context";'
    )

# 2. Add const { role } = useAuth();
old_func_start = """export default function AdminTrainingPage() {
  const [jobs, setJobs] = useState<TrainingJobItem[]>([]);"""

new_func_start = """export default function AdminTrainingPage() {
  const { role } = useAuth();
  const [jobs, setJobs] = useState<TrainingJobItem[]>([]);"""

if old_func_start in code:
    code = code.replace(old_func_start, new_func_start)

# 3. Add Role Banner before tabs
old_before_tab = """      {error && (
        <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 flex items-center gap-2 text-xs text-red-800">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* TAB 1: QUEUE WORKER TABLE */}"""

new_before_tab = """      {error && (
        <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 flex items-center gap-2 text-xs text-red-800">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Role-Aware Guidance Banner */}
      {role === "ADMIN" && (
        <div className="p-4 rounded-xl bg-amber-50/90 border border-amber-200 flex items-start gap-3 text-xs text-amber-900 shadow-xs">
          <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-amber-950">Mode Peninjau (Admin Operasional):</p>
            <p className="text-amber-800 leading-relaxed">
              Halaman pelatihan model machine learning ini dirancang khusus untuk <strong>Admin Periset (Tim Riset Medis & AI Engineering RSUKT)</strong>. Anda dapat melihat antrean job dan menjalankan simulasi pipeline. Untuk melatih model ke produksi, silakan gunakan akun Admin Periset (<code className="font-mono bg-amber-100 text-amber-900 px-1 py-0.5 rounded">periset@rsukt.go.id</code>).
            </p>
          </div>
        </div>
      )}

      {role === "RESEARCHER" && (
        <div className="p-4 rounded-xl bg-sky-50/90 border border-sky-200 flex items-start gap-3 text-xs text-sky-900 shadow-xs">
          <Cpu className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-sky-950">Workspace Aktif: Peneliti Medis AI (Researcher Mode)</p>
            <p className="text-sky-800 leading-relaxed">
              Anda memiliki hak istimewa penuh untuk meluncurkan training job, memproses antrean worker, serta mendaftarkan artefak model ke Model Registry RSUKT.
            </p>
          </div>
        </div>
      )}

      {/* TAB 1: QUEUE WORKER TABLE */}"""

assert old_before_tab in code, "old_before_tab not found in training page"
code = code.replace(old_before_tab, new_before_tab)

with open(training_file, "w", encoding="utf-8") as f:
    f.write(code)

print("[OK] Patched apps/web/src/app/admin/training/page.tsx successfully.")

