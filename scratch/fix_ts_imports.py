# Fix imports in apps/web/src/app/chat/layout.tsx and apps/web/src/app/chat/page.tsx

# 1. layout.tsx
layout_path = r"apps/web/src/app/chat/layout.tsx"
with open(layout_path, "r", encoding="utf-8") as f:
    l_code = f.read().replace("\r\n", "\n")

l_code = l_code.replace(
    "const { user, isAuthenticated, isLoading, logout } = useAuth();",
    "const { user, role, isAuthenticated, isLoading, logout } = useAuth();"
)

with open(layout_path, "w", encoding="utf-8") as f:
    f.write(l_code)
print("Fixed layout.tsx")

# 2. page.tsx
page_path = r"apps/web/src/app/chat/page.tsx"
with open(page_path, "r", encoding="utf-8") as f:
    p_code = f.read().replace("\r\n", "\n")

# Check if useRouter is imported
if 'import { useRouter } from "next/navigation";' not in p_code:
    # Add to imports
    p_code = p_code.replace(
        'import React, { useState, useEffect, useRef, useCallback } from "react";',
        'import React, { useState, useEffect, useRef, useCallback } from "react";\nimport { useRouter } from "next/navigation";'
    )

with open(page_path, "w", encoding="utf-8") as f:
    f.write(p_code)
print("Fixed page.tsx")
