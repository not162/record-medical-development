# Panduan SFT (LoRA dengan peft + trl)

## Yang sudah terbukti, dan yang belum

`scripts/sft_smoke_test.py` membuktikan **alur (pipeline) saja**: data SFT -> chat template -> LoRA lewat
peft/trl -> adapter tersimpan dan bisa dimuat ulang. Modelnya hanya model acak berukuran kecil
(GPT2, sekitar 0,65 juta parameter) dengan tokenizer yang dilatih lokal. Ini **bukan model yang berguna**.
Belum ada model dasar sungguhan yang dilatih di repo ini, jadi belum ada hasil kualitas jawaban.

Hasil nyata smoke test (CPU, 40 langkah, data `sft_fast`): loss latih rata-rata 5 langkah pertama 7,05
menjadi 6,21 di 5 langkah terakhir; loss validasi 7,31 menjadi 6,16; adapter tersimpan dan dimuat ulang.

## Versi yang diuji

transformers 5.18.0, torch 2.11.0 (CPU), peft 0.21.2, trl 1.17.1 (SFTTrainer). Versi dipin di
`services/ai-api/requirements-dev.txt` (bukan `requirements.txt`, karena itu untuk produksi serverless).

    python -m pip install -r services/ai-api/requirements-dev.txt

## Cek alur (tanpa unduhan, tanpa model)

    python scripts/sft_smoke_test.py

## Latih dengan model dasar sungguhan

Unduh sendiri model ke folder lokal (skrip tidak mengunduh apa pun kecuali Anda beri `--allow-download`).
Contoh model kecil yang mendukung bahasa Indonesia/multibahasa: Qwen2.5-0.5B-Instruct atau
Qwen2.5-1.5B-Instruct, Gemma-2-2B-it, Llama-3.2-1B-Instruct (cek lisensinya).

    python scripts/run_sft.py --base-model D:/models/Qwen2.5-0.5B-Instruct --mode fast
    python scripts/run_sft.py --base-model D:/models/Qwen2.5-0.5B-Instruct --mode both --epochs 3 --lora-r 8

Pilihan: `--mode fast|thinking|both`, `--epochs`, `--lr`, `--lora-r`, `--batch`, `--max-len`,
`--output-dir` (bawaan `services/ai-api/models/sft`), `--allow-download`.

Hasil: adapter LoRA di `<output-dir>/<mode>/` dan `run_report.json` berisi loss validasi sebelum dan sesudah.
Loss hanya dihitung pada jawaban asisten; bagian pertanyaan tidak dihitung.

## Perangkat keras (perkiraan, belum diukur di repo ini)

- Model 0,5B: CPU modern dengan RAM 8 GB cukup untuk 80 contoh, tetapi lambat (menit sampai puluhan menit per epoch).
- Model 1B sampai 2B: disarankan GPU 8 GB VRAM atau lebih (bf16/fp16 dipilih otomatis).
- Data saat ini hanya 80 contoh latih dan 10 validasi per mode, jadi hasilnya hanya cukup untuk uji coba,
  bukan untuk dipakai klinis.
