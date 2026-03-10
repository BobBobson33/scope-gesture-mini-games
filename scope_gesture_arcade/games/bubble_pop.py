"""Bubble Pop — Pop floating bubbles with pinch gestures."""

import math
import random

from PIL import Image, ImageDraw

from ..state import Bubble, FrameState, GameScore, GestureType
from .base import BaseGame

# Rainbow color palette for bubbles
BUBBLE_COLORS = [
    (255, 100, 100),   # red
    (255, 180, 60),    # orange
    (255, 255, 80),    # yellow
    (100, 255, 120),   # green
    (80, 200, 255),    # blue
    (160, 100, 255),   # purple
    (255, 120, 200),   # pink
]

GOLDEN = (255, 215, 0)


class BubblePopGame(BaseGame):
    """Pop floating bubbles using pinch gestures."""

    def __init__(self, spawn_rate: float = 2.0, difficulty: str = "medium"):
        super().__init__()
        self.base_spawn_rate = spawn_rate
        self.difficulty = difficulty
        self.bubbles: list[Bubble] = []
        self._frame_count = 0
        self._last_pop_frame = 0
        self._combo_window = 20  # frames for combo
        self._pop_animations: list[tuple[float, float, float, tuple[int, int, int], int]] = []
        self.reset()

    def reset(self):
        self.bubbles.clear()
        self.particles.clear()
        self._pop_animations.clear()
        self._frame_count = 0
        self._last_pop_frame = 0
        self.score = GameScore()

        diff = {"easy": 0.6, "medium": 1.0, "hard": 1.5}
        self._difficulty_mult = diff.get(self.difficulty, 1.0)

    def update(self, frame_state: FrameState, **kwargs) -> GameScore:
        if self.score.game_over:
            return self.score

        self._frame_count += 1
        w, h = frame_state.width, frame_state.height

        # Spawn bubbles
        spawn_rate = self.base_spawn_rate * self._difficulty_mult
        if random.random() < spawn_rate / 30.0:
            self._spawn_bubble(w, h)

        # Update bubble positions
        alive = []
        for b in self.bubbles:
            if b.popped:
                continue
            b.y += b.vy  # float upward (vy is negative)
            # Gentle sideways drift
            b.x += math.sin(self._frame_count * 0.05 + b.x * 0.01) * 0.5

            # Bubble escaped off top
            if b.y + b.radius < 0:
                self.score.lives -= 1
                if self.score.lives <= 0:
                    self.score.game_over = True
                    self.score.message = "Game Over!"
                continue
            alive.append(b)
        self.bubbles = alive

        # Check hand-bubble collisions
        for hand in frame_state.hands:
            hx, hy = hand.center

            # Pinch to pop
            if hand.gesture == GestureType.PINCH:
                for b in self.bubbles:
                    if b.popped:
                        continue
                    dist = math.hypot(hx - b.x, hy - b.y)
                    if dist < b.radius + 30:
                        b.popped = True
                        b.pop_frame = self._frame_count
                        self.spawn_explosion(b.x, b.y, b.color)
                        self._pop_animations.append(
                            (b.x, b.y, b.radius, b.color, self._frame_count)
                        )

                        # Combo logic
                        if self._frame_count - self._last_pop_frame < self._combo_window:
                            self.score.combo += 1
                        else:
                            self.score.combo = 1
                        self._last_pop_frame = self._frame_count
                        self.score.max_combo = max(self.score.max_combo, self.score.combo)

                        # Score: golden bubbles worth more
                        is_golden = b.color == GOLDEN
                        base_points = 25 if is_golden else 5
                        points = base_points * min(self.score.combo, 5)
                        self.score.score += points

            # Open palm pushes bubbles away
            elif hand.gesture == GestureType.OPEN_PALM:
                for b in self.bubbles:
                    if b.popped:
                        continue
                    dist = math.hypot(hx - b.x, hy - b.y)
                    if dist < b.radius + 60:
                        # Push away from hand
                        if dist > 0:
                            dx = (b.x - hx) / dist
                            dy = (b.y - hy) / dist
                            push = 3.0
                            b.x += dx * push
                            b.y += dy * push

        # Clean up pop animations
        self._pop_animations = [
            anim for anim in self._pop_animations
            if self._frame_count - anim[4] < 15
        ]

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

        # Draw bubbles
        for b in self.bubbles:
            if b.popped:
                continue
            x, y, r = int(b.x), int(b.y), int(b.radius)

            # Outer bubble (semi-transparent)
            draw.ellipse(
                [x - r, y - r, x + r, y + r],
                fill=(*b.color, 100),
                outline=(*b.color, 180),
                width=2,
            )

            # Specular highlight (top-left)
            hr = r // 3
            hx, hy = x - r // 4, y - r // 4
            draw.ellipse(
                [hx - hr, hy - hr, hx + hr, hy + hr],
                fill=(255, 255, 255, 120),
            )

            # Golden bubble indicator
            if b.color == GOLDEN:
                star_r = r // 4
                draw.regular_polygon(
                    (x, y, star_r),
                    n_sides=5,
                    rotation=0,
                    fill=(255, 255, 200, 200),
                )

        # Draw pop animations (expanding rings)
        for ax, ay, ar, acolor, aframe in self._pop_animations:
            elapsed = self._frame_count - aframe
            progress = elapsed / 15.0
            ring_r = int(ar * (1 + progress * 0.8))
            alpha = int(200 * (1 - progress))
            if alpha > 0:
                draw.ellipse(
                    [int(ax) - ring_r, int(ay) - ring_r, int(ax) + ring_r, int(ay) + ring_r],
                    outline=(*acolor, alpha),
                    width=3,
                )

        # Draw particles
        for p in self.particles:
            alpha = min(255, int(255 * p.life / 25))
            r = max(1, int(p.radius))
            draw.ellipse(
                [int(p.x) - r, int(p.y) - r, int(p.x) + r, int(p.y) + r],
                fill=(*p.color, alpha),
            )

        # Draw pinch indicators on hands
        for hand in frame_state.hands:
            if hand.gesture == GestureType.PINCH:
                hx, hy = int(hand.center[0]), int(hand.center[1])
                # Pulsing pinch circle
                pulse = int(5 * math.sin(self._frame_count * 0.3))
                pr = 20 + pulse
                draw.ellipse(
                    [hx - pr, hy - pr, hx + pr, hy + pr],
                    outline=(255, 255, 100, 180),
                    width=3,
                )

        result = Image.alpha_composite(image.convert("RGBA"), overlay)
        return result.convert("RGB")

    def _spawn_bubble(self, w: int, h: int):
        """Spawn a new bubble at the bottom of the screen."""
        radius = random.uniform(20, 50)
        x = random.uniform(radius, w - radius)
        y = h + radius

        # 10% chance of golden bubble
        if random.random() < 0.1:
            color = GOLDEN
        else:
            color = random.choice(BUBBLE_COLORS)

        speed = random.uniform(-2.5, -1.0) * self._difficulty_mult

        self.bubbles.append(
            Bubble(
                x=x,
                y=y,
                radius=radius,
                color=color,
                vy=speed,
            )
        )
