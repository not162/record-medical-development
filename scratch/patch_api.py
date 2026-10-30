import re

# 1. Patch apps/web/src/lib/api.ts
api_path = r"apps/web/src/lib/api.ts"
with open(api_path, "r", encoding="utf-8") as f:
    api_content = f.read()

old_error_block = """  if (!response.ok) {
    let errorDetail = "Terjadi kesalahan pada permintaan server.";
    try {
      const errJson = await response.json();
      errorDetail = formatErrorDetail(errJson?.detail, response.status) || errorDetail;
    } catch {
      errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorDetail);
  }"""

new_error_block = """  if (!response.ok) {
    let errorDetail = "";
    try {
      const errJson = await response.json();
      errorDetail = formatErrorDetail(errJson?.detail, response.status);
    } catch {
      // Non-JSON response
    }

    if (!errorDetail) {
      if (response.status === 404) {
        errorDetail = "Layanan atau endpoint klinis tidak ditemukan (404 Not Found).";
      } else if (response.status === 401) {
        errorDetail = "Kredensial tidak valid atau sesi otentikasi telah berakhir (401 Unauthorized).";
      } else if (response.status === 403) {
        errorDetail = "Akses ditolak: Anda tidak memiliki hak otorisasi yang memadai (403 Forbidden).";
      } else if (response.status >= 500) {
        errorDetail = "Gangguan pada server gateway klinis (500 Internal Error). Silakan coba beberapa saat lagi.";
      } else {
        errorDetail = `HTTP ${response.status}: ${response.statusText || "Permintaan gagal diproses."}`;
      }
    }
    throw new Error(errorDetail);
  }"""

# Normalize line endings to test replace
api_content_norm = api_content.replace("\r\n", "\n")
old_error_norm = old_error_block.replace("\r\n", "\n")
if old_error_norm in api_content_norm:
    api_content_norm = api_content_norm.replace(old_error_norm, new_error_block.replace("\r\n", "\n"))
    with open(api_path, "w", encoding="utf-8") as f:
        f.write(api_content_norm)
    print("Successfully patched apps/web/src/lib/api.ts")
else:
    print("Could not find old_error_block in apps/web/src/lib/api.ts")

