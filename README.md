# Rock–Paper–Scissors Robot Demo

A Raspberry Pi–based demo that performs Rock, Paper, or Scissors using real-time hand gesture recognition with MediaPipe and executes corresponding motions on a robotic arm. This demo was created for Oregon State University's ROB515 Intro to Robotics II course.

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

- Raspberry Pi (64-bit OS recommended) x2
- USB camera
- Robotic arm (e.g., HiWonder arm)
- Network connection (if using separate devices)

### Software

- Python 3.12
- mediapipe
- opencv-python

---
## Demo Setup
### Robot Arm
1. Plug in the robot arm RPi/motor driver (HiWonder arm with armv7l Raspberry Pi 4)
2. SSH into arm; Jamie's arm: `ssh -Y pi@JimmieRogers.engr.oregonstate.edu`; password is default password
3. Make sure it's connected to wifi (the same network as the picar)
4. Run `rps` which is an alias for `python3 arm_control_server.py` on the arm
   1. The code is in ~/Rock-Paper-Scissors-Bot

### Vision
1. Plug in the vision RPi (e.g., ROB515 PiCar w/ aarch64 Raspberry Pi 4)
2. SSH into car; Jamie's PiCar: `ssh -Y j@PiCar5.engr.oregonstate.edu`; ask for password
   1. For visualization, Jamie uses RealVNC (free account) to get the camera stream/model label visualization
4. Plug in the USB camera; it seems to work best facing a wall in order to minimze overhead shadows
5. Make sure it's connected to wifi (the same network as the arm RPi)
6. If the python env isn't activated, run `source env/bin/activate`
   1. If setting up a new RPi, create a python environment using python 3.10 - 3.12 in order to use mediapipe
   2. This should already be done in the bashrc; also make sure you haven't accidentally activated it twice
7. Run `rps` which is an alias for `python3 rock_paper_scissors_vision.py` on the vision/picar setup

### GitHub
- Both RPis have Jamie's ssh keys installed; you can either install your own or message Jamie for her passcode
- Don't forget to pull the latest code each time!

---
## Installation

Create and activate a virtual environment:

```bash
python -m venv env
source env/bin/activate
pip install --upgrade pip
pip install mediapipe opencv-python


