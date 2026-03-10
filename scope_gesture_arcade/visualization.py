"""Shared visualization helpers for hand skeleton, HUD, and gesture labels."""

from PIL import Image, ImageDraw, ImageFont

from .state import FrameState, GameScore, GestureType, HandState

# MediaPipe hand connections (pairs of landmark indices)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),       # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),       # Index
    (0, 9), (9, 10), (10, 11), (11, 12),   # Middle  (fixed: 0→9 not 5→9)
    (0, 13), (13, 14), (14, 15), (15, 16), # Ring    (fixed: 0→13)
    (0, 17), (17, 18), (18, 19), (19, 20), # Pinky   (fixed: 0→17)
    (5, 9), (9, 13), (13, 17),             # Palm
]

# Colors per finger group
FINGER_COLORS = {
    "thumb": (255, 100, 100),
    "index": (100, 255, 100),
    "middle": (100, 100, 255),
    "ring": (255, 255, 100),
    "pinky": (255, 100, 255),
    "palm": (200, 200, 200),
}


def _get_connection_color(i: int) -> tuple[int, int, int]:
    if i < 4:
        return FINGER_COLORS["thumb"]
    elif i < 8:
        return FINGER_COLORS["index"]
    elif i < 12:
        return FINGER_COLORS["middle"]
    elif i < 16:
        return FINGER_COLORS["ring"]
    elif i < 20:
        return FINGER_COLORS["pinky"]
    return FINGER_COLORS["palm"]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except (OSError, IOError):
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
        except (OSError, IOError):
            return ImageFont.load_default()


GESTURE_LABELS = {
    GestureType.NONE: "",
    GestureType.OPEN_PALM: "Open Palm",
    GestureType.FIST: "Fist",
    GestureType.PINCH: "Pinch",
    GestureType.POINTING: "Pointing",
    GestureType.PEACE: "Peace",
    GestureType.SLASH: "Slash!",
}


def draw_hand_skeleton(
    draw: ImageDraw.ImageDraw,
    hand: HandState,
    alpha: int = 200,
):
    """Draw the 21-landmark hand skeleton with connections."""
    pts = hand.pixel_landmarks
    if len(pts) < 21:
        return

    # Draw connections
    for i, (a, b) in enumerate(HAND_CONNECTIONS):
        color = _get_connection_color(i)
        draw.line(
            [pts[a], pts[b]],
            fill=(*color, alpha),
            width=2,
        )

    # Draw landmark dots
    for px, py in pts:
        draw.ellipse(
            [px - 3, py - 3, px + 3, py + 3],
            fill=(255, 255, 255, alpha),
        )


def draw_gesture_label(
    draw: ImageDraw.ImageDraw,
    hand: HandState,
):
    """Draw the detected gesture name near the hand."""
    label = GESTURE_LABELS.get(hand.gesture, "")
    if not label:
        return

    font = _load_font(16)
    x, y = int(hand.center[0]), int(hand.center[1]) - 40
    bbox = draw.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # Background pill
    padding = 4
    draw.rounded_rectangle(
        [x - tw // 2 - padding, y - padding, x + tw // 2 + padding, y + th + padding],
        radius=8,
        fill=(0, 0, 0, 150),
    )
    draw.text(
        (x - tw // 2, y),
        label,
        fill=(255, 255, 255, 230),
        font=font,
    )


def draw_score_hud(
    draw: ImageDraw.ImageDraw,
    score: GameScore,
    game_name: str,
    width: int,
):
    """Draw the score/combo/lives HUD at the top of the frame."""
    font = _load_font(18)
    small_font = _load_font(14)

    # Semi-transparent background bar
    draw.rectangle(
        [0, 0, width, 50],
        fill=(0, 0, 0, 120),
    )

    # Game name (left)
    draw.text((10, 5), game_name, fill=(255, 255, 255, 220), font=font)

    # Score (center-ish)
    score_text = f"Score: {score.score}"
    bbox = draw.textbbox((0, 0), score_text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(
        (width // 2 - tw // 2, 5),
        score_text,
        fill=(255, 255, 100, 230),
        font=font,
    )

    # Combo (below score if active)
    if score.combo > 1:
        combo_text = f"x{score.combo} Combo!"
        bbox = draw.textbbox((0, 0), combo_text, font=small_font)
        tw = bbox[2] - bbox[0]
        draw.text(
            (width // 2 - tw // 2, 28),
            combo_text,
            fill=(255, 180, 50, 230),
            font=small_font,
        )

    # Lives (right) — draw hearts
    if score.lives < 999:
        hearts = "♥ " * score.lives
        bbox = draw.textbbox((0, 0), hearts, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(
            (width - tw - 10, 5),
            hearts,
            fill=(255, 80, 80, 230),
            font=font,
        )

    # Custom message (pong score, etc.)
    if score.message and score.lives >= 999:
        bbox = draw.textbbox((0, 0), score.message, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(
            (width - tw - 10, 5),
            score.message,
            fill=(255, 255, 255, 220),
            font=font,
        )


def draw_game_over(
    draw: ImageDraw.ImageDraw,
    score: GameScore,
    width: int,
    height: int,
):
    """Draw a game-over overlay."""
    # Darken background
    draw.rectangle(
        [0, 0, width, height],
        fill=(0, 0, 0, 160),
    )

    title_font = _load_font(48)
    body_font = _load_font(24)
    small_font = _load_font(18)

    # Title
    title = score.message or "Game Over"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((width - tw) // 2, height // 2 - 60),
        title,
        fill=(255, 80, 80, 240),
        font=title_font,
    )

    # Final score
    score_text = f"Final Score: {score.score}"
    bbox = draw.textbbox((0, 0), score_text, font=body_font)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((width - tw) // 2, height // 2 + 10),
        score_text,
        fill=(255, 255, 255, 220),
        font=body_font,
    )

    # Max combo
    if score.max_combo > 1:
        combo_text = f"Best Combo: x{score.max_combo}"
        bbox = draw.textbbox((0, 0), combo_text, font=small_font)
        tw = bbox[2] - bbox[0]
        draw.text(
            ((width - tw) // 2, height // 2 + 50),
            combo_text,
            fill=(255, 200, 80, 200),
            font=small_font,
        )


def render_overlay(
    image: Image.Image,
    frame_state: FrameState,
    score: GameScore,
    game_name: str,
    show_skeleton: bool = True,
    show_labels: bool = True,
    show_hud: bool = True,
) -> Image.Image:
    """Draw the shared HUD and hand overlays on top of the game-rendered frame."""
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = image.size

    # Hand skeleton
    if show_skeleton:
        for hand in frame_state.hands:
            draw_hand_skeleton(draw, hand)

    # Gesture labels
    if show_labels:
        for hand in frame_state.hands:
            draw_gesture_label(draw, hand)

    # Score HUD
    if show_hud:
        draw_score_hud(draw, score, game_name, w)

    # Game over screen
    if score.game_over:
        draw_game_over(draw, score, w, h)

    result = Image.alpha_composite(image.convert("RGBA"), overlay)
    return result.convert("RGB")
