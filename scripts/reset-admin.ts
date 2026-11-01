/**
 * Emergency Admin Recovery Script - Web Klinik RSUKT (TypeScript CLI)
 * Usage:
 *   ADMIN_RECOVERY_EMAIL=admin@rsukt.go.id ADMIN_RECOVERY_PASSWORD=secret npx tsx scripts/reset-admin.ts
 */

import { execSync } from "child_process";
import * as path from "path";

const email = process.env.ADMIN_RECOVERY_EMAIL || "admin@rsukt.go.id";
const password = process.env.ADMIN_RECOVERY_PASSWORD;

if (!password) {
  console.error("Error: ADMIN_RECOVERY_PASSWORD environment variable must be set.");
  process.exit(1);
}

const pythonScript = path.resolve(__dirname, "reset_admin.py");

try {
  const result = execSync(`python "${pythonScript}" --email "${email}" --password "${password}"`, {
    env: { ...process.env, ADMIN_RECOVERY_PASSWORD: password },
    encoding: "utf-8",
  });
  console.log(result);
} catch (err: unknown) {
  console.error("Admin recovery failed:", err instanceof Error ? err.message : String(err));
  process.exit(1);
}
