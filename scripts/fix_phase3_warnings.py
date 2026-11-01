# 1. Fix privacy/page.tsx
p_path = r"apps/web/src/app/privacy/page.tsx"
with open(p_path, "r", encoding="utf-8") as f:
    p_text = f.read()
p_text = p_text.replace(
    'import { ShieldCheck, ArrowLeft, Lock, FileText, CheckCircle2 } from "lucide-react";',
    'import { ShieldCheck, ArrowLeft } from "lucide-react";'
)
with open(p_path, "w", encoding="utf-8") as f:
    f.write(p_text)

# 2. Fix terms/page.tsx
t_path = r"apps/web/src/app/terms/page.tsx"
with open(t_path, "r", encoding="utf-8") as f:
    t_text = f.read()
t_text = t_text.replace(
    'import { AlertTriangle, ArrowLeft, ShieldAlert, CheckCircle2, HeartPulse } from "lucide-react";',
    'import { AlertTriangle, ArrowLeft, ShieldAlert } from "lucide-react";'
)
with open(t_path, "w", encoding="utf-8") as f:
    f.write(t_text)

# 3. Fix BrandLoader.tsx
b_path = r"apps/web/src/components/BrandLoader.tsx"
with open(b_path, "r", encoding="utf-8") as f:
    b_text = f.read()

# Replace setVisible(true); with requestAnimationFrame to satisfy React 19 linter
b_text = b_text.replace(
    'setVisible(true);',
    'const rId = requestAnimationFrame(() => setVisible(true));'
)
b_text = b_text.replace(
    'return () => {\n      clearInterval(intervalId);\n    };',
    'return () => {\n      cancelAnimationFrame(rId);\n      clearInterval(intervalId);\n    };'
)
with open(b_path, "w", encoding="utf-8") as f:
    f.write(b_text)

print("Warnings in privacy, terms, and BrandLoader resolved!")
