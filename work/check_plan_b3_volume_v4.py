"""Integrity checks for the retrospective and live volume-v4 challenger."""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/season_to_date_plan_b3_volume_v4"
LIVE = ROOT / "outputs/live_plan_b3/2026-10-10/frozen_board_volume_v4.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    summary = load(OUT / "summary.json")
    picks = load(OUT / "official_picks.json")
    board = load(LIVE)
    assert summary["spec_version"] == "season-to-date-plan-b3-volume-v4"
    assert len(picks) == summary["official_picks"] == 38
    assert sum(bool(row["hit_3plus"]) for row in picks) == summary["hits_3plus"] == 33
    by_weekend = defaultdict(list)
    for row in picks:
        assert row["candidate_side"] == "home"
        assert row["plan_B"] is True
        assert row["decision"] == "official_pick"
        by_weekend[row["weekend"]].append(row)
    for rows in by_weekend.values():
        assert len(rows) <= 3
        assert max(Counter(row["league"] for row in rows).values()) <= 2
        assert len({row["match_id"] for row in rows}) == len(rows)
    candidates = board["candidates"]
    assert len(candidates) <= 3
    assert max(Counter(row["league"] for row in candidates).values()) <= 2
    assert len({row["match_id"] for row in candidates}) == len(candidates)
    assert all(row["candidate_side"] == "home" and row["plan_B"] for row in candidates)
    before = hashlib.sha256(LIVE.read_bytes()).hexdigest()
    # The board builder is idempotent and refuses to overwrite a frozen board.
    import subprocess, sys
    subprocess.run([sys.executable, str(ROOT / "work/build_live_plan_b3_volume_board.py"), "--weekend", "2026-10-10"], cwd=ROOT, check=True, capture_output=True)
    assert hashlib.sha256(LIVE.read_bytes()).hexdigest() == before
    print(json.dumps({"status": "ok", "historical_official": len(picks), "historical_hits": summary["hits_3plus"], "live_candidates": len(candidates), "live_board_sha256": before}, indent=2))


if __name__ == "__main__":
    main()
