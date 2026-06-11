import socket
import threading
import os

# Menyimpan data client {nama_client: socket_client}
clients = {}
# Menyimpan data grup/multicast {nama_grup: set(nama_client)}
groups = {}

def handle_client(client_socket):
    nama_client = None
    try:
        # Pendaftaran nama client saat pertama kali connect
        client_socket.send("INPUT_NAME".encode('utf-8'))
        nama_client = client_socket.recv(1024).decode('utf-8').strip()
        
        # Validasi nama tidak boleh kembar
        if nama_client in clients or not nama_client:
            client_socket.send("ERROR_NAME_TAKEN".encode('utf-8'))
            client_socket.close()
            return
            
        clients[nama_client] = client_socket
        print(f"[*] {nama_client} berhasil terhubung.")
        client_socket.send("SUCCESS_CONNECT".encode('utf-8'))

        while True:
            # Menerima string perintah utama dari client
            data_awal = client_socket.recv(1024).decode('utf-8').strip()
            if not data_awal:
                break

            # Memecah perintah (Format: /command ... )
            bagian = data_awal.split(" ", 1)
            command = bagian[0]
            argumen = bagian[1] if len(bagian) > 1 else ""

            # =================================================================
            # 1. FITUR BROADCAST (Teks & File)
            # =================================================================
            if command == "/broadcast":
                for nama, sock in clients.items():
                    if nama != nama_client:
                        sock.send(f"[BROADCAST dari {nama_client}]: {argumen}\n> ".encode('utf-8'))

            elif command == "/broadcastfile":
                # Argumen berisi nama file asli
                nama_file = argumen
                client_socket.send("READY_TO_RECEIVE_FILE".encode('utf-8'))
                
                # Terima ukuran file terlebih dahulu
                ukuran_file = int(client_socket.recv(1024).decode('utf-8'))
                client_socket.send("SEND_DATA_NOW".encode('utf-8'))
                
                # Baca data biner file dari pengirim
                isi_file = b""
                terbaca = 0
                while terbaca < ukuran_file:
                    chunk = client_socket.recv(4096)
                    isi_file += chunk
                    terbaca += len(chunk)
                
                # Teruskan file ke semua client lain
                for nama, sock in clients.items():
                    if nama != nama_client:
                        sock.send(f"INCOMING_FILE_BROADCAST {nama_client} {nama_file}".encode('utf-8'))
                        # Tunggu client siap menerima file
                        if sock.recv(1024).decode('utf-8') == "READY":
                            sock.send(str(ukuran_file).encode('utf-8'))
                            if sock.recv(1024).decode('utf-8') == "SEND":
                                sock.sendall(isi_file)

            # =================================================================
            # 2. FITUR UNICAST (Teks & File)
            # =================================================================
            elif command == "/unicast":
                detail = argumen.split(" ", 1)
                if len(detail) >= 2:
                    tujuan, isi_pesan = detail[0], detail[1]
                    if tujuan in clients:
                        clients[tujuan].send(f"[Bisik dari {nama_client}]: {isi_pesan}\n> ".encode('utf-8'))
                    else:
                        client_socket.send(f"[-] User '{tujuan}' tidak ditemukan.\n> ".encode('utf-8'))

            elif command == "/unicastfile":
                detail = argumen.split(" ", 1)
                if len(detail) >= 2:
                    tujuan, nama_file = detail[0], detail[1]
                    if tujuan in clients:
                        client_socket.send("READY_TO_RECEIVE_FILE".encode('utf-8'))
                        
                        ukuran_file = int(client_socket.recv(1024).decode('utf-8'))
                        client_socket.send("SEND_DATA_NOW".encode('utf-8'))
                        
                        isi_file = b""
                        terbaca = 0
                        while terbaca < ukuran_file:
                            chunk = client_socket.recv(4096)
                            isi_file += chunk
                            terbaca += len(chunk)
                            
                        # Kirim ke tujuan spesifik
                        sock_tujuan = clients[tujuan]
                        sock_tujuan.send(f"INCOMING_FILE_UNICAST {nama_client} {nama_file}".encode('utf-8'))
                        if sock_tujuan.recv(1024).decode('utf-8') == "READY":
                            sock_tujuan.send(str(ukuran_file).encode('utf-8'))
                            if sock_tujuan.recv(1024).decode('utf-8') == "SEND":
                                sock_tujuan.sendall(isi_file)
                    else:
                        client_socket.send(f"[-] User '{tujuan}' tidak ditemukan.\n> ".encode('utf-8'))

            # =================================================================
            # 3. FITUR MULTICAST / GRUP (Join, Teks, & File)
            # =================================================================
            elif command == "/join":
                nama_grup = argumen
                if nama_grup not in groups:
                    groups[nama_grup] = set()
                groups[nama_grup].add(nama_client)
                client_socket.send(f"[+] Berhasil bergabung ke grup '{nama_grup}'\n> ".encode('utf-8'))
                # Beritahu anggota grup lain
                for nama in groups[nama_grup]:
                    if nama != nama_client:
                        clients[nama].send(f"[GRUP {nama_grup}]: {nama_client} bergabung.\n> ".encode('utf-8'))

            elif command == "/multicast":
                detail = argumen.split(" ", 1)
                if len(detail) >= 2:
                    grup_tujuan, isi_pesan = detail[0], detail[1]
                    if grup_tujuan in groups and nama_client in groups[grup_tujuan]:
                        for nama in groups[grup_tujuan]:
                            if nama != nama_client:
                                clients[nama].send(f"[GRUP {grup_tujuan}] {nama_client}: {isi_pesan}\n> ".encode('utf-8'))
                    else:
                        client_socket.send(f"[-] Kamu bukan anggota grup '{grup_tujuan}' atau grup tidak ada.\n> ".encode('utf-8'))

            elif command == "/multicastfile":
                detail = argumen.split(" ", 1)
                if len(detail) >= 2:
                    grup_tujuan, nama_file = detail[0], detail[1]
                    if grup_tujuan in groups and nama_client in groups[grup_tujuan]:
                        client_socket.send("READY_TO_RECEIVE_FILE".encode('utf-8'))
                        
                        ukuran_file = int(client_socket.recv(1024).decode('utf-8'))
                        client_socket.send("SEND_DATA_NOW".encode('utf-8'))
                        
                        isi_file = b""
                        terbaca = 0
                        while terbaca < ukuran_file:
                            chunk = client_socket.recv(4096)
                            isi_file += chunk
                            terbaca += len(chunk)
                            
                        # Sebarkan ke seluruh anggota grup tersebut
                        for nama in groups[grup_tujuan]:
                            if nama != nama_client:
                                sock_grup = clients[nama]
                                sock_grup.send(f"INCOMING_FILE_MULTICAST {nama_client} {grup_tujuan} {nama_file}".encode('utf-8'))
                                if sock_grup.recv(1024).decode('utf-8') == "READY":
                                    sock_grup.send(str(ukuran_file).encode('utf-8'))
                                    if sock_grup.recv(1024).decode('utf-8') == "SEND":
                                        sock_grup.sendall(isi_file)
                    else:
                        client_socket.send(f"[-] Kamu bukan anggota grup '{grup_tujuan}' atau grup tidak ada.\n> ".encode('utf-8'))

            else:
                client_socket.send("[-] Perintah tidak dikenal.\n> ".encode('utf-8'))

    except Exception as e:
        pass
    finally:
        if nama_client in clients:
            del clients[nama_client]
            # Hapus dari semua grup jika keluar
            for grup in groups.values():
                grup.discard(nama_client)
            print(f"[-] {nama_client} keluar jaringan.")
        client_socket.close()

# Inisialisasi Server Utama (Multithreaded)
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('127.0.0.1', 6000))
server.listen(10)
print("[*] SERVER TUGAS BESAR AKTIF DI PORT 6000...")

while True:
    client_sock, addr = server.accept()
    # Menggunakan Multithread agar bisa melayani banyak user sekaligus [cite: 18]
    thread = threading.Thread(target=handle_client, args=(client_sock,))
    thread.start()
