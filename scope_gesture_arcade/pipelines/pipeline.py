"""Gesture Arcade pipeline — main orchestrator.

Detects hand gestures via MediaPipe and runs the selected mini-game,
compositing game visuals and hand overlay onto each video frame.
"""

import logging
from typing import TYPE_CHECKING

import numpy as np
import torch
from PIL import Image

from scope.core.pipelines.interface import Pipeline, Requirements

from ..games.bubble_pop import BubblePopGame
from ..games.gesture_smash import GestureSmashGame
from ..games.hand_pong import HandPongGame
from ..gestures import GestureDetector
from ..state import FrameState
from ..visualization import render_overlay
from .schema import GestureArcadeConfig

if TYPE_CHECKING:
    from scope.core.pipelines.base_schema import BasePipelineConfig

logger = logging.getLogger(__name__)

GAME_NAMES = {
    "gesture_smash": "Gesture Smash",
    "hand_pong": "Hand Pong",
    "bubble_pop": "Bubble Pop",
}


class GestureArcadePipeline(Pipeline):
    """Real-time hand gesture arcade games.

    Uses MediaPipe Hands for landmark detection and gesture classification,
    then runs one of three selectable mini-games rendered via PIL overlays.
    """

    @classmethod
    def get_config_class(cls) -> type["BasePipelineConfig"]:
        return GestureArcadeConfig

    def __init__(
        self,
        device: torch.device | None = None,
        **kwargs,
    ):
        detection_confidence: float = kwargs.get("detection_confidence", 0.7)
        tracking_confidence: float = kwargs.get("tracking_confidence", 0.5)

        self._detector = GestureDetector(
            max_num_hands=2,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )

        # Initialize all games (only the active one runs per frame)
        self._games = {
            "gesture_smash": GestureSmashGame(),
            "hand_pong": HandPongGame(),
            "bubble_pop": BubblePopGame(),
        }
        self._active_game: str | None = None
        self._frame_number = 0

        logger.info(
            "Gesture Arcade pipeline ready (detection=%.2f, tracking=%.2f)",
            detection_confidence,
            tracking_confidence,
        )

    def prepare(self, **kwargs) -> Requirements:
        return Requirements(input_size=1)

    @torch.no_grad()
    def __call__(self, **kwargs) -> dict:
        video = kwargs.get("video")
        if video is None:
            raise ValueError("Input video cannot be None for GestureArcadePipeline")

        # ── Unpack runtime config ─────────────────────────────────
        game_mode: str = kwargs.get("game_mode", "gesture_smash")
        difficulty: str = kwargs.get("difficulty", "medium")
        mirror: bool = kwargs.get("mirror_input", True)

        show_skeleton: bool = kwargs.get("show_hand_skeleton", True)
        show_labels: bool = kwargs.get("show_gesture_labels", True)
        show_hud: bool = kwargs.get("show_hud", True)

        slash_threshold: float = kwargs.get("slash_speed_threshold", 40.0)
        pinch_threshold: float = kwargs.get("pinch_distance_threshold", 0.05)

        target_spawn: float = kwargs.get("target_spawn_rate", 1.5)
        ball_speed: float = kwargs.get("ball_speed", 6.0)
        bubble_spawn: float = kwargs.get("bubble_spawn_rate", 2.0)

        # Update gesture detector thresholds
        self._detector.slash_speed_threshold = slash_threshold
        self._detector.pinch_distance_threshold = pinch_threshold

        # Handle game switching — reset on game change
        if game_mode != self._active_game:
            self._active_game = game_mode
            game = self._games[game_mode]
            game.difficulty = difficulty
            # Update game-specific params
            if hasattr(game, "base_spawn_rate"):
                if game_mode == "gesture_smash":
                    game.base_spawn_rate = target_spawn
                elif game_mode == "bubble_pop":
                    game.base_spawn_rate = bubble_spawn
            if hasattr(game, "base_ball_speed"):
                game.base_ball_speed = ball_speed
            game.reset()

        game = self._games[game_mode]

        output_frames: list[torch.Tensor] = []

        for frame_tensor in video:
            self._frame_number += 1

            # Convert tensor → numpy (H, W, C) uint8
            frame_np: np.ndarray = (
                frame_tensor.squeeze(0).cpu().numpy().astype(np.uint8)
            )

            # Mirror if enabled
            if mirror:
                frame_np = np.fliplr(frame_np).copy()

            pil_image = Image.fromarray(frame_np, mode="RGB")
            h, w = frame_np.shape[:2]

            # ── Step 1: Detect hands ──────────────────────────────
            hands = self._detector.detect(frame_np)

            frame_state = FrameState(
                frame_number=self._frame_number,
                hands=hands,
                width=w,
                height=h,
            )

            # ── Step 2: Update game logic ─────────────────────────
            score = game.update(frame_state)

            # ── Step 3: Render game objects ────────────────────────
            rendered = game.render(pil_image, frame_state, score)

            # ── Step 4: Render shared overlay (skeleton, HUD) ─────
            final = render_overlay(
                rendered,
                frame_state,
                score,
                game_name=GAME_NAMES.get(game_mode, game_mode),
                show_skeleton=show_skeleton,
                show_labels=show_labels,
                show_hud=show_hud,
            )

            # Convert back to tensor (H, W, C) float32 [0, 1]
            frame_out = torch.from_numpy(
                np.array(final, dtype=np.float32) / 255.0
            )
            output_frames.append(frame_out)

        # Stack to (T, H, W, C)
        video_out = torch.stack(output_frames, dim=0)
        return {"video": video_out}
