# Role-Based Access Control (RBAC) & Permission Matrix

## 1. Prinsip Utama Otorisasi

1. **Server adalah sumber kebenaran.** Setiap rute FastAPI memakai dependency peran; tampilan hanya menyembunyikan menu.
2. **Tiga peran, tiga ruang.** `USER`, `ADMIN`, `RESEARCHER`; tidak ada peran yang bisa masuk ke ruang peran lain. Admin pun tidak bisa membuka chat pasien.
3. **Hak minimum.** `ADMIN` hanya membaca data operasional; tindakan yang mengubah data/model khusus `RESEARCHER`.
4. **Peran tidak bisa didaftarkan sendiri.** `/auth/register` selalu membuat `USER`; perubahan peran hanya lewat Admin Riset.
5. **Jejak audit.** Penolakan akses dan aksi riset penting tercatat di `audit_logs`.

## 2. Matriks Hak Akses Peran × Fitur (Role Access Control Matrix)

| Rute | Anonim | `USER` | `ADMIN` | `RESEARCHER` |
|---|:---:|:---:|:---:|:---:|
| `/auth/register`, `/auth/login`, pemulihan sandi | ✓ | ✓ | ✓ | ✓ |
| `/chat/*` | kuota tamu | ✓ | 403 | 403 |
| `/profile`, `/auth/me` | 401 | ✓ | ✓ | ✓ |
| `/admin/dashboard`, `audit-logs`, `users`, `feedback`, `audit/reports`, `rag/status`, `GET knowledge`, `graph/schema` | 401 | 403 | ✓ | ✓ |
| `/admin/datasets/*`, `annotations`, `exports/*`, `models/*`, `evaluation/*`, `users/manage`, `PATCH users/{id}` | 401 | 403 | 403 | ✓ |
| `POST/PUT/DELETE /admin/knowledge`, `/admin/graph/nodes|edges|seed|all|subgraph`, `/admin/rag/index|evaluate`, `/admin/jobs/process` | 401 | 403 | 403 | ✓ |
| `/admin/insights/*` | 401 | 403 | 403 | ✓ |

Seluruh baris diuji otomatis di `services/ai-api/tests/test_rbac_matrix.py` (anonim → 401, `USER` → 403, `ADMIN` hanya operasional, `RESEARCHER` semua).

## 3. Daftar Hak Akses Standar (*Permission Scopes*)

| Scope | Arti |
|---|---|
| `chat.use` | Mengirim/membaca pesan sendiri |
| `profile.self` | Membaca/mengubah profil sendiri |
| `admin.read` | Membaca data operasional |
| `research.data` | Dataset, anotasi, ekspor |
| `research.model` | Training, aktivasi model, evaluasi |
| `research.knowledge` | Tulis basis pengetahuan & graf |
| `research.users` | Ubah peran & status akun |
| `insights.*` | Training, laporan, prediksi, ekspor insight pasien |

## 4. Evaluasi Hak Akses pada Kode

**Server (`services/ai-api/app/security/auth.py`):**
```python
def require_admin(current_user = Depends(get_current_user)):       # ADMIN atau RESEARCHER
    if normalize_role(current_user.role) not in ("ADMIN", "RESEARCHER"):
        raise HTTPException(403, "Akses ditolak: Operasi ini membutuhkan hak akses admin.")

def require_researcher(current_user = Depends(get_current_user)):  # RESEARCHER saja
    if normalize_role(current_user.role) != "RESEARCHER":
        raise HTTPException(403, "Akses ditolak: Fitur ini khusus untuk Admin Periset (superadmin).")
```
`normalize_role()` memetakan alias lama `ADMIN_PERISET` → `RESEARCHER`. Rute chat memeriksa `normalize_role(user.role) in ADMIN_ROLES` lalu menolak.

**Tampilan (`apps/web/src/lib/roles.ts`):** `canAccess(role, path)` (`USER` tidak pernah ke `/admin`; `ADMIN` hanya `OPERATIONAL_PATHS`; `RESEARCHER` semua `/admin`), `homePathForRole()`. Layout chat menolak peran admin; layout admin menolak `USER`.

## 5. Kebijakan Keamanan Unggah Berkas & Akses Kamera

- **Unggah dataset:** khusus `RESEARCHER`, divalidasi format, dihitung checksum, masuk sebagai `PENDING` sampai disetujui.
- **Unduh ekspor:** nama berkas divalidasi (daftar putih untuk ekspor insight), sehingga path traversal ditolak (`404`).
- **Kamera & mikrofon:** hanya di `/chat/suara` (peran `USER`), setelah layar persetujuan. Kamera opsional. `Permissions-Policy: camera=(self), microphone=(self)` mencegah iframe asing memakainya. Video/audio diproses di perangkat dan tidak pernah diunggah; *track* media dihentikan saat pasien menekan Berhenti atau meninggalkan halaman.
