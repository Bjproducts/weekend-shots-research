"""Build the immutable higher-volume v4 challenger from frozen v3 environments."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from simulate_season_to_date_plan_b3 import rank_plan_b_candidates

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs/live_plan_b3"
SPEC_PATH = ROOT / "work/live_plan_b3_volume_v4_spec.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def select_candidates(environments: list[dict], spec: dict) -> tuple[list[dict], list[dict]]:
    fixture_champions = []
    for environment in environments:
        candidates = rank_plan_b_candidates(environment.get("plan_B_candidates", []), spec)
        if candidates:
            fixture_champions.append(candidates[0])
    ranked = rank_plan_b_candidates(fixture_champions, spec)
    selected = []
    league_counts: Counter[str] = Counter()
    for candidate in ranked:
        if league_counts[candidate["league"]] >= spec["maximum_candidates_per_league"]:
            continue
        selected.append(candidate)
        league_counts[candidate["league"]] += 1
        if len(selected) >= spec["maximum_candidates"]:
            break
    return fixture_champions, selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weekend", required=True)
    args = parser.parse_args()
    folder = BASE / args.weekend
    control_path = folder / "frozen_board_league_balanced_v3.json"
    destination = folder / "frozen_board_volume_v4.json"
    if destination.exists():
        print(json.dumps({"status": "already_frozen", "board": str(destination), "sha256": sha(destination)}, indent=2))
        return
    spec = load(SPEC_PATH)
    control = load(control_path)
    if control.get("ranking_version") != spec["control"]:
        raise SystemExit("Frozen control board does not match the v4 specification.")
    champions, selected = select_candidates(control["selected_environments"], spec)
    candidates = [
        {
            **candidate,
            "provisional_rank": rank,
            "status": "challenger_provisional_awaiting_confirmed_home_lineup",
        }
        for rank, candidate in enumerate(selected, 1)
    ]
    payload = {
        "status": "frozen_provisional_home_only_volume_v4",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "weekend": args.weekend,
        "strategy_id": "volume_v4",
        "ranking_version": spec["version"],
        "ranking_spec_sha256": sha(SPEC_PATH),
        "control_board_sha256": sha(control_path),
        "selected_environments": control["selected_environments"],
        "fixture_champions_before_caps": champions,
        "candidates": candidates,
        "outcome_accessed": False,
        "prospective_gate_eligible": True,
    }
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "board": str(destination), "sha256": sha(destination), "candidates": [(row["provisional_rank"], row["league"], row["player"], row["fixture"]) for row in candidates]}, indent=2))


if __name__ == "__main__":
    main()
