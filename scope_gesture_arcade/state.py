"""Shared data classes for gesture detection and game state."""

from dataclasses import dataclass, field
from enum import Enum


class GestureType(Enum):
    NONE = "none"
    OPEN_PALM = "open_palm"
    FIST = "fist"
    PINCH = "pinch"
    POINTING = "pointing"
    PEACE = "peace"
    SLASH = "slash"


@dataclass
class HandState:
    hand_id: int
    handedness: str
    landmarks: list[tuple[float, float, float]]
    pixel_landmarks: list[tuple[int, int]]
    center: tuple[float, float]
    velocity: tuple[float, float]
    speed: float
    gesture: GestureType
    confidence: float


@dataclass
class FrameState:
    frame_number: int
    hands: list[HandState]
    width: int
    height: int


# ── Game-specific state ──────────────────────────────────────────


@dataclass
class Target:
    x: float
    y: float
    radius: float
    color: tuple[int, int, int]
    vx: float
    vy: float
    alive: bool = True
    spawn_frame: int = 0


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    radius: float = 12.0


@dataclass
class Bubble:
    x: float
    y: float
    radius: float
    color: tuple[int, int, int]
    vy: float
    popped: bool = False
    pop_frame: int = 0


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    life: int
    radius: float = 3.0


@dataclass
class GameScore:
    score: int = 0
    combo: int = 0
    max_combo: int = 0
    lives: int = 3
    game_over: bool = False
    message: str = ""
