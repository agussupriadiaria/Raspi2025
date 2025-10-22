'''
ATM SAMPAH V5
System: barcode scanner > raspi > webhook > database

Perpose:
Direct send data scan to database

Createde: 22 Oktober 2025
Modified: 23 Oktober 2025

'''


# Import library ================
from tkinter import *
import serial.tools.list_ports
import threading
import time
import sys
import signal
import RPi.GPIO as gp
import random
import os
import requests
from evdev import InputDevice, ecodes
from escpos.printer import Serial
from datetime import datetime

# --- PENGATURAN ---
DEVICE_PATH = '/dev/input/event4'
WEBHOOK_URL = 'https://pilahsampahsaja.duckdns.org/barcode/webhook.php'
SECRET_KEY = "GantiDenganKunciSuperRahasiaAnda123!"

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

nomor = 1  # variabel nomor urut

# Set GPIO pin =====================
gp.setwarnings(False)
gp.setmode(gp.BCM)
gp.setup(5, gp.OUT)
gp.output(5, gp.HIGH)
gp.setup(6, gp.IN, pull_up_down=gp.PUD_UP)
gp.setup(13, gp.OUT)
gp.output(13, gp.HIGH)
gp.setup(19, gp.OUT)
gp.output(19, gp.HIGH)
gp.setup(26, gp.IN, pull_up_down=gp.PUD_UP)

def signal_handler(signum, frame):
    sys.exit()
signal.signal(signal.SIGINT, signal_handler)

# --- FUNGSI LOG TERMINAL ---
def add_barcode_to_list(source, message):
    print(f"[{source}] {message}")

# --- GUI UTAMA ---
def mainPage():
    global root, timeStamp, dateStamp, barcodeLabel, jumlahLabel, ukuranLabel, nominalLabel
    global bottle, saldo, parameterLabel3, userIDLabel

    root = Tk()
    root.geometry("800x500")
    root.title("Atm Sampah - PilahSampah")
    root.config(bg="white")

    titleLabel = Label(root, text="PilahSampah", font=("Helvetica",18, "bold"), bg="white")
    titleLabel.place(relx=0.5, rely=0.1,anchor=CENTER)

    mainFrame = Frame(root, bg="white", bd=10, highlightbackground="green", highlightthickness=5)
    mainFrame.place(relx=0.025, rely=0.15, relwidth=0.95, relheight=0.80)

    stampFrame = Frame (mainFrame,bg="white",width=400, height=100)
    stampFrame.place(x=10, y=10)

    Label(stampFrame, text="Waktu   ", font=("Helvetica",10, "bold"), bg="white").place(x=10, y=1)
    Label(stampFrame, text="Tanggal ", font=("Helvetica",10, "bold"), bg="white").place(x=10, y=30)

    timeStamp = Label(stampFrame, text="00:00:00",font=("Helvetica",10, "bold"), bg="white")
    timeStamp.place(x=100, y=1)
    dateStamp = Label(stampFrame, text="dd/mm/yy",font=("Helvetica",10, "bold"), bg="white")
    dateStamp.place(x=100, y=30)

    Label(mainFrame, text="[PilahSampah - Malang]", font=("Courier",10, "bold"), bg="white").place(x=540, y=10)

    parameterFrame = Frame(mainFrame, bg="white",width=350, height=200, highlightbackground="blue", highlightthickness=5 )
    parameterFrame.place(x=10, y=75)

    Label(parameterFrame,bg="white", text="TOTAL SALDO", font=("Helvetica", 15, "bold")).place(x=85, y=10)
    Label(parameterFrame, text="Rp", font=("Helvetica", 30, "bold"), bg="white").place(x=65, y=80)
    parameterLabel3 = Label(parameterFrame, text="9999", font=("Helvetica", 30, "bold"), bg="white")
    parameterLabel3.place(x=140, y=80)

    transaksiFrame = Frame(mainFrame, bg="white",width=350, height=200, highlightbackground="red", highlightthickness=5 )
    transaksiFrame.place(x=370, y=75)

    Label(transaksiFrame, bg="white", text="DATA", font=("Helvetica", 15, "bold")).place(x=135, y=10)
    Label(transaksiFrame, bg="white", text="TID   ", font=("Helvetica", 10, "bold")).place(x=50, y=50)
    Label(transaksiFrame, bg="white", text="Jumlah    ", font=("Helvetica", 10, "bold")).place(x=50, y=75)
    Label(transaksiFrame, bg="white", text="Ukuran   ", font=("Helvetica", 10, "bold")).place(x=50, y=100)
    Label(transaksiFrame, bg="white", text="Nominal            Rp", font=("Helvetica", 10, "bold")).place(x=50, y=125)
    Label(transaksiFrame, bg="white", text="Barcode  ", font=("Helvetica", 10, "bold")).place(x=50, y=150)

    userIDLabel = Label(transaksiFrame, bg="white", text="99999", font=("Helvetica", 10, "bold"))
    userIDLabel.place(x=170, y=50)
    jumlahLabel = Label(transaksiFrame, bg="white", text="999", font=("Helvetica", 10, "bold"))
    jumlahLabel.place(x=170, y=75)
    ukuranLabel = Label(transaksiFrame, bg="white", text="Medium", font=("Helvetica", 10, "bold"))
    ukuranLabel.place(x=170, y=100)
    nominalLabel = Label(transaksiFrame, bg="white", text="999", font=("Helvetica", 10, "bold"))
    nominalLabel.place(x=210, y=125)
    barcodeLabel = Label(transaksiFrame, bg="white", text="9999999999999", font=("Helvetica", 10, "bold"))
    barcodeLabel.place(x=170, y=150)

    Button(mainFrame,text="Cetak Struk", font=("Helvetica",10, "bold"), bg="green",fg = "blue", width=10, height=3, command=resetCounter).place(x=55, y=290)
    Button(mainFrame,text="Scan Ulang", font=("Helvetica",10, "bold"), bg="yellow",fg = "blue", width=10, height=3, command=barcodeScanner).place(x=195, y=290)

    Label(mainFrame, text="Terima Kasih Sudah Ikut", font=("Helvetica", 10, "bold"),bg="white").place(x=457, y=300)
    Label(mainFrame, text="Menyelamatkan Lingkungan", font=("Helvetica", 10, "bold"),bg="white").place(x=445, y=325)

    bottle = 0
    saldo = 0

    updateTime()
    updateDate()
    userIDNum()

# --- FUNGSI KIRIM WEBHOOK + UPDATE LABEL BARCODE ---
def send_webhook(barcode_data):
    # tampilkan ke GUI
    barcodeLabel.config(text=barcode_data)
    root.update_idletasks()

    payload = {
        "barcode": barcode_data,
        "secret_key": SECRET_KEY
    }

    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code == 200:
            add_barcode_to_list("WEBHOOK", f"✅ Kirim sukses: {barcode_data}")
        else:
            add_barcode_to_list("WEBHOOK", f"❌ Gagal ({response.status_code})")
    except Exception as e:
        add_barcode_to_list("WEBHOOK", f"⚠️ Error koneksi: {e}")

# --- LOOP PEMINDAI BARCODE ---
def barcode_listener():
    if not os.path.exists(DEVICE_PATH):
        add_barcode_to_list("SYSTEM", f"❌ Device tidak ditemukan di {DEVICE_PATH}")
        return

    try:
        dev = InputDevice(DEVICE_PATH)
        add_barcode_to_list("SYSTEM", f"Scanner aktif: {dev.name}")

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
    except PermissionError:
        add_barcode_to_list("SYSTEM", "⚠️ Izin ditolak (jalankan pakai sudo)")
    except Exception as e:
        add_barcode_to_list("SYSTEM", f"⚠️ Error: {e}")

def userIDNum():
    global userID
    userID = random.randrange(10000, 100000)
    userIDLabel["text"] = userID

def bottleCounter():
    global bottle
    bottle += 1
    parameterLabel3["text"] = saldo
    jumlahLabel["text"] = bottle

def resetCounter():
    global bottle, saldo
    thermalPrinterX()
    bottle = 0
    saldo = 0
    parameterLabel3["text"] = saldo
    nominalLabel["text"] = saldo
    jumlahLabel["text"] = bottle
    ukuranLabel["text"] = "-"
    barcodeLabel["text"] = "0"
    userIDNum()
    add_barcode_to_list("RESET", "Data direset ke awal.")

def thermalPrinterX():
    try:
        p = Serial(devfile='/dev/serial0', baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=1.00, dsrdtr=True)
        p.set(font="a", height=1, align="center", bold=True, double_height=False)
        p.text("ATM SAMPAH\nPilah Sampah\n\n")
        p.text(f"Jumlah Botol: {bottle} Pcs\n")
        p.text(f"Total Saldo: Rp {saldo}\n\n")
        p.text(f"User ID: {userID}\n")
        current_date = datetime.now().strftime("%d-%m-%Y")
        p.text(current_date + "\n")
        p.text("Terima kasih\n\n\n")
        add_barcode_to_list("PRINTER", "🖨️ Struk berhasil dicetak.")
    except Exception as e:
        add_barcode_to_list("PRINTER", f"⚠️ Gagal print: {e}")

def updateTime():
    hours = time.strftime("%H")
    minutes = time.strftime("%M")
    seconds = time.strftime("%S")
    timeStamp.config(text=f"{hours}:{minutes}:{seconds}")
    timeStamp.after(1000, updateTime)

def updateDate():
    tanggal = time.strftime("%d")
    bulan = time.strftime("%m")
    tahun = time.strftime("%Y")
    dateStamp.config(text=f"{tanggal}-{bulan}-{tahun}")
    dateStamp.after(86400000, updateDate)

def barcodeScanner():
    add_barcode_to_list("SCANNER", "Barcode On")
    gp.output(13, gp.LOW)
    time.sleep(4)
    gp.output(13, gp.HIGH)

def pinOutArduino():
    add_barcode_to_list("ARDUINO", "Pin aktif LOW -> HIGH")
    gp.output(19, gp.LOW)
    time.sleep(2)
    gp.output(19, gp.HIGH)

def inSensor():
    if gp.input(26) == gp.LOW:
        time.sleep(3)
        add_barcode_to_list("SENSOR", "Bottle In")
        barcodeScanner()
    root.after(50, inSensor)

def fullSensor():
    if gp.input(6) == gp.LOW:
        gp.output(5, gp.HIGH)
    else:
        gp.output(5, gp.LOW)
    root.after(50, fullSensor)

def closeWindow():
    global root, serialData
    serialData = False
    gp.cleanup()
    root.destroy()

# --- THREAD PEMINDAI BARCODE ---
t = threading.Thread(target=barcode_listener, daemon=True)
t.start()

# --- MAIN PROGRAM ---
mainPage()
root.after(50, inSensor)
root.after(50, fullSensor)
root.protocol("WM_DELETE_WINDOW", closeWindow)
root.mainloop()
