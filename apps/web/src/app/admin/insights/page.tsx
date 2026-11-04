"use client";

import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Sparkles, Play, Loader2, AlertCircle, Download, Brain, Scale, Repeat, Tags, HeartPulse, Search,
} from "lucide-react";
import {
  api,
  type InsightsReport,
  type InsightsTextPrediction,
  type InsightsCardioPrediction,
  type InsightsTrainConfig,
} from "@/lib/api";
import { useLiveQuery, broadcastChange, LiveIndicator } from "@/lib/realtime";

const REPORT_KEY = ["admin", "insights", "report"] as const;

function isReport(r: unknown): r is InsightsReport {
  return !!r && typeof r === "object" && "version" in (r as Record<string, unknown>);
}

const pct = (v: number | null | undefined) => (v == null ? "-" : `${(v * 100).toFixed(1)}%`);

function Card({ title, icon: Icon, children, className = "" }: {
  title: string; icon: React.ComponentType<{ className?: string }>; children: React.ReactNode; className?: string;
}) {
  return (
    <section className={`bg-white border border-slate-200 rounded-2xl p-5 shadow-sm ${className}`}>
      <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2 mb-3">
        <Icon className="w-4 h-4 text-blue-600" />
        {title}
      </h2>
      {children}
    </section>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
      <div className="text-[11px] text-slate-500">{label}</div>
      <div className="text-2xl font-bold text-slate-900 mt-1">{value}</div>
      {hint && <div className="text-[10px] text-slate-500 mt-1">{hint}</div>}
    </div>
  );
}

function WeightBars({ before, after }: { before: Record<string, number>; after: Record<string, number> }) {
  const keys = Object.keys({ ...before, ...after });
  const max = Math.max(1, ...keys.map((k) => Math.max(before[k] ?? 0, after[k] ?? 0)));
  return (
    <div className="space-y-2">
      {keys.map((k) => (
        <div key={k} className="text-[11px]">
          <div className="flex justify-between text-slate-600">
            <span className="truncate">{k}</span>
            <span className="tabular-nums">{(before[k] ?? 0).toFixed(1)}% → <b className="text-slate-900">{(after[k] ?? 0).toFixed(1)}%</b></span>
          </div>
          <div className="relative h-2 mt-1 rounded-full bg-slate-100">
            <div className="absolute inset-y-0 left-0 rounded-full bg-slate-300" style={{ width: `${((before[k] ?? 0) / max) * 100}%` }} />
            <div className="absolute inset-y-0 left-0 rounded-full bg-blue-600/80 h-1 top-0.5" style={{ width: `${((after[k] ?? 0) / max) * 100}%` }} />
          </div>
        </div>
      ))}
      <p className="text-[10px] text-slate-500">Abu-abu = sebelum debias, biru = sesudah reweighing.</p>
    </div>
  );
}

export default function InsightsPage() {
  const reportQ = useLiveQuery(REPORT_KEY, () => api.admin.insights.report(), { intervalMs: 15000 });
  const report = isReport(reportQ.data) ? reportQ.data : null;

  const [cfg, setCfg] = useState<InsightsTrainConfig>({ rounds: 4, rlhf_random_rate: 0.2, rlhf_beta: 0.5, cardio_rows: 15000 });
  const train = useMutation({
    mutationFn: () => api.admin.insights.train(cfg),
    onSuccess: () => {
      reportQ.refetch();
      broadcastChange(REPORT_KEY);
    },
  });

  const [query, setQuery] = useState("Sudah 3 hari demam 39 derajat, batuk berdahak dan sesak saat malam");
  const predText = useMutation({ mutationFn: (t: string) => api.admin.insights.predictText(t) });
  const [cardio, setCardio] = useState<Record<string, string | number>>({
    age: 58, hypertension: 1, diabetes: 0, blood_pressure_systolic: 150, cholesterol_level: 240,
    smoking_status: "Current", previous_heart_disease: 0, physical_activity: "Low",
  });
  const predCardio = useMutation({ mutationFn: () => api.admin.insights.predictCardio(cardio) });
  const exportQ = useMutation({ mutationFn: () => api.admin.insights.exportColab() });

  const download = async (f: string) => {
    const blob = await api.admin.insights.downloadColabFile(f);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = f;
    a.click();
    URL.revokeObjectURL(url);
  };

  const err = (train.error || predText.error || predCardio.error || exportQ.error || reportQ.error) as Error | null;
  const tp: InsightsTextPrediction | undefined = predText.data;
  const cp: InsightsCardioPrediction | undefined = predCardio.data;

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-blue-600" />
            Insight Pasien & RLHF
          </h1>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            Pola, prediksi (angka + alasan), pelabelan, dan debias yang dipelajari dari respons pasien dan dataset yang ada.
            Isi percakapan pasien tidak pernah ditampilkan; yang terlihat hanya ringkasan. Metode graf tidak diubah.
          </p>
          <LiveIndicator className="mt-2" updatedAt={reportQ.dataUpdatedAt} isFetching={reportQ.isFetching} isError={reportQ.isError} />
        </div>
      </div>

      {err && (
        <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" /> {err.message}
        </div>
      )}

      {/* Pengaturan training */}
      <Card title="Latih ulang pipeline" icon={Play}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          {([
            ["rounds", "Putaran self-improvement", 0, 8, 1],
            ["rlhf_random_rate", "Peluang reward acak ±", 0, 0.5, 0.05],
            ["rlhf_beta", "Kekuatan RLHF (β)", 0, 2, 0.1],
            ["cardio_rows", "Sampel data jantung", 0, 60000, 1000],
          ] as const).map(([k, label, min, max, step]) => (
            <label key={k} className="space-y-1">
              <span className="font-medium text-slate-700">{label}</span>
              <input
                type="number" min={min} max={max} step={step} value={cfg[k]}
                onChange={(e) => setCfg({ ...cfg, [k]: Number(e.target.value) })}
                className="w-full p-2 rounded-lg border border-slate-200 bg-white"
              />
            </label>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-3 mt-4">
          <button
            onClick={() => train.mutate()}
            disabled={train.isPending}
            className="btn-primary inline-flex items-center gap-2 px-4 py-2 text-xs font-bold"
          >
            {train.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {train.isPending ? "Melatih... (±10–40 detik)" : "Jalankan training"}
          </button>
          <button
            onClick={() => exportQ.mutate()}
            disabled={exportQ.isPending}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-200 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            <Download className="w-4 h-4" />
            Siapkan ekspor Colab/GPU
          </button>
          {exportQ.data?.files.map((f) => (
            <button key={f} onClick={() => download(f)} className="text-[11px] text-blue-600 hover:underline">
              {f}
            </button>
          ))}
        </div>
        <p className="text-[10px] text-slate-500 mt-2">
          Ekspor Colab hanya berisi dataset yang sudah disetujui. Teks chat pasien tetap di server dan tidak ikut diunduh.
        </p>
      </Card>

      {!report ? (
        <div className="p-6 text-center text-sm text-slate-500 bg-white border border-slate-200 rounded-2xl">
          {reportQ.isLoading ? "Memuat laporan..." : "Belum ada model. Jalankan training untuk membuat laporan pertama."}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            <Stat label="Macro-F1 (test)" value={pct(report.test.macro_f1)} hint={`${report.test.n} contoh uji`} />
            <Stat label="Akurasi label (test)" value={pct(report.test.accuracy)} />
            <Stat label="Kalibrasi (ECE)" value={report.test.ece.toFixed(3)} hint={`suhu T=${report.calibration.temperature}`} />
            <Stat label="AUC risiko jantung" value={report.cardio.after_debias?.auc?.toFixed(3) ?? "-"} hint={`${report.cardio.n_rows_sampled ?? 0} baris`} />
            <Stat label="Versi model" value={report.version.slice(4, 12)} hint={`${report.duration_s}s training`} />
          </div>

          <div className="grid lg:grid-cols-2 gap-4">
            <Card title="Data & split" icon={Brain}>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
                {(["corpus", "unlabelled", "labelled", "train", "val", "test", "with_patient_feedback"] as const).map((k) => (
                  <React.Fragment key={k}>
                    <dt className="text-slate-500">{k.replace(/_/g, " ")}</dt>
                    <dd className="text-slate-900 font-semibold tabular-nums">{String(report.data[k] ?? 0)}</dd>
                  </React.Fragment>
                ))}
                <dt className="text-slate-500">pre-train (dimensi laten)</dt>
                <dd className="text-slate-900 font-semibold">
                  {report.pretrain.latent_dim} · var {pct(report.pretrain.explained_variance)}
                </dd>
              </dl>
            </Card>

            <Card title="Loop self-improvement (RLHF ± & hard-example mining)" icon={Repeat}>
              <div className="overflow-x-auto">
                <table className="w-full text-[11px]">
                  <thead className="text-slate-500 text-left">
                    <tr><th className="pb-1">#</th><th>C</th><th>Val F1</th><th>RLHF +/− (manusia · acak)</th><th>Status</th></tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {report.self_improvement.map((h) => (
                      <tr key={h.round}>
                        <td className="py-1.5">{h.round}</td>
                        <td>{h.C}</td>
                        <td className="tabular-nums">{pct(h.val.macro_f1)}</td>
                        <td className="tabular-nums">
                          {h.rlhf ? `${h.rlhf.human_pos}/${h.rlhf.human_neg} · ${h.rlhf.random_pos}/${h.rlhf.random_neg}` : "-"}
                        </td>
                        <td>
                          <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${h.accepted ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                            {h.accepted ? "diterima" : "ditolak"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-[10px] text-slate-500 mt-2">
                Pembaruan hanya diterima bila skor validasi naik. Data uji tidak dipakai sampai evaluasi akhir.
              </p>
            </Card>

            <Card title="Bobot label: sebelum vs sesudah debias" icon={Scale}>
              <WeightBars before={report.debias_text.label_weight_pct_before} after={report.debias_text.label_weight_pct_after} />
            </Card>

            <Card title="Fairness risiko jantung (atribut sensitif tidak dipakai sebagai fitur)" icon={HeartPulse}>
              {report.cardio.before_debias && report.cardio.after_debias ? (
                <table className="w-full text-[11px]">
                  <thead className="text-slate-500 text-left">
                    <tr><th className="pb-1">Atribut</th><th>Gap paritas (sebelum → sesudah)</th><th>Gap peluang setara</th></tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {Object.keys(report.cardio.after_debias.fairness).map((a) => {
                      const b = report.cardio.before_debias!.fairness[a];
                      const f = report.cardio.after_debias!.fairness[a];
                      return (
                        <tr key={a}>
                          <td className="py-1.5 font-medium text-slate-800">{a}</td>
                          <td className="tabular-nums">{pct(b.demographic_parity_gap)} → <b>{pct(f.demographic_parity_gap)}</b></td>
                          <td className="tabular-nums">{pct(b.equal_opportunity_gap)} → <b>{pct(f.equal_opportunity_gap)}</b></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              ) : (
                <p className="text-xs text-slate-500">{report.cardio.status ?? "Tidak tersedia."}</p>
              )}
            </Card>
          </div>

          <Card title="Pola keluhan (klaster tanpa label)" icon={Tags}>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {report.patterns.map((p) => (
                <div key={p.id} className="p-3 rounded-xl border border-slate-200 bg-slate-50">
                  <div className="text-[11px] text-slate-500">Pola #{p.id} · {p.size} teks</div>
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {p.top_terms.map((t) => (
                      <span key={t} className="px-1.5 py-0.5 rounded-md bg-white border border-slate-200 text-[11px] text-slate-700">{t}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}

      <div className="grid lg:grid-cols-2 gap-4">
        <Card title="Uji prediksi & label dari teks keluhan" icon={Search}>
          <form onSubmit={(e) => { e.preventDefault(); predText.mutate(query); }} className="space-y-2">
            <textarea value={query} onChange={(e) => setQuery(e.target.value)} rows={3}
              className="w-full p-2.5 rounded-xl border border-slate-200 bg-white text-xs" />
            <button disabled={predText.isPending} className="btn-primary px-4 py-2 text-xs font-bold">
              {predText.isPending ? "Memproses..." : "Prediksi"}
            </button>
          </form>
          {tp && (
            <div className="mt-3 space-y-2 text-xs">
              <div><b className="text-slate-900">{tp.label}</b> · keyakinan {pct(tp.confidence)}</div>
              <div className="text-slate-600">Alternatif: {tp.top_k.slice(1).map((k) => `${k.label} (${pct(k.probability)})`).join(", ")}</div>
              <div className="text-slate-600">Alasan: {tp.reasoning.map((r) => r.term).join(", ") || "-"}</div>
              <div className="text-slate-600">Pola #{tp.pattern.id}: {tp.pattern.top_terms.join(", ")}</div>
              <div className="flex flex-wrap gap-1">
                {Object.entries(tp.variables).filter(([, v]) => v).map(([k, v]) => (
                  <span key={k} className="px-1.5 py-0.5 rounded-md bg-slate-100 text-[10px] text-slate-700">{k}: {v}</span>
                ))}
              </div>
            </div>
          )}
        </Card>

        <Card title="Uji prediksi numerik risiko jantung" icon={HeartPulse}>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {Object.entries(cardio).map(([k, v]) => (
              <label key={k} className="space-y-0.5">
                <span className="text-slate-500">{k}</span>
                {typeof v === "number" ? (
                  <input type="number" value={v} onChange={(e) => setCardio({ ...cardio, [k]: Number(e.target.value) })}
                    className="w-full p-1.5 rounded-lg border border-slate-200 bg-white" />
                ) : (
                  <select value={v} onChange={(e) => setCardio({ ...cardio, [k]: e.target.value })}
                    className="w-full p-1.5 rounded-lg border border-slate-200 bg-white">
                    {(k === "smoking_status" ? ["Never", "Past", "Current"] : ["Low", "Moderate", "High"]).map((o) => (
                      <option key={o}>{o}</option>
                    ))}
                  </select>
                )}
              </label>
            ))}
          </div>
          <button onClick={() => predCardio.mutate()} disabled={predCardio.isPending} className="btn-primary px-4 py-2 text-xs font-bold mt-3">
            {predCardio.isPending ? "Menghitung..." : "Hitung risiko"}
          </button>
          {cp && (
            <div className="mt-3 text-xs space-y-1">
              <div>Risiko <b className="text-slate-900">{pct(cp.risk_probability)}</b> ({cp.risk_label}, ambang {pct(cp.threshold)})</div>
              <ul className="list-disc pl-4 text-slate-600">
                {cp.reasoning.map((r) => <li key={r.raw}>{r.feature} {r.direction} risiko ({r.weight})</li>)}
              </ul>
              <p className="text-[10px] text-slate-500">{cp.disclaimer}</p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
