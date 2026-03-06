# -*- coding: utf-8 -*-
"""
skamalearn.py - Aplikasi Koreksi Ujian Administrasi Linux
Siswa input nama & kelas, lalu pilih file ujian (.json) dari folder yang sama.
"""

import json
import os
import re
import socket
import subprocess
import sys
import datetime
import glob
from pathlib import Path

# === WARNA TERMINAL =============================================================
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"
    BLUE   = "\033[94m"
    DIM    = "\033[2m"
    MAGENTA= "\033[95m"

# === FUNGSI CETAK ===============================================================
def cetak_header_utama():
    lebar = 60
    print("\n" + C.CYAN + ("=" * lebar) + C.RESET)
    print(C.BOLD + C.WHITE + "SKAMALEARN - SISTEM KOREKSI UJIAN".center(lebar) + C.RESET)
    print(C.CYAN + ("=" * lebar) + C.RESET)
    print(C.DIM + "  Administrasi Linux Debian - SMK".center(lebar) + C.RESET)
    print(C.CYAN + ("-" * lebar) + C.RESET + "\n")

def cetak_header_ujian(ujian_info, nama_siswa, kelas_siswa):
    lebar = 60
    print("\n" + C.CYAN + ("=" * lebar) + C.RESET)
    print(C.BOLD + C.WHITE + "MULAI KOREKSI".center(lebar) + C.RESET)
    print(C.CYAN + ("=" * lebar) + C.RESET)
    print(C.YELLOW + "  Ujian   : " + C.WHITE + ujian_info.get("nama", "-") + C.RESET)
    print(C.YELLOW + "  Kode    : " + C.WHITE + ujian_info.get("kode", "-") + C.RESET)
    print(C.YELLOW + "  Siswa   : " + C.WHITE + nama_siswa + C.RESET)
    print(C.YELLOW + "  Kelas   : " + C.WHITE + kelas_siswa + C.RESET)
    print(C.CYAN + ("-" * lebar) + C.RESET + "\n")

def cetak_hasil_soal(nomor, deskripsi, nilai, keterangan=""):
    ikon = (C.GREEN + "[OK]" + C.RESET) if nilai == 1 else (C.RED + "[X] " + C.RESET)
    skor = (C.GREEN + "[1]" + C.RESET) if nilai == 1 else (C.RED + "[0]" + C.RESET)
    print("  " + ikon + " " + C.BOLD + "Soal " + str(nomor).rjust(2) + C.RESET + " | " + skor + " " + C.WHITE + deskripsi + C.RESET)
    if keterangan:
        print("             |   " + C.DIM + keterangan + C.RESET)

def cetak_ringkasan(total_benar, total_soal, nama_siswa, kelas_siswa, waktu_selesai):
    lebar = 60
    print("\n" + C.CYAN + ("-" * lebar) + C.RESET)
    print(C.BOLD + C.WHITE + "  RINGKASAN HASIL" + C.RESET)
    print(C.CYAN + ("-" * lebar) + C.RESET)
    print("  Nama     : " + C.BOLD + C.WHITE + nama_siswa + C.RESET)
    print("  Kelas    : " + C.BOLD + C.WHITE + kelas_siswa + C.RESET)
    warna_skor = C.GREEN if total_benar == total_soal else C.YELLOW
    print("  Skor     : " + C.BOLD + warna_skor + str(total_benar) + "/" + str(total_soal) + C.RESET)
    print("  Waktu    : " + C.DIM + waktu_selesai + C.RESET)
    if total_benar == total_soal:
        print("\n  " + C.GREEN + C.BOLD + "SELAMAT! Semua soal benar." + C.RESET)
    else:
        kurang = total_soal - total_benar
        print("\n  " + C.YELLOW + str(kurang) + " soal belum benar." + C.RESET)
    print(C.CYAN + ("=" * lebar) + C.RESET + "\n")

# === INPUT DENGAN VALIDASI ======================================================
def input_tidak_kosong(prompt, contoh=""):
    """Input yang tidak boleh kosong."""
    while True:
        if contoh:
            teks = input(C.YELLOW + prompt + C.RESET + C.DIM + " (" + contoh + ")" + C.RESET + ": ").strip()
        else:
            teks = input(C.YELLOW + prompt + C.RESET + ": ").strip()
        if teks:
            return teks
        print(C.RED + "  Tidak boleh kosong. Coba lagi." + C.RESET)

# === PILIH FILE UJIAN ===========================================================
def temukan_file_ujian(folder):
    """
    Cari semua file .json di folder yang sama dengan skamalearn.py.
    Kecualikan hasil_ujian.json.
    Return list of (nama_tampil, path_lengkap)
    """
    pola  = os.path.join(folder, "*.json")
    files = glob.glob(pola)
    hasil = []
    for f in sorted(files):
        nama_file = os.path.basename(f)
        if nama_file.lower() in ("hasil_ujian.json",):
            continue
        # Coba baca metadata ujian
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            nama_ujian = data.get("ujian", {}).get("nama", nama_file)
            kode_ujian = data.get("ujian", {}).get("kode", "")
            label = nama_ujian
            if kode_ujian:
                label = label + " [" + kode_ujian + "]"
        except Exception:
            label = nama_file
        hasil.append((label, f, nama_file))
    return hasil

def pilih_file_ujian(folder):
    """Tampilkan daftar file ujian dan minta pilihan dari siswa."""
    daftar = temukan_file_ujian(folder)

    if not daftar:
        print(C.RED + "\n[ERROR] Tidak ada file ujian (.json) di folder ini." + C.RESET)
        print(C.DIM + "Pastikan file ujian (misal: basiclinux.json) ada di folder yang sama." + C.RESET)
        sys.exit(1)

    if len(daftar) == 1:
        label, path, nama_file = daftar[0]
        print(C.DIM + "  File ujian ditemukan: " + C.WHITE + label + C.RESET)
        return path

    # Lebih dari 1 file - tampilkan pilihan
    print("\n" + C.CYAN + "  Pilih File Ujian:" + C.RESET)
    print(C.DIM + "  " + ("-" * 50) + C.RESET)
    for i, (label, path, nama_file) in enumerate(daftar, 1):
        print("  " + C.BOLD + C.WHITE + "[" + str(i) + "]" + C.RESET +
              "  " + C.WHITE + label + C.RESET +
              C.DIM + "  (" + nama_file + ")" + C.RESET)
    print(C.DIM + "  " + ("-" * 50) + C.RESET)

    while True:
        try:
            pilihan = input(C.YELLOW + "  Masukkan nomor ujian" + C.RESET + " [1-" + str(len(daftar)) + "]: ").strip()
            idx = int(pilihan) - 1
            if 0 <= idx < len(daftar):
                label, path, nama_file = daftar[idx]
                print(C.GREEN + "  Dipilih: " + label + C.RESET + "\n")
                return path
            else:
                print(C.RED + "  Pilihan tidak valid." + C.RESET)
        except (ValueError, KeyboardInterrupt):
            print(C.RED + "  Masukkan angka yang valid." + C.RESET)

# === PEMERIKSA SOAL =============================================================

def periksa_hostname(soal):
    hostname_aktual = socket.gethostname()
    nilai_expected  = soal.get("nilai_expected", "")
    pola            = soal.get("pola", "")
    if pola:
        cocok = bool(re.fullmatch(pola, hostname_aktual))
    else:
        cocok = hostname_aktual.strip().lower() == nilai_expected.strip().lower()
    return (1 if cocok else 0), "hostname: " + hostname_aktual

def periksa_direktori_ada(soal):
    path = soal.get("path", "")
    ada  = os.path.isdir(path)
    return (1 if ada else 0), ("ditemukan: " + path) if ada else ("tidak ada: " + path)

def periksa_file_ada(soal):
    path = soal.get("path", "")
    ada  = os.path.isfile(path)
    return (1 if ada else 0), ("ditemukan: " + path) if ada else ("tidak ada: " + path)

def periksa_timezone(soal):
    nilai_expected = soal.get("nilai_expected", "")
    tz_aktual = ""
    try:
        result = subprocess.run(
            ["timedatectl", "show", "--property=Timezone", "--value"],
            capture_output=True, text=True, timeout=5
        )
        tz_aktual = result.stdout.strip()
    except Exception:
        pass
    if not tz_aktual:
        try:
            tz_aktual = Path("/etc/timezone").read_text().strip()
        except Exception:
            tz_aktual = ""
    cocok = tz_aktual.lower() == nilai_expected.strip().lower()
    return (1 if cocok else 0), "timezone: " + (tz_aktual or "(tidak terbaca)")

def periksa_isi_file(soal):
    path  = soal.get("path", "")
    pola  = soal.get("pola", "")
    nilai = soal.get("nilai_expected", "")
    if not os.path.isfile(path):
        return 0, "file tidak ditemukan: " + path
    try:
        isi = Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return 0, "error baca file: " + str(e)
    if pola:
        cocok = bool(re.search(pola, isi, re.MULTILINE | re.IGNORECASE))
        ket   = ("pola ditemukan" if cocok else "pola tidak cocok") + " (" + pola + ")"
    else:
        cocok = nilai.strip() in isi
        ket   = ("nilai ditemukan" if cocok else "nilai tidak ditemukan")
    return (1 if cocok else 0), ket

def periksa_service_aktif(soal):
    """Cek apakah systemd service aktif/running."""
    service = soal.get("service", "")
    if not service:
        return 0, "nama service tidak didefinisikan"
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service],
            capture_output=True, text=True, timeout=5
        )
        status = result.stdout.strip()
        cocok  = status == "active"
        return (1 if cocok else 0), "service " + service + ": " + status
    except Exception as e:
        return 0, "error cek service: " + str(e)

def periksa_service_enabled(soal):
    """Cek apakah systemd service enabled (auto-start)."""
    service = soal.get("service", "")
    if not service:
        return 0, "nama service tidak didefinisikan"
    try:
        result = subprocess.run(
            ["systemctl", "is-enabled", service],
            capture_output=True, text=True, timeout=5
        )
        status = result.stdout.strip()
        cocok  = status in ("enabled", "static")
        return (1 if cocok else 0), "service " + service + " enabled: " + status
    except Exception as e:
        return 0, "error cek service: " + str(e)

def periksa_paket_terinstall(soal):
    """Cek apakah paket Debian sudah terinstall via dpkg."""
    paket = soal.get("paket", "")
    if not paket:
        return 0, "nama paket tidak didefinisikan"
    try:
        result = subprocess.run(
            ["dpkg", "-l", paket],
            capture_output=True, text=True, timeout=10
        )
        # dpkg -l mengeluarkan "ii" di kolom pertama jika installed
        terinstall = any(
            line.startswith("ii") and paket in line
            for line in result.stdout.splitlines()
        )
        ket = "paket " + paket + (" terinstall" if terinstall else " tidak terinstall")
        return (1 if terinstall else 0), ket
    except Exception as e:
        return 0, "error cek paket: " + str(e)

def periksa_port_listen(soal):
    """Cek apakah port tertentu sedang listen (menggunakan ss atau netstat)."""
    port = str(soal.get("port", ""))
    if not port:
        return 0, "port tidak didefinisikan"
    try:
        result = subprocess.run(
            ["ss", "-tlnp"],
            capture_output=True, text=True, timeout=5
        )
        output = result.stdout
    except Exception:
        try:
            result = subprocess.run(
                ["netstat", "-tlnp"],
                capture_output=True, text=True, timeout=5
            )
            output = result.stdout
        except Exception as e:
            return 0, "error cek port: " + str(e)
    cocok = (":" + port + " ") in output or (":" + port + "\t") in output
    return (1 if cocok else 0), "port " + port + (" terbuka" if cocok else " tidak terbuka")

def periksa_perintah(soal):
    """
    Jalankan perintah shell dan cocokkan output-nya.
    soal: { "perintah": "...", "pola": "..." atau "nilai_expected": "..." }
    """
    perintah = soal.get("perintah", "")
    pola     = soal.get("pola", "")
    nilai    = soal.get("nilai_expected", "")
    if not perintah:
        return 0, "perintah tidak didefinisikan"
    try:
        result = subprocess.run(
            perintah, shell=True, capture_output=True,
            text=True, timeout=10
        )
        output = (result.stdout + result.stderr).strip()
    except Exception as e:
        return 0, "error jalankan perintah: " + str(e)
    if pola:
        cocok = bool(re.search(pola, output, re.MULTILINE | re.IGNORECASE))
        ket   = ("output cocok" if cocok else "output tidak cocok") + " | " + output[:60]
    else:
        cocok = nilai.strip().lower() in output.lower()
        ket   = ("ditemukan" if cocok else "tidak ditemukan") + " | " + output[:60]
    return (1 if cocok else 0), ket

# Registry - tambah tipe baru di sini
PEMERIKSA = {
    "hostname":          periksa_hostname,
    "direktori_ada":     periksa_direktori_ada,
    "file_ada":          periksa_file_ada,
    "timezone":          periksa_timezone,
    "isi_file":          periksa_isi_file,
    "service_aktif":     periksa_service_aktif,
    "service_enabled":   periksa_service_enabled,
    "paket_terinstall":  periksa_paket_terinstall,
    "port_listen":       periksa_port_listen,
    "perintah":          periksa_perintah,
}

# === MAIN =======================================================================
def main():
    FOLDER = os.path.dirname(os.path.abspath(__file__))

    # 1. Header awal
    cetak_header_utama()

    # 2. Input nama dan kelas siswa
    print(C.CYAN + "  Data Siswa" + C.RESET)
    print(C.DIM + "  " + ("-" * 40) + C.RESET)
    nama_siswa  = input_tidak_kosong("  Nama Lengkap", "contoh: Budi Santoso")
    kelas_siswa = input_tidak_kosong("  Kelas       ", "contoh: XI TKJ 1")
    print()

    # 3. Pilih file ujian
    soal_path = pilih_file_ujian(FOLDER)

    # 4. Baca file ujian
    try:
        with open(soal_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(C.RED + "[ERROR] Gagal membaca file ujian: " + str(e) + C.RESET)
        sys.exit(1)

    ujian_info  = config.get("ujian", {})
    daftar_soal = config.get("soal", [])
    output_cfg  = config.get("output", {})

    # 5. Tentukan path hasil
    # Nama file hasil: hasil_<kode_ujian>.json agar tidak tertimpa antar ujian
    kode_ujian = ujian_info.get("kode", "ujian").replace(" ", "_").lower()
    default_hasil = "hasil_" + kode_ujian + ".json"
    hasil_nama = output_cfg.get("path", default_hasil)
    if not os.path.isabs(hasil_nama):
        hasil_path = os.path.join(FOLDER, hasil_nama)
    else:
        hasil_path = hasil_nama

    # 6. Header ujian
    cetak_header_ujian(ujian_info, nama_siswa, kelas_siswa)

    # 7. Periksa setiap soal
    waktu_mulai = datetime.datetime.now()
    hasil_soal  = []
    total_benar = 0

    for soal in daftar_soal:
        nomor     = soal.get("nomor", "?")
        tipe      = soal.get("tipe", "")
        deskripsi = soal.get("deskripsi", "(tanpa deskripsi)")

        pemeriksa_fn = PEMERIKSA.get(tipe)
        if pemeriksa_fn is None:
            print(C.YELLOW + "  [?] Soal " + str(nomor) + " - tipe tidak dikenal: " + tipe + C.RESET)
            nilai, ket = 0, "tipe tidak dikenal: " + tipe
        else:
            try:
                nilai, ket = pemeriksa_fn(soal)
            except Exception as e:
                nilai, ket = 0, "error: " + str(e)

        total_benar += nilai
        cetak_hasil_soal(nomor, deskripsi, nilai, ket)
        hasil_soal.append({
            "nomor":      nomor,
            "tipe":       tipe,
            "deskripsi":  deskripsi,
            "nilai":      nilai,
            "keterangan": ket,
        })

    waktu_selesai = datetime.datetime.now()

    # 8. Ringkasan
    cetak_ringkasan(total_benar, len(daftar_soal), nama_siswa, kelas_siswa,
                    waktu_selesai.strftime("%Y-%m-%d %H:%M:%S"))

    # 9. Simpan hasil
    output_data = {
        "ujian":         ujian_info,
        "file_ujian":    os.path.basename(soal_path),
        "nama_siswa":    nama_siswa,
        "kelas":         kelas_siswa,
        "hostname":      socket.gethostname(),
        "waktu_mulai":   waktu_mulai.isoformat(),
        "waktu_selesai": waktu_selesai.isoformat(),
        "total_soal":    len(daftar_soal),
        "total_benar":   total_benar,
        "detail":        hasil_soal,
    }

    dir_hasil = os.path.dirname(hasil_path)
    if dir_hasil:
        os.makedirs(dir_hasil, exist_ok=True)
    with open(hasil_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(C.DIM + "Hasil disimpan ke: " + hasil_path + C.RESET + "\n")

if __name__ == "__main__":
    main()