"""Bangun dataset SFT (format chat) dari data nyata di repo. Deterministik (seed tetap), tanpa jaringan, tanpa DB.

Keluaran di datasets/sft/: sft_{fast,thinking}_{train,val,test}.jsonl, sft_fast.jsonl, sft_thinking.jsonl,
DATASET_CARD.md. Setiap fakta berasal dari satu baris sumber (id sumber disimpan di meta).
Jalankan scripts/graph_kb_export.py lebih dulu (menghasilkan datasets/processed/graph_knowledge.jsonl).
"""
import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DS = ROOT / "datasets"
OUT = DS / "sft"
SEED = 20261103
GRAPH = DS / "processed" / "graph_knowledge.jsonl"

SYSTEM_FAST = ("Kamu adalah asisten informasi kesehatan untuk pasien rumah sakit. Jawab singkat, langsung, dan memakai bahasa "
               "Indonesia sehari-hari. Sebutkan poli yang sesuai dan apakah ada tanda bahaya (ya/tidak). Kamu bukan pengganti dokter. "
               "Untuk keadaan darurat, minta pasien segera ke IGD atau menelepon 119.")
SYSTEM_THINKING = ("Kamu adalah asisten informasi kesehatan untuk pasien rumah sakit. Jawab dengan bahasa Indonesia sehari-hari, "
                   "jelaskan alasanmu langkah demi langkah, dan sebutkan sumber pedoman rumah sakit serta fakta dari graf pengetahuan "
                   "yang dipakai. Jangan menambah fakta di luar sumber. Kamu bukan pengganti dokter. Untuk keadaan darurat, minta pasien "
                   "segera ke IGD atau menelepon 119.")

EMERGENCY = "Segera ke IGD terdekat atau hubungi 119."

# Ringkasan bahasa sehari-hari dari tiap potongan pedoman (hanya memuat isi chunk yang bersangkutan).
KB_PLAIN = {
    "KB-CARD-001_c1": {
        "poli": "Kardiologi",
        "plain": "Nyeri dada yang menjalar ke lengan kiri, leher, atau rahang lebih dari 20 menit bisa menjadi tanda serangan jantung. Rekam jantung (EKG) perlu dilakukan dalam 10 menit pertama, lalu pasien dirujuk ke pusat penanganan jantung.",
        "topic": "nyeri dada dan serangan jantung (sindrom koroner akut)"},
    "KB-PULM-002_c1": {
        "poli": "Pulmonologi",
        "plain": "Sesak napas berbunyi mengi biasanya tanda saluran napas menyempit seperti pada asma. Penanganan awalnya memakai obat hirup pelega napas. Obat golongan penyekat beta seperti propranolol tidak boleh diberikan karena bisa memicu sesak yang berat.",
        "topic": "asma dan sesak napas berbunyi mengi"},
    "KB-ENDO-003_c1": {
        "poli": "Endokrinologi",
        "plain": "Pasien diabetes dengan gula darah sewaktu di atas 400 mg/dL, tubuh kekurangan cairan, mual muntah, atau napas cepat dan dalam perlu diberi cairan infus dan diperiksa keton. Insulin diberikan setelah cairan awal dan kadar kalium diperbaiki.",
        "topic": "gula darah sangat tinggi pada penderita diabetes"},
    "KB-GASTRO-004_c1": {
        "poli": "Gastroenterologi",
        "plain": "Perih di ulu hati yang makin parah karena makanan pedas atau asam disertai mual biasanya mengarah ke maag atau radang lambung. Obat awalnya penetral asam atau penurun asam lambung. Namun nyeri ulu hati yang tidak membaik pada usia di atas 40 tahun perlu rekam jantung (EKG) untuk memastikan bukan serangan jantung.",
        "topic": "nyeri ulu hati dan maag"},
    "KB-TRAUMA-005_c1": {
        "poli": "Trauma/Bedah",
        "plain": "Luka robek yang berdarah aktif harus langsung ditekan dan dibalut tekan. Luka dibersihkan dengan cairan NaCl, lalu dicek kebutuhan suntik tetanus.",
        "topic": "luka robek dan perdarahan"},
    "KB-PSIK-006_c1": {
        "poli": "Psikiatri",
        "plain": "Serangan panik ditandai jantung berdebar, napas cepat, gemetar, dan rasa takut mati, tanpa kelainan jantung yang nyata. Penanganan awal: napas terkontrol dan ditenangkan dengan kata-kata. Pasien lalu dirujuk ke psikiater.",
        "topic": "serangan panik dan cemas berlebihan"},
}
DEPT_TO_CHUNK = {v["poli"]: k for k, v in KB_PLAIN.items()}

REL_ID = {"HAS_SYMPTOM": "punya gejala", "CONTRAINDICATES": "tidak boleh diberi", "RECOMMENDS": "dianjurkan",
          "GOVERNED_BY": "diatur oleh pedoman", "REQUIRES_PROCEDURE": "perlu tindakan"}

RED_FLAG_RE = re.compile(
    r"pingsan|perdarahan|pendarahan|berdarah|muntah darah|darah segar|nyeri dada|menjalar|sesak napas (akut|berat)|"
    r"saturasi|melampaui limit|membusuk|ketegangan dinding perut|180/110|iskemia|keringat dingin|menancap|tidak bisa digerakkan|"
    r"menguning|bunyi jantung|buang air besar hitam|nyeri hebat|nyeri tekan sangat hebat|infiltrat|darah", re.I)
EMERGENCY_DISEASES = {"DIS:STEMI", "DIS:Preeklamsia"}  # pedoman: rujuk segera / kebidanan gawat darurat

PII_PATTERNS = {
    "nik": re.compile(r"\b\d{16}\b"),
    "nik_label": re.compile(r"\bNIK\b", re.I),
    "phone": re.compile(r"(?<!\d)(\+62|62|0)8\d{8,11}\b"),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "titled_name": re.compile(r"\b(Tn|Ny|Nn|Sdr|Bpk|Bapak|Ibu)\.?\s+[A-Z][a-z]+"),
    "placeholder": re.compile(r"\[sensitif", re.I),
}


def pii_hits(text):
    return [k for k, p in PII_PATTERNS.items() if p.search(text)]


def read_jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf8").splitlines() if l.strip()]


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


def tokens(s):
    return {w for w in re.findall(r"[a-z]+", s.lower()) if len(w) > 4}


def sentence(s):
    s = s.strip()
    return s if s.endswith((".", "!", "?")) else s + "."


class Builder:
    def __init__(self):
        self.groups = []
        self.excluded = Counter()
        self.exclude_notes = []
        self.matched_approved = 0

    def load(self):
        self.kb = json.loads((DS / "raw/kb_chunks.json").read_text(encoding="utf8"))
        self.kb_by_id = {c["chunk_id"]: c for c in self.kb}
        for c in self.kb:
            assert c["chunk_id"] in KB_PLAIN, c["chunk_id"]
        recs = read_jsonl(GRAPH)
        self.nodes = {r["id"]: r for r in recs if r["kind"] == "node"}
        self.edges = [r for r in recs if r["kind"] == "edge"]
        self.cases = list(csv.DictReader((DS / "raw/df_clinical_combined.csv").open(encoding="utf8", newline="")))
        self.audit = list(csv.DictReader((DS / "raw/audited_clinical_predictions.csv").open(encoding="utf8", newline="")))
        self.approved = read_jsonl(DS / "approved/clinical_knowledge_approved.jsonl")

    def node_label(self, nid):
        return self.nodes[nid]["label"]

    @staticmethod
    def edge_id(e):
        return f"{e['source']}|{e['relation']}|{e['target']}"

    def dept_graph_facts(self, dept, text):
        """Fakta graf untuk poli tertentu yang bersinggungan dengan teks keluhan (kata kunci sama)."""
        tk = tokens(text)
        facts, used = [], []
        for d in [n for n in self.nodes.values() if n["type"] == "DISEASE" and n.get("department") == dept]:
            rel = [e for e in self.edges if e["source"] == d["id"]]
            related_ids = {d["id"]} | {e["target"] for e in rel}
            label_tokens = set()
            for i in related_ids:
                label_tokens |= tokens(self.node_label(i))
            if not (tk & label_tokens):
                continue
            for e in rel:
                if e["relation"] == "GOVERNED_BY":
                    continue
                facts.append(f"{d['label']} {REL_ID[e['relation']]} {e['target_label']} (catatan graf: {e['reason'].strip()})")
                used.append(self.edge_id(e))
        return facts, used

    # 1. kasus triase
    def build_cases(self):
        approved_triage = {norm(r["content_text"]) for r in self.approved if r["dataset_id"] == "DS-TRIAGE-COMBINED"}
        for i, r in enumerate(self.cases):
            text = r["text"].strip()
            sid = f"df_clinical_combined#{i}"
            if pii_hits(text):
                self.excluded["df_clinical_combined: berisi PII (NIK/nama)"] += 1
                self.exclude_notes.append(f"{sid} dibuang karena memuat NIK dan nama pasien.")
                continue
            if norm(r["text_clean"]) in approved_triage:
                self.matched_approved += 1
            dept = r["label"]
            chunk_id = DEPT_TO_CHUNK[dept]
            kb = KB_PLAIN[chunk_id]
            flag = bool(RED_FLAG_RE.search(text))
            prompt = f"Keluhan saya: {sentence(text)} Sebaiknya ke poli mana dan apa yang harus saya lakukan?"
            flag_fast = (f"Tanda bahaya: ya. {EMERGENCY}" if flag else
                         "Tanda bahaya: tidak terlihat dari keluhan ini. Tetap periksakan ke dokter, dan segera ke IGD atau telepon 119 bila keluhan memburuk.")
            fast = f"Keluhan ini paling sesuai dengan poli {dept}. {flag_fast} Ini bukan diagnosis, dokter yang akan memastikan."
            facts, used = self.dept_graph_facts(dept, text)
            graph_line = (("Fakta dari graf pengetahuan: " + "; ".join(facts) + ".") if facts else
                          "Fakta dari graf pengetahuan: tidak ada hubungan graf yang cocok langsung dengan keluhan ini, jadi jawaban hanya memakai pedoman.")
            thinking = (
                "Alasan langkah demi langkah:\n"
                f"1. Keluhan yang Anda sampaikan: \"{text}\"\n"
                f"2. Keluhan dicocokkan dengan pedoman [{chunk_id}] untuk poli {dept}. Isi pedoman dalam bahasa sehari-hari: {kb['plain']}\n"
                f"3. {graph_line}\n"
                "4. Tanda bahaya: " + (f"ya, ada kata kunci yang termasuk tanda bahaya pada keluhan ini. {EMERGENCY}" if flag else
                                       "tidak terlihat dari keluhan ini. Segera ke IGD atau telepon 119 bila keluhan memburuk.") + "\n"
                f"Kesimpulan: poli yang sesuai adalah {dept}. Ini bukan diagnosis, dokter yang akan memastikan."
            )
            self.groups.append(dict(gid=sid, prompt=prompt, fast=fast, thinking=thinking, department=dept,
                                    risk="tinggi" if flag else "rendah", source="df_clinical_combined",
                                    source_ids=[sid, chunk_id], graph_ids=used, audience="patient", task="triage"))

    # 2. potongan pedoman
    def build_kb(self):
        for cid, kb in KB_PLAIN.items():
            chunk = self.kb_by_id[cid]
            assert chunk["department"] == kb["poli"]
            dept = kb["poli"]
            flag = dept in ("Kardiologi", "Trauma/Bedah", "Endokrinologi")
            prompt = f"Apa penanganan awal untuk {kb['topic']} menurut pedoman rumah sakit?"
            red = ("ya, jika gejala berat. " + EMERGENCY) if flag else "tidak otomatis, tetapi segera ke IGD atau telepon 119 bila memburuk."
            fast = f"{kb['plain']} Poli yang sesuai: {dept}. Tanda bahaya: {red}"
            title, _, body = chunk["text"].partition(":")
            thinking = (f"Alasan langkah demi langkah:\n1. Topik yang ditanyakan: {kb['topic']}.\n"
                        f"2. Pedoman yang dipakai: [{cid}] \"{title.strip()}\". Isi pokoknya: {body.strip()}\n"
                        f"3. Dalam bahasa sehari-hari: {kb['plain']}\n"
                        f"4. Tanda bahaya: {red}\n"
                        f"Kesimpulan: poli yang sesuai adalah {dept}. Keputusan terapi ada di tangan dokter.")
            self.groups.append(dict(gid=f"kb#{cid}", prompt=prompt, fast=fast, thinking=thinking, department=dept,
                                    risk="tinggi" if flag else "sedang", source="kb_chunks", source_ids=[cid], graph_ids=[],
                                    audience="patient", task="guideline_qa"))

    # 3. graf
    def build_graph(self):
        kb_ids = set(self.kb_by_id)
        gov = {e["source"]: e for e in self.edges if e["relation"] == "GOVERNED_BY"}

        def dept_of(nid):
            return self.nodes[nid].get("department") or "Umum"

        def guideline_line(nid):
            e = gov.get(nid)
            if not e:
                return "", []
            doc = e["target"].split(":", 1)[1]
            note = f"Pedoman terkait: {e['target_label']} [{doc}]"
            if not any(k.startswith(doc) for k in kb_ids):
                note += " (isi pedoman ini belum ada di data KB repo, hanya tercatat di graf)"
            return note + ".", [self.edge_id(e)]

        for e in self.edges:
            did, rel = e["source"], e["relation"]
            if rel == "GOVERNED_BY":
                continue
            src, tgt = e["source_label"], e["target_label"]
            gl, gids = guideline_line(did) if self.nodes[did]["type"] == "DISEASE" else ("", [])
            eid = self.edge_id(e)
            dept = dept_of(did)
            if rel == "HAS_SYMPTOM":
                flag = did in EMERGENCY_DISEASES or bool(RED_FLAG_RE.search(tgt + " " + e["reason"]))
                red = f"ya. {EMERGENCY}" if flag else "tidak otomatis, segera ke IGD atau telepon 119 bila memburuk."
                prompt = f"Saya mengalami {tgt.lower()}. Kira-kira ini berkaitan dengan penyakit apa dan ke poli mana saya harus pergi?"
                fast = f"Keluhan ini dikaitkan dengan {src}, poli {dept}. Tanda bahaya: {red} Ini bukan diagnosis, dokter yang akan memastikan."
                thinking = (f"Alasan langkah demi langkah:\n1. Keluhan: {tgt}.\n"
                            f"2. Graf pengetahuan: {tgt} adalah gejala dari {src} (catatan graf: {e['reason']}).\n"
                            f"3. {src} ada di bidang poli {dept}. {gl}\n"
                            f"4. Tanda bahaya: {red}\n"
                            f"Kesimpulan: poli {dept}. Ini bukan diagnosis, dokter yang akan memastikan.")
                task = "symptom_to_disease"
            elif rel == "CONTRAINDICATES":
                flag = True
                prompt = f"Saya punya riwayat {src.lower()}. Bolehkah saya minum {tgt}?"
                fast = (f"Tidak boleh tanpa izin dokter. Menurut graf pengetahuan, {tgt} tidak boleh diberikan pada {src}: {e['reason']}. "
                        f"Poli yang sesuai: {dept}. Tanda bahaya: ya, bila sudah terlanjur diminum dan muncul keluhan, segera ke IGD atau hubungi 119.")
                thinking = (f"Alasan langkah demi langkah:\n1. Pertanyaan: apakah {tgt} aman untuk pasien dengan {src}.\n"
                            f"2. Graf pengetahuan mencatat hubungan CONTRAINDICATES (tidak boleh diberi): {src} -> {tgt}. Catatan graf: {e['reason']}.\n"
                            f"3. {gl}\n4. Tanda bahaya: ya, bila obat ini sudah terlanjur diminum dan muncul keluhan berat. {EMERGENCY}\n"
                            f"Kesimpulan: jangan minum obat ini tanpa bertanya ke dokter di poli {dept}.")
                task = "contraindication"
            elif rel == "RECOMMENDS":
                flag = did in EMERGENCY_DISEASES
                red = f"ya. {EMERGENCY}" if flag else "tidak otomatis, segera ke IGD atau telepon 119 bila memburuk."
                prompt = f"Menurut pedoman rumah sakit, apa yang dianjurkan untuk {src.lower()}?"
                contra = [x for x in self.edges if x["source"] == did and x["relation"] == "CONTRAINDICATES"]
                contra_txt = (" Yang tidak boleh diberikan: " + "; ".join(f"{x['target_label']} ({x['reason']})" for x in contra) + ".") if contra else ""
                gids = gids + [self.edge_id(x) for x in contra]
                fast = (f"Yang dianjurkan untuk {src}: {tgt} ({e['reason']}). Obat atau tindakan hanya diberikan oleh dokter. "
                        f"Poli: {dept}. Tanda bahaya: {red}")
                thinking = (f"Alasan langkah demi langkah:\n1. Pertanyaan: anjuran untuk {src}.\n"
                            f"2. Graf pengetahuan: {src} dianjurkan diberi {tgt} (catatan graf: {e['reason']}).{contra_txt}\n"
                            f"3. {gl}\n4. Tanda bahaya: {red}\n"
                            f"Kesimpulan: ini informasi dari pedoman, bukan resep. Keputusan obat ada di tangan dokter poli {dept}.")
                task = "recommendation"
            elif rel == "REQUIRES_PROCEDURE":
                flag = True
                prompt = f"Saya punya {src.lower()}. Apa tindakan yang diperlukan?"
                fast = f"Perlu tindakan {tgt}: {e['reason']}. Poli: {dept}. Tanda bahaya: ya, luka yang membusuk bisa berbahaya. {EMERGENCY}"
                thinking = (f"Alasan langkah demi langkah:\n1. Keluhan: {src}.\n"
                            f"2. Graf pengetahuan: {src} memerlukan tindakan {tgt} (catatan graf: {e['reason']}).\n"
                            f"3. Tanda bahaya: ya. {EMERGENCY}\nKesimpulan: periksakan ke poli {dept} untuk tindakan oleh dokter.")
                task = "procedure"
            else:
                continue
            self.groups.append(dict(gid=f"graph#{eid}", prompt=prompt, fast=fast, thinking=thinking, department=dept,
                                    risk="tinggi" if flag else "sedang", source="graph_knowledge", source_ids=[eid],
                                    graph_ids=[eid] + gids, audience="patient", task=task))

    # 4. audit catatan klinis (untuk admin riset)
    def build_audit(self):
        approved_by_id = {}
        for r in self.approved:
            m = re.match(r"RME-EXP-(RME-\d+)-", r["document_id"])
            if m:
                approved_by_id[m.group(1)] = r
        drug_nodes = [n for n in self.nodes.values() if n["type"] == "DRUG"]
        for r in self.audit:
            text, err = r["text"].strip(), r["reasoning_error"] == "1"
            corr = r["correction"].strip()
            ids = [r["id"] + "@audited_clinical_predictions"]
            if r["id"] in approved_by_id:
                ids.append(approved_by_id[r["id"]]["document_id"])
            gfacts, gids = [], []
            for d in drug_nodes:
                key = d["label"].split()[0].lower()
                if key in text.lower() or key in corr.lower():
                    for e in self.edges:
                        if e["target"] == d["id"] and e["relation"] in ("CONTRAINDICATES", "RECOMMENDS"):
                            gfacts.append(f"{e['source_label']} {REL_ID[e['relation']]} {e['target_label']} (catatan graf: {e['reason']})")
                            gids.append(self.edge_id(e))
            prompt = f"Tolong periksa apakah penalaran klinis pada catatan ini sudah tepat: {text}"
            if err:
                fast = f"Ada kesalahan penalaran ({r['error_type']}). Koreksi: {sentence(corr)} Tanda bahaya: ya, berisiko untuk pasien. Hasil ini perlu ditinjau dokter."
                verdict = f"Ada kesalahan penalaran jenis {r['error_type']}. Koreksi dari data audit: {sentence(corr)}"
            else:
                fast = "Tidak ditemukan kesalahan penalaran pada catatan ini menurut data audit. Tanda bahaya: tidak. Tetap perlu ditinjau dokter."
                verdict = "Menurut data audit, tidak ada kesalahan penalaran pada catatan ini."
            glines = (("Fakta graf yang relevan: " + "; ".join(gfacts) + ".") if gfacts else "Fakta graf yang relevan: tidak ada yang cocok langsung.")
            thinking = (f"Alasan langkah demi langkah:\n1. Isi catatan: \"{text}\"\n"
                        f"2. Label audit: reasoning_error={r['reasoning_error']}, jenis={r['error_type']}.\n"
                        f"3. {glines}\n4. Hasil: {verdict}\nCatatan: hasil ini bantuan peninjauan, bukan keputusan klinis.")
            self.groups.append(dict(gid=f"audit#{r['id']}", prompt=prompt, fast=fast, thinking=thinking, department="Audit Klinis",
                                    risk="tinggi" if err else "rendah", source="audited_clinical_predictions",
                                    source_ids=ids + gids, graph_ids=gids, audience="clinician_audit", task="reasoning_audit"))

    def note_exclusions(self):
        for r in self.approved:
            d = r["dataset_id"]
            if d == "DS-UNAPPROVED-TEST":
                self.excluded["approved: baris uji/rahasia DS-UNAPPROVED-TEST (secret_clinical_doc)"] += 1
            elif d == "DS-TRIAGE-COMBINED":
                self.excluded["approved: DS-TRIAGE-COMBINED (salinan df_clinical_combined, dipakai dari sumber aslinya)"] += 1
            elif d == "DS-TEST_UPLOAD_CASES":
                self.excluded["approved: DS-TEST_UPLOAD_CASES (data uji unggah)"] += 1
            elif d in ("DS-MEDICAL_RECORDS", "DS-CLINICAL_CASES", "DS-CLINICAL-REASONING"):
                self.excluded[f"approved: {d} (salinan RME-001..008, dipakai dari audited_clinical_predictions.csv)"] += 1
            elif d == "DS-SYMPTOMS":
                self.excluded["approved: DS-SYMPTOMS (dokumen protokol utuh, sudah dipecah di kb_chunks.json)"] += 1
        self.excluded["inbox/test_upload_cases.csv: 2 baris contoh uji"] += 1
        self.excluded["inbox/medical_records.csv, clinical_cases.jsonl, symptoms.txt: duplikat sumber lain (file)"] += 3
        self.excluded["synthetic/preferences (DPO): jawaban buatan model, bukan fakta sumber (file)"] += 1
        self.excluded["synthetic/noise_experiments: variasi derau dari kasus yang sama, bukan data baru (file)"] += 1
        self.excluded["raw/heart_attack_prediction_indonesia.csv: data tabular 158k baris, tidak ada teks klinis untuk SFT (file)"] += 1

    def finalize(self):
        seen, uniq = set(), []
        for g in self.groups:
            k = norm(g["prompt"])
            if k in seen:
                self.excluded["prompt duplikat dibuang"] += 1
                continue
            seen.add(k)
            uniq.append(g)
        self.groups = uniq
        rng = random.Random(SEED)
        order = sorted(g["gid"] for g in self.groups)
        rng.shuffle(order)
        n = len(order)
        n_test = n_val = max(1, round(n * 0.1))
        split_of = {gid: ("test" if i < n_test else "val" if i < n_test + n_val else "train") for i, gid in enumerate(order)}
        rows = {"fast": defaultdict(list), "thinking": defaultdict(list)}
        for g in sorted(self.groups, key=lambda x: x["gid"]):
            for mode, system in (("fast", SYSTEM_FAST), ("thinking", SYSTEM_THINKING)):
                row = {"messages": [{"role": "system", "content": system}, {"role": "user", "content": g["prompt"]},
                                    {"role": "assistant", "content": g[mode]}],
                       "meta": {"mode": mode, "source": g["source"], "source_ids": g["source_ids"], "graph_ids": g["graph_ids"],
                                "department": g["department"], "risk": g["risk"], "audience": g["audience"], "task": g["task"],
                                "group_id": g["gid"], "split": split_of[g["gid"]]}}
                rows[mode][split_of[g["gid"]]].append(row)
        return rows

    def verify(self, rows):
        problems, prompts = [], {}
        for mode in rows:
            for split, lst in rows[mode].items():
                for r in lst:
                    h = pii_hits(" ".join(m["content"] for m in r["messages"]))
                    if h:
                        problems.append(f"PII {h} di {r['meta']['group_id']}")
                    prompts.setdefault((mode, norm(r["messages"][1]["content"])), set()).add(split)
        for (mode, p), s in prompts.items():
            if len(s) > 1:
                problems.append(f"prompt bocor antar split ({mode}): {p[:60]}")
        sets = {m: {s: {norm(r["messages"][1]["content"]) for r in rows[m][s]} for s in ("train", "val", "test")} for m in rows}
        for s in ("train", "val", "test"):
            if sets["fast"][s] != sets["thinking"][s]:
                problems.append(f"split {s} berbeda antar mode")
        for m in rows:
            if sum(len(rows[m][s]) for s in rows[m]) != len(self.groups):
                problems.append(f"jumlah contoh mode {m} tidak sama dengan jumlah grup")
        return problems


def write_outputs(rows, b, problems):
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("sft_*.jsonl"):
        old.unlink()
    for mode in rows:
        allr = []
        for split in ("train", "val", "test"):
            with (OUT / f"sft_{mode}_{split}.jsonl").open("w", encoding="utf8", newline="\n") as f:
                for r in rows[mode][split]:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            allr += rows[mode][split]
        with (OUT / f"sft_{mode}.jsonl").open("w", encoding="utf8", newline="\n") as f:
            for r in allr:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    def cnt(key):
        c = Counter()
        for split in rows["fast"]:
            for r in rows["fast"][split]:
                c[r["meta"][key]] += 1
        return c

    by_split = {m: {s: len(rows[m][s]) for s in ("train", "val", "test")} for m in rows}
    used_cases = len(b.cases) - b.excluded["df_clinical_combined: berisi PII (NIK/nama)"]
    L = ["# Kartu Dataset SFT (FAST dan THINKING)", "",
         f"Dibuat oleh `scripts/build_sft_dataset.py` (seed {SEED}). Format: chat `messages` (system, user, assistant) plus `meta`.", "",
         "## Jumlah contoh", "", "| Mode | train | val | test | total |", "|---|---|---|---|---|"]
    for m in rows:
        s = by_split[m]
        L.append(f"| {m} | {s['train']} | {s['val']} | {s['test']} | {sum(s.values())} |")
    for title, key in (("Per poli/departemen (tiap mode sama)", "department"), ("Per sumber", "source"), ("Per tugas", "task"),
                       ("Per tingkat risiko", "risk"), ("Per audiens", "audience")):
        L += ["", f"## {title}", "", "| Nilai | jumlah |", "|---|---|"]
        for k, v in sorted(cnt(key).items()):
            L.append(f"| {k} | {v} |")
    L += ["", "## Per poli dan split (tiap mode sama)", "", "| Poli | train | val | test |", "|---|---|---|---|"]
    for d in sorted(cnt("department")):
        L.append(f"| {d} | " + " | ".join(str(sum(1 for r in rows['fast'][s] if r['meta']['department'] == d)) for s in ("train", "val", "test")) + " |")
    L += ["", "## Sumber data", "",
          "- `datasets/raw/kb_chunks.json`: 6 potongan pedoman (bukan 36) dengan poli. Dipakai untuk tanya jawab pedoman dan sebagai rujukan jawaban kasus.",
          f"- `datasets/raw/df_clinical_combined.csv`: {len(b.cases)} baris keluhan dengan label poli; {used_cases} dipakai.",
          "- `datasets/processed/graph_knowledge.jsonl`: graf hasil seed dari kode (28 simpul, 20 relasi) dari `scripts/graph_kb_export.py`.",
          f"- `datasets/raw/audited_clinical_predictions.csv`: {len(b.audit)} catatan klinis beraudit (contoh audit penalaran, audiens klinisi/admin riset, bukan pasien). Id RME yang sama di dataset approved dicatat di `source_ids`.",
          "", "## Dikecualikan", ""]
    for k, v in sorted(b.excluded.items()):
        L.append(f"- {k} ({v})")
    L += [""] + [f"- {n}" for n in b.exclude_notes]
    L += ["", "## Aturan penyusunan", "",
          "- Jawaban memakai kalimat templat; fakta (poli, obat, kontraindikasi, anjuran) berasal dari baris sumber yang dicatat di `meta.source_ids` dan `meta.graph_ids`.",
          "- Penanda tanda bahaya (ya/tidak) pada kasus triase memakai aturan kata kunci (`RED_FLAG_RE` di skrip), bukan label dokter. Ini heuristik.",
          "- Fakta graf pada kasus triase hanya disertakan bila ada kata kunci yang sama dengan simpul graf pada poli itu; kalau tidak, jawaban menyatakan tidak ada hubungan graf.",
          "- Nomor darurat: 119 dan IGD.",
          "- Pembagian train/val/test per grup kasus (seed tetap), sehingga tidak ada prompt yang sama di split berbeda. Prompt yang sama dipakai di kedua mode dan jatuh di split yang sama.",
          "- Pemeriksaan PII (NIK 16 digit, kata NIK, telepon, email, nama bergelar, penanda `[sensitif`) pada semua teks keluaran: " +
          ("LULUS, tidak ada temuan." if not problems else "GAGAL: " + "; ".join(problems)), "",
          "## Keterbatasan", "",
          f"- Data sangat kecil ({len(b.groups)} grup unik, tiap grup menjadi 1 contoh per mode). Cukup untuk uji alur SFT dan format, tidak cukup untuk model yang andal.",
          "- Graf hanya 28 simpul dan 20 relasi. Poli Gastroenterologi, Trauma/Bedah, dan Psikiatri tidak punya simpul penyakit di graf. Isi pedoman KB-OBS-005 (preeklamsia) tidak ada di data repo, dan KB-ENDO-003 tidak terhubung ke penyakit di graf.",
          "- Kasus triase sama untuk kedua mode, jadi FAST dan THINKING hanya berbeda gaya jawaban, bukan data.",
          "- Aturan tanda bahaya berbasis kata kunci dapat salah. Jawaban bukan diagnosis dan perlu ditinjau dokter sebelum dipakai pasien.",
          "- Skrip ini hanya membuat dataset, tidak menjalankan pelatihan model."]
    (OUT / "DATASET_CARD.md").write_text("\n".join(L) + "\n", encoding="utf8", newline="\n")


def main():
    b = Builder()
    b.load()
    b.build_cases()
    b.build_kb()
    b.build_graph()
    b.build_audit()
    b.note_exclusions()
    rows = b.finalize()
    problems = b.verify(rows)
    write_outputs(rows, b, problems)
    print(json.dumps({"groups": len(b.groups), "splits": {m: {s: len(rows[m][s]) for s in rows[m]} for m in rows},
                      "problems": problems, "approved_triage_matched_df": b.matched_approved}, ensure_ascii=False, indent=1))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
