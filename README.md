# WatermarkGuard

Aplikasi Streamlit untuk menyisipkan dan memeriksa watermark gambar tak terlihat menggunakan Hybrid DWT-DCT dengan Quantization Index Modulation (QIM).

[![Python](https://img.shields.io/badge/Python-project-1D4E89?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-app-1D4E89?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Tests](https://img.shields.io/badge/tests-pytest-1D4E89?logo=pytest&logoColor=white)](https://pytest.org/)

## Ikhtisar

WatermarkGuard menyisipkan teks identitas pemilik ke dalam gambar dan menyediakan alur untuk menguji perubahan gambar serta memeriksa watermark. Aplikasi memiliki halaman **Create Watermark**, **Attack**, dan **Detect Watermark**.

> Secret Key diperlukan untuk membaca urutan blok yang dipakai saat embedding dan untuk memvalidasi tag integritas. Simpan key dari proses pembuatan; tanpa key yang sama, identitas tidak dapat diekstrak dan divalidasi.

## Daftar isi

- [Fitur](#fitur)
  - [Create Watermark](#create-watermark)
  - [Detect Watermark](#detect-watermark)
  - [Attack](#attack)
- [Cara kerja](#cara-kerja)
- [Metrik evaluasi](#metrik-evaluasi)
- [Struktur proyek](#struktur-proyek)
- [Teknologi](#teknologi)
- [Instalasi dan menjalankan](#instalasi-dan-menjalankan)
- [Alur penggunaan](#alur-penggunaan)
- [Penyimpanan Secret Key](#penyimpanan-secret-key)
- [Deployment di Railway](#deployment-di-railway)
- [Pengujian](#pengujian)
- [Catatan dan batasan](#catatan-dan-batasan)
- [Screenshots](#screenshots)

## Fitur

### Create Watermark

- Menerima satu gambar PNG atau JPEG.
- Menyisipkan teks identitas pemilik dan membuat Secret Key secara otomatis.
- Menampilkan gambar asli, hasil watermark, PSNR, dan Difference Map untuk visualisasi perubahan.
- Menyediakan hasil watermark untuk diunduh.

### Detect Watermark

- Menerima gambar PNG/JPEG dan Secret Key.
- Mengekstrak identitas serta membandingkan tag integritas yang terbaca dengan tag yang dihitung ulang.
- Menampilkan status, kemiripan tag (NC), tingkat kesalahan bit (BER), dan identitas jika tag valid.

### Attack

Attack hanya mengubah gambar yang diunggah. Setiap attack pada mode **Multiple Attacks** diterapkan secara terpisah pada gambar input, bukan berurutan pada hasil attack sebelumnya. Hasil tersedia untuk diunduh.

| Attack | Parameter implementasi |
| --- | --- |
| JPEG 90, JPEG 70, JPEG 50 | Kompresi JPEG dengan quality 90, 70, atau 50 |
| Crop 10% | Memotong margin 5% dari tinggi dan lebar pada setiap sisi, sehingga dimensi hasil menjadi 90% dari semula |
| Resize 75% | Mengecilkan ke 75% dengan `INTER_AREA`, lalu mengembalikan ukuran semula dengan `INTER_CUBIC` |
| Gaussian Noise | Noise normal dengan simpangan baku 5; generator memakai seed tetap `12345` |
| Gaussian Blur | Gaussian blur kernel 3×3, `sigmaX=0.8` |
| Brightness +20 | Faktor kecerahan 1.20 |
| Contrast 1.2 | Faktor kontras 1.20 |

## Cara kerja

### Embedding

1. Gambar RGB dikonversi ke grayscale.
2. Transformasi Haar DWT satu level membentuk subband LL, LH, HL, dan HH. Penyisipan dilakukan pada subband LL.
3. Teks identitas diubah menjadi UTF-8. Frame memuat magic bytes `WGD2`, panjang payload dua byte, payload, dan tag HMAC-SHA-256 sepanjang 16 byte yang dihitung dari header dan payload menggunakan Secret Key.
4. Koordinat blok 8×8 pada LL diacak secara deterministik dari seed berbasis SHA-256 Secret Key.
5. Bit frame diulang tiga kali. Setiap bit disisipkan menggunakan QIM pada selisih koefisien DCT di posisi `(1, 2)` dan `(2, 1)`, dengan langkah kuantisasi `140`.
6. DWT direkonstruksi dan kanal luminance hasil dikombinasikan kembali dengan kanal warna untuk menghasilkan gambar watermarked.

### Deteksi

1. Gambar dikonversi dan diproses dengan Haar DWT level satu yang sama.
2. Secret Key yang sama membentuk kembali urutan blok 8×8; bit dibaca dari pasangan koefisien DCT menggunakan QIM.
3. Tiga salinan setiap bit digabung dengan majority vote (setidaknya dua dari tiga).
4. Header `WGD2` dan panjang payload menentukan batas payload serta tag.
5. Aplikasi menghitung ulang HMAC tag. Identitas ditampilkan sebagai terdeteksi hanya jika bit tag hasil pembacaan sama persis dengan bit tag yang diharapkan.

## Metrik evaluasi

| Metrik | Makna |
| --- | --- |
| PSNR | Mengukur perbedaan citra asli dan citra hasil watermark dalam dB; nilai lebih tinggi berarti perbedaan piksel lebih kecil. |
| NC | Normalized Correlation antara bit tag integritas yang diharapkan dan yang terbaca. |
| BER | Proporsi bit tag integritas yang berbeda antara nilai yang diharapkan dan yang terbaca. |

NC dan BER pada halaman Detect mengukur tag integritas, bukan kualitas visual gambar. Status deteksi di UI mengikuti kecocokan bit tag secara persis.

## Struktur proyek

```text
.
├── app.py                         # Antarmuka Streamlit dan alur halaman
├── requirements.txt               # Dependensi Python
├── attacks/
│   ├── __init__.py
│   └── image_attacks.py            # Implementasi transformasi attack gambar
├── metrics/
│   ├── __init__.py
│   └── metrics.py                  # PSNR, NC, BER, dan helper status
├── watermark/
│   ├── __init__.py
│   ├── dwt_dct_watermark.py        # Embedding dan ekstraksi watermark
│   └── secret_key_registry.py      # Registry SQLite dan enkripsi Secret Key
└── tests/
    ├── conftest.py                 # Environment registry sementara untuk tes
    ├── test_create_single_upload.py
    ├── test_detection_flow.py
    ├── test_metrics.py
    ├── test_multiple_attack_persistence.py
    └── test_secret_key_registry.py
```

## Teknologi

- Python
- Streamlit
- NumPy
- OpenCV (`opencv-python-headless`)
- Pillow
- `cryptography` (Fernet untuk nilai Secret Key)
- pytest

Versi dependensi dicantumkan di [`requirements.txt`](requirements.txt); dependensi Streamlit dan beberapa paket lain tidak dipatok ke versi tertentu.

## Instalasi dan menjalankan

Pastikan Python tersedia, lalu buat virtual environment dari direktori proyek.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

### Linux dan macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Alur penggunaan

1. **Create Watermark:** unggah gambar, masukkan identitas pemilik, jalankan embedding, lalu simpan gambar hasil dan Secret Key.
2. **Attack (opsional):** unggah gambar watermarked, pilih satu atau beberapa attack, lalu unduh hasilnya.
3. **Detect Watermark:** unggah gambar watermarked atau hasil attack dan masukkan Secret Key yang dipakai saat embedding.

## Penyimpanan Secret Key

Secret Key dibuat menggunakan generator acak kriptografis dan dicatat pada tabel SQLite `watermark_registry`. Fingerprint SHA-256 dari Secret Key menjadi primary key; nilai key disimpan terenkripsi dengan Fernet. Database juga mencatat identitas pemilik, algoritma, waktu pembuatan, dan status key.

Secara lokal, registry menggunakan `.watermarkguard/watermarkguard.sqlite3` dan file key enkripsi `.watermarkguard/watermarkguard.sqlite3.key` di direktori proyek. Direktori dibuat otomatis. `WATERMARK_DB_PATH` dapat menentukan path file database lokal; `SECRET_KEY_STORAGE_PATH` dapat menentukan direktori storage.

Jangan menghapus atau mengganti file key enkripsi maupun nilai `WATERMARK_ENCRYPTION_KEY` yang sudah digunakan. Database tidak dapat mendekripsi Secret Key yang tersimpan jika key enkripsinya hilang atau berubah. Secret Key hasil embedding juga diperlukan untuk ekstraksi dan validasi.

## Deployment di Railway

Dalam environment yang terdeteksi sebagai production/Railway, storage default registry adalah `/data`. Pasang **Volume** pada service dan mount di `/data` agar database serta file key enkripsi bertahan setelah restart atau redeploy:

```text
/data/watermarkguard.sqlite3
/data/watermarkguard.sqlite3.key
```

Environment variables yang dikenali:

| Variable | Fungsi |
| --- | --- |
| `WATERMARK_DB_PATH` | Path file database lokal; digunakan bila tidak ada `SECRET_KEY_STORAGE_PATH` dan bukan production. |
| `SECRET_KEY_STORAGE_PATH` | Direktori storage untuk database dan file key enkripsi. Di production, path relatif ditolak. |
| `WATERMARK_ENCRYPTION_KEY` | Fernet key yang disediakan secara eksplisit. Jika tidak diatur, registry memuat atau membuat file key di samping database. |
| `RAILWAY_VOLUME_MOUNT_PATH` | Menandai environment Railway; direktori default registry tetap `/data`. |
| `RAILWAY_ENVIRONMENT`, `RAILWAY_PROJECT_ID`, `RAILWAY_SERVICE_ID` | Penanda tambahan environment Railway. |
| `APP_ENV`, `ENVIRONMENT`, `ENV`, `NODE_ENV` | Nilai `production` pada variable pertama yang tersedia menandai environment production non-Railway. |

Jika storage tidak dapat ditulis, registry gagal disiapkan dan aplikasi menampilkan pesan umum terkait penyimpanan Secret Key; detail teknis dicatat ke log. Pastikan Volume ter-mount dan service memiliki izin tulis. Jangan mengandalkan storage ephemeral untuk menyimpan database dan key enkripsinya.

## Pengujian

Jalankan seluruh tes dari root proyek:

```bash
python -m pytest
```

Tes mencakup:

- PSNR, NC, BER, status watermark, round-trip embedding/ekstraksi, penolakan Secret Key yang salah, dan gambar yang tidak memiliki kapasitas.
- Ekstraksi setelah JPEG 90, Resize 75%, Gaussian Noise, dan Gaussian Blur.
- Ukuran hasil Crop 10%, format/ukuran JPEG, Gaussian Blur, serta penolakan jenis attack yang tidak dikenal.
- Alur UI pembuatan watermark untuk satu unggahan, pendaftaran key, persistensi key saat rerun, dan deteksi watermark.
- Persistensi hasil mode Multiple Attacks setelah rerun.
- Registry: keunikan 1.000 key, enkripsi dan persistensi, constraint serta proteksi perubahan/penghapusan, migrasi skema lama, dan pemilihan path lokal/Railway.

## Catatan dan batasan

- Kemampuan ekstraksi setelah perubahan gambar bergantung pada jenis dan kekuatan attack. Hasil pada beberapa tes tidak menjamin hasil yang sama untuk gambar atau parameter lain.
- Simpan Secret Key saat dibuat dan gunakan key tersebut saat deteksi.
- Jangan menghapus atau mengganti file key enkripsi registry. Kehilangannya dapat membuat Secret Key yang tersimpan tidak dapat dibaca.
- Crop dapat menghilangkan informasi watermark yang diperlukan untuk ekstraksi.
- `WATERMARK_ENCRYPTION_KEY` harus berupa Fernet key yang valid bila ditetapkan secara eksplisit.

## Screenshots

<!-- TODO: tambahkan screenshot aplikasi -->
