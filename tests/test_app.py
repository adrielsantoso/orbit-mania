"""The real Pygame window, run headless for a few seconds of play."""

import os

import pytest

pygame = pytest.importorskip("pygame")


@pytest.fixture(autouse=True)
def headless(monkeypatch, tmp_path):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    # never touch the real high-score file while testing
    monkeypatch.setenv("ORBIT_MANIA_SCORES", str(tmp_path / "highscores.json"))


def test_assets_load_and_frames_render():
    from orbit_mania.app import App
    app = App(seed=3)
    seconds = app.run(max_frames=180)
    assert seconds == pytest.approx(3.0)


def test_game_runs_from_any_working_directory(tmp_path, monkeypatch):
    from orbit_mania.app import App
    monkeypatch.chdir(tmp_path)               # assets must not depend on the cwd
    App(seed=3).run(max_frames=10)


def test_format_time():
    from orbit_mania.app import format_time
    assert format_time(0) == "00:00"
    assert format_time(75.9) == "01:15"


def test_window_is_three_quarters_of_the_screen_height():
    from orbit_mania.app import window_size
    assert window_size(1920, 1080) == (1080, 810)
    assert window_size(2880, 1800) == (1800, 1350)
    assert window_size(1080, 1920) == (810, 608)          # portrait: width limits it
    assert window_size(1024, 768) == (800, 600)           # never below the game size


def test_window_opens_at_that_size_and_draws_at_800x600(tmp_path, monkeypatch):
    from orbit_mania import app as app_module
    monkeypatch.setattr(app_module.pygame.display, "get_desktop_sizes", lambda: [(1920, 1080)])
    a = app_module.App(seed=3, scores_path=tmp_path / "s.json")
    assert pygame.display.get_window_size() == (1080, 810)
    assert a.screen.get_size() == (800, 600)              # drawing size unchanged
    a.run(max_frames=5)                                   # window events must not crash


def test_game_fills_the_window_without_black_borders(tmp_path, monkeypatch):
    import os
    from orbit_mania.app import App
    monkeypatch.delenv("SDL_HINT_RENDER_SCALE_QUALITY", raising=False)
    monkeypatch.delenv("SDL_RENDER_SCALE_QUALITY", raising=False)
    App(seed=3, scores_path=tmp_path / "s.json").run(max_frames=2)
    assert os.environ["SDL_HINT_RENDER_SCALE_QUALITY"] == "1"     # any scale, not only 1x, 2x
    assert os.environ["SDL_RENDER_SCALE_QUALITY"] == "1"          # smooth scaling


def test_orbits_are_drawn_smooth(tmp_path):
    from orbit_mania.app import App, CENTER
    from orbit_mania.assets import SKY
    from orbit_mania.game import OUTER_ORBIT
    a = App(seed=3, scores_path=tmp_path / "s.json")
    a.draw()
    x0, y0 = CENTER[0] + 150, CENTER[1] - 170                # on the outer orbit, away from sprites and HUD
    shades = {tuple(a.screen.get_at((x, y)))[:3] for x in range(x0, x0 + 20) for y in range(y0 - 20, y0 + 20)}
    assert any(px != SKY and px != (255, 255, 255) for px in shades)   # in-between greys = anti-aliased
    pygame.quit()


def test_starfield_is_drawn_not_loaded():
    from orbit_mania.assets import ASSETS, SKY, STARS, draw_starfield
    assert not (ASSETS / "background.png").exists()
    pygame.init()
    sky = draw_starfield(800, 600)
    assert sky.get_size() == (800, 600)
    lit = sum(1 for x in range(0, 800, 1) for y in range(0, 600, 1)
              if sum(tuple(sky.get_at((x, y)))[:3]) > sum(SKY) + 60)
    assert 4 * STARS <= lit <= 30 * STARS                     # STARS stars of 1-2 px radius


def test_starfield_keeps_the_orbits_clear():
    from orbit_mania.assets import CLEAR_RADIUS, SKY, draw_starfield
    pygame.init()
    sky = draw_starfield(800, 600)
    inner = CLEAR_RADIUS - 3                                  # allow for a star's own radius
    for x in range(400 - inner, 400 + inner):
        for y in range(max(0, 300 - inner), min(600, 300 + inner)):
            if (x - 400) ** 2 + (y - 300) ** 2 < inner ** 2:
                assert tuple(sky.get_at((x, y)))[:3] == SKY


def test_starfield_is_the_same_every_time():
    from orbit_mania.assets import draw_starfield
    pygame.init()
    a, b = draw_starfield(800, 600), draw_starfield(800, 600)
    assert pygame.image.tobytes(a, "RGB") == pygame.image.tobytes(b, "RGB")


def test_finished_game_is_saved_to_high_scores(tmp_path, monkeypatch):
    from orbit_mania import app as app_module, scores
    from orbit_mania.app import App
    monkeypatch.setattr(app_module.pygame.time, "wait", lambda ms: None)   # skip the pauses
    path = tmp_path / "scores" / "highscores.json"
    a = App(seed=3, scores_path=path)
    a.game.fuel = 0.01                                    # runs out on the first frame
    a.run()
    saved = scores.load(path)
    assert len(saved) == 1 and saved[0]["seconds"] == pytest.approx(1 / 60, abs=0.01)


def test_quitting_early_saves_nothing(tmp_path):
    from orbit_mania import scores
    from orbit_mania.app import App
    path = tmp_path / "highscores.json"
    App(seed=3, scores_path=path).run(max_frames=30)
    assert scores.load(path) == []


def test_f11_toggles_fullscreen_without_crashing(tmp_path):
    from orbit_mania.app import App
    a = App(seed=3, scores_path=tmp_path / "s.json")
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11))
    a.run(max_frames=5)                                   # handles F11, keeps running


def test_can_start_in_fullscreen(tmp_path):
    from orbit_mania.app import App
    App(seed=3, scores_path=tmp_path / "s.json", fullscreen=True).run(max_frames=5)


def test_fullscreen_option_on_the_command_line(monkeypatch, tmp_path):
    from orbit_mania import app as app_module
    seen = {}
    class Fake:
        def __init__(self, **kwargs): seen.update(kwargs)
        def run(self): pass
    monkeypatch.setattr(app_module, "App", Fake)
    app_module.main(["--fullscreen", "--seed", "4"])
    assert seen["fullscreen"] is True and seen["seed"] == 4
