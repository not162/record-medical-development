import os
from pathlib import Path

# 1. Patch apps/web/src/lib/api.ts
api_file = Path("apps/web/src/lib/api.ts")
with open(api_file, "r", encoding="utf-8") as f:
    api_code = f.read().replace("\r\n", "\n")

old_user_interface = """export interface User {
  id: string;
  username: string;
  email: string;
  role: "USER" | "ADMIN";
  full_name?: string | null;
  is_active: boolean;
  created_at: string;
}"""

new_user_interface = """export type UserRole = "USER" | "ADMIN" | "RESEARCHER";

export interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  full_name?: string | null;
  is_active: boolean;
  created_at: string;
}"""

old_auth_response = """export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  username: string;
  email: string;
  role: "USER" | "ADMIN";
  full_name?: string | null;
}"""

new_auth_response = """export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  username: string;
  email: string;
  role: UserRole;
  full_name?: string | null;
}"""

assert old_user_interface in api_code, "old_user_interface not found"
assert old_auth_response in api_code, "old_auth_response not found"

api_code = api_code.replace(old_user_interface, new_user_interface)
api_code = api_code.replace(old_auth_response, new_auth_response)

with open(api_file, "w", encoding="utf-8") as f:
    f.write(api_code)
print("[OK] Patched apps/web/src/lib/api.ts")

# 2. Patch apps/web/src/lib/auth-context.tsx
auth_ctx_file = Path("apps/web/src/lib/auth-context.tsx")
with open(auth_ctx_file, "r", encoding="utf-8") as f:
    ctx_code = f.read().replace("\r\n", "\n")

old_ctx_type = """interface AuthContextType {
  user: User | null;
  role: "USER" | "ADMIN" | null;"""

new_ctx_type = """import { User, UserRole, api, getToken, setToken, removeToken } from "./api";

interface AuthContextType {
  user: User | null;
  role: UserRole | null;"""

# Check imports in auth-context.tsx
if 'import { User, api, getToken, setToken, removeToken } from "./api";' in ctx_code:
    ctx_code = ctx_code.replace('import { User, api, getToken, setToken, removeToken } from "./api";', 'import { User, UserRole, api, getToken, setToken, removeToken } from "./api";')
    ctx_code = ctx_code.replace('role: "USER" | "ADMIN" | null;', 'role: UserRole | null;')

with open(auth_ctx_file, "w", encoding="utf-8") as f:
    f.write(ctx_code)
print("[OK] Patched apps/web/src/lib/auth-context.tsx")

# 3. Patch apps/web/src/app/login/page.tsx
login_page_file = Path("apps/web/src/app/login/page.tsx")
with open(login_page_file, "r", encoding="utf-8") as f:
    login_code = f.read().replace("\r\n", "\n")

old_login_redirect = """      if (loggedUser.role === "ADMIN") {
        router.push("/admin/dashboard");
      } else {
        router.push("/chat");
      }"""

new_login_redirect = """      if (loggedUser.role === "ADMIN" || loggedUser.role === "RESEARCHER") {
        router.push("/admin/dashboard");
      } else {
        router.push("/chat");
      }"""

if old_login_redirect in login_code:
    login_code = login_code.replace(old_login_redirect, new_login_redirect)
    with open(login_page_file, "w", encoding="utf-8") as f:
        f.write(login_code)
    print("[OK] Patched apps/web/src/app/login/page.tsx")
else:
    print("[INFO] apps/web/src/app/login/page.tsx already updated or pattern not found")

