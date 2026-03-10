"""Configuration schema for the Gesture Arcade pipeline."""

from typing import Annotated, ClassVar, Literal

from pydantic import Field

from scope.core.pipelines.base_schema import (
    BasePipelineConfig,
    ModeDefaults,
    ui_field_config,
)


class GestureArcadeConfig(BasePipelineConfig):
    """Hand gesture-controlled arcade games using MediaPipe.

    Detects hand landmarks from live webcam video and overlays one of
    three selectable gesture-controlled mini-games on the output.
    Supports two-hand tracking.
    """

    pipeline_id: ClassVar[str] = "gesture-arcade"
    pipeline_name: ClassVar[str] = "Gesture Arcade"
    pipeline_description: ClassVar[str] = (
        "Hand gesture-controlled arcade games using MediaPipe. "
        "Slash targets, play pong with your hands, or pop bubbles "
        "with pinch gestures — all in real-time on your webcam feed."
    )
    supports_prompts: ClassVar[bool] = False

    modes: ClassVar[dict[str, ModeDefaults]] = {
        "video": ModeDefaults(default=True),
    }

    # ── Load-time parameters ──────────────────────────────────────

    detection_confidence: Annotated[float, Field(ge=0.3, le=1.0)] = Field(
        default=0.7,
        description="MediaPipe hand detection confidence threshold.",
        json_schema_extra=ui_field_config(
            order=1,
            label="Detection Confidence",
            is_load_param=True,
        ),
    )

    tracking_confidence: Annotated[float, Field(ge=0.3, le=1.0)] = Field(
        default=0.5,
        description="MediaPipe hand tracking confidence threshold.",
        json_schema_extra=ui_field_config(
            order=2,
            label="Tracking Confidence",
            is_load_param=True,
        ),
    )

    # ── Game selection ────────────────────────────────────────────

    game_mode: Literal["gesture_smash", "hand_pong", "bubble_pop"] = Field(
        default="gesture_smash",
        description=(
            "Active game mode. "
            "gesture_smash: Slash/smash targets (Fruit Ninja-style). "
            "hand_pong: Classic Pong controlled by hand position. "
            "bubble_pop: Pop floating bubbles with pinch gestures."
        ),
        json_schema_extra=ui_field_config(
            order=10,
            label="Game Mode",
        ),
    )

    difficulty: Literal["easy", "medium", "hard"] = Field(
        default="medium",
        description="Game difficulty — affects spawn rates, speeds, and AI behavior.",
        json_schema_extra=ui_field_config(
            order=11,
            label="Difficulty",
        ),
    )

    # ── Gesture settings ──────────────────────────────────────────

    slash_speed_threshold: Annotated[float, Field(ge=10.0, le=100.0)] = Field(
        default=40.0,
        description="Minimum hand speed (px/frame) to trigger a slash gesture.",
        json_schema_extra=ui_field_config(
            order=20,
            label="Slash Speed Threshold",
        ),
    )

    pinch_distance_threshold: Annotated[float, Field(ge=0.01, le=0.15)] = Field(
        default=0.05,
        description="Maximum normalized distance between thumb and index tips for pinch detection.",
        json_schema_extra=ui_field_config(
            order=21,
            label="Pinch Distance Threshold",
        ),
    )

    # ── Visualization ─────────────────────────────────────────────

    show_hand_skeleton: bool = Field(
        default=True,
        description="Draw hand landmarks and connections overlay.",
        json_schema_extra=ui_field_config(
            order=30,
            label="Show Hand Skeleton",
        ),
    )

    show_gesture_labels: bool = Field(
        default=True,
        description="Show detected gesture name near each hand.",
        json_schema_extra=ui_field_config(
            order=31,
            label="Show Gesture Labels",
        ),
    )

    show_hud: bool = Field(
        default=True,
        description="Show score, combo, and lives HUD overlay.",
        json_schema_extra=ui_field_config(
            order=32,
            label="Show HUD",
        ),
    )

    mirror_input: bool = Field(
        default=True,
        description="Flip input horizontally for selfie/mirror mode.",
        json_schema_extra=ui_field_config(
            order=33,
            label="Mirror Mode",
        ),
    )

    # ── Game-specific tuning ──────────────────────────────────────

    target_spawn_rate: Annotated[float, Field(ge=0.5, le=5.0)] = Field(
        default=1.5,
        description="Gesture Smash: targets spawned per second.",
        json_schema_extra=ui_field_config(
            order=40,
            label="Target Spawn Rate",
        ),
    )

    ball_speed: Annotated[float, Field(ge=2.0, le=15.0)] = Field(
        default=6.0,
        description="Hand Pong: initial ball speed in pixels per frame.",
        json_schema_extra=ui_field_config(
            order=41,
            label="Ball Speed",
        ),
    )

    bubble_spawn_rate: Annotated[float, Field(ge=0.5, le=5.0)] = Field(
        default=2.0,
        description="Bubble Pop: bubbles spawned per second.",
        json_schema_extra=ui_field_config(
            order=42,
            label="Bubble Spawn Rate",
        ),
    )
