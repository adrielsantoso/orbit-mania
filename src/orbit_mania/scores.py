"""Best survival times, saved for each player on their own computer.

Scores live in a per-user data folder, outside the project:

    Linux    ~/.local/share/orbit-mania/highscores.json  (or $XDG_DATA_HOME)
    macOS    ~/Library/Application Support/orbit-mania/highscores.json
    Windows  %APPDATA%\\orbit-mania\\highscores.json

so they survive updates and re-clones and never end up in a git commit.
`--scores PATH` or the ORBIT_MANIA_SCORES variable can point elsewhere; the
file name highscores.json is in .gitignore in case it is placed in the repo.

A missing or unreadable file means "no scores yet"; the game never fails
because of it.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

KEEP = 10
FILE_NAME = "highscores.json"


def default_path() -> Path:
    if os.environ.get("ORBIT_MANIA_SCORES"):
        return Path(os.environ["ORBIT_MANIA_SCORES"])
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "orbit-mania" / FILE_NAME


def load(path: Path) -> list[dict]:
    """Saved scores, best first; [] if the file is missing or unreadable."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        scores = [{"seconds": float(s["seconds"]), "date": str(s["date"])} for s in data]
    except (OSError, ValueError, TypeError, KeyError):
        return []
    return sorted(scores, key=lambda s: -s["seconds"])[:KEEP]


def best(path: Path) -> float | None:
    scores = load(path)
    return scores[0]["seconds"] if scores else None


def record(path: Path, seconds: float, when: datetime | None = None) -> int | None:
    """Add a finished game; return its rank (1 = best) or None if not in the top KEEP.

    The file is written to a temporary name first and then renamed, so a crash
    while saving cannot leave a half-written file behind.
    """
    path = Path(path)
    when = when or datetime.now()
    entry = {"seconds": round(seconds, 2), "date": when.strftime("%Y-%m-%d %H:%M")}
    scores = load(path) + [entry]
    scores.sort(key=lambda s: -s["seconds"])          # stable: earlier equal scores stay ahead
    scores = scores[:KEEP]
    if entry not in scores:
        return None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(scores, indent=2), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        return None                                    # no write access: play on without saving
    return scores.index(entry) + 1
