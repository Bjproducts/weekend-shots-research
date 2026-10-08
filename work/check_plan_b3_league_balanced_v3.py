"""Validate equal-league environment and one-per-league candidate selection."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from simulate_season_to_date_plan_b3 import rank_plan_b_candidates

ROOT = Path(__file__).resolve().parents[1]
HIST = ROOT / "outputs/season_to_date_plan_b3_league_balanced_v3"
SOURCE = ROOT / "outputs/season_to_date_plan_b3"
HIST_SPEC = ROOT / "work/season_to_date_plan_b3_league_balanced_v3_spec.json"
LIVE = ROOT / "outputs/live_plan_b3/2026-10-10"
LIVE_SPEC = ROOT / "work/live_plan_b3_league_balanced_v3_spec.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def balanced_environment_ids(ranked: list[dict], league_order: list[str], maximum: int = 5) -> list[str]:
    selectable = [row for row in ranked if row["confidence_tier"] in ("A", "B")]
    chosen = []
    ids = set()
    for league in league_order:
        rows = [row for row in selectable if row["league"] == league]
        if rows:
            chosen.append(rows[0])
            ids.add(rows[0]["match_id"])
    for row in selectable:
        if len(chosen) >= maximum:
            break
        if row["match_id"] not in ids:
            chosen.append(row)
            ids.add(row["match_id"])
    chosen.sort(key=lambda row: (-row["environment_score"], row["match_id"]))
    return [row["match_id"] for row in chosen]


def main() -> None:
    spec = load(HIST_SPEC)
    summary = load(HIST / "summary.json")
    weekends = load(HIST / "weekends.json")
    picks = load(HIST / "official_picks.json")
    fixtures = {row["match_id"]: row for row in load(SOURCE / "target_fixtures.json")}
    matches = {row["match_id"]: row for row in load(SOURCE / "matches.json")}
    league_order = list(spec["scope"]["leagues"])
    checks = {}
    checks["historical_spec_hash_matches"] = summary["spec_sha256"] == digest(HIST_SPEC)
    environments_valid = True
    boards_valid = True
    home_valid = True
    for weekend in weekends:
        expected_ids = balanced_environment_ids(weekend["ranked_environments"], league_order)
        actual_ids = [row["match_id"] for row in weekend["selected_environments"]]
        if expected_ids != actual_ids:
            environments_valid = False
        pool = []
        for environment in weekend["selected_environments"]:
            for candidate in environment["plan_B_candidates"]:
                if (
                    candidate.get("candidate_side") != "home"
                    or candidate.get("home_team_id") != fixtures[environment["match_id"]]["home_team_id"]
                ):
                    home_valid = False
                pool.append(
                    {
                        **candidate,
                        "match_id": environment["match_id"],
                        "environment_rank": environment["environment_rank"],
                    }
                )
        ranked = rank_plan_b_candidates(pool, spec)
        champions = []
        used = set()
        for candidate in ranked:
            league = fixtures[candidate["match_id"]]["league"]
            if league not in used:
                champions.append(candidate)
                used.add(league)
        actual = weekend["provisional_board"]
        if len({row["league"] for row in actual}) != len(actual):
            boards_valid = False
        if [(row["match_id"], row["player_id"]) for row in actual] != [
            (row["match_id"], row["player_id"]) for row in champions[:3]
        ]:
            boards_valid = False
    checks["historical_environment_quota_valid"] = environments_valid
    checks["historical_board_has_at_most_one_per_league"] = boards_valid
    checks["historical_candidates_are_home_only"] = home_valid
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
        if not person or not person["started"] or person["shots"] != pick["actual_shots"]:
            outcomes_valid = False
    checks["historical_outcomes_reconcile"] = outcomes_valid
    checks["historical_headline_reconciles"] = summary["official_picks"] == len(picks) and summary["hits_3plus"] == sum(row["hit_3plus"] for row in picks)

    live_spec = load(LIVE_SPEC)
    live_board = load(LIVE / "frozen_board_league_balanced_v3.json")
    snapshot = load(LIVE / "environment_snapshot.json")
    selectable = sorted(
        (
            row
            for row in snapshot["fixtures"]
            if row["eligible"] and row["confidence_tier"] in ("A", "B")
        ),
        key=lambda row: (-row["environment_score"], row["match_id"]),
    )
    expected_live_ids = balanced_environment_ids(selectable, ["Premier League", "Serie A", "Bundesliga", "MLS"])
    checks["live_spec_hash_matches"] = live_board["ranking_spec_sha256"] == digest(LIVE_SPEC)
    checks["live_environment_quota_valid"] = expected_live_ids == [row["match_id"] for row in live_board["selected_environments"]]
    checks["live_board_has_at_most_one_per_league"] = len({row["league"] for row in live_board["candidates"]}) == len(live_board["candidates"])
    checks["live_board_is_home_only"] = all(row["candidate_side"] == "home" for row in live_board["candidates"])
    checks["live_board_has_no_outcome_access"] = live_board["outcome_accessed"] is False
    failures = [name for name, passed in checks.items() if not passed]
    report = {"passed": len(checks) - len(failures), "total": len(checks), "failures": failures, "checks": checks}
    (HIST / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
