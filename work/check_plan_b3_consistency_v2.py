"""Validate the historical and live home-only consistency-v2 boards."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from statistics import pstdev

from simulate_season_to_date_plan_b3 import rank_plan_b_candidates

ROOT = Path(__file__).resolve().parents[1]
HIST = ROOT / "outputs/season_to_date_plan_b3_consistency_v2"
SOURCE = ROOT / "outputs/season_to_date_plan_b3"
HIST_SPEC = ROOT / "work/season_to_date_plan_b3_consistency_v2_spec.json"
LIVE = ROOT / "outputs/live_plan_b3/2026-10-10"
LIVE_SPEC = ROOT / "work/live_plan_b3_consistency_v2_spec.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    historical_spec = load(HIST_SPEC)
    summary = load(HIST / "summary.json")
    weekends = load(HIST / "weekends.json")
    picks = load(HIST / "official_picks.json")
    fixtures = {row["match_id"]: row for row in load(SOURCE / "target_fixtures.json")}
    matches = {row["match_id"]: row for row in load(SOURCE / "matches.json")}
    checks = {}
    checks["historical_spec_hash_matches"] = summary["spec_sha256"] == digest(HIST_SPEC)
    checks["every_historical_candidate_is_home"] = all(
        candidate.get("candidate_side") == "home"
        and candidate.get("home_team_id") == fixtures[environment["match_id"]]["home_team_id"]
        for weekend in weekends
        for environment in weekend["selected_environments"]
        for candidate in environment["plan_B_candidates"]
    )
    boards_valid = True
    for weekend in weekends:
        pool = []
        for environment in weekend["selected_environments"]:
            for candidate in environment["plan_B_candidates"]:
                pool.append(
                    {
                        **candidate,
                        "match_id": environment["match_id"],
                        "environment_rank": environment["environment_rank"],
                    }
                )
        expected = rank_plan_b_candidates(pool, historical_spec)[:3]
        actual = weekend["provisional_board"]
        if [(row["match_id"], row["player_id"]) for row in actual] != [
            (row["match_id"], row["player_id"]) for row in expected
        ]:
            boards_valid = False
    checks["every_historical_board_obeys_consistency_order"] = boards_valid
    outcomes_valid = True
    for pick in picks:
        source = matches[pick["match_id"]]
        person = next(
            (
                row
                for row in source["players"]
                if row["player_id"] == pick["player_id"] and row["team_id"] == pick["home_team_id"]
            ),
            None,
        )
        if (
            pick["home_team_id"] != fixtures[pick["match_id"]]["home_team_id"]
            or not person
            or not person["started"]
            or person["shots"] != pick["actual_shots"]
        ):
            outcomes_valid = False
    checks["historical_official_picks_are_confirmed_home_starters"] = outcomes_valid
    checks["historical_totals_reconcile"] = (
        summary["official_picks"] == len(picks)
        and summary["hits_3plus"] == sum(row["hit_3plus"] for row in picks)
    )

    live_spec = load(LIVE_SPEC)
    live_board = load(LIVE / "frozen_board_consistency_v2.json")
    live_snapshot = load(LIVE / "environment_snapshot.json")
    live_possible = load(LIVE / "latest_possible_lineups.json")
    live_environments = {row["match_id"]: row for row in live_snapshot["fixtures"]}
    checks["live_spec_hash_matches"] = live_board["ranking_spec_sha256"] == digest(LIVE_SPEC)
    checks["live_board_is_home_only"] = all(
        row["candidate_side"] == "home"
        and row["home_team_id"] == live_environments[row["match_id"]]["home_team_id"]
        for row in live_board["candidates"]
    )
    enriched = []
    for candidate in live_possible["all_provisional_plan_B_candidates"]:
        shots = [row["shots"] for row in candidate["prior_rows"]]
        enriched.append(
            {
                **candidate,
                "candidate_side": "home",
                "shot_floor": min(shots),
                "shot_stddev": round(pstdev(shots), 5),
            }
        )
    expected_live = rank_plan_b_candidates(enriched, live_spec)[:3]
    checks["live_board_obeys_consistency_order"] = [
        (row["match_id"], row["player_id"]) for row in live_board["candidates"]
    ] == [(row["match_id"], row["player_id"]) for row in expected_live]
    checks["live_board_has_no_outcome_access"] = live_board["outcome_accessed"] is False
    failures = [name for name, passed in checks.items() if not passed]
    report = {"passed": len(checks) - len(failures), "total": len(checks), "failures": failures, "checks": checks}
    (HIST / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
