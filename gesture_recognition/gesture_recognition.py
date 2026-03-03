#!/usr/bin/python3
# coding=utf8

import cv2
import numpy as np

# ---- Config ----
FRAME_WIDTH = 300
FRAME_HEIGHT = 200
CALIBRATION_TIME = 30
BG_WEIGHT = 0.5
OBJ_THRESHOLD = 18

background = None
frames_elapsed = 0
fingers_history = []

# ---- ROI (top-right corner) ----
region_top = 0
region_bottom = FRAME_HEIGHT
region_left = 0
region_right = FRAME_WIDTH


# ---- Background Averaging ----
def update_background(region):
    global background
    if background is None:
        background = region.copy().astype("float")
        return
    cv2.accumulateWeighted(region, background, BG_WEIGHT)


# ---- Segment Hand ----
def segment(region):
    diff = cv2.absdiff(background.astype(np.uint8), region)
    thresholded = cv2.threshold(diff, OBJ_THRESHOLD, 255, cv2.THRESH_BINARY)[1]

    contours_data = cv2.findContours(
        thresholded.copy(),
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )
    contours = contours_data[-2]

    if len(contours) == 0:
        return None

    segmented = max(contours, key=cv2.contourArea)
    return thresholded, segmented


# ---- Count Fingers ----
def count_fingers(thresholded, segmented):
    convexHull = cv2.convexHull(segmented)

    top = tuple(convexHull[convexHull[:, :, 1].argmin()][0])
    bottom = tuple(convexHull[convexHull[:, :, 1].argmax()][0])
    left = tuple(convexHull[convexHull[:, :, 0].argmin()][0])
    right = tuple(convexHull[convexHull[:, :, 0].argmax()][0])

    line_height = int(top[1] + (0.2 * (bottom[1] - top[1])))

    line = np.zeros(thresholded.shape[:2], dtype=np.uint8)
    cv2.line(line, (thresholded.shape[1], line_height), (0, line_height), 255, 1)

    line = cv2.bitwise_and(thresholded, thresholded, mask=line)

    contours_data = cv2.findContours(
        line.copy(),
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_NONE
    )
    contours = contours_data[-2]

    fingers = 0
    hand_width = abs(right[0] - left[0])

    for curr in contours:
        width = len(curr)
        if 5 < width < 3 * hand_width / 4:
            fingers += 1

    return fingers


# ---- Map to RPS ----
def classify(fingers):
    if fingers == 0:
        return "Rock"
    elif fingers == 2:
        return "Scissors"
    elif fingers >= 4:
        return "Paper"
    else:
        return "Unknown"


# ---- Main ----
cap = cv2.VideoCapture(0)

print("Calibrating background... Keep region empty.")

while True:
    ret, frame = cap.read()
    if not ret:
        continue

    frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
    frame = cv2.flip(frame, 1)

    region = frame[region_top:region_bottom,
                   region_left:region_right]

    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    if frames_elapsed < CALIBRATION_TIME:
        update_background(gray)
        cv2.putText(frame, "Calibrating...",
                    (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 0, 255), 2)
    else:
        result = segment(gray)
        if result is not None:
            thresholded, segmented = result
            fingers = count_fingers(thresholded, segmented)

            fingers_history.append(fingers)

            # Smooth result every 10 frames
            if len(fingers_history) > 10:
                fingers_history.pop(0)

            stable = max(set(fingers_history),
                         key=fingers_history.count)

            gesture = classify(stable)

            cv2.putText(frame, gesture,
                        (10, 20),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 255, 0), 2)

            cv2.imshow("Thresholded", thresholded)

    cv2.rectangle(frame,
                  (region_left, region_top),
                  (region_right, region_bottom),
                  (255, 255, 255), 2)

    cv2.imshow("Camera", frame)

    frames_elapsed += 1

    if cv2.waitKey(1) & 0xFF == ord('x'):
        break

cap.release()
cv2.destroyAllWindows()
