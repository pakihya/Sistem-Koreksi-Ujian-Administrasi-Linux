# -*- coding: utf-8 -*-
"""
skamaserver.py - Server HTTP mini untuk mengekspos hasil ujian siswa.
Mendukung banyak file hasil (hasil_basic-lnx.json, hasil_dns-srv.json, dll).
Endpoint:
  GET /status        - info server & daftar file hasil yang ada
  GET /daftar        - list semua file hasil dalam JSON
  GET /hasil/<nama>  - ambil satu file hasil, contoh: /hasil/hasil_dns-srv.json
  GET /semua         - ambil semua hasil sekaligus dalam satu array JSON
"""

import http.server
import json
import os
import sys
import socket
import socketserver
import datetime
import glob
from pathlib import Path

PORT   = 9876
FOLDER = os.path.dirname(os.path.abspath(__file__))

class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"
    DIM    = "\033[2m"

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def cari_file_hasil():
    """Temukan semua file hasil_*.json di folder skamaserver."""
    files = glob.glob(os.path.join(FOLDER, "hasil_*.json"))
    hasil = []
    for f in sorted(files):
        nama = os.path.basename(f)
        try:
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(f)).isoformat()
        except Exception:
            mtime = "-"
        hasil.append({"nama": nama, "path": f, "waktu": mtime})
    return hasil

class HasilHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        waktu = datetime.datetime.now().strftime("%H:%M:%S")
        print(C.DIM + "[" + waktu + "] " + self.address_string() + " - " + (format % args) + C.RESET)

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

        # GET /status
        if path in ("", "/status"):
            file_list = cari_file_hasil()
            self.kirim_json({
                "status":       "ok",
                "hostname":     socket.gethostname(),
                "waktu_server": datetime.datetime.now().isoformat(),
                "jumlah_hasil": len(file_list),
                "file_hasil":   [f["nama"] for f in file_list],
            })

        # GET /daftar - daftar lengkap file beserta waktu
        elif path == "/daftar":
            file_list = cari_file_hasil()
            self.kirim_json({"file_hasil": file_list})

        # GET /semua - semua hasil sekaligus dalam array
        elif path == "/semua":
            file_list = cari_file_hasil()
            if not file_list:
                self.kirim_json({"error": "Belum ada file hasil. Jalankan skamalearn.py dulu."}, 404)
                return
            semua = []
            for item in file_list:
                try:
                    with open(item["path"], "r", encoding="utf-8") as f:
                        data = json.load(f)
                    semua.append(data)
                except Exception as e:
                    semua.append({"error": str(e), "file": item["nama"]})
            self.kirim_json(semua)

        # GET /hasil/<nama_file.json>
        elif path.startswith("/hasil"):
            # Bisa /hasil (ambil file pertama / jika hanya satu)
            # atau /hasil/nama_file.json
            bagian = path[len("/hasil"):].lstrip("/")

            if not bagian:
                # Tidak ada nama file - cek apakah hanya ada 1 file hasil
                file_list = cari_file_hasil()
                if not file_list:
                    self.kirim_json({"error": "Belum ada file hasil. Jalankan skamalearn.py dulu."}, 404)
                    return
                if len(file_list) == 1:
                    # Langsung kembalikan satu-satunya file
                    bagian = file_list[0]["nama"]
                else:
                    # Ada banyak - kasih tahu guru untuk pakai /semua atau nama spesifik
                    self.kirim_json({
                        "error": "Ada " + str(len(file_list)) + " file hasil. Gunakan /semua atau /hasil/<nama>.",
                        "file_tersedia": [f["nama"] for f in file_list],
                        "contoh": "/hasil/" + file_list[0]["nama"],
                    }, 300)
                    return

            # Keamanan: hanya izinkan nama file hasil_*.json, tanpa path traversal
            nama_bersih = os.path.basename(bagian)
            if not nama_bersih.startswith("hasil_") or not nama_bersih.endswith(".json"):
                self.kirim_json({"error": "Nama file tidak valid. Harus: hasil_*.json"}, 400)
                return

            target = os.path.join(FOLDER, nama_bersih)
            if not os.path.isfile(target):
                file_list = cari_file_hasil()
                self.kirim_json({
                    "error": "File tidak ditemukan: " + nama_bersih,
                    "file_tersedia": [f["nama"] for f in file_list],
                }, 404)
                return

            try:
                with open(target, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.kirim_json(data)
            except Exception as e:
                self.kirim_json({"error": "Gagal baca file: " + str(e)}, 500)

        else:
            self.kirim_json({
                "error": "Endpoint tidak dikenal.",
                "endpoint": ["/status", "/daftar", "/semua", "/hasil", "/hasil/<nama_file.json>"]
            }, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()


def main():
    ip_lokal = get_local_ip()
    hostname = socket.gethostname()
    file_list = cari_file_hasil()

    print("\n" + C.CYAN + ("=" * 58) + C.RESET)
    print(C.BOLD + C.WHITE + "  SKAMASERVER - Server Hasil Ujian".center(58) + C.RESET)
    print(C.CYAN + ("=" * 58) + C.RESET)
    print(C.YELLOW + "  Hostname  : " + C.WHITE + hostname + C.RESET)
    print(C.YELLOW + "  IP Lokal  : " + C.WHITE + ip_lokal + C.RESET)
    print(C.YELLOW + "  Port      : " + C.WHITE + str(PORT) + C.RESET)
    print(C.CYAN + ("-" * 58) + C.RESET)
    print(C.GREEN + "  Beritahu guru IP ini:" + C.RESET)
    print(C.BOLD + "    " + ip_lokal + C.RESET)
    print(C.DIM + "  (Guru tinggal masukkan IP di skamaguru, semua" + C.RESET)
    print(C.DIM + "   hasil ujian akan diambil otomatis)" + C.RESET)

    print(C.CYAN + ("-" * 58) + C.RESET)
    if file_list:
        print(C.GREEN + "  File hasil tersedia (" + str(len(file_list)) + "):" + C.RESET)
        for f in file_list:
            print(C.DIM + "    - " + f["nama"] + C.RESET)
    else:
        print(C.YELLOW + "  [!] Belum ada file hasil." + C.RESET)
        print(C.DIM + "      Jalankan skamalearn.py terlebih dahulu." + C.RESET)

    print(C.DIM + "\n  Tekan Ctrl+C untuk menghentikan server." + C.RESET)
    print(C.CYAN + ("=" * 58) + C.RESET + "\n")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), HasilHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n" + C.YELLOW + "  Server dihentikan." + C.RESET + "\n")

if __name__ == "__main__":
    main()