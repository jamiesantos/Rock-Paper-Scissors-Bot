import cv2
import mediapipe as mp
import time
import argparse
import socket

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

ARM_IP = "10.214.159.113"   # <-- change to arm Pi IP
PORT = 5005

def fingers_up(hand_landmarks):
    """
    Returns a list of booleans:
    [thumb, index, middle, ring, pinky]
    True = finger extended
    False = finger folded
    """

    tips = [4, 8, 12, 16, 20]
    pips = [3, 6, 10, 14, 18]

    fingers = []

    # Thumb (compare x because thumb moves sideways)
    if hand_landmarks.landmark[tips[0]].x < hand_landmarks.landmark[pips[0]].x:
        fingers.append(True)
    else:
        fingers.append(False)

    # Other four fingers (compare y because they move vertically)
    for i in range(1, 5):
        if hand_landmarks.landmark[tips[i]].y < hand_landmarks.landmark[pips[i]].y:
            fingers.append(True)
        else:
            fingers.append(False)

    return fingers


def classify_rps(fingers):
    """
    Determine Rock / Paper / Scissors from finger states
    Ignores thumb for stability.
    """

    _, index, middle, ring, pinky = fingers

    # Rock: all four fingers folded
    if not index and not middle and not ring and not pinky:
        return "ROCK"

    # Paper: all four fingers extended
    if index and middle and ring and pinky:
        return "PAPER"

    # Scissors: index + middle only
    if index and middle and not ring and not pinky:
        return "SCISSORS"

    return ""

def run(camera_id, width, height):

    #TCP socket setup to communicate with robot arm
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((ARM_IP, PORT))

    cap = cv2.VideoCapture(camera_id)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    if not cap.isOpened():
        print("ERROR: Cannot open camera.")
        return

    with mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    ) as hands:

        current_rps = ""
        last_update = 0
        update_interval = 0.5  # evaluate twice per second

        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            results = hands.process(rgb)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:

                    mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS
                    )

                    # Throttle evaluation
                    now = time.time()
                    if now - last_update > update_interval:
                        fingers = fingers_up(hand_landmarks)
                        new_rps = classify_rps(fingers)

                        if new_rps != current_rps:
                            current_rps = new_rps
                            print("Sending:", current_rps)
                            try:
                                client.sendall((current_rps + "\n").encode())
                            except:
                                print("Connection lost")
                        last_update = now

            # Draw RPS label
            if current_rps:
                h, w = frame.shape[:2]
                text_size = cv2.getTextSize(
                    current_rps,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    2,
                    4
                )[0]

                x = (w - text_size[0]) // 2
                y = (h + text_size[1]) // 2

                cv2.putText(
                    frame,
                    current_rps,
                    (x, y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    2,
                    (0, 255, 0),
                    4,
                    cv2.LINE_AA
                )

            cv2.imshow("Rock Paper Scissors", frame)

            if cv2.waitKey(1) == 27:
                break

    cap.release()
    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cameraId", default=1)
    parser.add_argument("--frameWidth", default=320)
    parser.add_argument("--frameHeight", default=240)
    args = parser.parse_args()

    run(
        int(args.cameraId),
        int(args.frameWidth),
        int(args.frameHeight)
    )


if __name__ == "__main__":
    main()
