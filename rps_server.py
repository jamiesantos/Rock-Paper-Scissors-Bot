import socket

HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 5005

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(1)

print("Waiting for connection...")

conn, addr = server.accept()
print(f"Connected from {addr}")

while True:
    data = conn.recv(1024).decode().strip()
    if not data:
        break

    print("Received:", data)

    # 🔥 Put your arm control logic here
    if data == "ROCK":
        print("Do ROCK motion")
    elif data == "PAPER":
        print("Do PAPER motion")
    elif data == "SCISSORS":
        print("Do SCISSORS motion")

conn.close()
