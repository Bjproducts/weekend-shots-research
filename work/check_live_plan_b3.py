"""Integrity checks for the prospective four-league Plan B 3+ workflow."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs/live_plan_b3"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def walk_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_keys(item)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weekend", required=True)
    args = parser.parse_args()
    out = BASE / args.weekend
    snapshot_path = out / "environment_snapshot.json"
    board_path = out / "frozen_board.json"
    snapshot = load(snapshot_path)
    manifest = load(out / "manifest.json")
    board = load(board_path)
    history = load(out / "history_matches.json")
    acquisition = load(out / "acquisition.json")
    history_by_id = {row["match_id"]: row for row in history}
    start = datetime.fromisoformat(args.weekend).astimezone(dt(snapshot["created_utc"]).tzinfo)
    target_dates = {start.date().isoformat(), (start + timedelta(days=1)).date().isoformat()}
    expected_leagues = {"Premier League", "Serie A", "Bundesliga", "MLS"}
    checks = {}

    checks["acquisition_has_no_failures"] = acquisition["failures"] == []
    checks["acquisition_count_reconciles"] = acquisition["normalized_matches"] == len(history)
    checks["snapshot_hash_matches_manifest"] = digest(snapshot_path) == manifest["environment_snapshot_sha256"]
    checks["spec_hash_matches_manifest"] = digest(ROOT / "work/live_plan_b3_spec.json") == manifest["spec_sha256"]
    checks["only_four_requested_leagues"] = {row["league"] for row in snapshot["fixtures"]} == expected_leagues
    checks["only_target_weekend_dates"] = all(row["date"][:10] in target_dates for row in snapshot["fixtures"])
    checks["all_fixture_ids_unique"] = len({row["match_id"] for row in snapshot["fixtures"]}) == len(snapshot["fixtures"])
    selected = [row for row in snapshot["fixtures"] if row["selected_environment"]]
    checks["five_environments_selected"] = len(selected) == 5
    checks["selected_are_tier_A_or_B"] = all(row["confidence_tier"] in ("A", "B") for row in selected)
    checks["selected_ids_match_manifest"] = [
        row["match_id"] for row in sorted(selected, key=lambda item: item["environment_rank"])
    ] == manifest["selected_environment_ids"]
    checks["environment_ranks_are_contiguous"] = sorted(row["environment_rank"] for row in selected) == list(range(1, len(selected) + 1))

    all_prior_valid = True
    all_candidate_rows_valid = True
    all_candidate_aggregates_reconcile = True
    for fixture in snapshot["fixtures"]:
        cutoff = dt(fixture["history_cutoff"])
        for match_id in fixture["home_prior_ids"] + fixture["away_prior_ids"]:
            if match_id not in history_by_id or dt(history_by_id[match_id]["date"]) >= cutoff:
                all_prior_valid = False
        for candidate in fixture["candidate_pool"]:
            rows = candidate["prior_rows"]
            if len(rows) != 5 or candidate["prior_ids"] != [row["match_id"] for row in rows]:
                all_candidate_rows_valid = False
            if any(dt(row["date"]) >= cutoff or row["match_id"] not in history_by_id for row in rows):
                all_candidate_rows_valid = False
            expected_shots = sum(row["shots"] for row in rows) / 5
            expected_minutes = sum(row["minutes"] for row in rows) / 5
            expected_share = sum(row["shot_share"] for row in rows) / 5
            if not (
                abs(candidate["avg_shots"] - expected_shots) < 0.0011
                and abs(candidate["avg_minutes"] - expected_minutes) < 0.0011
                and abs(candidate["avg_shot_share"] - expected_share) < 0.00002
                and candidate["hits_2plus"] == sum(row["shots"] >= 2 for row in rows)
                and candidate["hits_3plus"] == sum(row["shots"] >= 3 for row in rows)
            ):
                all_candidate_aggregates_reconcile = False
    checks["all_team_history_precedes_cutoff"] = all_prior_valid
    checks["candidate_histories_are_five_pre_cutoff_starts"] = all_candidate_rows_valid
    checks["candidate_aggregates_reconcile"] = all_candidate_aggregates_reconcile

    candidates = board["candidates"]
    checks["board_has_at_most_three"] = len(candidates) <= 3
    checks["board_ranks_are_contiguous"] = [item["provisional_rank"] for item in candidates] == list(range(1, len(candidates) + 1))
    checks["all_board_names_pass_plan_B"] = all(
        item["plan_B"]
        and item["shooter_rank_within_possible_XI"] <= 2
        and item["hits_2plus"] >= 4
        and item["avg_shots"] >= 3
        and item["avg_minutes"] >= 80
        for item in candidates
    )
    expected_order = sorted(
        candidates,
        key=lambda item: (
            -item["hits_3plus"],
            -item["avg_shot_share"],
            -item["avg_shots"],
            -item["avg_minutes"],
            item["environment_rank"],
            item["player_id"],
        ),
    )
    checks["board_obeys_frozen_3plus_ranking"] = [item["player_id"] for item in candidates] == [item["player_id"] for item in expected_order]
    forbidden_outcome_keys = {"settled_utc", "official_picks", "actual_shots", "profit", "hit_rate"}
    checks["snapshot_contains_no_outcomes"] = not (set(walk_keys(snapshot)) & forbidden_outcome_keys)
    checks["board_contains_no_outcomes"] = not (set(walk_keys(board)) & forbidden_outcome_keys)
    checks["snapshot_and_board_mark_outcome_unaccessed"] = manifest["outcome_accessed"] is False and board["outcome_accessed"] is False

    failures = [name for name, passed in checks.items() if not passed]
    report = {"weekend": args.weekend, "passed": len(checks) - len(failures), "total": len(checks), "failures": failures, "checks": checks}
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
