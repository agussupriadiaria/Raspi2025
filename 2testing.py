'''
ATM SAMPAH V5 (Thread-Safe Version)
Testing
System: barcode scanner > raspi > webhook > database

Purpose:
Direct send data scan to database safely (thread-safe version)

Feature:
- Inject data dari barcode scanner ke DB langsung
- QR hasil transaksi mengarah ke page input transaction

Updated: 26 Oktober 2025
'''

from tkinter import *
import random
import time
import qrcode
from PIL import Image, ImageTk
import RPi.GPIO as gp
from datetime import datetime
from escpos.printer import Serial
import requests
import threading
from evdev import InputDevice, ecodes
import os
import sys
import signal

# --- KONFIGURASI BARCODE ---
DEVICE_PATH = '/dev/input/event4'

# --- KONFIGURASI WEBHOOK ---
WEBHOOK_URL = 'https://pilahsampahsaja.duckdns.org/barcode/webhook1.php'
WEBHOOK_URL2 = 'https://pilahsampahsaja.duckdns.org/barcode/webhook2.php'
SECRET_KEY = "GantiDenganKunciSuperRahasiaAnda123!"

# --- KONFIGURASI WORDPRESS ---
WORDPRESS_URL = "https://pilahsampahsaja.duckdns.org/"

# --- GPIO SETUP ---
gp.setwarnings(False)
gp.setmode(gp.BCM)
gp.setup(5, gp.OUT)
gp.setup(6, gp.IN, pull_up_down=gp.PUD_UP)
gp.setup(13, gp.OUT)
gp.setup(19, gp.OUT)
gp.setup(26, gp.IN, pull_up_down=gp.PUD_UP)
gp.output(5, gp.HIGH)
gp.output(13, gp.HIGH)
gp.output(19, gp.HIGH)

# --- VARIABEL GLOBAL ---
root = None
bottle = 0
poin = 0
trxID = 0
lock = threading.Lock()

# --- PEMETAAN KEYBOARD BARCODE ---
key_mapping = {
    ecodes.KEY_0: '0', ecodes.KEY_1: '1', ecodes.KEY_2: '2',
    ecodes.KEY_3: '3', ecodes.KEY_4: '4', ecodes.KEY_5: '5',
    ecodes.KEY_6: '6', ecodes.KEY_7: '7', ecodes.KEY_8: '8',
    ecodes.KEY_9: '9', ecodes.KEY_A: 'A', ecodes.KEY_B: 'B',
    ecodes.KEY_C: 'C', ecodes.KEY_D: 'D', ecodes.KEY_E: 'E',
    ecodes.KEY_F: 'F', ecodes.KEY_G: 'G', ecodes.KEY_H: 'H',
    ecodes.KEY_I: 'I', ecodes.KEY_J: 'J', ecodes.KEY_K: 'K',
    ecodes.KEY_L: 'L', ecodes.KEY_M: 'M', ecodes.KEY_N: 'N',
    ecodes.KEY_O: 'O', ecodes.KEY_P: 'P', ecodes.KEY_Q: 'Q',
    ecodes.KEY_R: 'R', ecodes.KEY_S: 'S', ecodes.KEY_T: 'T',
    ecodes.KEY_U: 'U', ecodes.KEY_V: 'V', ecodes.KEY_W: 'W',
    ecodes.KEY_X: 'X', ecodes.KEY_Y: 'Y', ecodes.KEY_Z: 'Z',
    ecodes.KEY_ENTER: 'ENTER', ecodes.KEY_KPENTER: 'ENTER'
}

# --- DATA BARCODE ---
barcode_values = {
    "8994096222069": {"value": 50, "size": "Small"}, 
    "4902430874267": {"value": 50, "size": "Small"},
    "8997022362389": {"value": 75, "size": "Medium"},
    "8999999540159": {"value": 100, "size": "Big"}
}

# --- UPDATE WAKTU ---
def updateTime():
    hours = time.strftime("%H")
    minutes = time.strftime("%M")
    seconds = time.strftime("%S")
    time_text = f"{hours}:{minutes}:{seconds}"
    timeStamp.config(text=time_text)
    timeStamp.after(1000, updateTime)

# --- UPDATE TANGGAL ---
def updateDate():
    tanggal = time.strftime("%d-%m-%Y")
    dateStamp.config(text=tanggal)
    dateStamp.after(86400000, updateDate)

# --- CETAK STRUK ---
def thermalPrinterX():
    global bottle, poin, trxID
    try:
        p = Serial(devfile='/dev/serial0', baudrate=9600, bytesize=8, parity='N',
                   stopbits=1, timeout=1.00, dsrdtr=True)
        p.set(font="a", height=1, align="center", bold=True)
        p.text("ATM SAMPAH\nPilah Sampah\n\n")
        p.text(f"Jumlah Botol: {bottle} pcs\n")
        p.text(f"Total Poin: {poin}\n\n")
        p.text(f"Trx ID: {trxID}\n")
        p.text(datetime.now().strftime("%d-%m-%Y %H:%M") + "\n")
        p.text("Terima kasih\n\n\n")
        p.close()
    except Exception as e:
        print("Gagal print:", e)

# --- FUNGSI WEBHOOK 1 ---
def send_webhook(barcode_data):
    global poin, bottle

    item = barcode_values.get(barcode_data)
    with lock:
        if item:
            poin += item["value"]
            bottle += 1
        else:
            item = {"value": 0, "size": "unregistered"}

    # update GUI aman via main thread
    root.after(0, lambda: update_labels(item, barcode_data))

    payload = {
        "barcode": barcode_data,
        "ukuran": item["size"],
        "nominal": item["value"],
        "secret_key": SECRET_KEY
    }

    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=5)
        print("→ Status (Webhook 1):", r.status_code)
    except requests.exceptions.RequestException as e:
        print("🚨 Error request (Webhook 1):", e)

# --- UPDATE LABEL GUI ---
def update_labels(item, barcode_data):
    parameterLabel3.config(text=str(poin))
    jumlahLabel.config(text=str(bottle))
    ukuranLabel.config(text=item["size"])
    nominalLabel.config(text=str(item["value"]))
    barcodeLabel.config(text=barcode_data)

# --- FUNGSI WEBHOOK 2 ---
def send_webhook2():
    global poin, trxID
    payload = {
        "trxid": trxID,
        "poin": poin,
        "secret_key": SECRET_KEY
    }
    try:
        r = requests.post(WEBHOOK_URL2, json=payload, timeout=5)
        print("→ Status (Webhook 2):", r.status_code)
    except requests.exceptions.RequestException as e:
        print("🚨 Error request (Webhook 2):", e)

# --- DETECT BARCODE SCANNER ---
def barcode_listener():
    if not os.path.exists(DEVICE_PATH):
        print("Scanner tidak ditemukan.")
        return
    dev = InputDevice(DEVICE_PATH)
    current_barcode = ""
    for event in dev.read_loop():
        if event.type == ecodes.EV_KEY and event.value == 1:
            key_code = event.code
            if key_code in [ecodes.KEY_ENTER, ecodes.KEY_KPENTER]:
                if current_barcode:
                    send_webhook(current_barcode)
                    current_barcode = ""
            elif key_code in key_mapping:
                current_barcode += key_mapping[key_code]
'''
# --- HALAMAN QR CODE (SATU VERSI SAJA) ---
def showQRCodePage():
    global root, trxID, poin
    for widget in root.winfo_children():
        widget.destroy()
    root.config(bg="white")

    try:
        qr_url = f"{WORDPRESS_URL}transactions/?number={trxID}&date={datetime.now().strftime('%Y-%m-%d')}"
        qr = qrcode.make(qr_url)
        qr.save("/tmp/qr.png")
        img = Image.open("/tmp/qr.png").resize((250, 250))
        qr_img = ImageTk.PhotoImage(img)
    except Exception as e:
        print("Gagal membuat QR:", e)
        return

    Label(root, text="Scan QR Code ini", font=("Helvetica", 16, "bold"), bg="white").pack(pady=20)
    Label(root, image=qr_img, bg="white").pack(pady=10)
    Label(root, text=f"Trx ID: {trxID}", font=("Helvetica", 12), bg="white").pack(pady=10)
    Label(root, text=f"Poin: {poin}", font=("Helvetica", 12), bg="white").pack(pady=10)
    Label(root, text="Arahkan kamera HP Anda ke QR ini", font=("Helvetica", 10), bg="white").pack(pady=10)

    Button(
        root, text="⬅ Kembali", font=("Helvetica", 12, "bold"),
        bg="lightblue", width=12, height=2, command=reloadMainPage
    ).pack(pady=25)

    root.qr_img = qr_img
'''
def showQRCodePage():
    global qr_img, qr_label, root, trxID, poin

    # Kosongkan semua widget lama
    for widget in root.winfo_children():
        widget.destroy()

    # Tampilkan QR code
    qr_label = Label(root, image=root.qr_img, bg="white")
    qr_label.pack(pady=30)

    Label(
        root,
        text="Scan QR Code ini menggunakan aplikasi di ponsel Anda",
        font=("Helvetica", 14, "bold"),
        bg="white"
    ).pack(pady=10)

    # Tombol kembali (harus dipanggil di frame ini)
    Button(
        root, text="⬅ Kembali", font=("Helvetica", 12, "bold"),
        bg="lightblue", width=12, height=2, command=reloadMainPage
    ).pack(pady=25)

# --- RESET DAN CETAK STRUK ---
def resetCounter():
    thermalPrinterX()
    send_webhook2()
    showQRCodePage()

# --- HALAMAN UTAMA ---
def mainPage():
    global root, parameterLabel3, jumlahLabel, ukuranLabel, nominalLabel, barcodeLabel, trxIDLabel
    global poin, bottle, trxID, timeStamp, dateStamp

    for widget in root.winfo_children():
        widget.destroy()

    root.config(bg="white")
    root.geometry("800x500")
    root.title("ATM Sampah - PilahSampah")

    titleLabel = Label(root, text="PilahSampah", font=("Helvetica",18,"bold"), bg="white")
    titleLabel.place(relx=0.5, rely=0.1, anchor=CENTER)

    mainFrame = Frame(root, bg="white", bd=10, highlightbackground="green", highlightthickness=5)
    mainFrame.place(relx=0.025, rely=0.15, relwidth=0.95, relheight=0.80)

    # --- STAMP FRAME ---
    stampFrame = Frame (mainFrame,bg="white",width=400, height=100)
    stampFrame.place(x=10, y=10)

    Label(stampFrame, text="Waktu   ", font=("Helvetica",10, "bold"), bg="white").place(x=10, y=1)
    Label(stampFrame, text="Tanggal ", font=("Helvetica",10, "bold"), bg="white").place(x=10, y=30)

    timeStamp = Label(stampFrame, text="00:00:00",font=("Helvetica",10, "bold"), bg="white")
    timeStamp.place(x=100, y=1)
    dateStamp = Label(stampFrame, text="dd/mm/yy",font=("Helvetica",10, "bold"), bg="white")
    dateStamp.place(x=100, y=30)

    Label(mainFrame, text="[PilahSampah - Malang]", font=("Courier",10, "bold"), bg="white").place(x=540, y=10)

    # --- PARAMETER FRAME ---
    parameterFrame = Frame(mainFrame, bg="white", width=350, height=200,highlightbackground="blue", highlightthickness=5)
    parameterFrame.place(x=10, y=75)

    Label(parameterFrame, text="TOTAL POIN", font=("Helvetica",15,"bold"), bg="white").place(x=85, y=10)
    parameterLabel3 = Label(parameterFrame, text=str(poin), font=("Helvetica",30,"bold"), bg="white")
    parameterLabel3.place(x=140, y=80)

    transaksiFrame = Frame(mainFrame, bg="white", width=350, height=200, highlightbackground="red", highlightthickness=5)
    transaksiFrame.place(x=370, y=75)

    Label(transaksiFrame, text="DATA", font=("Helvetica",15,"bold"), bg="white").place(x=135, y=10)
    Label(transaksiFrame, text="Trx ID", font=("Helvetica",10,"bold"), bg="white").place(x=50, y=50)
    Label(transaksiFrame, text="Jumlah", font=("Helvetica",10,"bold"), bg="white").place(x=50, y=75)
    Label(transaksiFrame, text="Ukuran", font=("Helvetica",10,"bold"), bg="white").place(x=50, y=100)
    Label(transaksiFrame, text="Poin", font=("Helvetica",10,"bold"), bg="white").place(x=50, y=125)
    Label(transaksiFrame, text="Barcode", font=("Helvetica",10,"bold"), bg="white").place(x=50, y=150)

    trxIDLabel = Label(transaksiFrame, text=str(trxID), font=("Helvetica",10,"bold"), bg="white")
    trxIDLabel.place(x=170, y=50)
    jumlahLabel = Label(transaksiFrame, text=str(bottle), font=("Helvetica",10,"bold"), bg="white")
    jumlahLabel.place(x=170, y=75)
    ukuranLabel = Label(transaksiFrame, text="-", font=("Helvetica",10,"bold"), bg="white")
    ukuranLabel.place(x=170, y=100)
    nominalLabel = Label(transaksiFrame, text="0", font=("Helvetica",10,"bold"), bg="white")
    nominalLabel.place(x=210, y=125)
    barcodeLabel = Label(transaksiFrame, text="-", font=("Helvetica",10,"bold"), bg="white")
    barcodeLabel.place(x=170, y=150)

    Button(mainFrame, text="Cetak Struk", font=("Helvetica",10,"bold"), bg="green", fg="white", width=10, height=3, command=resetCounter).place(x=55, y=290)
    Button(mainFrame, text="Scan Ulang", font=("Helvetica",10,"bold"), bg="yellow", fg="black", width=10, height=3, command=barcodeScanner).place(x=195, y=290)

    updateTime()
    updateDate()

# --- GPIO SCANNER RESTART ---
def barcodeScanner():
    gp.output(13, gp.LOW)
    time.sleep(2)
    gp.output(13, gp.HIGH)

# --- RESET VARIABLE DAN KE HALAMAN UTAMA ---
def reloadMainPage():
    global poin, bottle, trxID
    with lock:
        poin = 0
        bottle = 0
        trxID = random.randint(10**13, 10**14 - 1)
    mainPage()

# --- CLEANUP DATA WHEN APP CLOSED ---
def closeWindow():
    gp.cleanup()
    try:
        root.destroy()
    except:
        pass

# --- MAIN PROGRAM ---
def main():
    global root, trxID
    signal.signal(signal.SIGINT, lambda s, f: sys.exit())
    root = Tk()

    # trxID diinisialisasi lebih awal
    trxID = random.randint(10**13, 10**14 - 1)
    mainPage()

    # Mulai thread listener
    t = threading.Thread(target=barcode_listener, daemon=True)
    t.start()

    root.protocol("WM_DELETE_WINDOW", closeWindow)
    root.mainloop()

if __name__ == "__main__":
    main()
