"""Train + evaluate decision models using ONLY local data. Never touches Neon.
Run:  python scripts/train_decision_models.py
Artifacts: services/ai-api/models/decision/ ; metrics: docs/decision_metrics.json
Seed = 42 everywhere. Not clinically validated.
"""
import json, os, sys, tempfile, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "services" / "ai-api"
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(tempfile.gettempdir()) / "decision_train.db").replace("\\", "/")
os.environ["ENVIRONMENT"] = "development"
sys.path.insert(0, str(API))
import numpy as np, pandas as pd, joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold, cross_val_predict, cross_validate, train_test_split
from sklearn.metrics import f1_score, classification_report, confusion_matrix, roc_auc_score, recall_score, accuracy_score
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from app.ml import mode_router
from app.ml.mode_router import extract_features, FEATURES, route_mode, RED_FLAG_RE

assert os.environ["DATABASE_URL"].startswith("sqlite")
SEED = 42
OUT = API / "models" / "decision"; OUT.mkdir(parents=True, exist_ok=True)
R = {"seed": SEED}


def sft(name):
    return [json.loads(l) for l in open(ROOT / "datasets" / "sft" / name, encoding="utf8") if l.strip()]


def user_text(r):
    return r["messages"][1]["content"]


# ---------- a) department routing ----------
df = pd.read_csv(ROOT / "datasets/raw/df_clinical_combined.csv")
texts = list(df["text_clean"].astype(str)); labels = list(df["label"].astype(str))
for r in sft("sft_fast.jsonl"):
    m = r["meta"]
    if m["audience"] == "patient" and m["source"] != "df_clinical_combined":
        texts.append(user_text(r)); labels.append(m["department"])
d = pd.DataFrame({"t": texts, "y": labels}).drop_duplicates("t")
vc = d["y"].value_counts()
dropped = {k: int(v) for k, v in vc.items() if v < 5}
d = d[d.y.isin(vc[vc >= 5].index)].reset_index(drop=True)


def mk(clf):
    return Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)), ("clf", clf)])


cands = {"tfidf_logreg": LogisticRegression(C=10, class_weight="balanced", max_iter=2000, random_state=SEED),
         "tfidf_linearsvc": LinearSVC(C=1, class_weight="balanced", random_state=SEED),
         "tfidf_tree": DecisionTreeClassifier(max_depth=6, class_weight="balanced", random_state=SEED)}
cv = RepeatedStratifiedKFold(n_splits=4, n_repeats=5, random_state=SEED)
res = {}
for n, c in cands.items():
    s = cross_validate(mk(c), d.t, d.y, cv=cv, scoring=["accuracy", "f1_macro"])
    res[n] = {"acc_mean": round(float(s["test_accuracy"].mean()), 4), "acc_std": round(float(s["test_accuracy"].std()), 4),
              "f1_macro_mean": round(float(s["test_f1_macro"].mean()), 4), "f1_macro_std": round(float(s["test_f1_macro"].std()), 4)}
best = max(res, key=lambda k: res[k]["f1_macro_mean"])
pred = cross_val_predict(mk(cands[best]), d.t, d.y, cv=StratifiedKFold(4, shuffle=True, random_state=SEED))
cls = sorted(d.y.unique())
R["department"] = {"n_samples": len(d), "class_counts": {k: int(v) for k, v in d.y.value_counts().items()},
                   "classes_dropped_lt5": dropped, "cv": "4-fold x5 repeated stratified", "candidates": res, "best": best,
                   "per_class_report_oof": classification_report(d.y, pred, output_dict=True, zero_division=0),
                   "confusion_matrix_labels": cls, "confusion_matrix": confusion_matrix(d.y, pred, labels=cls).tolist(),
                   "note": "tiny data; paraphrase near-duplicates may inflate CV; not a clinical validation"}
joblib.dump(mk(cands[best]).fit(d.t, d.y), OUT / "department_router.joblib")

# ---------- b) cardio risk ----------
h = pd.read_csv(ROOT / "datasets/raw/heart_attack_prediction_indonesia.csv")
y = h["heart_attack"]; X = h.drop(columns="heart_attack")
sf = {}
for c in X.columns:
    v = X[c] if X[c].dtype != object else X[c].astype("category").cat.codes
    a = roc_auc_score(y, v); sf[c] = round(float(max(a, 1 - a)), 4)
Xe = pd.get_dummies(X, drop_first=True).astype(float)
Xtr, Xte, ytr, yte = train_test_split(Xe, y, test_size=0.2, stratify=y, random_state=SEED)


def ev(m):
    p = m.predict_proba(Xte)[:, 1]; yh = (p >= 0.5).astype(int)
    tn = int(((yh == 0) & (yte == 0)).sum()); fp = int(((yh == 1) & (yte == 0)).sum())
    return {"roc_auc": round(float(roc_auc_score(yte, p)), 4), "sensitivity": round(float(recall_score(yte, yh)), 4),
            "specificity": round(tn / (tn + fp), 4), "accuracy": round(float(accuracy_score(yte, yh)), 4)}


models = {"decision_tree_d4": DecisionTreeClassifier(max_depth=4, class_weight="balanced", min_samples_leaf=200, random_state=SEED),
          "decision_tree_d8": DecisionTreeClassifier(max_depth=8, class_weight="balanced", min_samples_leaf=100, random_state=SEED),
          "random_forest": RandomForestClassifier(n_estimators=100, max_depth=12, class_weight="balanced", n_jobs=-1, random_state=SEED),
          "gradient_boosting": GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=SEED)}
cres = {}
for n, m in models.items():
    if n == "gradient_boosting":
        w = np.where(ytr == 1, (ytr == 0).sum() / (ytr == 1).sum(), 1.0); m.fit(Xtr, ytr, sample_weight=w)
    else:
        m.fit(Xtr, ytr)
    cres[n] = ev(m)
tree = models["decision_tree_d4"]
(OUT / "cardio_tree_rules.txt").write_text(export_text(tree, feature_names=list(Xe.columns), show_weights=True), encoding="utf8")
joblib.dump({"model": tree, "features": list(Xe.columns)}, OUT / "cardio_tree_d4.joblib")
R["cardio"] = {"rows": len(h), "positive_rate": round(float(y.mean()), 4), "exact_duplicate_rows": int(h.duplicated().sum()),
               "duplicate_feature_rows": int(X.duplicated().sum()),
               "top_single_feature_auc": sorted(sf.items(), key=lambda kv: -kv[1])[:6],
               "split": "80/20 stratified seed 42", "imbalance": "class_weight=balanced (sample_weight for GB)", "results": cres,
               "tree_rules_file": "services/ai-api/models/decision/cardio_tree_rules.txt"}

# ---------- c) mode router ----------
rows = sft("sft_fast.jsonl")


def label_mode(r):
    m = r["meta"]
    if m["risk"] == "tinggi":
        return "thinking"
    if m["task"] in ("recommendation", "contraindication", "procedure", "guideline_qa", "reasoning_audit"):
        return "thinking"
    if extract_features(user_text(r))["symptom_hits"] >= 3:
        return "thinking"
    return "fast"


Xm = np.array([[extract_features(user_text(r))[k] for k in FEATURES] for r in rows])
ym = np.array([label_mode(r) for r in rows]); sp = np.array([r["meta"]["split"] for r in rows])
tr = sp != "test"; te = sp == "test"


def newtree():
    return DecisionTreeClassifier(max_depth=3, min_samples_leaf=3, class_weight="balanced", random_state=SEED)


cvp = cross_val_predict(newtree(), Xm[tr], ym[tr], cv=StratifiedKFold(5, shuffle=True, random_state=SEED))
t1 = newtree().fit(Xm[tr], ym[tr]); pt = t1.predict(Xm[te])
nrf = Xm[:, FEATURES.index("redflag_hits")] == 0
sub = tr & nrf
cv_nrf = cross_val_predict(newtree(), Xm[sub], ym[sub], cv=StratifiedKFold(3, shuffle=True, random_state=SEED))
final_m = newtree().fit(Xm, ym)
joblib.dump(final_m, mode_router.ARTIFACT)
(OUT / "mode_router_rules.txt").write_text(export_text(final_m, feature_names=FEATURES), encoding="utf8")
tinggi = np.array([r["meta"]["risk"] == "tinggi" for r in rows])
R["mode_router"] = {
    "n": len(rows), "label_counts": {k: int((ym == k).sum()) for k in sorted(set(ym))},
    "labeling": "risk==tinggi OR task in {recommendation,contraindication,procedure,guideline_qa,reasoning_audit} OR >=3 symptom hits => thinking, else fast. Labels are rule-derived, so metrics show how well a tree recovers the rules, not real routing quality.",
    "cv5_train_val_acc": round(float(accuracy_score(ym[tr], cvp)), 4),
    "cv5_train_val_f1_macro": round(float(f1_score(ym[tr], cvp, average="macro")), 4),
    "test_n": int(te.sum()), "test_acc": round(float(accuracy_score(ym[te], pt)), 4),
    "test_f1_macro": round(float(f1_score(ym[te], pt, average="macro", zero_division=0)), 4),
    "no_redflag_subset_n": int(sub.sum()), "no_redflag_subset_cv3_acc": round(float(accuracy_score(ym[sub], cv_nrf)), 4),
    "redflag_lexicon_recall_on_meta_risk_tinggi": round(float((Xm[tinggi, FEATURES.index("redflag_hits")] > 0).mean()), 4),
    "rules_file": "services/ai-api/models/decision/mode_router_rules.txt"}

# ---------- unit-style checks ----------
checks = []


def chk(name, ok):
    checks.append((name, bool(ok)))
    assert ok, name


mode_router._loaded = False
chk("redflag->thinking", route_mode("Nyeri dada menjalar ke lengan kiri")["mode"] == "thinking")
chk("redflag conf 1.0", route_mode("pingsan mendadak")["confidence"] == 1.0)
chk("output keys", set(route_mode("batuk pilek ringan")) == {"mode", "confidence", "reasons"})
chk("empty text safe", route_mode("")["mode"] in ("fast", "thinking"))
chk("redflag overrides model on all SFT prompts",
    all(route_mode(user_text(r))["mode"] == "thinking" for r in rows if RED_FLAG_RE.search(user_text(r))))
bak = mode_router.ARTIFACT
mode_router.ARTIFACT = Path("/nonexistent.joblib"); mode_router._loaded = False; mode_router._model = None
chk("fallback works", route_mode("kejang")["mode"] == "thinking" and route_mode("gatal ringan di tangan")["mode"] == "fast")
mode_router.ARTIFACT = bak; mode_router._loaded = False; mode_router._model = None
chk("artifact loads", mode_router._load() is not None)
R["unit_checks"] = checks

# ---------- SFT data validation ----------
sv = {}
for mode in ("fast", "thinking"):
    sets = {s: sft(f"sft_{mode}_{s}.jsonl") for s in ("train", "val", "test")}
    pr = {s: {user_text(r) for r in v} for s, v in sets.items()}
    lens = [sum(len(m["content"]) for m in r["messages"]) for v in sets.values() for r in v]
    ok = all([m["role"] for m in r["messages"]] == ["system", "user", "assistant"] for v in sets.values() for r in v)
    sv[mode] = {"counts": {s: len(v) for s, v in sets.items()}, "schema_ok": ok,
                "cross_split_prompt_overlap": len(pr["train"] & pr["val"]) + len(pr["train"] & pr["test"]) + len(pr["val"] & pr["test"]),
                "chars_per_example": {"min": min(lens), "median": int(np.median(lens)), "max": max(lens)}}
R["sft_validation"] = sv
hub = Path.home() / ".cache/huggingface/hub"
R["sft_base_model_check"] = {"hf_cache_models": sorted(p.name for p in hub.glob("models--*")) if hub.exists() else [],
                             "causal_lm_found": False, "real_sft_run": False}
(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs" / "decision_metrics.json").write_text(json.dumps(R, indent=2, ensure_ascii=False, default=str), encoding="utf8")
print(json.dumps({k: R[k] for k in ("mode_router", "sft_validation")}, indent=1, ensure_ascii=False))
print("dept best", best, json.dumps(res)); print("dept n", len(d), "dropped", dropped)
print("cardio", json.dumps(cres)); print("top auc", R["cardio"]["top_single_feature_auc"])
print("dupes", R["cardio"]["exact_duplicate_rows"], R["cardio"]["duplicate_feature_rows"], "checks ok", len(checks))
