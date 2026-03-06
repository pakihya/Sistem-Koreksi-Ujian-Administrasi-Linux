# -*- coding: utf-8 -*-
"""
skamaguru.py - Dashboard Guru Penilaian Ujian Linux
Buka folder hasil ATAU ambil langsung dari IP siswa.
Mendukung berbagai jenis ujian (basiclinux, dns, dll) secara otomatis.
"""

import json
import os
import sys
import glob
import datetime
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
try:
    from urllib.request import urlopen, Request
    from urllib.error import URLError, HTTPError
except ImportError:
    pass

# === KONSTANTA ==================================================================
APP_TITLE   = "SKAMAGURU - Dashboard Penilaian Ujian"
APP_VERSION = "1.2"
SERVER_PORT = 9876

WARNA = {
    "bg"        : "#0f1923",
    "sidebar"   : "#162230",
    "card"      : "#1e2d3e",
    "card2"     : "#243447",
    "accent"    : "#00d4aa",
    "accent2"   : "#0099ff",
    "hijau"     : "#00c853",
    "merah"     : "#ff3d3d",
    "kuning"    : "#ffd600",
    "teks"      : "#e8f0f7",
    "teks_dim"  : "#6b8399",
    "border"    : "#2a3f55",
    "header_bg" : "#0d1821",
    "row_alt"   : "#1a2a3a",
    "input_bg"  : "#1a2a3a",
    "ungu"      : "#b060ff",
    "orange"    : "#ff8c00",
}

FN = ("Consolas", 10)
FB = ("Consolas", 10, "bold")
FK = ("Consolas", 9)
FJ = ("Consolas", 18, "bold")

# === MODEL DATA =================================================================
class DataSiswa:
    def __init__(self, sumber, sumber_ip=None):
        self.valid     = False
        self.data      = {}
        self.sumber_ip = sumber_ip or ""
        self.path      = ""

        if isinstance(sumber, dict):
            self.data  = sumber
            self.valid = True
            self.path  = "[IP: " + sumber_ip + "]" if sumber_ip else "[jaringan]"
        else:
            self.path = sumber
            self._baca_file()

    def _baca_file(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data  = json.load(f)
            self.valid = True
        except Exception as e:
            self.data  = {"error": str(e)}
            self.valid = False

    # --- properti ---
    @property
    def nama_siswa(self):
        return self.data.get("nama_siswa", "Tidak Diketahui")

    @property
    def kelas(self):
        return self.data.get("kelas", "-")

    @property
    def hostname(self):
        return self.data.get("hostname",
               self.data.get("hostname_mesin", "-"))

    @property
    def waktu(self):
        t = self.data.get("waktu_selesai", "-")
        if len(t) >= 19:
            return t[:19].replace("T", " ")
        return t

    @property
    def total_soal(self):
        return self.data.get("total_soal", 0)

    @property
    def total_benar(self):
        return self.data.get("total_benar", 0)

    @property
    def detail(self):
        return self.data.get("detail", [])

    @property
    def ujian_info(self):
        return self.data.get("ujian", {})

    @property
    def nama_ujian(self):
        return self.ujian_info.get("nama", self.data.get("file_ujian", "-"))

    @property
    def kode_ujian(self):
        return self.ujian_info.get("kode", "-")

    @property
    def lengkap(self):
        return self.valid and self.total_soal > 0 and self.total_benar == self.total_soal

    @property
    def label_listbox(self):
        if not self.valid:
            ikon = "[!]"
        elif self.lengkap:
            ikon = "[OK]"
        else:
            ikon = "[ ]"
        sumber = " *" if self.sumber_ip else ""
        nama   = (self.nama_siswa[:18]).ljust(19)
        kls    = (self.kelas[:10]).ljust(11)
        skor   = str(self.total_benar) + "/" + str(self.total_soal)
        return "  " + ikon + "  " + nama + kls + "[" + skor + "]" + sumber

# === FETCH JARINGAN =============================================================
def _http_get(url, timeout=5):
    """Raw HTTP GET, return (parsed_json, error_str)."""
    try:
        with urlopen(Request(url), timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
            return None, body.get("error", "HTTP " + str(e.code))
        except Exception:
            return None, "HTTP Error " + str(e.code)
    except URLError as e:
        return None, "Tidak bisa konek: " + str(e.reason)
    except Exception as e:
        return None, str(e)

def fetch_semua_dari_ip(ip, port=SERVER_PORT, timeout=8):
    """
    Ambil SEMUA hasil ujian dari komputer siswa via /semua.
    Return: (list_of_DataSiswa, error_str)
    Jika hanya ada 1 file di server lama (/hasil), fallback ke sana.
    """
    base = "http://" + ip.strip() + ":" + str(port)

    # Coba endpoint /semua dulu (skamaserver versi baru)
    data, err = _http_get(base + "/semua", timeout)
    if err is None:
        if isinstance(data, list):
            siswa_list = [DataSiswa(d, sumber_ip=ip) for d in data]
            return siswa_list, None
        # Respons bukan array - server lama? Coba wrap jadi list
        return [DataSiswa(data, sumber_ip=ip)], None

    # Fallback: coba /hasil (server lama yang hanya punya hasil_ujian.json)
    data2, err2 = _http_get(base + "/hasil", timeout)
    if err2 is None:
        return [DataSiswa(data2, sumber_ip=ip)], None

    # Kedua endpoint gagal - kembalikan error pertama yang lebih informatif
    return None, err

# === DIALOG AMBIL IP ============================================================
class DialogIP(tk.Toplevel):
    def __init__(self, parent, cb):
        super().__init__(parent)
        self.cb = cb
        self.title("Ambil Nilai dari IP Siswa")
        self.geometry("530x440")
        self.configure(bg=WARNA["bg"])
        self.resizable(False, False)
        self.grab_set()
        self._build()
        self.focus_force()

    def _build(self):
        tk.Label(self, text="Ambil Nilai dari IP Siswa",
                 font=("Consolas", 14, "bold"),
                 fg=WARNA["accent"], bg=WARNA["bg"]).pack(pady=(18, 3))
        tk.Label(self, text="Pastikan skamaserver.py sudah berjalan di komputer siswa.",
                 font=FK, fg=WARNA["teks_dim"], bg=WARNA["bg"]).pack()

        # Input tunggal
        f1 = tk.Frame(self, bg=WARNA["card"], padx=18, pady=14)
        f1.pack(fill="x", padx=18, pady=(14, 5))
        tk.Label(f1, text="IP Address Siswa:", font=FN,
                 fg=WARNA["teks"], bg=WARNA["card"]).pack(anchor="w")
        baris = tk.Frame(f1, bg=WARNA["card"])
        baris.pack(fill="x", pady=(5, 0))
        self.e_ip = tk.Entry(baris, font=("Consolas", 12),
                              bg=WARNA["input_bg"], fg=WARNA["teks"],
                              insertbackground=WARNA["accent"],
                              relief="flat", bd=5)
        self.e_ip.pack(side="left", fill="x", expand=True, ipady=6)
        self.e_ip.bind("<Return>", lambda e: self._ambil_satu())
        self.e_ip.focus_set()
        self._btn(baris, "Ambil", self._ambil_satu, WARNA["accent2"]).pack(
            side="left", padx=(8, 0), ipady=6)

        self.lbl_status = tk.Label(self, text="", font=FK,
                                    fg=WARNA["teks_dim"], bg=WARNA["bg"],
                                    wraplength=460)
        self.lbl_status.pack(pady=(7, 0), padx=18)

        # Batch
        f2 = tk.Frame(self, bg=WARNA["card"], padx=18, pady=14)
        f2.pack(fill="x", padx=18, pady=(8, 5))
        tk.Label(f2, text="Ambil banyak IP sekaligus (satu per baris):",
                 font=FN, fg=WARNA["teks"], bg=WARNA["card"]).pack(anchor="w")
        self.t_batch = tk.Text(f2, height=5, font=("Consolas", 10),
                                bg=WARNA["input_bg"], fg=WARNA["teks"],
                                insertbackground=WARNA["accent"],
                                relief="flat", bd=3)
        self.t_batch.pack(fill="x", pady=(5, 0))

        bawah = tk.Frame(self, bg=WARNA["bg"])
        bawah.pack(fill="x", padx=18, pady=(10, 18))
        self._btn(bawah, "Ambil Semua dari Daftar",
                  self._ambil_batch, WARNA["ungu"]).pack(side="left")
        self._btn(bawah, "Tutup", self.destroy,
                  WARNA["card2"]).pack(side="right")

    def _btn(self, p, t, cmd, bg):
        return tk.Button(p, text=t, command=cmd, bg=bg, fg=WARNA["teks"],
                         font=FB, relief="flat", padx=10, pady=6,
                         cursor="hand2", activebackground=WARNA["accent"])

    def _status(self, teks, warna=None):
        self.lbl_status.config(text=teks, fg=warna or WARNA["teks_dim"])
        self.update_idletasks()

    def _ambil_satu(self):
        ip = self.e_ip.get().strip()
        if not ip:
            self._status("Masukkan IP address.", WARNA["kuning"])
            return
        self._status("Menghubungi " + ip + " ...", WARNA["teks_dim"])
        def kerja():
            siswa_list, err = fetch_semua_dari_ip(ip)
            if err:
                self.after(0, lambda: self._status("Gagal: " + err, WARNA["merah"]))
            else:
                for s in siswa_list:
                    self.after(0, lambda _s=s: self.cb(_s))
                n = len(siswa_list)
                nama = siswa_list[0].nama_siswa if siswa_list else "-"
                msg = "OK: " + nama + " - " + str(n) + " hasil ujian dari " + ip
                self.after(0, lambda: self._status(msg, WARNA["hijau"]))
        threading.Thread(target=kerja, daemon=True).start()

    def _ambil_batch(self):
        ips = [x.strip() for x in self.t_batch.get("1.0", tk.END).splitlines() if x.strip()]
        if not ips:
            self._status("Daftar IP kosong.", WARNA["kuning"])
            return
        self._status("Mengambil dari " + str(len(ips)) + " IP ...", WARNA["teks_dim"])
        def kerja():
            ok = 0; gagal = 0; total_hasil = 0
            for ip in ips:
                siswa_list, err = fetch_semua_dari_ip(ip)
                if err:
                    gagal += 1
                else:
                    for s in siswa_list:
                        self.after(0, lambda _s=s: self.cb(_s))
                    ok += 1
                    total_hasil += len(siswa_list)
            msg = "Selesai: " + str(ok) + " IP OK (" + str(total_hasil) + " hasil), " + str(gagal) + " gagal."
            self.after(0, lambda: self._status(msg, WARNA["hijau"] if gagal == 0 else WARNA["kuning"]))
        threading.Thread(target=kerja, daemon=True).start()

# === APLIKASI UTAMA =============================================================
class AppGuru:
    def __init__(self, root):
        self.root         = root
        self.siswa_list   = []
        self.siswa_aktif  = None
        self.folder_aktif = tk.StringVar(value="Belum dipilih")
        self._setup_window()
        self._build_ui()

    def _setup_window(self):
        self.root.title(APP_TITLE + " v" + APP_VERSION)
        self.root.geometry("1200x720")
        self.root.minsize(960, 600)
        self.root.configure(bg=WARNA["bg"])
        try:
            self.root.state("zoomed")
        except Exception:
            try:
                self.root.attributes("-zoomed", True)
            except Exception:
                pass

    # --- BUILD UI ---
    def _build_ui(self):
        self._build_header()
        self._build_content()
        self._build_statusbar()

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=WARNA["header_bg"], height=68)
        hdr.pack(fill="x"); hdr.pack_propagate(False)

        kiri = tk.Frame(hdr, bg=WARNA["header_bg"])
        kiri.pack(side="left", padx=20, pady=10)
        tk.Label(kiri, text="SKAMAGURU", font=("Consolas", 18, "bold"),
                 fg=WARNA["accent"], bg=WARNA["header_bg"]).pack(side="left")
        tk.Label(kiri, text="  Dashboard Penilaian Ujian  v" + APP_VERSION,
                 font=("Consolas", 11), fg=WARNA["teks_dim"],
                 bg=WARNA["header_bg"]).pack(side="left")

        kanan = tk.Frame(hdr, bg=WARNA["header_bg"])
        kanan.pack(side="right", padx=20)
        self._btn(kanan, "Ambil dari IP Siswa", self._buka_dialog_ip,
                  WARNA["ungu"]).pack(side="left", padx=4)
        self._btn(kanan, "Buka Folder Hasil", self._buka_folder,
                  WARNA["accent2"]).pack(side="left", padx=4)
        self._btn(kanan, "Refresh", self._refresh,
                  WARNA["card2"]).pack(side="left", padx=4)

    def _build_content(self):
        wrap = tk.Frame(self.root, bg=WARNA["bg"])
        wrap.pack(fill="both", expand=True)
        self._build_left(wrap)
        self._build_right(wrap)

    def _build_left(self, parent):
        frame = tk.Frame(parent, bg=WARNA["sidebar"], width=360)
        frame.pack(side="left", fill="y"); frame.pack_propagate(False)

        # Header
        hdr = tk.Frame(frame, bg=WARNA["sidebar"])
        hdr.pack(fill="x", padx=12, pady=(14, 6))
        tk.Label(hdr, text="DAFTAR SISWA", font=FB,
                 fg=WARNA["accent"], bg=WARNA["sidebar"]).pack(side="left")
        self.lbl_jml = tk.Label(hdr, text="(0)", font=FK,
                                 fg=WARNA["teks_dim"], bg=WARNA["sidebar"])
        self.lbl_jml.pack(side="left", padx=4)
        self._btn(hdr, "Hapus", self._hapus_terpilih,
                  WARNA["merah"]).pack(side="right")

        # Kolom header listbox
        col_hdr = tk.Frame(frame, bg=WARNA["card2"])
        col_hdr.pack(fill="x", padx=10)
        for teks, lbr in [("St", 5), ("Nama", 19), ("Kelas", 12), ("Skor", 7)]:
            tk.Label(col_hdr, text=teks, font=FK, fg=WARNA["teks_dim"],
                     bg=WARNA["card2"], width=lbr, anchor="w",
                     padx=4, pady=4).pack(side="left")

        # Listbox
        lf = tk.Frame(frame, bg=WARNA["sidebar"])
        lf.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        sb = tk.Scrollbar(lf, bg=WARNA["card"])
        self.listbox = tk.Listbox(
            lf, bg=WARNA["card"], fg=WARNA["teks"],
            selectbackground=WARNA["accent"], selectforeground="#000",
            font=("Consolas", 9), relief="flat", bd=0,
            highlightthickness=0, activestyle="none",
            yscrollcommand=sb.set)
        sb.config(command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._pilih_siswa)

        # Ringkasan
        self.f_ring = tk.Frame(frame, bg=WARNA["card"], pady=8)
        self.f_ring.pack(fill="x", padx=10, pady=(0, 12))
        self._update_ringkasan()

        # Folder info
        ff = tk.Frame(frame, bg=WARNA["card2"], padx=10, pady=5)
        ff.pack(fill="x", padx=10, pady=(0, 10))
        tk.Label(ff, text="Folder:", font=FK, fg=WARNA["teks_dim"],
                 bg=WARNA["card2"]).pack(side="left")
        tk.Label(ff, textvariable=self.folder_aktif, font=FK,
                 fg=WARNA["teks"], bg=WARNA["card2"],
                 wraplength=230, anchor="w").pack(side="left", padx=4)

    def _build_right(self, parent):
        self.panel = tk.Frame(parent, bg=WARNA["bg"])
        self.panel.pack(side="left", fill="both", expand=True, padx=16, pady=12)
        self._placeholder()

    def _placeholder(self):
        for w in self.panel.winfo_children():
            w.destroy()
        ph = tk.Frame(self.panel, bg=WARNA["bg"])
        ph.place(relx=0.5, rely=0.45, anchor="center")
        tk.Label(ph, text="[ SKAMAGURU ]", font=("Consolas", 28, "bold"),
                 fg=WARNA["border"], bg=WARNA["bg"]).pack()
        tk.Label(ph, text="Pilih siswa dari daftar atau ambil nilai dari IP",
                 font=("Consolas", 11), fg=WARNA["teks_dim"],
                 bg=WARNA["bg"]).pack(pady=8)
        self._btn(ph, "  Ambil dari IP Siswa",
                  self._buka_dialog_ip, WARNA["ungu"]).pack(pady=4)

    def _build_statusbar(self):
        sb = tk.Frame(self.root, bg=WARNA["header_bg"], height=26)
        sb.pack(fill="x", side="bottom"); sb.pack_propagate(False)
        self.lbl_status = tk.Label(sb, text="Siap", font=FK,
                                    fg=WARNA["teks_dim"], bg=WARNA["header_bg"])
        self.lbl_status.pack(side="left", padx=14)
        self.lbl_jam = tk.Label(sb, text="", font=FK,
                                 fg=WARNA["teks_dim"], bg=WARNA["header_bg"])
        self.lbl_jam.pack(side="right", padx=14)
        self._tick()

    def _tick(self):
        self.lbl_jam.config(text=datetime.datetime.now().strftime("%d/%m/%Y  %H:%M:%S"))
        self.root.after(1000, self._tick)

    # --- HELPERS ---
    def _btn(self, p, t, cmd, bg=None):
        return tk.Button(p, text=t, command=cmd,
                         bg=bg or WARNA["card2"], fg=WARNA["teks"],
                         font=FB, relief="flat", padx=10, pady=6,
                         cursor="hand2", activebackground=WARNA["accent"])

    def _status(self, t):
        self.lbl_status.config(text=t)

    # --- AKSI FOLDER ---
    def _buka_folder(self):
        folder = filedialog.askdirectory(title="Pilih Folder Hasil Ujian Siswa")
        if not folder:
            return
        self.folder_aktif.set(folder)
        self._muat_folder(folder)

    def _refresh(self):
        f = self.folder_aktif.get()
        if f and f != "Belum dipilih":
            self._muat_folder(f)
        else:
            messagebox.showinfo("Info", "Pilih folder terlebih dahulu.")

    def _muat_folder(self, folder):
        # Cari semua hasil_*.json
        files = glob.glob(os.path.join(folder, "**", "hasil_*.json"), recursive=True)
        files += glob.glob(os.path.join(folder, "hasil_*.json"))
        files = list(set(files))
        siswa_baru = [DataSiswa(f) for f in sorted(files)]
        # Pertahankan data dari IP
        siswa_ip   = [s for s in self.siswa_list if s.sumber_ip]
        self.siswa_list = siswa_baru + siswa_ip
        self._update_listbox()
        self._update_ringkasan()
        self._status("Dimuat " + str(len(siswa_baru)) + " file dari: " + folder)

    # --- AKSI IP ---
    def _buka_dialog_ip(self):
        DialogIP(self.root, self._tambah_dari_ip)

    def _tambah_dari_ip(self, siswa):
        # Kunci unik: IP + kode ujian (satu siswa bisa kerjakan banyak ujian)
        def kunci(s):
            return s.sumber_ip + "|" + s.kode_ujian

        for i, s in enumerate(self.siswa_list):
            if s.sumber_ip and kunci(s) == kunci(siswa):
                self.siswa_list[i] = siswa
                self._update_listbox()
                self._update_ringkasan()
                self._status("Diperbarui: " + siswa.nama_siswa + " [" + siswa.kode_ujian + "] dari " + siswa.sumber_ip)
                if (self.siswa_aktif and self.siswa_aktif.sumber_ip == siswa.sumber_ip
                        and self.siswa_aktif.kode_ujian == siswa.kode_ujian):
                    self._tampil_detail(siswa)
                return
        self.siswa_list.append(siswa)
        self._update_listbox()
        self._update_ringkasan()
        self._status("Ditambahkan: " + siswa.nama_siswa + " (" + siswa.kelas + ") [" + siswa.kode_ujian + "] dari " + siswa.sumber_ip)

    def _hapus_terpilih(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(self.siswa_list):
            s = self.siswa_list[idx]
            if messagebox.askyesno("Hapus", "Hapus data " + s.nama_siswa + "?"):
                self.siswa_list.pop(idx)
                self._update_listbox()
                self._update_ringkasan()
                self._placeholder()

    # --- UPDATE LISTBOX & RINGKASAN ---
    def _update_listbox(self):
        self.listbox.delete(0, tk.END)
        for s in self.siswa_list:
            self.listbox.insert(tk.END, s.label_listbox)
            idx = self.listbox.size() - 1
            if not s.valid:
                self.listbox.itemconfig(idx, fg=WARNA["kuning"])
            elif s.lengkap:
                self.listbox.itemconfig(idx, fg=WARNA["hijau"])
            elif s.sumber_ip:
                self.listbox.itemconfig(idx, fg=WARNA["ungu"])
            else:
                self.listbox.itemconfig(idx, fg=WARNA["merah"])
        self.lbl_jml.config(text="(" + str(len(self.siswa_list)) + ")")

    def _update_ringkasan(self):
        for w in self.f_ring.winfo_children():
            w.destroy()
        if not self.siswa_list:
            tk.Label(self.f_ring, text="Belum ada data", font=FK,
                     fg=WARNA["teks_dim"], bg=WARNA["card"]).pack()
            return
        valid   = [s for s in self.siswa_list if s.valid]
        lengkap = [s for s in valid if s.lengkap]
        ip_list = [s for s in self.siswa_list if s.sumber_ip]
        for label, val, warna in [
            ("Total Siswa",  len(self.siswa_list), WARNA["teks"]),
            ("Semua Benar",  len(lengkap),          WARNA["hijau"]),
            ("Ada Kurang",   len(valid)-len(lengkap),WARNA["merah"]),
            ("Dari IP",      len(ip_list),           WARNA["ungu"]),
        ]:
            b = tk.Frame(self.f_ring, bg=WARNA["card"])
            b.pack(fill="x", pady=1)
            tk.Label(b, text="  " + label, font=FK, fg=WARNA["teks_dim"],
                     bg=WARNA["card"], width=14, anchor="w").pack(side="left")
            tk.Label(b, text=str(val), font=FB, fg=warna,
                     bg=WARNA["card"]).pack(side="right", padx=10)

    def _pilih_siswa(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(self.siswa_list):
            self.siswa_aktif = self.siswa_list[idx]
            self._tampil_detail(self.siswa_aktif)

    # --- DETAIL SISWA ---
    def _tampil_detail(self, siswa):
        for w in self.panel.winfo_children():
            w.destroy()

        if not siswa.valid:
            tk.Label(self.panel,
                     text="Gagal membaca data:\n" + siswa.path + "\n\n" + siswa.data.get("error", ""),
                     font=FN, fg=WARNA["kuning"], bg=WARNA["bg"],
                     justify="center").pack(expand=True)
            return

        # Scrollable container
        canvas = tk.Canvas(self.panel, bg=WARNA["bg"], highlightthickness=0)
        scroll = tk.Scrollbar(self.panel, orient="vertical", command=canvas.yview)
        sf = tk.Frame(canvas, bg=WARNA["bg"])
        sf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=sf, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        f = sf
        warna_status = WARNA["hijau"] if siswa.lengkap else WARNA["merah"]

        # Header nama
        hf = tk.Frame(f, bg=WARNA["card"], pady=14, padx=20)
        hf.pack(fill="x", pady=(0, 14))
        tk.Label(hf, text=siswa.nama_siswa, font=FJ,
                 fg=warna_status, bg=WARNA["card"]).pack(anchor="w")
        info_line = siswa.kelas
        if siswa.sumber_ip:
            info_line += "   |   IP: " + siswa.sumber_ip
        elif siswa.hostname and siswa.hostname != "-":
            info_line += "   |   Host: " + siswa.hostname
        info_line += "   |   " + siswa.nama_ujian
        tk.Label(hf, text=info_line, font=FK,
                 fg=WARNA["teks_dim"], bg=WARNA["card"]).pack(anchor="w")

        # Kartu info
        kf = tk.Frame(f, bg=WARNA["bg"])
        kf.pack(fill="x", pady=(0, 14))
        waktu_pendek = siswa.waktu[:16] if len(siswa.waktu) >= 16 else siswa.waktu
        for judul, nilai, warna in [
            ("KELAS",       siswa.kelas,                              WARNA["accent2"]),
            ("UJIAN",       siswa.kode_ujian,                         WARNA["orange"]),
            ("SKOR",        str(siswa.total_benar)+"/"+str(siswa.total_soal), warna_status),
            ("WAKTU",       waktu_pendek,                              WARNA["teks"]),
            ("STATUS",      "LULUS" if siswa.lengkap else "BELUM LULUS", warna_status),
        ]:
            k = tk.Frame(kf, bg=WARNA["card2"], padx=14, pady=10)
            k.pack(side="left", fill="x", expand=True, padx=4)
            tk.Label(k, text=judul, font=FK, fg=WARNA["teks_dim"],
                     bg=WARNA["card2"]).pack(anchor="w")
            tk.Label(k, text=nilai, font=("Consolas", 12, "bold"),
                     fg=warna, bg=WARNA["card2"]).pack(anchor="w")

        # Tabel soal
        tk.Label(f, text="DETAIL SOAL", font=FB,
                 fg=WARNA["accent"], bg=WARNA["bg"]).pack(anchor="w", pady=(4, 4))
        tf = tk.Frame(f, bg=WARNA["card"])
        tf.pack(fill="x")

        # Header tabel
        hdr_t = tk.Frame(tf, bg=WARNA["card2"])
        hdr_t.pack(fill="x")
        for teks, lbr in [("No", 4), ("Deskripsi", 40), ("Nilai", 6), ("Keterangan", 36)]:
            tk.Label(hdr_t, text=teks, font=("Consolas", 9, "bold"),
                     fg=WARNA["accent"], bg=WARNA["card2"],
                     width=lbr, anchor="w", padx=8, pady=7).pack(side="left")

        for i, d in enumerate(siswa.detail):
            bg_b  = WARNA["row_alt"] if i % 2 == 0 else WARNA["card"]
            baris = tk.Frame(tf, bg=bg_b)
            baris.pack(fill="x")
            nilai = d.get("nilai", 0)
            wn    = WARNA["hijau"] if nilai == 1 else WARNA["merah"]
            iv    = "[1]" if nilai == 1 else "[0]"
            ket   = str(d.get("keterangan", ""))
            if len(ket) > 55:
                ket = ket[:52] + "..."
            tk.Label(baris, text=str(d.get("nomor", "")),
                     font=FN, fg=WARNA["teks_dim"], bg=bg_b,
                     width=4, anchor="w", padx=8, pady=6).pack(side="left")
            tk.Label(baris, text=str(d.get("deskripsi", "")),
                     font=FN, fg=WARNA["teks"], bg=bg_b,
                     width=40, anchor="w", padx=8).pack(side="left")
            tk.Label(baris, text=iv, font=FB, fg=wn,
                     bg=bg_b, width=6, anchor="w", padx=8).pack(side="left")
            tk.Label(baris, text=ket, font=FK, fg=WARNA["teks_dim"],
                     bg=bg_b, width=36, anchor="w", padx=8).pack(side="left")

        # Tombol bawah
        tk.Frame(f, bg=WARNA["bg"], height=8).pack()
        bf = tk.Frame(f, bg=WARNA["bg"])
        bf.pack(fill="x", pady=5)
        self._btn(bf, "Salin Ringkasan",
                  lambda s=siswa: self._salin(s), WARNA["card2"]).pack(side="left", padx=5)
        if siswa.sumber_ip:
            self._btn(bf, "Refresh dari IP",
                      lambda ip=siswa.sumber_ip: self._refresh_ip(ip),
                      WARNA["ungu"]).pack(side="left", padx=5)

    def _refresh_ip(self, ip):
        self._status("Mengambil ulang dari " + ip + " ...")
        def kerja():
            siswa_list, err = fetch_semua_dari_ip(ip)
            if err:
                self.root.after(0, lambda: messagebox.showerror("Gagal", err))
            else:
                for s in siswa_list:
                    self.root.after(0, lambda _s=s: self._tambah_dari_ip(_s))
                if siswa_list:
                    last = siswa_list[-1]
                    self.root.after(0, lambda: self._tampil_detail(last))
        threading.Thread(target=kerja, daemon=True).start()

    def _salin(self, siswa):
        baris = [
            "=== HASIL UJIAN ===",
            "Nama   : " + siswa.nama_siswa,
            "Kelas  : " + siswa.kelas,
            "Ujian  : " + siswa.nama_ujian + " [" + siswa.kode_ujian + "]",
            "Host   : " + (siswa.sumber_ip or siswa.hostname),
            "Waktu  : " + siswa.waktu,
            "Skor   : " + str(siswa.total_benar) + "/" + str(siswa.total_soal),
            "Status : " + ("LULUS" if siswa.lengkap else "BELUM LULUS"),
            "", "Detail:"
        ]
        for d in siswa.detail:
            n = "[1]" if d.get("nilai") == 1 else "[0]"
            baris.append("  " + n + " Soal " + str(d.get("nomor","")) + ": " + str(d.get("deskripsi","")))
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(baris))
        messagebox.showinfo("Disalin", "Ringkasan hasil ujian telah disalin ke clipboard.")

# === MAIN =======================================================================
def main():
    root = tk.Tk()
    app  = AppGuru(root)
    if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
        app.folder_aktif.set(sys.argv[1])
        app._muat_folder(sys.argv[1])
    root.mainloop()

if __name__ == "__main__":
    main()