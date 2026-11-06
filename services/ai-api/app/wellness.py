"""
Tips hidup sehat & rekomendasi berbasis biodata pasien.

Mesin ini murni berbasis aturan (deterministik). Data pribadi (usia, jenis kelamin, golongan darah,
riwayat penyakit, input gaya hidup) hanya dipakai di fungsi ini dan TIDAK PERNAH dikirim ke LLM
atau disimpan. Acuan: Pedoman Gizi Seimbang & "Isi Piringku" Kemenkes RI, rekomendasi aktivitas
fisik WHO 2020, dan rekomendasi durasi tidur National Sleep Foundation.

Golongan darah sengaja TIDAK dipakai untuk menentukan makanan: "diet golongan darah" tidak
didukung bukti ilmiah. Golongan darah hanya dipakai untuk info donor darah.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

SOURCES = [
    "Kemenkes RI — Pedoman Gizi Seimbang & Isi Piringku",
    "WHO — Guidelines on physical activity and sedentary behaviour (2020)",
    "National Sleep Foundation — Sleep duration recommendations",
    "PMI — Ketentuan donor darah",
]

DISCLAIMER = (
    "Rekomendasi ini bersifat umum dan dihitung otomatis dari biodata Anda tanpa AI/LLM. "
    "Bukan pengganti pemeriksaan atau saran dokter."
)

# Golongan darah (ABO + rhesus) -> boleh mendonorkan ke / menerima dari
_DONATE_TO: Dict[str, List[str]] = {
    "O-": ["semua golongan darah"],
    "O+": ["O+", "A+", "B+", "AB+"],
    "A-": ["A-", "A+", "AB-", "AB+"],
    "A+": ["A+", "AB+"],
    "B-": ["B-", "B+", "AB-", "AB+"],
    "B+": ["B+", "AB+"],
    "AB-": ["AB-", "AB+"],
    "AB+": ["AB+"],
}
_RECEIVE_FROM: Dict[str, List[str]] = {
    "O-": ["O-"],
    "O+": ["O+", "O-"],
    "A-": ["A-", "O-"],
    "A+": ["A+", "A-", "O+", "O-"],
    "B-": ["B-", "O-"],
    "B+": ["B+", "B-", "O+", "O-"],
    "AB-": ["AB-", "A-", "B-", "O-"],
    "AB+": ["semua golongan darah"],
}

# Kata kunci riwayat penyakit -> kondisi. Dicocokkan lokal, teks riwayat tidak pernah dikembalikan.
_CONDITIONS = {
    "hipertensi": ("hipertensi", "darah tinggi", "tekanan darah tinggi"),
    "diabetes": ("diabetes", "kencing manis", "gula darah"),
    "kolesterol": ("kolesterol", "dislipidemia"),
    "asam_urat": ("asam urat", "gout"),
    "maag": ("maag", "gerd", "lambung", "asam lambung"),
}


@dataclass
class Lifestyle:
    activity: Optional[str] = None       # "rendah" | "sedang" | "tinggi"
    sleep_hours: Optional[float] = None
    water_glasses: Optional[int] = None  # gelas 250 ml per hari
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    smoker: Optional[bool] = None


def age_group(age: Optional[int]) -> str:
    if age is None:
        return "dewasa"  # asumsi aman bila tanggal lahir belum diisi
    if age < 13:
        return "anak"
    if age < 18:
        return "remaja"
    if age < 60:
        return "dewasa"
    return "lansia"


_GROUP_LABEL = {"anak": "Anak (< 13 th)", "remaja": "Remaja (13–17 th)", "dewasa": "Dewasa (18–59 th)", "lansia": "Lansia (≥ 60 th)"}


def detect_conditions(history: Optional[str]) -> List[str]:
    text = (history or "").lower()
    return [k for k, words in _CONDITIONS.items() if any(w in text for w in words)]


def _item(title: str, detail: str, reason: str) -> Dict[str, str]:
    return {"title": title, "detail": detail, "reason": reason}


def _food(group: str, gender: Optional[str], age: Optional[int], conds: List[str]) -> List[Dict[str, str]]:
    items = [_item(
        "Isi Piringku",
        "Setengah piring sayur dan buah, seperempat makanan pokok (nasi, kentang, jagung), seperempat lauk (ikan, telur, tempe, tahu, ayam).",
        "Anjuran gizi seimbang Kemenkes untuk semua usia.",
    )]
    if group == "anak":
        items.append(_item("Susu & protein untuk tumbuh", "2–3 porsi susu/olahan susu dan lauk hewani setiap hari, batasi jajanan manis.", "Usia anak: masa pertumbuhan."))
    elif group == "remaja":
        items.append(_item("Sarapan setiap hari", "Sarapan sebelum sekolah: makanan pokok + lauk + buah. Hindari mengganti makan dengan mi instan atau camilan.", "Usia remaja: kebutuhan energi dan protein tinggi."))
    elif group == "lansia":
        items.append(_item("Protein cukup, tekstur lunak", "Lauk berprotein tiap makan (ikan, telur, tahu), sayur dimasak lunak, sumber kalsium seperti susu rendah lemak atau ikan teri.", "Usia lansia: menjaga massa otot dan tulang."))
    if gender == "P" and age is not None and 13 <= age < 50:
        items.append(_item("Makanan kaya zat besi", "Daging merah tanpa lemak, hati, bayam, kacang-kacangan; makan bersama buah sumber vitamin C.", "Perempuan usia subur: kebutuhan zat besi lebih tinggi."))
    if "hipertensi" in conds:
        items.append(_item("Kurangi garam", "Maksimal 1 sendok teh garam per hari; batasi ikan asin, kecap, makanan kaleng dan olahan.", "Riwayat tekanan darah tinggi di profil Anda."))
    if "diabetes" in conds:
        items.append(_item("Atur karbohidrat", "Pilih nasi merah/beras campur, porsi makanan pokok tetap, perbanyak sayur, hindari kue dan gorengan manis.", "Riwayat diabetes di profil Anda."))
    if "kolesterol" in conds:
        items.append(_item("Batasi lemak jenuh", "Kurangi gorengan, jeroan, santan kental; pilih ikan, kacang-kacangan, dan cara masak rebus/kukus.", "Riwayat kolesterol di profil Anda."))
    if "asam_urat" in conds:
        items.append(_item("Batasi purin tinggi", "Kurangi jeroan, seafood, emping, daging merah berlebih.", "Riwayat asam urat di profil Anda."))
    if "maag" in conds:
        items.append(_item("Makan teratur porsi kecil", "Makan tepat waktu, hindari makanan terlalu pedas, asam, dan berlemak; jangan langsung berbaring setelah makan.", "Riwayat maag/asam lambung di profil Anda."))
    items.append(_item("Batasi gula, garam, lemak", "Per hari: gula ≤ 4 sdm, garam ≤ 1 sdt, minyak ≤ 5 sdm (anjuran GGL Kemenkes).", "Berlaku untuk semua orang."))
    return items


def _drink(group: str, conds: List[str], ls: Lifestyle) -> List[Dict[str, str]]:
    target = {"anak": "5–6", "remaja": "7–8", "dewasa": "8", "lansia": "7–8"}[group]
    items = [_item(f"Air putih {target} gelas/hari", "Minum sedikit-sedikit tapi sering; tambah bila banyak berkeringat atau cuaca panas.", f"Kebutuhan cairan kelompok usia {_GROUP_LABEL[group]}.")]
    if ls.water_glasses is not None and ls.water_glasses < 6 and group != "anak":
        items.append(_item("Tambah asupan air", f"Anda mencatat {ls.water_glasses} gelas/hari. Coba sediakan botol minum dan isi ulang 3–4 kali sehari.", "Asupan air yang Anda isi masih di bawah anjuran."))
    if group == "lansia":
        items.append(_item("Jangan menunggu haus", "Rasa haus berkurang seiring usia; jadwalkan minum, misalnya setiap selesai makan dan bangun tidur.", "Usia lansia rawan dehidrasi."))
    items.append(_item("Batasi minuman manis", "Kurangi teh/kopi manis, minuman kemasan, dan soda; pilih air putih, teh tawar, atau infused water.", "Gula tersembunyi terbesar sering dari minuman."))
    if group in ("anak", "remaja"):
        items.append(_item("Hindari kopi & minuman energi", "Kafein dan minuman energi tidak dianjurkan untuk anak dan remaja.", f"Kelompok usia {_GROUP_LABEL[group]}."))
    if "diabetes" in conds:
        items.append(_item("Tanpa gula tambahan", "Minum teh/kopi tanpa gula, hindari jus kemasan; buah utuh lebih baik daripada jus.", "Riwayat diabetes di profil Anda."))
    return items


def _activity(group: str, ls: Lifestyle) -> List[Dict[str, str]]:
    if group in ("anak", "remaja"):
        items = [_item("Aktif 60 menit setiap hari", "Bermain aktif, bersepeda, olahraga sekolah; batasi layar hiburan ≤ 2 jam/hari.", "Rekomendasi WHO untuk usia 5–17 tahun.")]
    else:
        items = [_item("150 menit/minggu intensitas sedang", "Misalnya jalan cepat 30 menit, 5 hari seminggu, ditambah latihan kekuatan 2 hari/minggu.", "Rekomendasi WHO untuk dewasa.")]
    if group == "lansia":
        items.append(_item("Latihan keseimbangan", "Senam lansia, tai chi, atau berdiri satu kaki sambil berpegangan, 3 kali seminggu.", "Mengurangi risiko jatuh pada lansia."))
    if ls.activity == "rendah":
        items.append(_item("Mulai dari yang ringan", "Jalan kaki 10 menit setelah makan, naik tangga, dan berdiri/berjalan tiap 1 jam duduk.", "Anda mencatat aktivitas fisik rendah."))
    return items


def _sleep(group: str, ls: Lifestyle) -> List[Dict[str, str]]:
    rng = {"anak": (9, 11), "remaja": (8, 10), "dewasa": (7, 9), "lansia": (7, 8)}[group]
    items = [_item(f"Tidur {rng[0]}–{rng[1]} jam", "Jam tidur dan bangun yang sama setiap hari; jauhkan gawai 30 menit sebelum tidur.", f"Durasi anjuran untuk {_GROUP_LABEL[group]}.")]
    if ls.sleep_hours is not None and ls.sleep_hours < rng[0]:
        items.append(_item("Tidur Anda masih kurang", f"Anda mencatat {ls.sleep_hours:g} jam. Majukan jam tidur 15–30 menit secara bertahap.", "Di bawah durasi anjuran usia Anda."))
    return items


def _body(ls: Lifestyle, group: str) -> Optional[Dict[str, object]]:
    if not ls.height_cm or not ls.weight_kg or group in ("anak", "remaja"):
        return None
    bmi = ls.weight_kg / (ls.height_cm / 100) ** 2
    # Ambang IMT Asia-Pasifik (WHO 2000) yang dipakai Kemenkes
    if bmi < 18.5:
        cat, tip = "Berat badan kurang", "Tambah porsi makan bertahap dan camilan bergizi (kacang, susu, telur)."
    elif bmi < 23:
        cat, tip = "Normal", "Pertahankan pola makan seimbang dan aktivitas fisik."
    elif bmi < 25:
        cat, tip = "Berat badan lebih", "Kurangi porsi makanan pokok dan camilan manis/gorengan, tambah aktivitas fisik."
    else:
        cat, tip = "Obesitas", "Konsultasikan target penurunan berat badan dengan dokter atau ahli gizi."
    return {"bmi": round(bmi, 1), "category": cat, "tip": tip}


def _habits(ls: Lifestyle) -> List[Dict[str, str]]:
    items = [_item("Cuci tangan & cek kesehatan rutin", "Cuci tangan pakai sabun, dan periksa tekanan darah, gula darah, dan berat badan minimal setahun sekali.", "Gerakan CERDIK Kemenkes.")]
    if ls.smoker:
        items.insert(0, _item("Berhenti merokok", "Hubungi layanan berhenti merokok Kemenkes (Quitline 0800-177-6565) atau puskesmas terdekat.", "Anda mencatat masih merokok."))
    return items


def _blood(blood_type: Optional[str], age: Optional[int]) -> Optional[Dict[str, object]]:
    if not blood_type or blood_type not in _DONATE_TO:
        return None
    can_donate = age is not None and 17 <= age <= 60
    return {
        "blood_type": blood_type,
        "can_donate_to": _DONATE_TO[blood_type],
        "can_receive_from": _RECEIVE_FROM[blood_type],
        "donor_eligible_by_age": can_donate,
        "note": "Golongan darah tidak menentukan jenis makanan; rekomendasi makanan di atas berlaku untuk semua golongan darah.",
    }


def build_recommendations(
    age: Optional[int],
    gender: Optional[str],
    blood_type: Optional[str],
    medical_history: Optional[str],
    lifestyle: Optional[Lifestyle] = None,
) -> Dict[str, object]:
    ls = lifestyle or Lifestyle()
    group = age_group(age)
    conds = detect_conditions(medical_history)
    missing = [k for k, v in (("birth_date", age), ("gender", gender), ("blood_type", blood_type)) if v is None]
    return {
        "basis": {
            "age": age,
            "age_group": group,
            "age_group_label": _GROUP_LABEL[group],
            "gender": gender,
            "blood_type": blood_type,
            "conditions": conds,
            "missing_fields": missing,
        },
        "sections": [
            {"id": "food", "title": "Makanan", "items": _food(group, gender, age, conds)},
            {"id": "drink", "title": "Minuman", "items": _drink(group, conds, ls)},
            {"id": "activity", "title": "Aktivitas Fisik", "items": _activity(group, ls)},
            {"id": "sleep", "title": "Tidur", "items": _sleep(group, ls)},
            {"id": "habits", "title": "Kebiasaan Sehat", "items": _habits(ls)},
        ],
        "body": _body(ls, group),
        "blood": _blood(blood_type, age),
        "sources": SOURCES,
        "disclaimer": DISCLAIMER,
        "llm_used": False,
    }
