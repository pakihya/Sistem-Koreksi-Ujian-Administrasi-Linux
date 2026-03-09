# -*- coding: utf-8 -*-
"""
skamalearn.py - Sistem Koreksi Ujian Administrasi Linux
Alur: input nama+kelas -> pilih soal -> koreksi -> rekap -> server aktif -> Ctrl+C -> hapus hasil
"""

import json
import os
import re
import socket
import subprocess
import sys
import datetime
import glob
import threading
import signal
import atexit
import http.server
import socketserver
from pathlib import Path

FOLDER      = os.path.dirname(os.path.abspath(__file__))
SERVER_PORT = 9876

# ============================================================
# WARNA
# ============================================================
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    GREEN   = "\033[92m"
    RED     = "\033[91m"
    YELLOW  = "\033[93m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    DIM     = "\033[2m"

# ============================================================
# CETAK
# ============================================================
def garis(char="=", lebar=62):
    print(C.CYAN + (char * lebar) + C.RESET)

def cetak_header_utama():
    print()
    garis("=")
    print(C.BOLD + C.WHITE + "  SKAMALEARN - SISTEM KOREKSI UJIAN".center(62) + C.RESET)
    print(C.DIM   + "  Administrasi Linux -- NDS Lab".center(62) + C.RESET)
    garis("=")
    print()

def cetak_header_ujian(ujian_info, nama, kelas):
    print()
    garis("=")
    print(C.BOLD + C.WHITE + "  MULAI KOREKSI".center(62) + C.RESET)
    garis("=")
    print(C.YELLOW + "  Ujian  : " + C.WHITE + ujian_info.get("nama", "-") + C.RESET)
    print(C.YELLOW + "  Kode   : " + C.WHITE + ujian_info.get("kode", "-") + C.RESET)
    print(C.YELLOW + "  Siswa  : " + C.WHITE + nama + C.RESET)
    print(C.YELLOW + "  Kelas  : " + C.WHITE + kelas + C.RESET)
    garis("-")
    print()

def cetak_hasil_soal(nomor, deskripsi, nilai, keterangan=""):
    ikon = (C.GREEN + "[OK]" + C.RESET) if nilai == 1 else (C.RED + "[X] " + C.RESET)
    skor = (C.GREEN + "[1]" + C.RESET) if nilai == 1 else (C.RED + "[0]" + C.RESET)
    print("  " + ikon + " " + C.BOLD + "Soal " + str(nomor).rjust(2) + C.RESET +
          " | " + skor + " " + C.WHITE + deskripsi + C.RESET)
    if keterangan:
        print("             |   " + C.DIM + keterangan + C.RESET)

def cetak_rekap(hasil_soal, nama, kelas, ujian_info, waktu):
    total       = len(hasil_soal)
    total_benar = sum(s["nilai"] for s in hasil_soal)
    salah       = [s for s in hasil_soal if s["nilai"] == 0]

    print()
    garis("=")
    print(C.BOLD + C.WHITE + "  REKAP HASIL UJIAN".center(62) + C.RESET)
    garis("=")
    print("  Nama   : " + C.BOLD + C.WHITE + nama + C.RESET)
    print("  Kelas  : " + C.BOLD + C.WHITE + kelas + C.RESET)
    print("  Ujian  : " + C.WHITE + ujian_info.get("nama", "-") + C.RESET)
    print("  Waktu  : " + C.DIM + waktu + C.RESET)
    garis("-")
    warna_skor = C.GREEN if total_benar == total else C.YELLOW
    print("  Skor   : " + C.BOLD + warna_skor +
          str(total_benar) + "/" + str(total) +
          "  (" + str(round(total_benar/total*100)) + "%)" + C.RESET)
    if total_benar == total:
        print("\n  " + C.GREEN + C.BOLD + "SEMPURNA! Semua soal benar." + C.RESET)
    else:
        print("\n  " + C.YELLOW + "Soal yang belum benar:" + C.RESET)
        for s in salah:
            print("    " + C.RED + "[" + str(s["nomor"]) + "]" + C.RESET +
                  " " + s["deskripsi"])
    garis("=")
    print()

# ============================================================
# INPUT
# ============================================================
def tanya(prompt, contoh=""):
    while True:
        hint = (" " + C.DIM + "(" + contoh + ")" + C.RESET) if contoh else ""
        val  = input(C.YELLOW + "  " + prompt + C.RESET + hint + ": ").strip()
        if val:
            return val
        print(C.RED + "  Tidak boleh kosong." + C.RESET)

# ============================================================
# PILIH FILE UJIAN  (filter ketat: hanya file soal, bukan hasil)
# ============================================================
def temukan_file_ujian():
    files  = glob.glob(os.path.join(FOLDER, "*.json"))
    pilihan = []
    for f in sorted(files):
        nama = os.path.basename(f)
        # Keluarkan semua file hasil (awalan hasil_) dan file lain yang bukan soal
        if nama.lower().startswith("hasil_"):
            continue
        # Coba baca, pastikan punya key "ujian" dan "soal"
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if "ujian" not in data or "soal" not in data:
                continue  # bukan file soal yang valid
            nama_ujian = data["ujian"].get("nama", nama)
            kode_ujian = data["ujian"].get("kode", "")
            label = nama_ujian + (" [" + kode_ujian + "]" if kode_ujian else "")
        except Exception:
            continue  # skip file JSON yang rusak/tidak relevan
        pilihan.append((label, f, nama))
    return pilihan

def pilih_file_ujian():
    daftar = temukan_file_ujian()
    if not daftar:
        print(C.RED + "\n  [ERROR] Tidak ada file soal (.json) di folder ini." + C.RESET)
        print(C.DIM  + "  Pastikan file ujian ada di folder yang sama." + C.RESET)
        sys.exit(1)

    if len(daftar) == 1:
        label, path, _ = daftar[0]
        print(C.DIM + "  File ujian: " + C.WHITE + label + C.RESET + "\n")
        return path

    print(C.CYAN + "\n  Pilih File Ujian:" + C.RESET)
    garis("-", 50)
    for i, (label, _, nama_file) in enumerate(daftar, 1):
        print("  " + C.BOLD + C.WHITE + "[" + str(i) + "]" + C.RESET +
              "  " + C.WHITE + label + C.RESET +
              C.DIM + "  (" + nama_file + ")" + C.RESET)
    garis("-", 50)
    while True:
        try:
            pil = input(C.YELLOW + "  Nomor ujian" + C.RESET +
                        " [1-" + str(len(daftar)) + "]: ").strip()
            idx = int(pil) - 1
            if 0 <= idx < len(daftar):
                label, path, _ = daftar[idx]
                print(C.GREEN + "  Dipilih: " + label + C.RESET + "\n")
                return path
            print(C.RED + "  Pilihan tidak valid." + C.RESET)
        except (ValueError, KeyboardInterrupt):
            print(C.RED + "  Masukkan angka." + C.RESET)

# ============================================================
# PEMERIKSA SOAL
# ============================================================
def periksa_hostname(soal):
    h  = socket.gethostname()
    ex = soal.get("nilai_expected", "")
    po = soal.get("pola", "")
    ok = bool(re.fullmatch(po, h)) if po else h.strip().lower() == ex.strip().lower()
    return (1 if ok else 0), "hostname: " + h

def periksa_direktori_ada(soal):
    p  = soal.get("path", "")
    ok = os.path.isdir(p)
    return (1 if ok else 0), ("ada: " + p) if ok else ("tidak ada: " + p)

def periksa_file_ada(soal):
    p  = soal.get("path", "")
    ok = os.path.isfile(p)
    return (1 if ok else 0), ("ada: " + p) if ok else ("tidak ada: " + p)

def periksa_timezone(soal):
    ex = soal.get("nilai_expected", "")
    tz = ""
    try:
        r  = subprocess.run(["timedatectl", "show", "--property=Timezone", "--value"],
                            capture_output=True, text=True, timeout=5)
        tz = r.stdout.strip()
    except Exception:
        pass
    if not tz:
        try:
            tz = Path("/etc/timezone").read_text().strip()
        except Exception:
            tz = ""
    ok = tz.lower() == ex.strip().lower()
    return (1 if ok else 0), "timezone: " + (tz or "(tidak terbaca)")

def periksa_isi_file(soal):
    p   = soal.get("path", "")
    po  = soal.get("pola", "")
    ex  = soal.get("nilai_expected", "")
    if not os.path.isfile(p):
        return 0, "file tidak ada: " + p
    try:
        isi = Path(p).read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return 0, "error: " + str(e)
    if po:
        ok  = bool(re.search(po, isi, re.MULTILINE | re.IGNORECASE))
        ket = ("pola cocok" if ok else "pola tidak cocok") + " (" + po + ")"
    else:
        ok  = ex.strip() in isi
        ket = "nilai " + ("ditemukan" if ok else "tidak ditemukan")
    return (1 if ok else 0), ket

def periksa_service_aktif(soal):
    svc = soal.get("service", "")
    if not svc:
        return 0, "nama service tidak ada"
    try:
        r   = subprocess.run(["systemctl", "is-active", svc],
                             capture_output=True, text=True, timeout=5)
        st  = r.stdout.strip()
        ok  = st == "active"
        return (1 if ok else 0), svc + ": " + st
    except Exception as e:
        return 0, "error: " + str(e)

def periksa_service_enabled(soal):
    svc = soal.get("service", "")
    if not svc:
        return 0, "nama service tidak ada"
    try:
        r   = subprocess.run(["systemctl", "is-enabled", svc],
                             capture_output=True, text=True, timeout=5)
        st  = r.stdout.strip()
        ok  = st in ("enabled", "static")
        return (1 if ok else 0), svc + " enabled: " + st
    except Exception as e:
        return 0, "error: " + str(e)

def periksa_paket_terinstall(soal):
    pkg = soal.get("paket", "")
    if not pkg:
        return 0, "nama paket tidak ada"
    try:
        r   = subprocess.run(["dpkg", "-l", pkg],
                             capture_output=True, text=True, timeout=10)
        ok  = any(l.startswith("ii") and pkg in l for l in r.stdout.splitlines())
        return (1 if ok else 0), pkg + (" terinstall" if ok else " tidak terinstall")
    except Exception as e:
        return 0, "error: " + str(e)

def periksa_port_listen(soal):
    port = str(soal.get("port", ""))
    if not port:
        return 0, "port tidak ada"
    try:
        r   = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True, timeout=5)
        out = r.stdout
    except Exception:
        try:
            r   = subprocess.run(["netstat", "-tlnp"], capture_output=True, text=True, timeout=5)
            out = r.stdout
        except Exception as e:
            return 0, "error: " + str(e)
    ok = (":" + port + " ") in out or (":" + port + "\t") in out
    return (1 if ok else 0), "port " + port + (" terbuka" if ok else " tidak terbuka")

def periksa_perintah(soal):
    cmd = soal.get("perintah", "")
    po  = soal.get("pola", "")
    ex  = soal.get("nilai_expected", "")
    if not cmd:
        return 0, "perintah tidak ada"
    try:
        r   = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        out = (r.stdout + r.stderr).strip()
    except Exception as e:
        return 0, "error: " + str(e)
    if po:
        ok  = bool(re.search(po, out, re.MULTILINE | re.IGNORECASE))
        ket = ("cocok" if ok else "tidak cocok") + " | " + out[:70]
    else:
        ok  = ex.strip().lower() in out.lower()
        ket = ("ditemukan" if ok else "tidak ditemukan") + " | " + out[:70]
    return (1 if ok else 0), ket

PEMERIKSA = {
    "hostname":         periksa_hostname,
    "direktori_ada":    periksa_direktori_ada,
    "file_ada":         periksa_file_ada,
    "timezone":         periksa_timezone,
    "isi_file":         periksa_isi_file,
    "service_aktif":    periksa_service_aktif,
    "service_enabled":  periksa_service_enabled,
    "paket_terinstall": periksa_paket_terinstall,
    "port_listen":      periksa_port_listen,
    "perintah":         periksa_perintah,
}

# ============================================================
# MINI SERVER (embedded -- tidak perlu skamaserver.py terpisah)
# ============================================================
_hasil_path_global = None   # diset setelah hasil disimpan
_httpd_instance    = None

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class HasilHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # silent

    def kirim_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.rstrip("/")

        if path in ("", "/status"):
            ada = _hasil_path_global and os.path.isfile(_hasil_path_global)
            self.kirim_json({
                "status":       "ok",
                "hostname":     socket.gethostname(),
                "waktu_server": datetime.datetime.now().isoformat(),
                "ada_hasil":    bool(ada),
                "file_hasil":   [os.path.basename(_hasil_path_global)] if ada else [],
            })

        elif path in ("/hasil", "/semua"):
            if not _hasil_path_global or not os.path.isfile(_hasil_path_global):
                self.kirim_json({"error": "Hasil belum tersedia."}, 404)
                return
            try:
                with open(_hasil_path_global, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # /semua mengembalikan array (kompatibel skamaguru)
                payload = [data] if path == "/semua" else data
                self.kirim_json(payload)
            except Exception as e:
                self.kirim_json({"error": str(e)}, 500)

        else:
            self.kirim_json({"error": "Endpoint tidak dikenal."}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

def jalankan_server():
    global _httpd_instance
    socketserver.TCPServer.allow_reuse_address = True
    try:
        _httpd_instance = socketserver.TCPServer(("", SERVER_PORT), HasilHandler)
        _httpd_instance.serve_forever()
    except Exception:
        pass

def hentikan_server():
    global _httpd_instance
    if _httpd_instance:
        try:
            _httpd_instance.shutdown()
        except Exception:
            pass

# ============================================================
# CLEANUP: hapus file hasil saat Ctrl+C / exit
# ============================================================
_file_untuk_dihapus = []

def cleanup():
    for f in _file_untuk_dihapus:
        try:
            if os.path.isfile(f):
                os.remove(f)
                print("\n" + C.DIM + "  File hasil dihapus: " + f + C.RESET)
        except Exception:
            pass
    hentikan_server()

atexit.register(cleanup)

def handle_sigint(sig, frame):
    print("\n\n" + C.YELLOW + "  Sesi ujian diakhiri." + C.RESET)
    sys.exit(0)

signal.signal(signal.SIGINT, handle_sigint)

# ============================================================
# MAIN
# ============================================================
def main():
    global _hasil_path_global

    cetak_header_utama()

    # 1. Input identitas
    print(C.CYAN + "  Identitas Siswa" + C.RESET)
    garis("-", 44)
    nama  = tanya("Nama Lengkap", "Budi Santoso")
    kelas = tanya("Kelas       ", "XI TKJ 1")
    print()

    # 2. Pilih file soal (hasil_*.json otomatis disaring)
    soal_path = pilih_file_ujian()

    # 3. Baca soal
    try:
        with open(soal_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(C.RED + "  [ERROR] Gagal baca soal: " + str(e) + C.RESET)
        sys.exit(1)

    ujian_info  = config.get("ujian", {})
    daftar_soal = config.get("soal", [])

    # 4. Tentukan path hasil (di folder yang sama, awalan hasil_)
    kode_ujian  = ujian_info.get("kode", "ujian").replace(" ", "_").lower()
    hasil_path  = os.path.join(FOLDER, "hasil_" + kode_ujian + ".json")
    _hasil_path_global = hasil_path
    _file_untuk_dihapus.append(hasil_path)

    # 5. Koreksi
    cetak_header_ujian(ujian_info, nama, kelas)

    waktu_mulai = datetime.datetime.now()
    hasil_soal  = []
    total_benar = 0

    for soal in daftar_soal:
        nomor     = soal.get("nomor", "?")
        tipe      = soal.get("tipe", "")
        deskripsi = soal.get("deskripsi", "")
        fn        = PEMERIKSA.get(tipe)
        if fn is None:
            nilai, ket = 0, "tipe tidak dikenal: " + tipe
            print(C.YELLOW + "  [?] Soal " + str(nomor) + " - " + ket + C.RESET)
        else:
            try:
                nilai, ket = fn(soal)
            except Exception as e:
                nilai, ket = 0, "error: " + str(e)
        total_benar += nilai
        cetak_hasil_soal(nomor, deskripsi, nilai, ket)
        hasil_soal.append({"nomor": nomor, "tipe": tipe,
                           "deskripsi": deskripsi, "nilai": nilai, "keterangan": ket})

    waktu_selesai = datetime.datetime.now()
    waktu_str     = waktu_selesai.strftime("%Y-%m-%d %H:%M:%S")

    # 6. Rekap
    cetak_rekap(hasil_soal, nama, kelas, ujian_info, waktu_str)

    # 7. Simpan hasil
    output = {
        "ujian":         ujian_info,
        "file_ujian":    os.path.basename(soal_path),
        "nama_siswa":    nama,
        "kelas":         kelas,
        "hostname":      socket.gethostname(),
        "waktu_mulai":   waktu_mulai.isoformat(),
        "waktu_selesai": waktu_selesai.isoformat(),
        "total_soal":    len(daftar_soal),
        "total_benar":   total_benar,
        "detail":        hasil_soal,
    }
    with open(hasil_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 8. Jalankan server di background
    ip_lokal = get_local_ip()
    print(C.CYAN + "=" * 62 + C.RESET)
    print(C.BOLD + C.WHITE + "  SERVER AKTIF -- Guru dapat mengambil nilai sekarang".center(62) + C.RESET)
    print(C.CYAN + "=" * 62 + C.RESET)
    print(C.GREEN + "  IP Address  : " + C.BOLD + ip_lokal + C.RESET)
    print(C.GREEN + "  Port        : " + C.BOLD + str(SERVER_PORT) + C.RESET)
    print(C.DIM   + "\n  Beritahu guru IP ini. Nilai akan otomatis terkirim." + C.RESET)
    print(C.YELLOW + "\n  Tekan Ctrl+C untuk mengakhiri sesi dan menghapus data." + C.RESET)
    print(C.CYAN + "=" * 62 + C.RESET + "\n")

    t = threading.Thread(target=jalankan_server, daemon=True)
    t.start()

    # 9. Tunggu Ctrl+C
    try:
        signal.pause()   # Linux
    except AttributeError:
        # Windows tidak punya signal.pause
        import time
        while True:
            time.sleep(1)

if __name__ == "__main__":
    main()
