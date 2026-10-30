chat_path = r"services/ai-api/app/routes/chat.py"
with open(chat_path, "r", encoding="utf-8") as f:
    code = f.read().replace("\r\n", "\n")

target1 = """    # Authorization Check: User can only see their own sessions unless admin
    if session.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses ditolak: Anda tidak memiliki wewenang melihat sesi rekam medis pengguna lain."
        )"""

replacement1 = """    # Strict Privacy Separation (UU PDP No. 27/2022 Pasal 4 & Kerahasiaan Rekam Medis):
    # Administrator sistem secara tegas TIDAK MEMILIKI hak akses langsung ke percakapan privat pasien.
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses Ditolak (UU PDP No. 27/2022): Administrator dilarang keras mengakses atau melihat sesi konsultasi pribadi pasien."
        )"""

code = code.replace(target1, replacement1, 1)

target2 = """    if session.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak.")"""

replacement2 = """    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses Ditolak: Anda hanya berhak mengelola sesi rekam medis milik akun Anda sendiri."
        )"""

code = code.replace(target2, replacement2, 1)

with open(chat_path, "w", encoding="utf-8") as f:
    f.write(code)

print("Successfully enforced strict admin access block to user sessions in chat.py.")

