"""Build the immutable equal-league v3 board from the live snapshot."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import pstdev

from live_plan_b3 import dt
from simulate_season_to_date_plan_b3 import possible_xi, rank_plan_b_candidates

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs/live_plan_b3"
SPEC_PATH = ROOT / "work/live_plan_b3_league_balanced_v3_spec.json"
LEAGUE_ORDER = ("Premier League", "Serie A", "Bundesliga", "MLS")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weekend", required=True)
    args = parser.parse_args()
    out = BASE / args.weekend
    destination = out / "frozen_board_league_balanced_v3.json"
    if destination.exists():
        print(json.dumps({"status": "already_frozen", "board": str(destination), "sha256": digest(destination)}, indent=2))
        return
    spec = load(SPEC_PATH)
    snapshot_path = out / "environment_snapshot.json"
    snapshot = load(snapshot_path)
    history = load(out / "history_matches.json")
    selectable = sorted(
        (
            row
            for row in snapshot["fixtures"]
            if row["eligible"] and row["confidence_tier"] in ("A", "B")
        ),
        key=lambda row: (-row["environment_score"], row["match_id"]),
    )
    selected = []
    selected_ids = set()
    for league in LEAGUE_ORDER:
        rows = [row for row in selectable if row["league"] == league]
        if rows:
            selected.append(rows[0])
            selected_ids.add(rows[0]["match_id"])
    for row in selectable:
        if len(selected) >= spec["maximum_environments"]:
            break
        if row["match_id"] not in selected_ids:
            selected.append(row)
            selected_ids.add(row["match_id"])
    selected.sort(key=lambda row: (-row["environment_score"], row["match_id"]))
    rank_by_id = {row["match_id"]: rank for rank, row in enumerate(selected, 1)}

    team_matches = defaultdict(list)
    for match in history:
        team_matches[match["league"], match["home_team_id"]].append(match)
        team_matches[match["league"], match["away_team_id"]].append(match)
    for rows in team_matches.values():
        rows.sort(key=lambda item: (item["date"], item["match_id"]))
    all_plan_b = []
    selected_environments = []
    for environment in selected:
        target = dt(environment["date"])
        cutoff = dt(environment["history_cutoff"])
        xi, recent_ids = possible_xi(
            environment["home_team_id"], environment["league"], cutoff, target, team_matches
        )
        possible_ids = {row["player_id"] for row in xi}
        candidates = [row for row in environment["candidate_pool"] if row["player_id"] in possible_ids]
        candidates.sort(key=lambda row: (-row["avg_shots"], -row["avg_minutes"], row["player_id"]))
        plan_b = []
        for shooter_rank, candidate in enumerate(candidates, 1):
            passes = (
                shooter_rank <= 2
                and candidate["hits_2plus"] >= 4
                and candidate["avg_shots"] >= 3
                and candidate["avg_minutes"] >= 80
            )
            if not passes:
                continue
            shots = [row["shots"] for row in candidate["prior_rows"]]
            value = {
                **candidate,
                "candidate_side": "home",
                "home_team_id": environment["home_team_id"],
                "shooter_rank_within_possible_XI": shooter_rank,
                "plan_B": True,
                "shot_floor": min(shots),
                "shot_stddev": round(pstdev(shots), 5),
                "match_id": environment["match_id"],
                "date": environment["date"],
                "league": environment["league"],
                "fixture": environment["fixture"],
                "environment_rank": rank_by_id[environment["match_id"]],
                "environment_score": environment["environment_score"],
            }
            plan_b.append(value)
            all_plan_b.append(value)
        selected_environments.append(
            {
                "match_id": environment["match_id"],
                "date": environment["date"],
                "league": environment["league"],
                "fixture": environment["fixture"],
                "environment_rank": rank_by_id[environment["match_id"]],
                "environment_score": environment["environment_score"],
                "confidence_tier": environment["confidence_tier"],
                "projected_home_shots": environment["projected_home_shots"],
                "projected_shot_gap": environment["projected_shot_gap"],
                "recent_team_match_ids": recent_ids,
                "possible_XI_ids": sorted(possible_ids),
                "plan_B_candidates": plan_b,
            }
        )
    ranked = rank_plan_b_candidates(all_plan_b, spec)
    champions = []
    used = set()
    for candidate in ranked:
        if candidate["league"] not in used:
            champions.append(candidate)
            used.add(candidate["league"])
    top = [
        {**candidate, "provisional_rank": rank, "status": "provisional_awaiting_confirmed_home_lineup"}
        for rank, candidate in enumerate(champions[: spec["maximum_candidates"]], 1)
    ]
    payload = {
        "status": "frozen_provisional_home_only_league_balanced_v3",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "weekend": args.weekend,
        "ranking_version": spec["version"],
        "ranking_spec_sha256": digest(SPEC_PATH),
        "environment_snapshot_sha256": digest(snapshot_path),
        "selected_environments": selected_environments,
        "league_champions_before_top3": champions,
        "candidates": top,
        "outcome_accessed": False,
    }
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "selected_environments": [
                    (row["environment_rank"], row["league"], row["fixture"])
                    for row in selected_environments
                ],
                "top3": [
                    (row["provisional_rank"], row["league"], row["player"], row["fixture"])
                    for row in top
                ],
                "board": str(destination),
                "sha256": digest(destination),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
