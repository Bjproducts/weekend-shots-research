"""Create an immutable home-only, consistency-ranked v2 board."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import pstdev

from simulate_season_to_date_plan_b3 import rank_plan_b_candidates

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs/live_plan_b3"
SPEC_PATH = ROOT / "work/live_plan_b3_consistency_v2_spec.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weekend", required=True)
    args = parser.parse_args()
    out = BASE / args.weekend
    destination = out / "frozen_board_consistency_v2.json"
    if destination.exists():
        print(json.dumps({"status": "already_frozen", "board": str(destination), "sha256": digest(destination)}, indent=2))
        return
    source = load(out / "latest_possible_lineups.json")
    spec = load(SPEC_PATH)
    candidates = []
    for candidate in source["all_provisional_plan_B_candidates"]:
        if not candidate.get("home_team_id"):
            raise SystemExit(f"Candidate lacks a home-team identity: {candidate['player']}")
        shots = [row["shots"] for row in candidate["prior_rows"]]
        candidates.append(
            {
                **candidate,
                "candidate_side": "home",
                "shot_floor": min(shots),
                "shot_stddev": round(pstdev(shots), 5),
            }
        )
    ranked = rank_plan_b_candidates(candidates, spec)
    top = [
        {**candidate, "provisional_rank": rank, "status": "provisional_awaiting_confirmed_home_lineup"}
        for rank, candidate in enumerate(ranked[: spec["maximum_provisional_candidates"]], 1)
    ]
    payload = {
        "status": "frozen_provisional_home_only_consistency_v2",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "weekend": args.weekend,
        "ranking_version": spec["version"],
        "ranking_spec_sha256": digest(SPEC_PATH),
        "source_possible_lineups_created_utc": source["created_utc"],
        "environment_snapshot_sha256": source["environment_snapshot_sha256"],
        "candidates": top,
        "outcome_accessed": False,
    }
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "board": str(destination),
                "sha256": digest(destination),
                "top3": [
                    {
                        "rank": item["provisional_rank"],
                        "player": item["player"],
                        "fixture": item["fixture"],
                        "shot_floor": item["shot_floor"],
                        "shot_stddev": item["shot_stddev"],
                    }
                    for item in top
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
