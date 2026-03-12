from pathlib import Path
import socket
import time
import sys

# Try a few likely roots and add the one that actually contains an ArmIK/ folder
CANDIDATE_ROOTS = [
    Path("/home/pi/RobotSystems/ArmPi"),
    Path("/home/pi/RobotSystems/ArmPi/ArmIK"),
    Path("/home/pi/RobotSystems"),
]

added = False
for root in CANDIDATE_ROOTS:
    if (root / "ArmIK").is_dir():   # root contains ArmIK/ package dir
        sys.path.insert(0, str(root))
        print(f"[arm_server] Added to sys.path: {root}")
        added = True
        break

if not added:
    raise RuntimeError(
        "Could not find ArmIK/ folder. Check where ArmIK is installed. "
        "Tried: " + ", ".join(str(p) for p in CANDIDATE_ROOTS)
    )

from ArmIK.ArmMoveIK import ArmIK
import HiwonderSDK.Board as Board
AK = ArmIK()
SERVO1 = 500
GRIPPER_CLOSED = 500
GRIPPER_OPEN = 100

BASE_XY = (0, 12)
UP_Z = 12
DOWN_Z = 5

HOST = "0.0.0.0"
PORT = 5005


def initMove():
    Board.setBusServoPulse(1, SERVO1 - 50, 300)
    Board.setBusServoPulse(2, 500, 500)
    AK.setPitchRangeMoving((0, 10, 10), -30, -30, -90, 1200)


def windup_three_times():
    print("Starting windup")
    for _ in range(3):
        AK.setPitchRangeMoving((BASE_XY[0], BASE_XY[1], UP_Z), -90, -90, 0, 350)
        time.sleep(0.4)
        AK.setPitchRangeMoving((BASE_XY[0], BASE_XY[1], DOWN_Z), -90, -90, 0, 350)
        time.sleep(0.4)
    initMove()


def pose_robot_move(move):
    print("Robot move:", move)
    if move == "ROCK":
        AK.setPitchRangeMoving((0, 12, 6), -60, -60, 0, 500)
        time.sleep(0.6)
        Board.setBusServoPulse(1, GRIPPER_CLOSED, 400)
    elif move == "PAPER":
        AK.setPitchRangeMoving((0, 14, 10), -30, -30, 0, 500)
        time.sleep(0.6)
        Board.setBusServoPulse(1, GRIPPER_OPEN, 400)
    elif move == "SCISSORS":
        AK.setPitchRangeMoving((2, 13, 8), -45, -45, 0, 500)
        time.sleep(0.6)
        for _ in range(3):
            Board.setBusServoPulse(1, GRIPPER_CLOSED, 300)
            time.sleep(0.4)
            Board.setBusServoPulse(1, GRIPPER_OPEN, 300)
            time.sleep(0.4)
    else:
        initMove()


def handle_command(cmd):
    """Process a single newline-delimited command."""
    print("Received:", cmd)

    if cmd == "WINDUP":
        windup_three_times()
    elif cmd.startswith("ROBOT:"):
        pose_robot_move(cmd.split(":", 1)[1])
    elif cmd.startswith("HUMAN:"):
        print("Human played", cmd.split(":", 1)[1])
    elif cmd.startswith("WINNER:"):
        print("Winner:", cmd.split(":", 1)[1])
    else:
        print("Unknown command:", cmd)


def handle_client(conn, addr):
    """Read newline-delimited commands from one client until it disconnects."""
    print(f"Connected from {addr}")
    buf = ""
    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                break
            buf += data
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if line:
                    handle_command(line)
    finally:
        print(f"Client {addr} disconnected.")
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        conn.close()


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)

    initMove()
    print(f"Listening on {HOST}:{PORT} ...")

    try:
        while True:
            conn, addr = server.accept()
            handle_client(conn, addr)
            # After client disconnects, return arm home and wait for next client
            initMove()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        initMove()
        server.close()
        print("Server closed cleanly.")


if __name__ == "__main__":
    main()