"""MediaPipe hand detection and gesture classification.

Uses the MediaPipe Tasks ``HandLandmarker`` API (replaces the removed
``mp.solutions.hands`` legacy module).
"""

import logging
import math
from pathlib import Path
from urllib.request import urlretrieve

import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    RunningMode,
)

from .state import GestureType, HandState

logger = logging.getLogger(__name__)

# Official Google-hosted model file
_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
)
_MODEL_FILENAME = "hand_landmarker.task"


def _ensure_model_path() -> Path:
    """Return a local path to the HandLandmarker ``.task`` model file.

    Downloads the file on first use and caches it under the project's
    standard models directory (``~/.daydream-scope/models/mediapipe/``).
    """
    try:
        from scope.core.config import get_models_dir

        models_dir = get_models_dir() / "mediapipe"
    except Exception:
        models_dir = Path.home() / ".daydream-scope" / "models" / "mediapipe"

    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / _MODEL_FILENAME

    if not model_path.exists():
        logger.info("Downloading MediaPipe HandLandmarker model to %s …", model_path)
        urlretrieve(_MODEL_URL, str(model_path))
        logger.info("Download complete.")

    return model_path


class GestureDetector:
    """Detects hands and classifies gestures using MediaPipe Hands."""

    # MediaPipe landmark indices
    WRIST = 0
    THUMB_TIP = 4
    INDEX_TIP = 8
    MIDDLE_TIP = 12
    RING_TIP = 16
    PINKY_TIP = 20
    INDEX_MCP = 5
    MIDDLE_MCP = 9
    RING_MCP = 13
    PINKY_MCP = 17
    # PIP joints (for finger curl detection)
    INDEX_PIP = 6
    MIDDLE_PIP = 10
    RING_PIP = 14
    PINKY_PIP = 18
    THUMB_IP = 3
    THUMB_MCP = 2

    def __init__(
        self,
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.5,
        slash_speed_threshold: float = 40.0,
        pinch_distance_threshold: float = 0.05,
    ):
        model_path = _ensure_model_path()

        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=RunningMode.VIDEO,
            num_hands=max_num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._hands = HandLandmarker.create_from_options(options)

        self._slash_speed_threshold = slash_speed_threshold
        self._pinch_distance_threshold = pinch_distance_threshold

        # Previous frame state for velocity calculation
        self._prev_centers: dict[int, tuple[float, float]] = {}

        # Monotonic timestamp counter required by RunningMode.VIDEO
        self._frame_count: int = 0

    @property
    def slash_speed_threshold(self) -> float:
        return self._slash_speed_threshold

    @slash_speed_threshold.setter
    def slash_speed_threshold(self, value: float):
        self._slash_speed_threshold = value

    @property
    def pinch_distance_threshold(self) -> float:
        return self._pinch_distance_threshold

    @pinch_distance_threshold.setter
    def pinch_distance_threshold(self, value: float):
        self._pinch_distance_threshold = value

    def detect(self, rgb_frame: np.ndarray) -> list[HandState]:
        """Run hand detection on an RGB frame.

        Args:
            rgb_frame: numpy array (H, W, 3) in RGB uint8.

        Returns:
            List of HandState (0-2 hands).
        """
        h, w, _ = rgb_frame.shape

        # Wrap numpy array in a MediaPipe Image and run detection
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        self._frame_count += 1
        results = self._hands.detect_for_video(mp_image, self._frame_count)

        hands: list[HandState] = []
        if not results.hand_landmarks:
            self._prev_centers.clear()
            return hands

        for i, (hand_lm_list, hand_info_list) in enumerate(
            zip(results.hand_landmarks, results.handedness)
        ):
            # Extract landmarks — each entry is a NormalizedLandmark with .x/.y/.z
            landmarks = [
                (lm.x, lm.y, lm.z) for lm in hand_lm_list
            ]
            pixel_landmarks = [
                (int(lm.x * w), int(lm.y * h)) for lm in hand_lm_list
            ]

            # Palm center (average of wrist and MCP joints)
            cx = np.mean([pixel_landmarks[j][0] for j in [0, 5, 9, 13, 17]])
            cy = np.mean([pixel_landmarks[j][1] for j in [0, 5, 9, 13, 17]])
            center = (float(cx), float(cy))

            # Velocity from previous frame
            prev = self._prev_centers.get(i)
            if prev is not None:
                vx = center[0] - prev[0]
                vy = center[1] - prev[1]
            else:
                vx, vy = 0.0, 0.0
            velocity = (vx, vy)
            speed = math.hypot(vx, vy)

            # Classify gesture
            gesture = self._classify_gesture(landmarks, speed)

            # Tasks API: handedness is a list of Category objects
            handedness = hand_info_list[0].category_name
            confidence = hand_info_list[0].score

            hands.append(
                HandState(
                    hand_id=i,
                    handedness=handedness,
                    landmarks=landmarks,
                    pixel_landmarks=pixel_landmarks,
                    center=center,
                    velocity=velocity,
                    speed=speed,
                    gesture=gesture,
                    confidence=confidence,
                )
            )

        # Update previous centers
        self._prev_centers = {h.hand_id: h.center for h in hands}

        return hands

    def _classify_gesture(
        self, landmarks: list[tuple[float, float, float]], speed: float
    ) -> GestureType:
        """Classify hand gesture from normalized landmarks."""

        # Finger extension checks (y decreases upward in normalized coords)
        index_extended = landmarks[self.INDEX_TIP][1] < landmarks[self.INDEX_PIP][1]
        middle_extended = landmarks[self.MIDDLE_TIP][1] < landmarks[self.MIDDLE_PIP][1]
        ring_extended = landmarks[self.RING_TIP][1] < landmarks[self.RING_PIP][1]
        pinky_extended = landmarks[self.PINKY_TIP][1] < landmarks[self.PINKY_PIP][1]

        # Thumb: use x-axis (thumb extends sideways)
        thumb_extended = abs(landmarks[self.THUMB_TIP][0] - landmarks[self.THUMB_MCP][0]) > 0.05

        all_extended = index_extended and middle_extended and ring_extended and pinky_extended
        all_closed = not index_extended and not middle_extended and not ring_extended and not pinky_extended

        # Pinch: thumb tip close to index tip (normalized distance)
        pinch_dist = math.hypot(
            landmarks[self.THUMB_TIP][0] - landmarks[self.INDEX_TIP][0],
            landmarks[self.THUMB_TIP][1] - landmarks[self.INDEX_TIP][1],
        )
        is_pinching = pinch_dist < self._pinch_distance_threshold

        # Priority-based classification
        if is_pinching and not middle_extended:
            return GestureType.PINCH

        if all_extended and speed > self._slash_speed_threshold:
            return GestureType.SLASH

        if all_closed:
            return GestureType.FIST

        if all_extended:
            return GestureType.OPEN_PALM

        if index_extended and middle_extended and not ring_extended and not pinky_extended:
            return GestureType.PEACE

        if index_extended and not middle_extended and not ring_extended and not pinky_extended:
            return GestureType.POINTING

        return GestureType.NONE

    def close(self):
        self._hands.close()
