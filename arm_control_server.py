import socket

HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 5005

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen(1)

print("Waiting for connection...")

conn = None

try:
    conn, addr = server.accept()
    print(f"Connected from {addr}")

    while True:
        data = conn.recv(1024).decode().strip()

        if not data:
            print("Client disconnected.")
            break

        print("Received:", data)

        # ARM CONTROL LOGIC HERE
        if data == "ROCK":
            print("Do ROCK motion")
        elif data == "PAPER":
            print("Do PAPER motion")
        elif data == "SCISSORS":
            print("Do SCISSORS motion")

except KeyboardInterrupt:
    print("\nShutting down server...")

finally:
    if conn:
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except:
            pass
        conn.close()

    server.close()
    print("Server closed cleanly.")
