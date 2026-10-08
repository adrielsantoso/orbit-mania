"""The Pygame window: reads the keyboard, steps the game, draws each frame.

Controls: Space switches orbit, holding S raises the shield, F11 toggles
fullscreen, Esc quits. The game is drawn at 800x600 and scaled to fit the
window or screen, so fullscreen shows the same layout, just larger.
Finished games are saved to the player's high scores (see scores.py).
"""

import argparse
import os
from pathlib import Path

import pygame
import pygame.gfxdraw

from . import scores
from .assets import Assets
from .game import INNER_ORBIT, MAX_FUEL, OUTER_ORBIT, Game

WIDTH, HEIGHT = 800, 600
CENTER = (WIDTH // 2, HEIGHT // 2)
FPS = 60
WINDOW_FRACTION = 0.75      # window height as a fraction of the screen height

WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 200, 255)
GREY = (180, 180, 180)


def format_time(seconds: float) -> str:
    return f"{int(seconds // 60):02}:{int(seconds % 60):02}"


_window = None              # see App.resize_window


def window_size(screen_width: int, screen_height: int) -> tuple[int, int]:
    """Window size with the game's 4:3 shape, WINDOW_FRACTION of the screen height.

    On a screen narrower than 4:3 (e.g. portrait) the width limits it instead.
    Never smaller than 800x600, which pygame's SCALED mode will not shrink below.
    """
    scale = max(1.0, WINDOW_FRACTION * min(screen_width / WIDTH, screen_height / HEIGHT))
    return round(WIDTH * scale), round(HEIGHT * scale)


class App:
    def __init__(self, seed: int | None = None, scores_path: Path | None = None,
                 fullscreen: bool = False):
        # Without these, pygame's SCALED window only scales by whole numbers
        # (1x, 2x, ...) and fills the rest of the window with a black border.
        # The first (pygame's own spelling) allows any scale, so the game fills
        # the window; the second (SDL) smooths the scaled image.
        os.environ.setdefault("SDL_HINT_RENDER_SCALE_QUALITY", "1")
        os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "1")
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED)
        pygame.display.set_caption("Orbit Mania")
        self.resize_window()
        if fullscreen:
            self.toggle_fullscreen()
        self.assets = Assets(WIDTH, HEIGHT)
        self.clock = pygame.time.Clock()
        self.game = Game(seed=seed)
        self.shield_was_on = False
        self.scores_path = scores_path or scores.default_path()
        self.best = scores.best(self.scores_path)

    def draw_at(self, image: pygame.Surface, x: float, y: float) -> None:
        """Draw an image centred on a point given relative to the planet."""
        rect = image.get_rect(center=(int(x + CENTER[0]), int(y + CENTER[1])))
        self.screen.blit(image, rect)

    def run(self, max_frames: int | None = None) -> float:
        """Play until the game ends, the window closes or max_frames pass.

        Returns the survival time in seconds (frames / FPS).
        """
        self.assets.play_music()
        running = True
        while running and not self.game.over:
            switch = False
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_F11:
                        self.toggle_fullscreen()
                    elif event.key == pygame.K_SPACE:
                        switch = True
            shield = pygame.key.get_pressed()[pygame.K_s]

            events = self.game.step(switch=switch, shield=bool(shield))
            if events.packets_collected:
                self.assets.packet_sound.play()
            if self.game.shield and not self.shield_was_on:
                self.assets.shield_sound.play()
            self.shield_was_on = self.game.shield

            if events.game_over:
                self.game_over()
                break
            self.draw()
            self.clock.tick(FPS)
            if max_frames is not None and self.game.frame >= max_frames:
                break

        pygame.quit()
        return self.game.frame / FPS

    def resize_window(self) -> None:
        """Set the window to window_size() of its screen; keep pygame's size if unsupported.

        Pygame 2 has no public call to resize a window, so this uses its
        pygame._sdl2 module. The Window object is kept in _window on purpose:
        pygame points the SDL window back at it, and if it were freed the next
        window event would crash the game.
        """
        global _window
        try:
            from pygame._sdl2.video import WINDOWPOS_CENTERED, Window
            _window = Window.from_display_module()
            screen = pygame.display.get_desktop_sizes()[_window.display_index]
            _window.size = window_size(*screen)
            _window.position = WINDOWPOS_CENTERED
        except (ImportError, AttributeError, IndexError, pygame.error):
            pass

    def toggle_fullscreen(self) -> None:
        """Switch between window and fullscreen; ignored where unsupported."""
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            pass

    def draw(self) -> None:
        g, a = self.game, self.assets
        self.screen.blit(a.background, (0, 0))
        for r in (INNER_ORBIT, OUTER_ORBIT):                  # anti-aliased: smooth when scaled up
            pygame.gfxdraw.aacircle(self.screen, *CENTER, int(r), WHITE)
        self.draw_at(a.planet, 0, 0)
        for p in g.packets:
            self.draw_at(a.energy_packet, p.x, p.y)
        for ob in g.obstacles:
            self.draw_at(a.obstacle, ob.x, ob.y)
        x, y = g.ship
        if g.shield:
            self.draw_at(a.shield, x, y)
        self.draw_at(a.player, x, y)
        self.draw_hud()
        pygame.display.flip()

    def draw_hud(self) -> None:
        g, a = self.game, self.assets
        self.screen.blit(a.small_font.render("Fuel", True, WHITE), (20, 10))
        pygame.draw.rect(self.screen, WHITE, (20, 40, 200, 20), 3)
        pygame.draw.rect(self.screen, YELLOW, (20, 40, int(200 * g.fuel / MAX_FUEL), 20))
        orbit = a.small_font.render(f"Orbit: {g.radius:.0f} px", True, CYAN)
        self.screen.blit(orbit, (20, 70))
        if self.best is not None:
            best = a.small_font.render(f"Best: {format_time(self.best)}", True, GREY)
            self.screen.blit(best, best.get_rect(topright=(WIDTH - 10, 60)))
        clock = a.large_font.render(format_time(g.frame / FPS), True, YELLOW)
        self.screen.blit(clock, clock.get_rect(topright=(WIDTH - 10, 10)))
        hint = a.small_font.render("SPACE: orbit  |  S: shield  |  F11: fullscreen", True, GREY)
        self.screen.blit(hint, hint.get_rect(midbottom=(WIDTH // 2, HEIGHT - 5)))

    def game_over(self) -> None:
        a = self.assets
        seconds = self.game.frame / FPS
        rank = scores.record(self.scores_path, seconds)
        x, y = self.game.ship
        self.draw_at(a.explosion, x, y)
        pygame.display.flip()
        a.stop_music()
        a.game_over_sound.play()
        pygame.time.wait(500)

        self.screen.blit(a.background, (0, 0))
        title = a.large_font.render("GAME OVER", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 150)))
        time = a.small_font.render(f"Time: {format_time(seconds)}", True, WHITE)
        self.screen.blit(time, time.get_rect(center=(WIDTH // 2, 210)))
        if rank == 1:
            note = "New high score!"
        elif rank is not None:
            note = f"#{rank} on your high scores"
        else:
            note = ""
        if note:
            line = a.small_font.render(note, True, YELLOW)
            self.screen.blit(line, line.get_rect(center=(WIDTH // 2, 250)))
        for i, s in enumerate(scores.load(self.scores_path)[:5], 1):
            colour = YELLOW if i == rank else GREY
            row = a.small_font.render(f"{i}.  {format_time(s['seconds'])}   {s['date']}", True, colour)
            self.screen.blit(row, row.get_rect(center=(WIDTH // 2, 290 + 40 * i)))
        pygame.display.flip()
        pygame.time.wait(3500)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="orbit-mania", description="Play Orbit Mania.")
    parser.add_argument("--seed", type=int, default=None,
                        help="fix the random asteroid and packet pattern")
    parser.add_argument("--fullscreen", action="store_true",
                        help="start in fullscreen (F11 switches at any time)")
    parser.add_argument("--scores", type=Path, default=None,
                        help=f"high-score file (default: {scores.default_path()})")
    args = parser.parse_args(argv)
    App(seed=args.seed, scores_path=args.scores, fullscreen=args.fullscreen).run()
