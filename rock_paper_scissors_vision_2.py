import cv2
import mediapipe as mp
import time
import argparse
import socket
import random
import threading

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

PORT = 5005

# Round timing tunables
UPDATE_INTERVAL = 0.2        # evaluate gestures 5x/sec
STABLE_REQUIRED_S = 0.6      # human must hold gesture this long
ROUND_COOLDOWN_S = 10.0      # pause between rounds
WINDUP_DURATION_S = 3.0      # how long the arm windup takes
REVEAL_WINDOW_S = 2.0        # how long we wait for stable hand after windup


def fingers_up(hand_landmarks):
    tips = [4, 8, 12, 16, 20]
    pips = [3, 6, 10, 14, 18]
    fingers = []
    # Thumb (assumes right-hand view after horizontal flip)
    fingers.append(hand_landmarks.landmark[tips[0]].x < hand_landmarks.landmark[pips[0]].x)
    for i in range(1, 5):
        fingers.append(hand_landmarks.landmark[tips[i]].y < hand_landmarks.landmark[pips[i]].y)
    return fingers


def classify_rps(fingers):
    _, index, middle, ring, pinky = fingers
    if not index and not middle and not ring and not pinky:
        return "ROCK"
    if index and middle and ring and pinky:
        return "PAPER"
    if index and middle and not ring and not pinky:
        return "SCISSORS"
    return ""


def decide_winner(human_move: str, robot_move: str) -> str:
    if human_move not in ("ROCK", "PAPER", "SCISSORS"):
        return "UNKNOWN"
    if robot_move not in ("ROCK", "PAPER", "SCISSORS"):
        return "UNKNOWN"
    if human_move == robot_move:
        return "TIE"
    wins = {("ROCK", "SCISSORS"), ("PAPER", "ROCK"), ("SCISSORS", "PAPER")}
    return "HUMAN" if (human_move, robot_move) in wins else "ROBOT"


def move_that_beats(human_move: str) -> str:
    return {"ROCK": "PAPER", "PAPER": "SCISSORS", "SCISSORS": "ROCK"}.get(human_move, "ROCK")


def choose_robot_move(human_move: str, mode: str) -> str:
    if mode == "cheat":
        return move_that_beats(human_move)
    return random.choice(["ROCK", "PAPER", "SCISSORS"])


def connect_to_arm(arm_ip: str):
    while True:
        try:
            print(f"Connecting to arm at {arm_ip}:{PORT} ...")
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(5)
            client.connect((arm_ip, PORT))
            client.settimeout(None)
            print("Connected to arm!")
            return client
        except OSError:
            print("Connection failed. Retrying in 2 seconds...")
            time.sleep(2)


def safe_send(client, msg: str, arm_ip: str):
    try:
        client.sendall((msg + "\n").encode())
        return client
    except OSError:
        print("Connection lost while sending. Reconnecting...")
        try:
            client.close()
        except OSError:
            pass
        return connect_to_arm(arm_ip)


def run(camera_id: int, width: int, height: int, headless: bool, mode: str, arm_ip: str):
    client = connect_to_arm(arm_ip)

    cap = cv2.VideoCapture(f"/dev/video{camera_id}", cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    if not cap.isOpened():
        print(f"ERROR: Cannot open camera /dev/video{camera_id}.")
        return

    # Score tracking
    score = {"HUMAN": 0, "ROBOT": 0, "TIE": 0}

    # Gesture stability tracking
    last_seen = "NONE"
    last_change_t = time.time()

    # Round state machine: COOLDOWN -> WINDUP -> REVEAL -> COOLDOWN ...
    round_state = "COOLDOWN"
    state_until = 0.0
    next_round_time = float("inf")      # held until user presses Enter
    stable_move_for_round = "NONE"

    robot_move = "—"
    winner = "—"
    current_rps = "NONE"

    started = threading.Event()
    threading.Thread(target=lambda: [input("Press Enter to start the game..."), started.set()], daemon=True).start()

    try:
        with mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6,
        ) as hands:

            last_update = 0.0

            while cap.isOpened():
                success, frame = cap.read()
                if not success:
                    print("ERROR: Failed to read frame from camera.")
                    break

                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb)
                now = time.time()

                # ---- Waiting for Enter ----
                if not started.is_set():
                    cv2.putText(frame, "Press Enter to start",
                                (width // 2 - 200, height // 2), cv2.FONT_HERSHEY_SIMPLEX,
                                1.0, (0, 255, 255), 2, cv2.LINE_AA)
                    if not headless:
                        cv2.imshow("Rock Paper Scissors (Vision Pi)", frame)
                        cv2.waitKey(1)
                    continue

                if next_round_time == float("inf"):
                    next_round_time = now  # first round starts immediately after Enter

                # ---- Round state transitions ----
                if round_state == "COOLDOWN" and now >= next_round_time:
                    print("== ROUND START: WINDUP ==")
                    client = safe_send(client, "WINDUP", arm_ip)
                    round_state = "WINDUP"
                    state_until = now + WINDUP_DURATION_S
                    stable_move_for_round = "NONE"
                    robot_move = "—"
                    winner = "—"

                if round_state == "WINDUP" and now >= state_until:
                    print("== WINDUP DONE: SHOW YOUR HAND ==")
                    round_state = "REVEAL"
                    state_until = now + REVEAL_WINDOW_S
                    # reset stability so a pre-held hand doesn't count
                    last_seen = "NONE"
                    last_change_t = now
                    current_rps = "NONE"

                if round_state == "REVEAL" and now >= state_until and stable_move_for_round == "NONE":
                    print("== REVEAL TIMEOUT: no hand detected ==")
                    next_round_time = now + ROUND_COOLDOWN_S
                    round_state = "COOLDOWN"

                # ---- Throttled gesture classification ----
                if now - last_update > UPDATE_INTERVAL:
                    if results.multi_hand_landmarks:
                        hand_landmarks = results.multi_hand_landmarks[0]
                        mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                        fingers = fingers_up(hand_landmarks)
                        new_rps = classify_rps(fingers) or "NONE"
                    else:
                        new_rps = "NONE"

                    # stability bookkeeping
                    if new_rps != last_seen:
                        last_seen = new_rps
                        last_change_t = now

                    stable_move = (
                        last_seen
                        if last_seen in ("ROCK", "PAPER", "SCISSORS") and (now - last_change_t) >= STABLE_REQUIRED_S
                        else "NONE"
                    )

                    current_rps = new_rps
                    last_update = now

                    # Accept move only during the REVEAL window
                    if round_state == "REVEAL" and stable_move != "NONE" and stable_move_for_round == "NONE":
                        stable_move_for_round = stable_move
                        robot_move = choose_robot_move(stable_move_for_round, mode)
                        winner = decide_winner(stable_move_for_round, robot_move)

                        if winner in score:
                            score[winner] += 1

                        print(f"REVEAL: human={stable_move_for_round}  robot={robot_move}  winner={winner}")
                        print(f"SCORE:  Human {score['HUMAN']} - Robot {score['ROBOT']}  (ties: {score['TIE']})")

                        client = safe_send(client, f"ROBOT:{robot_move}", arm_ip)

                        next_round_time = time.time() + ROUND_COOLDOWN_S
                        round_state = "COOLDOWN"

                # ---- HUD overlay ----
                score_text = f"H {score['HUMAN']} - R {score['ROBOT']}"
                cv2.putText(frame, f"State: {round_state}",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(frame, f"Human: {current_rps}",
                            (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2, cv2.LINE_AA)
                cv2.putText(frame, f"Robot: {robot_move}",
                            (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(frame, f"Winner: {winner}",
                            (10, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(frame, score_text,
                            (10, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 200, 255), 2, cv2.LINE_AA)

                if not headless:
                    cv2.imshow("Rock Paper Scissors (Vision Pi)", frame)
                    if (cv2.waitKey(1) & 0xFF) == 27:
                        break
                else:
                    time.sleep(0.001)

    finally:
        cap.release()
        if not headless:
            cv2.destroyAllWindows()
        try:
            client.close()
        except OSError:
            pass
        print(f"\nFinal score — Human {score['HUMAN']} : Robot {score['ROBOT']}  (ties: {score['TIE']})")


def main():
    parser = argparse.ArgumentParser(description="RPS vision client (connects to arm server)")
    parser.add_argument("--armIp", required=True, help="IP address of the arm Pi")
    parser.add_argument("--cameraId", type=int, default=0)
    parser.add_argument("--frameWidth", type=int, default=320)
    parser.add_argument("--frameHeight", type=int, default=240)
    parser.add_argument("--headless", action="store_true", help="Run without GUI (e.g. over SSH)")
    parser.add_argument("--mode", choices=["random", "cheat"], default="random",
                        help="Robot strategy: 'random' or 'cheat'")
    args = parser.parse_args()

    run(args.cameraId, args.frameWidth, args.frameHeight, args.headless, args.mode, args.armIp)


if __name__ == "__main__":
    main()