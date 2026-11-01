with open(r"apps/web/src/app/login/page.tsx", "r", encoding="utf-8") as f:
    login_src = f.read()

# 1. Update handleSubmit to trim username_or_email
login_src = login_src.replace(
    "username_or_email: usernameOrEmail,",
    "username_or_email: usernameOrEmail.trim(),"
)

# 2. Update input field
login_src = login_src.replace(
    'placeholder="No. Rekam Medis / nama_pasien / email@rsukt.go.id"',
    'placeholder="No. Rekam Medis / nama_pasien / email@rsukt.go.id"\n                autoCapitalize="none"\n                autoCorrect="off"\n                spellCheck="false"'
)

with open(r"apps/web/src/app/login/page.tsx", "w", encoding="utf-8") as f:
    f.write(login_src)
print("apps/web/src/app/login/page.tsx patched successfully!")

with open(r"apps/web/src/app/register/page.tsx", "r", encoding="utf-8") as f:
    reg_src = f.read()

# 1. Update handleSubmit to trim and lowercase
reg_src = reg_src.replace(
    "username,\n        email,\n        password,\n        full_name: fullName || undefined,",
    "username: username.trim(),\n        email: email.trim().toLowerCase(),\n        password,\n        full_name: fullName ? fullName.trim() : undefined,"
)

# 2. Update username and email inputs with autoCapitalize="none" autoCorrect="off" spellCheck="false"
reg_src = reg_src.replace(
    'placeholder="cth. ahmad_dahlan (min. 3 karakter)"',
    'placeholder="cth. ahmad_dahlan (min. 3 karakter)"\n                autoCapitalize="none"\n                autoCorrect="off"\n                spellCheck="false"'
)
reg_src = reg_src.replace(
    'placeholder="pasien@rsukt.go.id"',
    'placeholder="pasien@rsukt.go.id"\n                autoCapitalize="none"\n                autoCorrect="off"\n                spellCheck="false"'
)

with open(r"apps/web/src/app/register/page.tsx", "w", encoding="utf-8") as f:
    f.write(reg_src)
print("apps/web/src/app/register/page.tsx patched successfully!")
