"""Regenerate the README screenshots in docs/images/.

    python scripts/make_screenshots.py

Plays a short seeded game without opening a window (dodging with the shield
when an asteroid comes close) and saves three frames: gameplay, shield, and
the game over screen. It uses a temporary high-score file, so your own
scores are not touched. Run it after changing anything visible.
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from orbit_mania import app as orbit_app  # noqa: E402

OUT = ROOT / "docs" / "images"


def attempt(seed: int, scores_file: Path) -> bool:
    a = orbit_app.App(seed=seed, scores_path=scores_file)
    g = a.game

    def play_frame(shield_if_close: bool = True) -> bool:
        sx, sy = g.ship
        close = any((o.x - sx) ** 2 + (o.y - sy) ** 2 < 60 ** 2 for o in g.obstacles)
        g.step(shield=shield_if_close and close)
        if g.fuel < 40:
            g.fuel = 70                      # keep the demo going
        return not g.over

    # Gameplay: at least 12 s in, with packets and asteroids on screen.
    while g.frame < 720 or len(g.packets) < 2 or len(g.obstacles) < 3:
        if not play_frame():
            return False
    a.draw()
    pygame.image.save(a.screen, str(OUT / "gameplay.png"))

    # Shield: move to the outer orbit, then raise the shield.
    g.step(switch=True)
    for _ in range(240):
        if not play_frame():
            return False
    for _ in range(6):
        g.step(shield=True)
    a.draw()
    pygame.image.save(a.screen, str(OUT / "shield.png"))

    # Game over: run out of fuel, capture the final screen instead of waiting.
    waits = []

    def capture(ms):
        waits.append(ms)
        if len(waits) == 2:                  # second pause = game over screen
            pygame.image.save(a.screen, str(OUT / "game-over.png"))

    orbit_app.pygame.time.wait = capture
    g.fuel = 0.01
    a.run()
    print(f"seed {seed}: saved gameplay.png, shield.png, game-over.png to {OUT}")
    return True


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for seed in range(11, 100):
            if attempt(seed, Path(tmp) / f"scores-{seed}.json"):
                return
    sys.exit("No seed produced a full demo; adjust the script.")


if __name__ == "__main__":
    main()
