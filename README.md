# Rock–Paper–Scissors Robot Demo

A Raspberry Pi–based demo that performs Rock, Paper, or Scissors using real-time hand gesture recognition with MediaPipe and executes corresponding motions on a robotic arm.

---

## Overview

This project:

1. Uses MediaPipe Hands to detect hand landmarks from a camera feed.
2. Classifies gestures as Rock, Paper, or Scissors.
3. Sends the detected gesture to a robotic arm controller.
4. Executes a predefined motion for each gesture.

---

## Credit

MediaPipe installation steps and Raspberry Pi setup were adapted from:

https://github.com/make2explore/MediaPipe-Installation-on-RaspberryPi/tree/main#

---

## Requirements

### Hardware

- Raspberry Pi (64-bit OS recommended)
- USB camera
- Robotic arm (e.g., ArmPi)
- Network connection (if using separate devices)

### Software

- Python 3.12
- mediapipe
- opencv-python

---

## Installation

Create and activate a virtual environment:

```bash
python -m venv env
source env/bin/activate
pip install --upgrade pip
pip install mediapipe opencv-python
