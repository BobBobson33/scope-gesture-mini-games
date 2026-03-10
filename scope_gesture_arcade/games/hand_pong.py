"""Hand Pong — Classic Pong with hand-controlled paddles."""

import random

from PIL import Image, ImageDraw, ImageFont

from ..state import Ball, FrameState, GameScore, GestureType
from .base import BaseGame

PADDLE_WIDTH = 16
PADDLE_HEIGHT = 100
PADDLE_MARGIN = 30


class HandPongGame(BaseGame):
    """Two-player Pong controlled by hand position."""

    def __init__(self, ball_speed: float = 6.0, difficulty: str = "medium"):
        super().__init__()
        self.base_ball_speed = ball_speed
        self.difficulty = difficulty
        self.ball = Ball(x=0, y=0, vx=0, vy=0)
        self._left_paddle_y = 0.0
        self._right_paddle_y = 0.0
        self._left_score = 0
        self._right_score = 0
        self._ball_waiting = True
        self._volley_count = 0
        self._ai_paddle_speed = 4.0
        self._frame_count = 0
        self.reset()

    def reset(self):
        self.particles.clear()
        self._left_score = 0
        self._right_score = 0
        self._volley_count = 0
        self._frame_count = 0
        self.score = GameScore(lives=999)  # Lives not used in pong
        self._ball_waiting = True

        diff = {"easy": 0.7, "medium": 1.0, "hard": 1.4}
        self._difficulty_mult = diff.get(self.difficulty, 1.0)

    def _serve_ball(self, w: int, h: int):
        self.ball.x = w / 2
        self.ball.y = h / 2
        speed = self.base_ball_speed * self._difficulty_mult
        direction = random.choice([-1, 1])
        self.ball.vx = speed * direction
        self.ball.vy = random.uniform(-speed * 0.5, speed * 0.5)
        self._ball_waiting = False
        self._volley_count = 0

    def update(self, frame_state: FrameState, **kwargs) -> GameScore:
        self._frame_count += 1
        w, h = frame_state.width, frame_state.height

        # Default paddle positions (center)
        if self._frame_count == 1:
            self._left_paddle_y = h / 2
            self._right_paddle_y = h / 2

        # Track hands to paddles
        left_hand = None
        right_hand = None
        for hand in frame_state.hands:
            # MediaPipe mirrors: "Left" label = user's left = screen right
            if hand.handedness == "Left":
                right_hand = hand
            else:
                left_hand = hand

        # Move paddles to hand positions
        if left_hand:
            self._left_paddle_y = left_hand.center[1]
        if right_hand:
            self._right_paddle_y = right_hand.center[1]

        # AI for missing hand
        if not left_hand:
            self._ai_move_paddle("left", h)
        if not right_hand:
            self._ai_move_paddle("right", h)

        # Clamp paddles
        half = PADDLE_HEIGHT / 2
        self._left_paddle_y = max(half, min(h - half, self._left_paddle_y))
        self._right_paddle_y = max(half, min(h - half, self._right_paddle_y))

        # Serve on fist gesture
        if self._ball_waiting:
            for hand in frame_state.hands:
                if hand.gesture == GestureType.FIST:
                    self._serve_ball(w, h)
                    break
            # Auto-serve after 90 frames
            if self._ball_waiting and self._frame_count > 90:
                self._serve_ball(w, h)
            self.score.score = self._left_score + self._right_score
            self.score.message = f"{self._left_score} - {self._right_score}"
            return self.score

        # Move ball
        self.ball.x += self.ball.vx
        self.ball.y += self.ball.vy

        # Top/bottom wall bounce
        if self.ball.y - self.ball.radius <= 0:
            self.ball.y = self.ball.radius
            self.ball.vy = abs(self.ball.vy)
        elif self.ball.y + self.ball.radius >= h:
            self.ball.y = h - self.ball.radius
            self.ball.vy = -abs(self.ball.vy)

        # Left paddle collision
        lx = PADDLE_MARGIN + PADDLE_WIDTH
        if (
            self.ball.x - self.ball.radius <= lx
            and self.ball.vx < 0
            and abs(self.ball.y - self._left_paddle_y) < half + self.ball.radius
        ):
            self.ball.x = lx + self.ball.radius
            self.ball.vx = abs(self.ball.vx)
            # Add angle based on where ball hits paddle
            offset = (self.ball.y - self._left_paddle_y) / half
            self.ball.vy += offset * 3
            self._volley_count += 1
            # Speed up slightly
            self.ball.vx *= 1.05
            self.spawn_explosion(self.ball.x, self.ball.y, (100, 200, 255), count=6)

        # Right paddle collision
        rx = w - PADDLE_MARGIN - PADDLE_WIDTH
        if (
            self.ball.x + self.ball.radius >= rx
            and self.ball.vx > 0
            and abs(self.ball.y - self._right_paddle_y) < half + self.ball.radius
        ):
            self.ball.x = rx - self.ball.radius
            self.ball.vx = -abs(self.ball.vx)
            offset = (self.ball.y - self._right_paddle_y) / half
            self.ball.vy += offset * 3
            self._volley_count += 1
            self.ball.vx *= 1.05
            self.spawn_explosion(self.ball.x, self.ball.y, (255, 150, 100), count=6)

        # Scoring
        if self.ball.x < 0:
            self._right_score += 1
            self.spawn_explosion(0, self.ball.y, (255, 60, 60), count=15)
            self._ball_waiting = True
        elif self.ball.x > w:
            self._left_score += 1
            self.spawn_explosion(w, self.ball.y, (60, 60, 255), count=15)
            self._ball_waiting = True

        # Cap ball speed
        max_speed = 20 * self._difficulty_mult
        if abs(self.ball.vx) > max_speed:
            self.ball.vx = max_speed * (1 if self.ball.vx > 0 else -1)
        if abs(self.ball.vy) > max_speed:
            self.ball.vy = max_speed * (1 if self.ball.vy > 0 else -1)

        # Check win condition
        win_score = 7
        if self._left_score >= win_score:
            self.score.game_over = True
            self.score.message = f"Left Wins! {self._left_score}-{self._right_score}"
        elif self._right_score >= win_score:
            self.score.game_over = True
            self.score.message = f"Right Wins! {self._left_score}-{self._right_score}"
        else:
            self.score.message = f"{self._left_score} - {self._right_score}"

        self.score.score = self._left_score + self._right_score
        self.score.combo = self._volley_count
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
        w, h = image.size

        # Center line (dashed)
        for y in range(0, h, 20):
            draw.line(
                [(w // 2, y), (w // 2, min(y + 10, h))],
                fill=(255, 255, 255, 60),
                width=2,
            )

        # Left paddle
        lpy = int(self._left_paddle_y)
        draw.rounded_rectangle(
            [
                PADDLE_MARGIN,
                lpy - PADDLE_HEIGHT // 2,
                PADDLE_MARGIN + PADDLE_WIDTH,
                lpy + PADDLE_HEIGHT // 2,
            ],
            radius=PADDLE_WIDTH // 2,
            fill=(100, 180, 255, 220),
        )

        # Right paddle
        rpy = int(self._right_paddle_y)
        draw.rounded_rectangle(
            [
                w - PADDLE_MARGIN - PADDLE_WIDTH,
                rpy - PADDLE_HEIGHT // 2,
                w - PADDLE_MARGIN,
                rpy + PADDLE_HEIGHT // 2,
            ],
            radius=PADDLE_WIDTH // 2,
            fill=(255, 140, 80, 220),
        )

        # Ball
        if not self._ball_waiting:
            bx, by = int(self.ball.x), int(self.ball.y)
            br = int(self.ball.radius)
            # Glow
            draw.ellipse(
                [bx - br - 4, by - br - 4, bx + br + 4, by + br + 4],
                fill=(255, 255, 255, 60),
            )
            # Ball
            draw.ellipse(
                [bx - br, by - br, bx + br, by + br],
                fill=(255, 255, 255, 240),
            )
        else:
            # "Fist to serve" hint
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
            except (OSError, IOError):
                font = ImageFont.load_default()
            text = "Make a FIST to serve!"
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            draw.text(
                ((w - tw) // 2, h // 2 + 30),
                text,
                fill=(255, 255, 255, 200),
                font=font,
            )

        # Score display
        try:
            score_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
        except (OSError, IOError):
            score_font = ImageFont.load_default()

        draw.text(
            (w // 2 - 80, 20),
            str(self._left_score),
            fill=(100, 180, 255, 200),
            font=score_font,
        )
        draw.text(
            (w // 2 + 50, 20),
            str(self._right_score),
            fill=(255, 140, 80, 200),
            font=score_font,
        )

        # Particles
        for p in self.particles:
            alpha = min(255, int(255 * p.life / 25))
            r = max(1, int(p.radius))
            draw.ellipse(
                [int(p.x) - r, int(p.y) - r, int(p.x) + r, int(p.y) + r],
                fill=(*p.color, alpha),
            )

        result = Image.alpha_composite(image.convert("RGBA"), overlay)
        return result.convert("RGB")

    def _ai_move_paddle(self, side: str, h: int):
        """Simple AI paddle movement tracking the ball."""
        target_y = self.ball.y if not self._ball_waiting else h / 2
        speed = self._ai_paddle_speed * self._difficulty_mult

        if side == "left":
            diff = target_y - self._left_paddle_y
            self._left_paddle_y += max(-speed, min(speed, diff))
        else:
            diff = target_y - self._right_paddle_y
            self._right_paddle_y += max(-speed, min(speed, diff))
