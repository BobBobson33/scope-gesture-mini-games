"""Gesture Smash — Fruit Ninja-style target slashing game."""

import math
import random

from PIL import Image, ImageDraw

from ..state import FrameState, GameScore, GestureType, Target
from .base import BaseGame

# Target color palette
TARGET_COLORS = [
    (255, 60, 60),    # red
    (255, 160, 40),   # orange
    (180, 60, 255),   # purple
    (40, 220, 255),   # cyan
    (60, 255, 100),   # green
    (255, 220, 40),   # yellow
]


class GestureSmashGame(BaseGame):
    """Slash and smash targets using hand gestures."""

    def __init__(self, spawn_rate: float = 1.5, difficulty: str = "medium"):
        super().__init__()
        self.base_spawn_rate = spawn_rate
        self.difficulty = difficulty
        self.targets: list[Target] = []
        self._frame_count = 0
        self._last_hit_frame = 0
        self._combo_window = 30  # frames for combo
        self._trail_positions: list[list[tuple[float, float]]] = []
        self.reset()

    def reset(self):
        self.targets.clear()
        self.particles.clear()
        self._trail_positions.clear()
        self._frame_count = 0
        self._last_hit_frame = 0
        self.score = GameScore()

        diff = {"easy": 0.7, "medium": 1.0, "hard": 1.5}
        self._difficulty_mult = diff.get(self.difficulty, 1.0)

    def update(self, frame_state: FrameState, **kwargs) -> GameScore:
        if self.score.game_over:
            return self.score

        self._frame_count += 1
        w, h = frame_state.width, frame_state.height

        # Spawn targets
        spawn_rate = self.base_spawn_rate * self._difficulty_mult
        # Increase spawn rate with score
        spawn_rate += self.score.score / 500.0
        if random.random() < spawn_rate / 30.0:  # normalized per frame at ~30fps
            self._spawn_target(w, h)

        # Update target positions
        alive_targets = []
        for t in self.targets:
            if not t.alive:
                continue
            t.x += t.vx
            t.y += t.vy
            t.vy += 0.3 * self._difficulty_mult  # gravity

            # Check if target left screen
            if t.y > h + t.radius or t.x < -t.radius or t.x > w + t.radius:
                self.score.lives -= 1
                if self.score.lives <= 0:
                    self.score.game_over = True
                    self.score.message = "Game Over!"
                continue
            alive_targets.append(t)
        self.targets = alive_targets

        # Update trail positions
        self._trail_positions = []
        for hand in frame_state.hands:
            self._trail_positions.append(
                [hand.center]
            )

        # Check hand-target collisions
        for hand in frame_state.hands:
            can_hit = hand.gesture in (
                GestureType.SLASH,
                GestureType.FIST,
                GestureType.OPEN_PALM,
            )
            if not can_hit:
                continue

            # Larger hit radius for slash
            hit_radius = 60 if hand.gesture == GestureType.SLASH else 45

            hx, hy = hand.center
            for t in self.targets:
                if not t.alive:
                    continue
                dist = math.hypot(hx - t.x, hy - t.y)
                if dist < t.radius + hit_radius:
                    t.alive = False
                    self.spawn_explosion(t.x, t.y, t.color)

                    # Combo logic
                    if self._frame_count - self._last_hit_frame < self._combo_window:
                        self.score.combo += 1
                    else:
                        self.score.combo = 1
                    self._last_hit_frame = self._frame_count
                    self.score.max_combo = max(self.score.max_combo, self.score.combo)

                    # Score with combo multiplier
                    points = 10 * min(self.score.combo, 5)
                    self.score.score += points

        self.update_particles()
        return self.score

    def render(
        self,
        image: Image.Image,
        frame_state: FrameState,
        score: GameScore,
        **kwargs,
    ) -> Image.Image:
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Draw targets
        for t in self.targets:
            if not t.alive:
                continue
            r = int(t.radius)
            x, y = int(t.x), int(t.y)

            # Outer glow
            draw.ellipse(
                [x - r - 4, y - r - 4, x + r + 4, y + r + 4],
                fill=(*t.color, 80),
            )
            # Main circle
            draw.ellipse(
                [x - r, y - r, x + r, y + r],
                fill=(*t.color, 220),
            )
            # Inner highlight
            inner_r = r // 3
            draw.ellipse(
                [x - inner_r, y - inner_r, x + inner_r, y + inner_r],
                fill=(255, 255, 255, 120),
            )

        # Draw slash trails for fast-moving hands
        for hand in frame_state.hands:
            if hand.speed > 15:
                hx, hy = int(hand.center[0]), int(hand.center[1])
                trail_len = min(int(hand.speed * 1.5), 80)
                if hand.speed > 0:
                    nx = -hand.velocity[0] / hand.speed
                    ny = -hand.velocity[1] / hand.speed
                    ex, ey = int(hx + nx * trail_len), int(hy + ny * trail_len)
                    draw.line(
                        [(hx, hy), (ex, ey)],
                        fill=(255, 255, 255, 150),
                        width=4,
                    )

        # Draw particles
        for p in self.particles:
            alpha = min(255, int(255 * p.life / 25))
            r = max(1, int(p.radius))
            draw.ellipse(
                [int(p.x) - r, int(p.y) - r, int(p.x) + r, int(p.y) + r],
                fill=(*p.color, alpha),
            )

        result = Image.alpha_composite(image.convert("RGBA"), overlay)
        return result.convert("RGB")

    def _spawn_target(self, w: int, h: int):
        """Spawn a new target from a random edge."""
        side = random.choice(["bottom", "left", "right"])
        radius = random.uniform(25, 55)
        color = random.choice(TARGET_COLORS)

        if side == "bottom":
            x = random.uniform(radius, w - radius)
            y = h + radius
            vx = random.uniform(-3, 3)
            vy = random.uniform(-12, -7) * self._difficulty_mult
        elif side == "left":
            x = -radius
            y = random.uniform(h * 0.3, h * 0.7)
            vx = random.uniform(3, 7) * self._difficulty_mult
            vy = random.uniform(-5, -2)
        else:
            x = w + radius
            y = random.uniform(h * 0.3, h * 0.7)
            vx = random.uniform(-7, -3) * self._difficulty_mult
            vy = random.uniform(-5, -2)

        self.targets.append(
            Target(
                x=x,
                y=y,
                radius=radius,
                color=color,
                vx=vx,
                vy=vy,
                spawn_frame=self._frame_count,
            )
        )
