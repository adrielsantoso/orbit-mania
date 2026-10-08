"""Images, sounds and fonts, loaded from the package's assets/ folder.

Paths are relative to this file, so the game runs from any working directory.
If no audio device is available, the game runs silently instead of failing.
The starfield background is drawn by code (draw_starfield), not loaded.
"""

import random
from pathlib import Path

import pygame
import pygame.gfxdraw

ASSETS = Path(__file__).parent / "assets"


SKY = (14, 14, 14)
STAR = (230, 185, 135)
STARS = 28
STAR_SEED = 2024
CLEAR_RADIUS = 260      # no stars this close to the centre: keeps the orbits uncluttered


def draw_starfield(width: int, height: int, stars: int = STARS,
                   seed: int = STAR_SEED) -> pygame.Surface:
    """A dark sky with small warm-white stars around the edges.

    The same seed always gives the same sky.
    """
    rng = random.Random(seed)
    sky = pygame.Surface((width, height))
    sky.fill(SKY)
    cx, cy = width / 2, height / 2
    placed = 0
    while placed < stars:
        x, y = rng.randrange(width), rng.randrange(height)
        if (x - cx) ** 2 + (y - cy) ** 2 < CLEAR_RADIUS ** 2:
            continue
        placed += 1
        r = rng.choice((1, 2, 2))
        shade = rng.uniform(0.8, 1.0)
        colour = tuple(int(c * shade) for c in STAR)
        pygame.gfxdraw.filled_circle(sky, x, y, r, colour)
        pygame.gfxdraw.aacircle(sky, x, y, r, colour)
    return sky


class Silent:
    """Stands in for a pygame Sound when audio is unavailable."""

    def play(self, *args, **kwargs):
        pass

    def set_volume(self, *args):
        pass


class Assets:
    def __init__(self, width: int, height: int):
        image = lambda name: pygame.image.load(str(ASSETS / name)).convert_alpha()
        self.background = draw_starfield(width, height).convert()
        self.planet = image("planet.png")
        self.player = image("player.png")
        self.obstacle = image("obstacle.png")
        self.explosion = image("explosion.png")
        self.shield = image("shield.png")
        self.energy_packet = image("energy_packet.png")

        self.large_font = pygame.font.Font(None, 64)
        self.small_font = pygame.font.Font(None, 40)

        self.audio = self._init_audio()
        sound = (lambda name, volume: self._sound(name, volume)) if self.audio else \
                (lambda name, volume: Silent())
        self.shield_sound = sound("activate_shield.mp3", 1.0)
        self.packet_sound = sound("energy_packet.mp3", 1.0)
        self.game_over_sound = sound("game_over.mp3", 1.0)

    @staticmethod
    def _init_audio() -> bool:
        try:
            pygame.mixer.init()
        except pygame.error:
            return False
        return True

    @staticmethod
    def _sound(name: str, volume: float):
        s = pygame.mixer.Sound(str(ASSETS / name))
        s.set_volume(volume)
        return s

    def play_music(self) -> None:
        if self.audio:
            pygame.mixer.music.load(str(ASSETS / "background_music.mp3"))
            pygame.mixer.music.play(-1)

    def stop_music(self) -> None:
        if self.audio:
            pygame.mixer.music.stop()
