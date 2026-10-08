"""High-score file: saving, ranking, and never failing the game."""

import json
from datetime import datetime

from orbit_mania import scores

WHEN = datetime(2026, 10, 8, 12, 0)


def test_no_file_means_no_scores(tmp_path):
    assert scores.load(tmp_path / "missing.json") == []
    assert scores.best(tmp_path / "missing.json") is None


def test_first_game_is_rank_one_and_creates_the_folder(tmp_path):
    path = tmp_path / "a" / "b" / "highscores.json"
    assert scores.record(path, 42.5, WHEN) == 1
    assert scores.load(path) == [{"seconds": 42.5, "date": "2026-10-08 12:00"}]


def test_scores_are_ranked_best_first(tmp_path):
    path = tmp_path / "highscores.json"
    for s in (30, 90, 60):
        scores.record(path, s, WHEN)
    assert [s["seconds"] for s in scores.load(path)] == [90, 60, 30]
    assert scores.record(path, 75, WHEN) == 2
    assert scores.best(path) == 90


def test_only_the_top_ten_are_kept(tmp_path):
    path = tmp_path / "highscores.json"
    for s in range(1, 13):
        scores.record(path, s, WHEN)
    kept = [s["seconds"] for s in scores.load(path)]
    assert kept == list(range(12, 2, -1))
    assert scores.record(path, 1, WHEN) is None            # too low to enter


def test_equal_time_ranks_below_the_earlier_one(tmp_path):
    path = tmp_path / "highscores.json"
    scores.record(path, 50, datetime(2026, 1, 1))
    assert scores.record(path, 50, datetime(2026, 2, 1)) == 2


def test_corrupt_file_is_treated_as_empty(tmp_path):
    path = tmp_path / "highscores.json"
    path.write_text("{not json")
    assert scores.load(path) == []
    assert scores.record(path, 10, WHEN) == 1               # and is replaced cleanly
    assert json.loads(path.read_text())[0]["seconds"] == 10


def test_unwritable_location_does_not_crash(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("")
    assert scores.record(blocker / "highscores.json", 10, WHEN) is None


def test_default_path_is_outside_the_project(monkeypatch):
    from pathlib import Path
    monkeypatch.delenv("ORBIT_MANIA_SCORES", raising=False)
    project = Path(__file__).resolve().parents[1]
    path = scores.default_path()
    assert path.name == "highscores.json"
    assert project not in path.resolve().parents


def test_environment_variable_overrides_the_location(monkeypatch, tmp_path):
    monkeypatch.setenv("ORBIT_MANIA_SCORES", str(tmp_path / "x.json"))
    assert scores.default_path() == tmp_path / "x.json"
