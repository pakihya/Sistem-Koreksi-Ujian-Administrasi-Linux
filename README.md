# Sistem-Koreksi-Ujian-Administrasi-Linux
Aplikasi penilaian ujian praktik administrasi Linux Debian berbasis terminal dan GUI. Dirancang untuk lingkungan lab sekolah (SMK/sederajat) agar guru dapat menilai konfigurasi sistem siswa secara otomatis — tanpa perlu memeriksa satu per satu.
## Fitur Utama

- Siswa menjalankan koreksi mandiri di komputer masing-masing
- Guru mengambil nilai langsung via **IP address** siswa (tidak perlu kumpulkan file)
- Mendukung **banyak jenis ujian** dari file JSON terpisah (basic Linux, DNS, Samba, dll)
- Menambah soal baru **tanpa mengubah kode** — cukup edit file JSON
- Hasil disimpan otomatis dan dapat dibuka via GUI dashboard guru

---

## Struktur Aplikasi

```
skamalearn/
├── student/
│   ├── skamalearn.py       # Program koreksi (dijalankan siswa)
│   ├── skamaserver.py      # Mini HTTP server (dijalankan siswa, port 9876)
│   ├── basiclinux.json     # Contoh soal: Basic Linux
│   └── ujiandns.json       # Contoh soal: Konfigurasi DNS Server
└── teacher/
    └── skamaguru.py        # Dashboard GUI guru (Windows/Linux)
```

---

## Cara Penggunaan

### Di Komputer Siswa

**1. Salin file ke komputer siswa**

Letakkan di satu folder yang sama:

```
/home/app/
├── skamalearn.py
├── skamaserver.py
├── basiclinux.json
└── ujiandns.json
```

**2. Jalankan koreksi ujian**

```bash
python3 skamalearn.py
```

Program akan meminta:

```
Nama Lengkap (contoh: Budi Santoso): Budi Santoso
Kelas        (contoh: XI TKJ 1)    : XI TKJ 1

  Pilih File Ujian:
  [1]  Ujian Basic Linux Debian [BASIC-LNX]    (basiclinux.json)
  [2]  Ujian Konfigurasi DNS Server [DNS-SRV]  (ujiandns.json)
  Masukkan nomor ujian [1-2]: _
```

Hasil koreksi disimpan otomatis ke `hasil_<kode-ujian>.json` di folder yang sama.

**3. Jalankan server agar guru bisa mengambil nilai**

```bash
python3 skamaserver.py
```

Output menampilkan IP address yang perlu diberitahu ke guru:

```
  IP Lokal  : 192.168.1.15
  Port      : 9876

  Beritahu guru IP ini:
    192.168.1.15
```

Server tetap berjalan sampai ditekan `Ctrl+C`.

---

### Di Komputer Guru

**1. Jalankan dashboard**

```bash
python3 skamaguru.py
```

**2. Ambil nilai dari IP siswa**

Klik tombol **"Ambil dari IP Siswa"**, masukkan IP address siswa, lalu klik **Ambil**.

Jika siswa mengerjakan lebih dari satu ujian, semua hasil muncul otomatis sebagai
baris terpisah di daftar.

Untuk mengambil nilai seluruh kelas sekaligus, masukkan semua IP di kolom batch
(satu IP per baris) lalu klik **Ambil Semua dari Daftar**.

**3. Atau buka dari folder**

Klik **"Buka Folder Hasil"** dan pilih folder yang berisi file `hasil_*.json`
yang sudah dikumpulkan dari siswa.

---

## Format File Soal (JSON)

Buat file `<nama-ujian>.json` dengan struktur berikut:

```json
{
  "ujian": {
    "nama": "Nama Ujian Lengkap",
    "kode": "KODE-UJIAN",
    "versi": "1.0"
  },
  "soal": [
    {
      "nomor": 1,
      "tipe": "<tipe_soal>",
      "deskripsi": "Deskripsi soal yang ditampilkan",
      "...": "parameter tergantung tipe"
    }
  ]
}
```

---

## Tipe Soal yang Tersedia

| Tipe | Memeriksa | Parameter |
|---|---|---|
| `hostname` | Nama hostname mesin | `nilai_expected` atau `pola` (regex) |
| `direktori_ada` | Keberadaan direktori | `path` |
| `file_ada` | Keberadaan file | `path` |
| `isi_file` | Isi/konten file | `path`, `pola` (regex) atau `nilai_expected` |
| `timezone` | Konfigurasi timezone | `nilai_expected` (contoh: `Asia/Jakarta`) |
| `service_aktif` | Status service running | `service` (nama systemd) |
| `service_enabled` | Service auto-start boot | `service` (nama systemd) |
| `paket_terinstall` | Paket Debian terinstall | `paket` (nama paket dpkg) |
| `port_listen` | Port sedang terbuka | `port` (nomor port) |
| `perintah` | Output perintah shell | `perintah`, `pola` (regex) atau `nilai_expected` |

### Contoh Konfigurasi Soal

```json
{ "nomor": 1, "tipe": "hostname",
  "deskripsi": "Hostname sudah dikonfigurasi",
  "pola": "^(?!localhost$)[a-zA-Z0-9\\-]+$" }

{ "nomor": 2, "tipe": "timezone",
  "deskripsi": "Timezone diatur ke Asia/Jakarta",
  "nilai_expected": "Asia/Jakarta" }

{ "nomor": 3, "tipe": "service_aktif",
  "deskripsi": "Service bind9 sedang aktif",
  "service": "bind9" }

{ "nomor": 4, "tipe": "paket_terinstall",
  "deskripsi": "Paket bind9 sudah terinstall",
  "paket": "bind9" }

{ "nomor": 5, "tipe": "port_listen",
  "deskripsi": "Port 53 (DNS) terbuka",
  "port": 53 }

{ "nomor": 6, "tipe": "perintah",
  "deskripsi": "named-checkconf tidak ada error",
  "perintah": "named-checkconf 2>&1; echo EXIT:$?",
  "pola": "EXIT:0" }
```

---

## Menambah Tipe Soal Baru

Buka `skamalearn.py`, tambahkan fungsi checker dan daftarkan di `PEMERIKSA`:

```python
def periksa_tipe_baru(soal):
    # soal adalah dict dari JSON
    # kembalikan: (nilai, keterangan)
    # nilai: 1 = benar, 0 = salah
    return 1, "keterangan hasil"

PEMERIKSA = {
    # ... tipe yang sudah ada ...
    "tipe_baru": periksa_tipe_baru,
}
```

Lalu gunakan `"tipe": "tipe_baru"` di file JSON soal.

---

## Endpoint HTTP Server (skamaserver.py)

| Endpoint | Fungsi |
|---|---|
| `GET /status` | Info server dan daftar file hasil yang ada |
| `GET /daftar` | List semua file hasil dalam JSON |
| `GET /semua` | Semua hasil ujian siswa dalam satu array |
| `GET /hasil/<nama>` | Ambil satu file, contoh: `/hasil/hasil_dns-srv.json` |

---

## Format File Hasil

File `hasil_<kode>.json` yang disimpan di komputer siswa dan dibaca oleh guru:

```json
{
  "ujian": { "nama": "...", "kode": "..." },
  "file_ujian": "ujiandns.json",
  "nama_siswa": "Budi Santoso",
  "kelas": "XI TKJ 1",
  "hostname": "debian-budi",
  "waktu_mulai": "2025-01-01T08:00:00",
  "waktu_selesai": "2025-01-01T08:00:05",
  "total_soal": 10,
  "total_benar": 8,
  "detail": [
    {
      "nomor": 1,
      "tipe": "service_aktif",
      "deskripsi": "Service bind9 sedang aktif",
      "nilai": 1,
      "keterangan": "service bind9: active"
    }
  ]
}
```

---

## Persyaratan Sistem

**Komputer Siswa (Linux Debian):**
- Python 3.6+
- Hanya library standar Python (tidak perlu `pip install`)
- Akses jaringan lokal untuk skamaserver

**Komputer Guru (Windows/Linux):**
- Python 3.6+
- Tkinter (biasanya sudah termasuk di instalasi Python)
- Koneksi ke jaringan lokal yang sama dengan siswa

---

## Lisensi

MIT License — bebas digunakan dan dimodifikasi untuk keperluan pendidikan.
