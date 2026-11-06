/** Usia kalender real-time dari tanggal lahir (sama dengan perhitungan backend `age_on`). */

export const BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

/** Tanggal hari ini menurut kalender perangkat, format YYYY-MM-DD. */
export function todayLocalIso(d: Date = new Date()): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

const parse = (iso: string) => {
  const [y, m, d] = iso.split("-").map(Number);
  return { y, m, d };
};
const daysIn = (y: number, m: number) => new Date(y, m, 0).getDate(); // m: 1..12

export function ageFromIso(birthIso: string, todayIso: string = todayLocalIso()) {
  const b = parse(birthIso);
  const t = parse(todayIso);
  if (!b.y || !t.y || birthIso > todayIso) return null;
  const years = t.y - b.y - (t.m < b.m || (t.m === b.m && t.d < b.d) ? 1 : 0);
  const months = ((t.y - b.y) * 12 + t.m - b.m - (t.d < b.d ? 1 : 0)) % 12;
  let am = t.m - (t.d < b.d ? 1 : 0);
  let ay = t.y;
  if (am < 1) {
    am += 12;
    ay -= 1;
  }
  const anchor = Date.UTC(ay, am - 1, Math.min(b.d, daysIn(ay, am)));
  const days = Math.round((Date.UTC(t.y, t.m - 1, t.d) - anchor) / 86_400_000);
  return { years, months, days };
}
