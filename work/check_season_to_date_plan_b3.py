"""Integrity checks for the four-league season-to-date engine replay."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/season_to_date_plan_b3"
SPEC_PATH = ROOT / "work/season_to_date_plan_b3_spec.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    spec = load(SPEC_PATH)
    acquisition = load(OUT / "acquisition.json")
    matches = load(OUT / "matches.json")
    fixtures = load(OUT / "target_fixtures.json")
    weekends = load(OUT / "weekends.json")
    picks = load(OUT / "official_picks.json")
    summary = load(OUT / "summary.json")
    match_by_id = {row["match_id"]: row for row in matches}
    fixture_by_id = {row["match_id"]: row for row in fixtures}
    expected_leagues = set(spec["scope"]["leagues"])
    checks = {}
    checks["zero_acquisition_failures"] = acquisition["failures"] == []
    checks["source_count_reconciles"] = acquisition["normalized_matches"] == len(matches) == summary["source_matches"]
    checks["target_count_reconciles"] = acquisition["target_weekend_fixtures"] == len(fixtures) == summary["target_weekend_fixtures"]
    checks["spec_hash_reconciles"] = digest(SPEC_PATH) == summary["spec_sha256"]
    checks["only_requested_leagues"] = {row["league"] for row in fixtures} == expected_leagues
    checks["all_targets_are_finished_source_matches"] = all(row["match_id"] in match_by_id for row in fixtures)
    checks["all_targets_are_saturday_or_sunday"] = all(dt(row["date"]).weekday() in (5, 6) for row in fixtures)
    checks["target_seasons_are_current"] = all(
        row["season"] == spec["scope"]["leagues"][row["league"]]["current_season"] for row in fixtures
    )
    checks["weekends_sorted_and_unique"] = [row["weekend"] for row in weekends] == sorted({row["weekend"] for row in weekends})
    checks["weekend_count_reconciles"] = len(weekends) == summary["calendar_weekends"]

    leakage_free = True
    environment_order_valid = True
    boards_valid = True
    candidate_history_valid = True
    decisions_valid = True
    pick_outcomes_valid = True
    all_decision_picks = []
    for record in weekends:
        cutoff = dt(record["history_cutoff"])
        saturday = dt(record["weekend"] + "T00:00:00Z")
        if cutoff != saturday - timedelta(days=1):
            leakage_free = False
        ranked = record["ranked_environments"]
        if [row["overall_environment_rank"] for row in ranked] != list(range(1, len(ranked) + 1)):
            environment_order_valid = False
        if ranked != sorted(ranked, key=lambda row: (-row["environment_score"], row["match_id"])):
            environment_order_valid = False
        selectable = [row for row in ranked if row["confidence_tier"] in ("A", "B")]
        expected_selected = [row["match_id"] for row in selectable[:5]]
        actual_selected = [row["match_id"] for row in record["selected_environments"]]
        if expected_selected != actual_selected:
            environment_order_valid = False
        all_plan_b = []
        for environment in record["selected_environments"]:
            for match_id in environment["home_prior_ids"] + environment["away_prior_ids"] + environment["recent_team_match_ids"]:
                if match_id not in match_by_id or dt(match_by_id[match_id]["date"]) >= cutoff:
                    leakage_free = False
            for candidate in environment["plan_B_candidates"]:
                rows = candidate["prior_rows"]
                if len(rows) != 5 or candidate["prior_ids"] != [row["match_id"] for row in rows]:
                    candidate_history_valid = False
                if any(row["match_id"] not in match_by_id or dt(row["date"]) >= cutoff for row in rows):
                    leakage_free = False
                if not (
                    candidate["plan_B"]
                    and candidate["shooter_rank_within_possible_XI"] <= 2
                    and candidate["hits_2plus"] >= 4
                    and candidate["avg_shots"] >= 3
                    and candidate["avg_minutes"] >= 80
                ):
                    candidate_history_valid = False
                if not (
                    abs(candidate["avg_shots"] - sum(row["shots"] for row in rows) / 5) < 0.0011
                    and abs(candidate["avg_minutes"] - sum(row["minutes"] for row in rows) / 5) < 0.0011
                    and candidate["hits_3plus"] == sum(row["shots"] >= 3 for row in rows)
                ):
                    candidate_history_valid = False
                all_plan_b.append(
                    {
                        **candidate,
                        "match_id": environment["match_id"],
                        "environment_rank": environment["environment_rank"],
                    }
                )
        expected_board = sorted(
            all_plan_b,
            key=lambda item: (
                -item["hits_3plus"],
                -item["avg_shot_share"],
                -item["avg_shots"],
                -item["avg_minutes"],
                item["environment_rank"],
                item["player_id"],
            ),
        )[:3]
        actual_board = record["provisional_board"]
        if len(actual_board) > 3 or [row["player_id"] for row in actual_board] != [row["player_id"] for row in expected_board]:
            boards_valid = False
        board_keys = {(row["match_id"], row["player_id"]) for row in actual_board}
        for decision in record["lineup_decisions"]:
            if (decision["match_id"], decision["player_id"]) not in board_keys:
                decisions_valid = False
            if decision["decision"] == "official_pick":
                all_decision_picks.append(decision)
                source = match_by_id[decision["match_id"]]
                person = next(
                    (
                        row
                        for row in source["players"]
                        if row["team_id"] == decision["home_team_id"]
                        and row["player_id"] == decision["player_id"]
                    ),
                    None,
                )
                if not person or not person["started"] or person["shots"] != decision["actual_shots"]:
                    pick_outcomes_valid = False
                if decision["hit_3plus"] != (decision["actual_shots"] >= 3):
                    pick_outcomes_valid = False
    checks["all_selection_features_precede_friday_cutoff"] = leakage_free
    checks["environment_ranking_and_top_five_valid"] = environment_order_valid
    checks["candidate_histories_and_plan_B_gates_valid"] = candidate_history_valid
    checks["provisional_top_three_ranking_valid"] = boards_valid
    checks["lineup_decisions_only_use_frozen_board"] = decisions_valid
    checks["official_picks_reconcile_to_actual_starters_and_shots"] = pick_outcomes_valid
    checks["official_pick_file_matches_weekend_decisions"] = [
        (row["match_id"], row["player_id"]) for row in picks
    ] == [
        (row["match_id"], row["player_id"])
        for row in sorted(all_decision_picks, key=lambda item: (item["date"], item["match_id"], item["provisional_rank"], item["player_id"]))
    ]
    hits = sum(row["hit_3plus"] for row in picks)
    checks["headline_totals_reconcile"] = (
        summary["official_picks"] == len(picks)
        and summary["hits_3plus"] == hits
        and summary["misses_3plus"] == len(picks) - hits
        and summary["hit_rate_3plus"] == round(100 * hits / len(picks), 1)
    )
    league_counts = Counter(row["league"] for row in picks)
    checks["league_pick_counts_reconcile"] = all(
        row["picks"] == league_counts[row["league"]] for row in summary["by_league"]
    )
    full_three = [row for row in weekends if row["official_picks"] == 3]
    checks["three_pick_weekend_totals_reconcile"] = (
        summary["weekends_with_three_official_picks"] == len(full_three)
        and summary["clean_three_pick_weekends"] == sum(row["hits_3plus"] == 3 for row in full_three)
    )
    failures = [name for name, passed in checks.items() if not passed]
    report = {"passed": len(checks) - len(failures), "total": len(checks), "failures": failures, "checks": checks}
    (OUT / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
