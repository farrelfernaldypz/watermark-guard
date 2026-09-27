# WatermarkGuard

WatermarkGuard adalah aplikasi Streamlit untuk menyisipkan dan menguji watermark kepemilikan pada citra. Watermark menggunakan algoritma Hybrid DWT-DCT: teks identitas di-encode menjadi bit dan disisipkan ke koefisien DCT pada subband LL dari DWT Haar level 1.

Secret Key menentukan urutan blok pseudo-random dan dipakai untuk memvalidasi watermark. Gunakan key yang sama saat mendeteksi watermark.

## Fitur

### Create Watermark

Unggah gambar PNG/JPEG dan masukkan teks identitas. Aplikasi membuat Secret Key acak, menyisipkan watermark, menampilkan PSNR serta Difference Map, dan menyediakan gambar hasil untuk diunduh. Simpan Secret Key untuk proses Detect Watermark.

### Detect Watermark

Unggah gambar watermarked atau hasil attack, lalu masukkan Secret Key. Aplikasi mengekstrak identitas dari gambar dan menampilkan status serta NC/BER dari pemeriksaan tag integritas. Jika watermark tidak valid atau tidak ditemukan, Owner Identity tidak ditampilkan.

### Attack

Unggah gambar watermarked, pilih satu atau beberapa serangan, lalu unduh hasilnya. Attack hanya memodifikasi gambar; detection/extraction dilakukan di halaman Detect Watermark. Serangan yang tersedia:

- JPEG Quality 90, 70, dan 50
- Crop 10%
- Resize 75%
- Gaussian Noise
- Gaussian Blur
- Brightness +20
- Contrast 1.2

Pada mode Multiple Attacks, setiap serangan diterapkan terpisah pada gambar input dan hasilnya tetap tersedia untuk diunduh.

## Metrik

- **PSNR (Peak Signal-to-Noise Ratio):** mengukur perbedaan citra asli dan citra watermarked.
- **NC (Normalized Correlation):** mengukur kemiripan bit tag integritas.
- **BER (Bit Error Rate):** mengukur proporsi bit tag integritas yang berbeda.

## Instalasi dan Menjalankan

```bash
python -m venv .venv
pip install -r requirements.txt
python -m streamlit run app.py
```

## Workflow Demo

1. **Create Watermark:** unggah gambar, masukkan identitas, buat watermark, lalu simpan Secret Key dan `watermarked.png`.
2. **Attack:** unggah `watermarked.png`, jalankan attack, lalu unduh hasilnya.
3. **Detect Watermark:** unggah gambar watermarked atau hasil attack dan masukkan Secret Key untuk memeriksa watermark dan mengekstrak identitas.

## Pengujian

```bash
python -m pytest
```

Tes mencakup embedding/extraction Hybrid DWT-DCT serta ekstraksi setelah JPEG 90, Resize 75%, Gaussian Noise, dan Gaussian Blur.
