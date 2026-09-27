# WatermarkGuard

WatermarkGuard adalah aplikasi Streamlit untuk menyisipkan dan menguji tanda kepemilikan pada citra. Aplikasi menggunakan **Robust Digital Watermarking berbasis Discrete Cosine Transform (DCT) dengan penyisipan watermark pada koefisien frekuensi menengah**. Watermark adalah teks identitas yang dikodekan menjadi bit, kemudian disisipkan ke pasangan koefisien DCT pada blok 8×8.

Secret key di-hash untuk menghasilkan urutan pseudo-random blok yang deterministik. Key yang sama diperlukan saat extraction untuk mengunjungi posisi yang sama. Watermark bersifat invisible; Difference Map hanya memperkuat perubahan kecil untuk visualisasi.

## Fitur

### 1. Create Watermark

Upload gambar PNG/JPEG, masukkan teks identitas dan secret key, lalu buat gambar watermark. Aplikasi menampilkan gambar asli, gambar ber-watermark, teks watermark, PSNR Original vs Watermarked, serta Difference Map. Hasil dapat diunduh sebagai `watermarked.png`.

### 2. Detect Watermark

Upload gambar yang ingin diperiksa, lalu masukkan secret key dan expected watermark text yang digunakan saat Create. Detect memakai fungsi blind DCT extraction yang sama dengan Recovery, kemudian membandingkan bit hasil ekstraksi terhadap bit dari expected text menggunakan NC dan BER. Hasil ditampilkan sebagai Detected, Corrupted / Low Confidence, atau Not Detected, beserta preview teks hasil extraction.

Gambar cover tanpa watermark juga diproses dengan cara yang sama. Key atau expected text yang tidak cocok biasanya menurunkan NC dan menaikkan BER. Confidence bukan angka terpisah; NC adalah ukuran kemiripan bit yang benar-benar dihitung. Threshold status adalah prototype threshold dan harus divalidasi dengan hasil eksperimen.

### 3. Attack

Upload sendiri file watermarked (tidak diambil otomatis dari sesi Create). Pilih Single Attack atau Multiple Attacks, lalu unduh setiap hasil untuk dipakai pada tahap Recovery. Serangan yang tersedia:

- JPEG Quality 90, 70, dan 50
- Crop 10%
- Resize 75%
- Gaussian Noise
- Brightness +20
- Contrast 1.2

Untuk setiap attack yang dipilih, aplikasi melakukan blind extraction dan menampilkan NC, BER, status, dan PSNR terhadap file watermarked bila dimensi sama. Crop mengubah ukuran gambar sehingga PSNR diberi N/A, tanpa membandingkan array dengan ukuran berbeda. Pada mode Multiple, tiap serangan diterapkan terpisah pada input yang diunggah.

### 4. Recovery

Upload gambar watermarked atau hasil attack, masukkan secret key dan expected watermark text. Aplikasi mengekstrak teks, lalu menghitung NC, BER, dan status. **Blind extraction** tidak memerlukan citra asli; expected text hanya digunakan untuk menentukan panjang payload dan membandingkan bit.

Status memakai kombinasi NC dan BER. Cutoff saat ini adalah prototype threshold dan perlu divalidasi dengan hasil eksperimen pada dataset yang relevan. Hasil attack ditampilkan sebagaimana terukur; aplikasi tidak mengubah metrik agar tampak lebih baik. Crop dan resize dapat merusak keselarasan blok sehingga extraction bisa gagal.

## Metrik

- **PSNR (Peak Signal-to-Noise Ratio):** mengukur perbedaan kualitas antara citra asli dan citra watermarked. Nilai utama ditampilkan pada Create Watermark. PSNR attack hanya ditampilkan bila ukuran citra cocok.
- **NC (Normalized Correlation):** mengukur kesamaan antara bit expected dan bit hasil ekstraksi; nilai lebih tinggi berarti lebih banyak bit cocok.
- **BER (Bit Error Rate):** proporsi bit yang berbeda; nilai lebih rendah berarti lebih sedikit kesalahan.

## Konteks Keamanan Informasi

Penyisipan informasi kepemilikan langsung ke citra merupakan pendekatan **active protection/authentication**. Aplikasi ini bukan deepfake detector. Penelitian VERITAS tentang deteksi deepfake berbasis Vision Transformer dapat menjadi konteks pelengkap: watermarking sebagai pendekatan aktif dan deteksi deepfake sebagai pendekatan pasif.

## Instalasi dan Menjalankan

```bash
python -m venv .venv
```

Aktifkan virtual environment, lalu install dependency:

```bash
pip install -r requirements.txt
```

Jalankan aplikasi:

```bash
python -m streamlit run app.py
```

## Contoh Workflow Demo

1. **Create Watermark:** upload `original.jpg`, masukkan `Farrel - NPM 43` dan secret key, klik Create, lalu download `watermarked.png`.
2. **Detect Watermark:** upload `watermarked.png` (atau cover tanpa watermark), masukkan key dan expected text, lalu klik Detect Watermark untuk melihat status, NC, BER, dan preview extraction.
3. **Attack:** upload `watermarked.png`, pilih JPEG Quality 50, klik Apply Attack, lalu download hasilnya. Ulangi dari file watermarked yang sama untuk Crop 10% dan satu attack lain.
4. Jalankan **Detect Watermark** pada tiap hasil attack untuk melihat kondisi deteksi aktual. **Recovery** tetap tersedia sebagai fitur tambahan untuk mengambil kembali teks watermark.

## Menjalankan Unit Test

```bash
python -m pytest
```

Test mencakup PSNR, NC, BER, DCT embedding/extraction, deteksi pada cover dan gambar watermarked, deteksi setelah JPEG attack, serta fungsi attack.

## Struktur Project

```text
WatermarkGuard/
├── app.py
├── attacks/
│   └── image_attacks.py
├── metrics/
│   └── metrics.py
├── tests/
│   └── test_metrics.py
├── watermark/
│   └── dct_watermark.py
├── README.md
└── requirements.txt
```
