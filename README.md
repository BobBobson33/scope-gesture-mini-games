# Scope Gesture Mini Games

A Scope plugin that uses **MediaPipe Hands** to detect hand landmarks from live video and overlays gesture-controlled mini-games on the output. Supports two-hand tracking and works on CPU.


https://github.com/user-attachments/assets/f71924b8-3468-49f0-8a97-db4de23516f0


## Games

- **Gesture Smash** — Slash/smash targets with hand gestures (Fruit Ninja-style)
- **Hand Pong** — Pong with hand-controlled paddles
- **Bubble Pop** — Pop floating bubbles with a pinch gesture

## Recognised Gestures

Open Palm · Fist · Pinch · Pointing · Peace · Slash (open palm + fast movement)

## Install

```bash
pip install -e .
```

The MediaPipe `hand_landmarker.task` model is downloaded automatically on first run.

