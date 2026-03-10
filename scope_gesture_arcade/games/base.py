"""Abstract base class for all gesture arcade games."""

from abc import ABC, abstractmethod

from PIL import Image

from ..state import FrameState, GameScore, Particle


class BaseGame(ABC):
    """Interface that all mini-games must implement."""

    def __init__(self):
        self.particles: list[Particle] = []
        self.score = GameScore()

    @abstractmethod
    def reset(self):
        """Reset game state to initial conditions."""
        ...

    @abstractmethod
    def update(self, frame_state: FrameState, **kwargs) -> GameScore:
        """Advance game logic by one frame.

        Args:
            frame_state: Current frame's hand detection results.

        Returns:
            Updated game score.
        """
        ...

    @abstractmethod
    def render(
        self,
        image: Image.Image,
        frame_state: FrameState,
        score: GameScore,
        **kwargs,
    ) -> Image.Image:
        """Render game objects onto the frame.

        Args:
            image: Base PIL image to draw on.
            frame_state: Current frame's hand state.
            score: Current game score.

        Returns:
            Annotated image with game objects.
        """
        ...

    def update_particles(self):
        """Tick all active particles and remove dead ones."""
        alive = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.5  # gravity
            p.life -= 1
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def spawn_explosion(
        self,
        x: float,
        y: float,
        color: tuple[int, int, int],
        count: int = 12,
    ):
        """Spawn burst particles at a position."""
        import math
        import random

        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 8)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    color=color,
                    life=random.randint(10, 25),
                    radius=random.uniform(2, 5),
                )
            )
