import argparse
import sys
import time

import cv2
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.framework.formats import landmark_pb2

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles


def run(model: str,
        num_hands: int,
        min_hand_detection_confidence: float,
        min_hand_presence_confidence: float,
        min_tracking_confidence: float,
        camera_id: int,
        width: int,
        height: int) -> None:

    # Open camera (USB webcam is index 1 on your system)
    cap = cv2.VideoCapture(camera_id)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    if not cap.isOpened():
        sys.exit("ERROR: Unable to open camera.")

    # Inference throttling
    inference_interval = 1.0  # seconds
    last_inference_time = 0
    latest_result = None

    def save_result(result: vision.GestureRecognizerResult,
                    unused_output_image: mp.Image,
                    timestamp_ms: int):
        nonlocal latest_result
        latest_result = result

    # Initialize recognizer
    base_options = python.BaseOptions(model_asset_path=model)
    options = vision.GestureRecognizerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.LIVE_STREAM,
        num_hands=num_hands,
        min_hand_detection_confidence=min_hand_detection_confidence,
        min_hand_presence_confidence=min_hand_presence_confidence,
        min_tracking_confidence=min_tracking_confidence,
        result_callback=save_result
    )

    recognizer = vision.GestureRecognizer.create_from_options(options)

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            sys.exit("ERROR: Unable to read from webcam.")

        frame = cv2.flip(frame, 1)

        # Run inference only once per interval
        current_time = time.time()
        if current_time - last_inference_time >= inference_interval:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb_frame
            )
            recognizer.recognize_async(
                mp_image,
                int(current_time * 1000)
            )
            last_inference_time = current_time

        # Draw latest result (if available)
        if latest_result and latest_result.hand_landmarks:

            for hand_index, hand_landmarks in enumerate(
                    latest_result.hand_landmarks):

                # Convert to proto format for drawing
                hand_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
                hand_landmarks_proto.landmark.extend([
                    landmark_pb2.NormalizedLandmark(
                        x=l.x, y=l.y, z=l.z
                    ) for l in hand_landmarks
                ])

                mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks_proto,
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style()
                )

                # Draw gesture label
                if latest_result.gestures:
                    gesture = latest_result.gestures[hand_index]
                    category_name = gesture[0].category_name
                    score = round(gesture[0].score, 2)
                    label = f"{category_name} ({score})"

                    h, w = frame.shape[:2]
                    x = int(min(l.x for l in hand_landmarks) * w)
                    y = int(min(l.y for l in hand_landmarks) * h) - 10
                    if y < 0:
                        y = 30

                    cv2.putText(
                        frame,
                        label,
                        (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (255, 255, 255),
                        2,
                        cv2.LINE_AA
                    )

        cv2.imshow("gesture_recognition", frame)

        if cv2.waitKey(1) == 27:
            break

    recognizer.close()
    cap.release()
    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--model',
        default='gesture_recognizer.task'
    )
    parser.add_argument(
        '--numHands',
        default=1
    )
    parser.add_argument(
        '--minHandDetectionConfidence',
        default=0.5
    )
    parser.add_argument(
        '--minHandPresenceConfidence',
        default=0.5
    )
    parser.add_argument(
        '--minTrackingConfidence',
        default=0.5
    )
    parser.add_argument(
        '--cameraId',
        default=1  # USB webcam on your system
    )
    parser.add_argument(
        '--frameWidth',
        default=320  # lower resolution = faster
    )
    parser.add_argument(
        '--frameHeight',
        default=240
    )

    args = parser.parse_args()

    run(
        args.model,
        int(args.numHands),
        float(args.minHandDetectionConfidence),
        float(args.minHandPresenceConfidence),
        float(args.minTrackingConfidence),
        int(args.cameraId),
        int(args.frameWidth),
        int(args.frameHeight)
    )


if __name__ == '__main__':
    main()
