'''
ATM SAMPAH V5
TESTING
System: barcode scanner > raspi > webhook > database

Perpose:
Direct send data scan to database

Feature:
- inject data dari barcode scanner ke db langsung
- ada QR hasil transaksi yang bisa discan dan mengarahkan ke page input transaction

Createde: 22 Oktober 2025
Modified: 23 Oktober 2025

Issue:
- Flow QR belum sesuai dengan ekspektasi
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

# --- KONFIGURASI BARCODE FINAL ---
WORDPRESS_URL = "https://pilahsampahsaja.duckdns.org/"  # ganti dgn situs WordPress kamu

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
saldo = 0
trxID = 0

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

# --- DATA BARCODE SEDERHANA ---
barcode_values = {
    "8994096222069": {"value": 50, "size": "Small"}, #cuttonbud
    "4902430874267": {"value": 50, "size": "Small"}, #gilete
    "8997022362389": {"value": 75, "size": "Medium"}, #masker
    "8999999540159": {"value": 100, "size": "Big"} #vaseline
    # contoh unregistered: 8996001600269 le minarale
}

# --- CETAK STRUK ---
def thermalPrinterX():
    global bottle, saldo, trxID
    try:
        p = Serial(devfile='/dev/serial0', baudrate=9600, bytesize=8, parity='N',
                   stopbits=1, timeout=1.00, dsrdtr=True)
        p.set(font="a", height=1, align="center", bold=True)
        p.text("ATM SAMPAH\nPilah Sampah\n\n")
        p.text(f"Jumlah Botol: {bottle} pcs\n")
        p.text(f"Total Saldo: Rp {saldo}\n\n")
        p.text(f"Trx ID: {trxID}\n")
        p.text(datetime.now().strftime("%d-%m-%Y %H:%M") + "\n")
        p.text("Terima kasih\n\n\n")
    except Exception as e:
        print("Gagal print:", e)

# --- FUNGSI SCAN BARCODE ---
def send_webhook(barcode_data):
    global saldo, bottle
    item = barcode_values.get(barcode_data)
    if item:
        saldo += item["value"]
        bottle += 1
        parameterLabel3.config(text=str(saldo))
        jumlahLabel.config(text=str(bottle))
        ukuranLabel.config(text=item["size"])
        nominalLabel.config(text=str(item["value"]))
        barcodeLabel.config(text=barcode_data)
        print("barcodenya:", barcode_data)
    else:
        barcodeLabel.config(text="unregistered")

    payload = {
        "barcode": barcode_data,
        "ukuran": item["size"] if item else "unregistered",
        "nominal": item["value"] if item else 0,
        "secret_key": SECRET_KEY
    }
    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=5)
        print("→ Status:", r.status_code)
        print("→ Response:", r.text)
    except Exception as e:
        print("🚨 Error request:", e)
'''
    try:
        requests.post(WEBHOOK_URL, json=payload, timeout=5)
        print("data payload: ", payload)
    except:
        pass
'''
# --- FUNGSI SCAN BARCODE ---
def send_webhook2():
    global saldo, trxID
    payload = {
        "trxid": trxID,
        "saldo": saldo,
        "secret_key": SECRET_KEY
    }
    try:
        requests.post(WEBHOOK_URL2, json=payload, timeout=5)
    except:
        pass


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


# --- HALAMAN QR CODE ---
def showQRCodePage():
    global root, trxID, saldo, bottle
    for widget in root.winfo_children():
        widget.destroy()

    root.config(bg="white")
# --- INPUT PARAMETER URL HERE ---
    qr_url = f"{WORDPRESS_URL}transactions/?number={trxID}&date={datetime.now().strftime('%Y-%m-%d')}"
    qr = qrcode.make(qr_url)
    qr.save("/tmp/qr.png")
    img = Image.open("/tmp/qr.png").resize((250, 250))
    qr_img = ImageTk.PhotoImage(img)

    Label(root, text="Scan QR Code ini", font=("Helvetica", 16, "bold"), bg="white").pack(pady=20)
    Label(root, image=qr_img, bg="white").pack(pady=10)
    Label(root, text=f"Trx ID: {trxID}", font=("Helvetica", 12), bg="white").pack(pady=10)
    Label(root, text="Arahkan kamera HP Anda ke QR ini", font=("Helvetica", 10), bg="white").pack(pady=10)

    Button(root, text="⬅ Kembali", font=("Helvetica", 12, "bold"), bg="lightblue", width=12, height=2, command=reloadMainPage).pack(pady=25)
    root.qr_img = qr_img  # simpan agar tidak hilang dari memori

'''
def showQRCodePage():
    global root, trxID, saldo, bottle
    for widget in root.winfo_children():
        widget.destroy()

    root.config(bg="white")

    # --- INPUT PARAMETER URL HERE ---
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
    Label(root, text="Arahkan kamera HP Anda ke QR ini", font=("Helvetica", 10), bg="white").pack(pady=10)

    Button(
        root, text="⬅ Kembali", font=("Helvetica", 12, "bold"),
        bg="lightblue", width=12, height=2, command=reloadMainPage
    ).pack(pady=25)

    root.qr_img = qr_img  # simpan agar tidak hilang dari memori
'''
# --- RESET DAN CETAK STRUK ---
def resetCounter():
    global saldo, bottle, trxID
    thermalPrinterX()
    send_webhook2()
    showQRCodePage()

# --- HALAMAN UTAMA ---
def mainPage():
    global root, parameterLabel3, jumlahLabel, ukuranLabel, nominalLabel, barcodeLabel, trxIDLabel
    global saldo, bottle, trxID

    for widget in root.winfo_children():
        widget.destroy()

    root.config(bg="white")
    root.geometry("800x500")
    root.title("ATM Sampah - PilahSampah")

    titleLabel = Label(root, text="PilahSampah", font=("Helvetica",18,"bold"), bg="white")
    titleLabel.place(relx=0.5, rely=0.1, anchor=CENTER)

    mainFrame = Frame(root, bg="white", bd=10, highlightbackground="green", highlightthickness=5)
    mainFrame.place(relx=0.025, rely=0.15, relwidth=0.95, relheight=0.80)

    parameterFrame = Frame(mainFrame, bg="white", width=350, height=200,highlightbackground="blue", highlightthickness=5)
    parameterFrame.place(x=10, y=75)

    Label(parameterFrame, text="TOTAL SALDO", font=("Helvetica",15,"bold"), bg="white").place(x=85, y=10)
    Label(parameterFrame, text="Rp", font=("Helvetica",30,"bold"), bg="white").place(x=65, y=80)
    parameterLabel3 = Label(parameterFrame, text=str(saldo), font=("Helvetica",30,"bold"), bg="white")
    parameterLabel3.place(x=140, y=80)

    transaksiFrame = Frame(mainFrame, bg="white", width=350, height=200, highlightbackground="red", highlightthickness=5)
    transaksiFrame.place(x=370, y=75)

    Label(transaksiFrame, text="DATA", font=("Helvetica",15,"bold"), bg="white").place(x=135, y=10)
    Label(transaksiFrame, text="Trx ID", font=("Helvetica",10,"bold"), bg="white").place(x=50, y=50)
    Label(transaksiFrame, text="Jumlah", font=("Helvetica",10,"bold"), bg="white").place(x=50, y=75)
    Label(transaksiFrame, text="Ukuran", font=("Helvetica",10,"bold"), bg="white").place(x=50, y=100)
    Label(transaksiFrame, text="Nominal Rp", font=("Helvetica",10,"bold"), bg="white").place(x=50, y=125)
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

# --- RANDOM TRX ID ---
    #trxID = random.randrange(10000, 99999)
    '''
    import string
    trxID = ''.join(random.choices(string.digits, k=14))
    trxIDLabel.config(text=str(trxID))
    '''
    trxID = random.randint(10**13, 10**14 - 1)
    trxIDLabel.config(text=str(trxID))

# --- GPIO UNTUK MENJALANKAN ULANG BARCODE SCANNER ---
def barcodeScanner():
    gp.output(13, gp.LOW)
    time.sleep(2)
    gp.output(13, gp.HIGH)

# --- RESET VARIABLE ---
def reloadMainPage():
    global saldo, bottle
    saldo = 0
    bottle = 0
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
    global root
    signal.signal(signal.SIGINT, lambda s, f: sys.exit())
    root = Tk()
    mainPage()

    t = threading.Thread(target=barcode_listener, daemon=True)
    t.start()

    root.protocol("WM_DELETE_WINDOW", closeWindow)
    root.mainloop()

if __name__ == "__main__":
    main()
