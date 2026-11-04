import Link from "next/link";
import { Stethoscope } from "lucide-react";

/** Logo + nama aplikasi, dipakai di header publik dan halaman auth. */
export function BrandMark({ href = "/", compact = false }: { href?: string; compact?: boolean }) {
  return (
    <Link href={href} className="flex items-center gap-2.5 shrink-0" aria-label="Web Klinik - Beranda">
      <span
        className="inline-flex h-8 w-8 items-center justify-center rounded-[10px] text-white shadow-sm"
        style={{ backgroundImage: "var(--brand-gradient)" }}
      >
        <Stethoscope className="h-4 w-4" />
      </span>
      {!compact && <span className="text-[15px] font-extrabold tracking-tight text-slate-900">Web Klinik</span>}
    </Link>
  );
}
