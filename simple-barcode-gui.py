import os
import threading
import time
from tkinter import *
from evdev import InputDevice, ecodes
import requests

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

# --- FUNGSI KIRIM WEBHOOK ---
def send_webhook(barcode_data):
    payload = {
        "barcode": barcode_data,
        "secret_key": SECRET_KEY
    }

    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"Webhook terkirim: {barcode_data}")
            add_barcode_to_list(barcode_data, "✅ Berhasil")
        else:
            print(f"Gagal kirim: {response.status_code}")
            add_barcode_to_list(barcode_data, f"❌ Gagal ({response.status_code})")
    except Exception as e:
        print(f"Error webhook: {e}")
        add_barcode_to_list(barcode_data, f"⚠️ Error koneksi")

# --- FUNGSI TAMBAH DATA KE GUI ---
def add_barcode_to_list(barcode, status):
    """Tampilkan data barcode ke GUI listbox"""
    timestamp = time.strftime("%H:%M:%S")
    listbox.insert(END, f"[{timestamp}] {barcode} {status}")
    listbox.yview(END)

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

# --- GUI TKINTER ---
root = Tk()
root.title("Barcode Scanner - PilahSampah")
root.geometry("700x400")
root.config(bg="white")

Label(root, text="ATM Sampah - Barcode Scanner", font=("Helvetica", 16, "bold"), bg="white").pack(pady=10)

frame = Frame(root, bg="white")
frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

scrollbar = Scrollbar(frame)
scrollbar.pack(side=RIGHT, fill=Y)

listbox = Listbox(frame, font=("Courier", 11), yscrollcommand=scrollbar.set, bg="#f4f4f4", fg="black")
listbox.pack(side=LEFT, fill=BOTH, expand=True)
scrollbar.config(command=listbox.yview)

Label(root, text="Tekan ENTER setelah barcode selesai discan", font=("Helvetica", 10), bg="white", fg="gray").pack(pady=5)

# --- JALANKAN PEMINDAI DI THREAD TERPISAH ---
t = threading.Thread(target=barcode_listener, daemon=True)
t.start()

root.mainloop()
