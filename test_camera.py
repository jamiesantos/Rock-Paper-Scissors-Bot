import cv2

for i in range(5):
    print(f"\nTesting index {i}")
    cap = cv2.VideoCapture(i)
    print("Opened:", cap.isOpened())
    if cap.isOpened():
        ret, frame = cap.read()
        print("Frame read:", ret)
    cap.release()
