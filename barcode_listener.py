#!/usr/bin/env python3

import os
from evdev import InputDevice, categorize, ecodes
import requests
import time

# --- PENGATURAN ---
# GANTI JALUR INI dengan event device yang Anda temukan di Langkah 2.2
DEVICE_PATH = '/dev/input/event4' 
# GANTI URL INI dengan alamat webhook PHP Anda
WEBHOOK_URL = 'https://pilahsampahsaja.duckdns.org/barcode/webhook.php'
# GANTI KUNCI INI dengan KUNCI RAHASIA yang sama di kode PHP (Langkah 1.2)
SECRET_KEY = "GantiDenganKunciSuperRahasiaAnda123!"

# Mapping key code ke karakter (hanya untuk angka dan Enter/Return)
key_mapping = {
    ecodes.KEY_0: '0', ecodes.KEY_1: '1', ecodes.KEY_2: '2', 
    ecodes.KEY_3: '3', ecodes.KEY_4: '4', ecodes.KEY_5: '5', 
    ecodes.KEY_6: '6', ecodes.KEY_7: '7', ecodes.KEY_8: '8', 
    ecodes.KEY_9: '9', ecodes.KEY_KPENTER: 'ENTER', ecodes.KEY_ENTER: 'ENTER'
}
# Anda bisa menambahkan mapping untuk huruf dan simbol jika barcode Anda mengandung itu.

def send_webhook(barcode_data):
    """Mengirim data barcode ke Webhook dengan kunci rahasia."""
    payload = {
        "barcode": barcode_data,
        "secret_key": SECRET_KEY
    }
    
    print(f"Mengirim data: {barcode_data}")
    
    try:
        # PENTING: Gunakan HTTPS untuk keamanan!
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        
        # Cek status code dan respons dari server
        if response.status_code == 200:
            print("Pengiriman Webhook BERHASIL!")
        else:
            print(f"Pengiriman Webhook GAGAL. Status: {response.status_code}. Respon: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Terjadi error saat koneksi ke server: {e}")

def main():
    try:
        # Cek apakah device path ada
        if not os.path.exists(DEVICE_PATH):
            print(f"ERROR: Device tidak ditemukan di {DEVICE_PATH}")
            print("Silakan cek langkah 2.2 lagi.")
            return

        # Buka perangkat input
        dev = InputDevice(DEVICE_PATH)
        print(f"Scanner siap, mendengarkan input dari: {dev.name} ({DEVICE_PATH})")
        
        current_barcode = ""

        # Loop utama untuk mendengarkan event
        for event in dev.read_loop():
            # Filter hanya event "Key Up" (ketika tombol dilepas)
            if event.type == ecodes.EV_KEY and event.value == 0: 
                key_code = event.code
                
                # Cek apakah itu tombol "Enter"
                if key_code in [ecodes.KEY_ENTER, ecodes.KEY_KPENTER]:
                    if current_barcode:
                        # Barcode selesai dipindai, kirim webhook
                        send_webhook(current_barcode)
                        current_barcode = "" # Reset
                    
                # Cek apakah itu tombol dengan data barcode
                elif key_code in key_mapping:
                    current_barcode += key_mapping[key_code]
                    
    except FileNotFoundError:
        print(f"Error: Perangkat {DEVICE_PATH} tidak ditemukan.")
    except PermissionError:
        print("Error: Perlu izin sudo untuk membaca event device.")
        print("Coba jalankan dengan: sudo python3 barcode_listener.py")
    except Exception as e:
        print(f"Terjadi error: {e}")

if __name__ == '__main__':
    main()
