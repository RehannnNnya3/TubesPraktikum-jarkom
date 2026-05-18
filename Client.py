import socket
import threading
import os
import sys

def menerima_pesan_dan_file(client_socket):
    while True:
        try:
            pesan = client_socket.recv(4096).decode('utf-8')
            if not pesan:
                break
            
            # --- LOGIKA PENANGANAN FILE MASUK OTOMATIS ---
            if pesan.startswith("INCOMING_FILE_"):
                bagian = pesan.split(" ")
                tipe = bagian[0] # UNICAST / BROADCAST / MULTICAST
                pengirim = bagian[1]
                
                if tipe == "INCOMING_FILE_MULTICAST":
                    grup = bagian[2]
                    nama_file = bagian[3]
                    print(f"\n[!] Menerima File Grup '{grup}' dari {pengirim}: {nama_file}")
                else:
                    nama_file = bagian[2]
                    print(f"\n[!] Menerima File Pribadi/Siaran dari {pengirim}: {nama_file}")
                
                # Konfirmasi ke server siap menerima detail file
                client_socket.send("READY".encode('utf-8'))
                ukuran_file = int(client_socket.recv(1024).decode('utf-8'))
                
                client_socket.send("SEND".encode('utf-8'))
                
                # Proses download file biner
                data_file = b""
                terbaca = 0
                while terbaca < ukuran_file:
                    chunk = client_socket.recv(4096)
                    data_file += chunk
                    terbaca += len(chunk)
                
                # Simpan file di folder tempat script dijalankan 
                nama_simpan = "downloaded_" + nama_file
                with open(nama_simpan, "wb") as f:
                    f.write(data_file)
                print(f"[✓] File sukses diunduh dan disimpan sebagai: {nama_simpan}")
                print("> ", end="", flush=True)

            elif pesan == "INPUT_NAME":
                pass # Ditangani di thread utama saat login
            else:
                print(pesan, end="", flush=True)
        except:
            print("\n[-] Koneksi terputus dari server.")
            break

# Koneksi Utama ke Server
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('127.0.0.1', 6000))

# Thread penerima diaktifkan secara background
thread_penerima = threading.Thread(target=menerima_pesan_dan_file, args=(client,))
thread_penerima.daemon = True

# Proses pendaftaran nama user
sinyal = client.recv(1024).decode('utf-8')
if sinyal == "INPUT_NAME":
    nama = input("Masukkan Username Anda: ")
    client.send(nama.encode('utf-8'))
    
    respon = client.recv(1024).decode('utf-8')
    if respon == "SUCCESS_CONNECT":
        print(f"[+] Berhasil Masuk Aplikasi Chatting Jarkom!")
        print("=====================================================")
        print("Panduan Perintah:")
        print("1. Teks Broadcast    : /broadcast [pesan]")
        print("2. File Broadcast    : /broadcastfile [nama_file_kamu.ekstensi]")
        print("3. Teks Unicast      : /unicast [nama_tujuan] [pesan]")
        print("4. File Unicast      : /unicastfile [nama_tujuan] [nama_file_kamu.ekstensi]")
        print("5. Gabung Grup       : /join [nama_grup]")
        print("6. Teks Multicast    : /multicast [nama_grup] [pesan]")
        print("7. File Multicast    : /multicastfile [nama_grup] [nama_file_kamu.ekstensi]")
        print("=====================================================\n")
        thread_penerima.start()
    else:
        print("[-] Nama sudah digunakan atau tidak valid. Keluar.")
        client.close()
        sys.exit()

# Loop Utama pengiriman input perintah pengguna
while True:
    try:
        teks_input = input("> ").strip()
        if not teks_input:
            continue
        if teks_input.lower() == 'exit':
            break

        bagian = teks_input.split(" ", 2)
        command = bagian[0]

        # Logika khusus Client untuk mengirim file (baca biner file di laptop pengirim) 
        if command in ["/broadcastfile", "/unicastfile", "/multicastfile"]:
            # Cari letak parameter nama file lokal
            nama_file_lokal = bagian[1] if command == "/broadcastfile" else bagian[2]
            
            if not os.path.exists(nama_file_lokal):
                print(f"[-] File '{nama_file_lokal}' tidak ditemukan di foldermu.")
                continue
            
            # Beritahu server akan mengirim instruksi file
            client.send(teks_input.encode('utf-8'))
            
            # Alur jabat tangan (handshake) proses pengiriman file biner
            if client.recv(1024).decode('utf-8') == "READY_TO_RECEIVE_FILE":
                ukuran_file = os.path.getsize(nama_file_lokal)
                client.send(str(ukuran_file).encode('utf-8'))
                
                if client.recv(1024).decode('utf-8') == "SEND_DATA_NOW":
                    with open(nama_file_lokal, "rb") as f:
                        data_biner = f.read()
                        client.sendall(data_biner)
                    print(f"[✓] File '{nama_file_lokal}' berhasil dikirim ke server!")
            
        else:
            # Jika hanya mengirim teks biasa, langsung teruskan ke server
            client.send(teks_input.encode('utf-8'))

    except KeyboardInterrupt:
        break

client.close()
