"""Prospective four-league Plan B 3+ shots weekend workflow.

The workflow is deliberately split into immutable stages:
prepare -> possible -> lineups -> settle.  Outcomes are unavailable to the
first three stages and provisional names never count as official picks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from statistics import mean

from download_fotmob_big5_carryover import extract_stat, get_json

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs/live_plan_b3"
SPEC_PATH = ROOT / "work/live_plan_b3_spec.json"


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_once(path: Path, payload: dict) -> None:
    if path.exists():
        raise RuntimeError(f"Immutable file already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def active_board_path(out: Path) -> Path:
    balanced = out / "frozen_board_league_balanced_v3.json"
    consistency = out / "frozen_board_consistency_v2.json"
    if balanced.exists():
        return balanced
    return consistency if consistency.exists() else out / "frozen_board.json"


def average(rows: list[dict], key: str):
    values = [row[key] for row in rows if row.get(key) is not None]
    return mean(values) if values else None


def percentile(value: float, values: list[float]) -> float:
    if len(values) == 1:
        return 50.0
    less = sum(item < value for item in values)
    equal = sum(item == value for item in values)
    return 100 * (less + (equal - 1) / 2) / (len(values) - 1)


def weekend_dates(weekend: str) -> set[str]:
    start = datetime.fromisoformat(weekend).replace(tzinfo=timezone.utc)
    return {start.date().isoformat(), (start + timedelta(days=1)).date().isoformat()}


def fetch_fixtures(spec: dict) -> list[dict]:
    rows = []
    for league, config in spec["leagues"].items():
        query = urllib.parse.urlencode(
            {
                "id": config["fotmob_id"],
                "ccode3": config["country"],
                "season": config["current_season"],
            }
        )
        data = get_json("https://www.fotmob.com/api/data/leagues?" + query)
        for source in data["fixtures"]["allMatches"]:
            row = dict(source)
            row.update(
                league=league,
                league_id=config["fotmob_id"],
                season=config["current_season"],
            )
            rows.append(row)
    return rows


def build_indexes(matches: list[dict]):
    team = defaultdict(list)
    player = defaultdict(list)
    for match in sorted(matches, key=lambda row: (row["date"], row["match_id"])):
        date = dt(match["date"])
        league = match["league"]
        home_id = match["home_team_id"]
        away_id = match["away_team_id"]
        if None not in (match.get("home_score"), match.get("away_score")):
            for team_id, home in ((home_id, True), (away_id, False)):
                goals_for = match["home_score"] if home else match["away_score"]
                goals_against = match["away_score"] if home else match["home_score"]
                team[league, team_id].append(
                    {
                        "date": date,
                        "match_id": match["match_id"],
                        "season": match["season"],
                        "home": home,
                        "points": 3 if goals_for > goals_against else 1 if goals_for == goals_against else 0,
                        "shots": match["home_shots"] if home else match["away_shots"],
                        "against": match["away_shots"] if home else match["home_shots"],
                    }
                )
        for person in match["players"]:
            if not person.get("started") or person.get("team_id") not in (home_id, away_id):
                continue
            is_home = person["team_id"] == home_id
            team_shots = match["home_shots"] if is_home else match["away_shots"]
            shots = person.get("shots")
            player[league, person["team_id"], person["player_id"]].append(
                {
                    "date": date,
                    "match_id": match["match_id"],
                    "season": match["season"],
                    "player": person["player"],
                    "position_id": person.get("position_id"),
                    "shots": shots,
                    "minutes": person.get("minutes"),
                    "team_shots": team_shots,
                    "shot_share": shots / team_shots if shots is not None and team_shots else None,
                }
            )
    return team, player


def bounded_team_history(
    rows: list[dict], target: datetime, cutoff: datetime, current_season: str, maximum: int
) -> list[dict]:
    eligible = [
        row
        for row in rows
        if row["date"] < cutoff and target - row["date"] <= timedelta(days=180)
    ]
    current = [row for row in eligible if row["season"] == current_season]
    prior = [row for row in eligible if row["season"] != current_season]
    if len(current) >= maximum:
        return current[-maximum:]
    return prior[-(maximum - len(current)) :] + current


def prepare(weekend: str) -> None:
    spec = load_json(SPEC_PATH)
    out = BASE / weekend
    out.mkdir(parents=True, exist_ok=True)
    snapshot = out / "environment_snapshot.json"
    if snapshot.exists():
        print(json.dumps({"status": "already_locked", "snapshot": str(snapshot), "sha256": sha256(snapshot)}, indent=2))
        return
    history_path = out / "history_matches.json"
    if not history_path.exists():
        raise SystemExit("Run sync_live_plan_b3_data.py for this weekend first.")
    acquisition = load_json(out / "acquisition.json")
    if acquisition["failures"]:
        raise SystemExit("Acquisition has failures; fix them before freezing a snapshot.")

    dates = weekend_dates(weekend)
    fixtures = [row for row in fetch_fixtures(spec) if row["status"]["utcTime"][:10] in dates]
    fixtures.sort(key=lambda row: (row["status"]["utcTime"], str(row["id"])))
    matches = load_json(history_path)
    team_index, player_index = build_indexes(matches)
    rows = []
    maximum = spec["environment"]["maximum_team_matches"]
    current_seasons = {league: config["current_season"] for league, config in spec["leagues"].items()}

    for fixture in fixtures:
        target = dt(fixture["status"]["utcTime"])
        # A one-day buffer ensures that the weekend snapshot cannot ingest a
        # result from the same fixture day.
        cutoff = target - timedelta(days=1)
        league = fixture["league"]
        home_id = str(fixture["home"]["id"])
        away_id = str(fixture["away"]["id"])
        current_season = current_seasons[league]
        home_history = bounded_team_history(
            team_index[league, home_id], target, cutoff, current_season, maximum
        )
        away_history = bounded_team_history(
            team_index[league, away_id], target, cutoff, current_season, maximum
        )
        home_venue = [
            row for row in home_history if row["home"] and None not in (row["shots"], row["against"])
        ][-5:]
        away_venue = [
            row for row in away_history if not row["home"] and None not in (row["shots"], row["against"])
        ][-5:]
        eligible = (
            len(home_history) >= spec["environment"]["minimum_team_matches"]
            and len(away_history) >= spec["environment"]["minimum_team_matches"]
            and len(home_venue) >= spec["environment"]["minimum_venue_matches"]
            and len(away_venue) >= spec["environment"]["minimum_venue_matches"]
        )
        home_current = sum(row["season"] == current_season for row in home_history)
        away_current = sum(row["season"] == current_season for row in away_history)
        if home_current >= 3 and away_current >= 3:
            tier = "A"
        elif home_current >= 1 and away_current >= 1:
            tier = "B"
        else:
            tier = "C"
        row = {
            "match_id": str(fixture["id"]),
            "date": fixture["status"]["utcTime"],
            "league": league,
            "league_id": fixture["league_id"],
            "fixture": f"{fixture['home']['name']} vs {fixture['away']['name']}",
            "home_team_id": home_id,
            "away_team_id": away_id,
            "home_team": fixture["home"]["name"],
            "away_team": fixture["away"]["name"],
            "eligible": eligible,
            "confidence_tier": tier if eligible else "EXCLUDED",
            "home_current_matches": home_current,
            "away_current_matches": away_current,
            "history_cutoff": cutoff.isoformat(),
            "home_prior_ids": [item["match_id"] for item in home_history],
            "away_prior_ids": [item["match_id"] for item in away_history],
        }
        if eligible:
            row.update(
                overall_ppg_gap=average(home_history, "points") - average(away_history, "points"),
                recent_five_ppg_gap=average(home_history[-5:], "points") - average(away_history[-5:], "points"),
                home_home_shots=average(home_venue, "shots"),
                away_away_conceded=average(away_venue, "against"),
                away_away_shots=average(away_venue, "shots"),
                home_home_conceded=average(home_venue, "against"),
            )
            row["projected_home_shots"] = (row["home_home_shots"] + row["away_away_conceded"]) / 2
            row["projected_away_shots"] = (row["away_away_shots"] + row["home_home_conceded"]) / 2
            row["projected_shot_gap"] = row["projected_home_shots"] - row["projected_away_shots"]

        candidate_pool = []
        for (player_league, team_id, player_id), appearances in player_index.items():
            if player_league != league or team_id != home_id:
                continue
            prior = [
                item
                for item in appearances
                if item["date"] < cutoff and target - item["date"] <= timedelta(days=180)
            ][-5:]
            complete = len(prior) == 5 and all(
                None not in (item["shots"], item["minutes"], item["shot_share"]) for item in prior
            )
            if not complete:
                continue
            candidate_pool.append(
                {
                    "player_id": player_id,
                    "player": prior[-1]["player"],
                    "position_id": prior[-1].get("position_id"),
                    "avg_shots": round(average(prior, "shots"), 3),
                    "avg_minutes": round(average(prior, "minutes"), 3),
                    "hits_2plus": sum(item["shots"] >= 2 for item in prior),
                    "hits_3plus": sum(item["shots"] >= 3 for item in prior),
                    "avg_shot_share": round(average(prior, "shot_share"), 5),
                    "current_season_starts": sum(item["season"] == current_season for item in prior),
                    "prior_ids": [item["match_id"] for item in prior],
                    "prior_rows": [
                        {
                            "match_id": item["match_id"],
                            "date": item["date"].isoformat(),
                            "shots": item["shots"],
                            "minutes": item["minutes"],
                            "team_shots": item["team_shots"],
                            "shot_share": round(item["shot_share"], 5),
                        }
                        for item in prior
                    ],
                }
            )
        row["candidate_pool"] = sorted(candidate_pool, key=lambda item: item["player_id"])
        rows.append(row)

    eligible_rows = [row for row in rows if row["eligible"]]
    metric_keys = (
        "overall_ppg_gap",
        "recent_five_ppg_gap",
        "projected_home_shots",
        "projected_shot_gap",
    )
    for key in metric_keys:
        values = [row[key] for row in eligible_rows]
        for row in eligible_rows:
            row[key + "_percentile"] = round(percentile(row[key], values), 1)
    weights = spec["environment"]["weights"]
    for row in eligible_rows:
        row["environment_score"] = round(
            weights["overall_ppg_gap_percentile"] * row["overall_ppg_gap_percentile"]
            + weights["recent_five_ppg_gap_percentile"] * row["recent_five_ppg_gap_percentile"]
            + weights["projected_home_shots_percentile"] * row["projected_home_shots_percentile"]
            + weights["projected_shot_gap_percentile"] * row["projected_shot_gap_percentile"],
            1,
        )
    ranked = sorted(eligible_rows, key=lambda item: (-item["environment_score"], item["match_id"]))
    selection_rank = 0
    for overall_rank, row in enumerate(ranked, 1):
        row["overall_environment_rank"] = overall_rank
        if row["confidence_tier"] in ("A", "B"):
            selection_rank += 1
            row["environment_rank"] = selection_rank
            row["selected_environment"] = selection_rank <= 5
        else:
            row["environment_rank"] = None
            row["selected_environment"] = False
    for row in rows:
        if not row["eligible"]:
            row["selected_environment"] = False
            row["environment_rank"] = None

    snapshot_object = {
        "status": "environment_locked_awaiting_lineups",
        "prospective": True,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "weekend": weekend,
        "spec_version": spec["version"],
        "acquisition_retrieved_utc": acquisition["retrieved_utc"],
        "rules": spec,
        "fixtures": rows,
    }
    write_once(snapshot, snapshot_object)
    manifest = {
        "environment_snapshot_sha256": sha256(snapshot),
        "spec_sha256": sha256(SPEC_PATH),
        "selected_environment_ids": [
            row["match_id"]
            for row in sorted(
                (item for item in rows if item["selected_environment"]),
                key=lambda item: item["environment_rank"],
            )
        ],
        "outcome_accessed": False,
    }
    write_once(out / "manifest.json", manifest)
    print(
        json.dumps(
            {
                "status": snapshot_object["status"],
                "weekend": weekend,
                "fixtures": len(rows),
                "ranked": len(eligible_rows),
                "selected": len(manifest["selected_environment_ids"]),
                "snapshot": str(snapshot),
                "sha256": manifest["environment_snapshot_sha256"],
            },
            indent=2,
        )
    )


def possible(weekend: str) -> None:
    out = BASE / weekend
    snapshot_path = out / "environment_snapshot.json"
    if not snapshot_path.exists():
        raise SystemExit("Prepare the environment snapshot first.")
    snapshot = load_json(snapshot_path)
    history = load_json(out / "history_matches.json")
    forecasts = []
    all_plan_b = []
    selected = sorted(
        (row for row in snapshot["fixtures"] if row["selected_environment"]),
        key=lambda row: row["environment_rank"],
    )
    for environment in selected:
        target = dt(environment["date"])
        cutoff = dt(environment["history_cutoff"])
        team_matches = [
            match
            for match in history
            if match["league"] == environment["league"]
            and environment["home_team_id"] in (match["home_team_id"], match["away_team_id"])
            and dt(match["date"]) < cutoff
            and target - dt(match["date"]) <= timedelta(days=180)
        ][-5:]
        appearances = defaultdict(list)
        names = {}
        positions = {}
        for order, match in enumerate(team_matches, 1):
            for person in match["players"]:
                if person["team_id"] == environment["home_team_id"] and person["started"]:
                    appearances[person["player_id"]].append(
                        {"match_id": match["match_id"], "order": order, "minutes": person["minutes"]}
                    )
                    names[person["player_id"]] = person["player"]
                    positions[person["player_id"]] = person.get("position_id")
        possible_pool = []
        for player_id, starts in appearances.items():
            minutes = [item["minutes"] for item in starts if item["minutes"] is not None]
            possible_pool.append(
                {
                    "player_id": player_id,
                    "player": names[player_id],
                    "position_id": positions[player_id],
                    "starts_in_last_five": len(starts),
                    "recency_score": sum(item["order"] for item in starts),
                    "average_start_minutes": round(mean(minutes), 1) if minutes else None,
                    "source_match_ids": [item["match_id"] for item in starts],
                }
            )
        possible_pool.sort(
            key=lambda item: (
                -item["starts_in_last_five"],
                -item["recency_score"],
                -(item["average_start_minutes"] or 0),
                item["player_id"],
            )
        )
        possible_xi = possible_pool[:11]
        possible_ids = {item["player_id"] for item in possible_xi}
        candidates = [item for item in environment["candidate_pool"] if item["player_id"] in possible_ids]
        candidates.sort(key=lambda item: (-item["avg_shots"], -item["avg_minutes"], item["player_id"]))
        evaluated = []
        for shooter_rank, candidate in enumerate(candidates, 1):
            plan_b = (
                shooter_rank <= 2
                and candidate["hits_2plus"] >= 4
                and candidate["avg_shots"] >= 3
                and candidate["avg_minutes"] >= 80
            )
            evaluated_candidate = {
                **candidate,
                "shooter_rank_within_possible_XI": shooter_rank,
                "plan_B": plan_b,
            }
            evaluated.append(evaluated_candidate)
            if plan_b:
                all_plan_b.append(
                    {
                        **evaluated_candidate,
                        "match_id": environment["match_id"],
                        "date": environment["date"],
                        "league": environment["league"],
                        "fixture": environment["fixture"],
                        "home_team_id": environment["home_team_id"],
                        "environment_rank": environment["environment_rank"],
                        "environment_score": environment["environment_score"],
                    }
                )
        forecasts.append(
            {
                "match_id": environment["match_id"],
                "date": environment["date"],
                "league": environment["league"],
                "fixture": environment["fixture"],
                "environment_rank": environment["environment_rank"],
                "confidence_tier": environment["confidence_tier"],
                "method": "Top 11 by starts, recency and starting minutes across the team's last five matches; not a published or confirmed lineup.",
                "recent_team_matches": [match["match_id"] for match in team_matches],
                "possible_XI": possible_xi,
                "evaluated_candidates": evaluated,
            }
        )
    all_plan_b.sort(
        key=lambda item: (
            -item["hits_3plus"],
            -item["avg_shot_share"],
            -item["avg_shots"],
            -item["avg_minutes"],
            item["environment_rank"],
            item["player_id"],
        )
    )
    board_candidates = [
        {**candidate, "provisional_rank": rank, "status": "provisional_awaiting_confirmed_lineup"}
        for rank, candidate in enumerate(all_plan_b[:3], 1)
    ]
    now = datetime.now(timezone.utc)
    forecast_object = {
        "status": "possible_lineups_only_not_official_picks",
        "created_utc": now.isoformat(),
        "weekend": weekend,
        "environment_snapshot_sha256": sha256(snapshot_path),
        "forecasts": forecasts,
        "all_provisional_plan_B_candidates": all_plan_b,
        "provisional_top3": board_candidates,
    }
    folder = out / "possible_lineups"
    folder.mkdir(exist_ok=True)
    version = folder / (now.strftime("%Y%m%dT%H%M%SZ") + ".json")
    version.write_text(json.dumps(forecast_object, indent=2), encoding="utf-8")
    (out / "latest_possible_lineups.json").write_text(
        json.dumps(forecast_object, indent=2), encoding="utf-8"
    )
    board_path = out / "frozen_board.json"
    if not board_path.exists():
        write_once(
            board_path,
            {
                "status": "frozen_provisional_top3_not_official_picks",
                "created_utc": now.isoformat(),
                "weekend": weekend,
                "environment_snapshot_sha256": sha256(snapshot_path),
                "possible_lineup_version": version.name,
                "ranking_rule": load_json(SPEC_PATH)["three_plus_ranking"],
                "candidates": board_candidates,
                "outcome_accessed": False,
            },
        )
    print(
        json.dumps(
            {
                "status": forecast_object["status"],
                "version": str(version),
                "selected_environments": len(forecasts),
                "plan_B_candidates": len(all_plan_b),
                "frozen_board": str(board_path),
                "provisional_top3": [
                    {"rank": item["provisional_rank"], "player": item["player"], "fixture": item["fixture"]}
                    for item in load_json(board_path)["candidates"]
                ],
            },
            indent=2,
        )
    )


def lineups(weekend: str) -> None:
    out = BASE / weekend
    board_path = active_board_path(out)
    snapshot_path = out / "environment_snapshot.json"
    if not board_path.exists():
        raise SystemExit("Build and freeze the provisional board first.")
    board = load_json(board_path)
    snapshot = load_json(snapshot_path)
    environments = {row["match_id"]: row for row in snapshot["fixtures"]}
    by_match = defaultdict(list)
    for candidate in board["candidates"]:
        by_match[candidate["match_id"]].append(candidate)
    decisions_dir = out / "lineup_decisions"
    decisions_dir.mkdir(exist_ok=True)
    created = []
    waiting = []
    refused = []
    for match_id, board_candidates in by_match.items():
        destination = decisions_dir / f"{match_id}.json"
        if destination.exists():
            continue
        detail = get_json(
            "https://www.fotmob.com/api/data/matchDetails?"
            + urllib.parse.urlencode({"matchId": match_id})
        )
        general = detail.get("general") or {}
        if general.get("started") or general.get("finished"):
            refused.append({"match_id": match_id, "reason": "already_started_or_finished"})
            continue
        lineup = (detail.get("content") or {}).get("lineup") or {}
        home = lineup.get("homeTeam") or {}
        starters = {str(person["id"]) for person in home.get("starters") or [] if person.get("id") is not None}
        # FotMob also exposes predicted and last-used XIs.  Only its standard
        # lineup type represents the official match lineup.
        if lineup.get("lineupType") != "standard" or len(starters) < 11:
            waiting.append(match_id)
            continue
        environment = environments[match_id]
        confirmed_candidates = [
            item for item in environment["candidate_pool"] if item["player_id"] in starters
        ]
        confirmed_candidates.sort(
            key=lambda item: (-item["avg_shots"], -item["avg_minutes"], item["player_id"])
        )
        rank_by_player = {
            item["player_id"]: rank for rank, item in enumerate(confirmed_candidates, 1)
        }
        official = []
        rejected = []
        for candidate in board_candidates:
            shooter_rank = rank_by_player.get(candidate["player_id"])
            reasons = []
            if candidate["player_id"] not in starters:
                reasons.append("not_in_confirmed_home_starting_XI")
            if shooter_rank is None or shooter_rank > 2:
                reasons.append("outside_top_two_confirmed_home_shooters")
            if candidate["hits_2plus"] < 4:
                reasons.append("below_4_of_5_prior_2plus_gate")
            if candidate["avg_shots"] < 3:
                reasons.append("below_3_average_shots_gate")
            if candidate["avg_minutes"] < 80:
                reasons.append("below_80_average_minutes_gate")
            evaluated = {**candidate, "confirmed_shooter_rank": shooter_rank}
            if reasons:
                rejected.append({**evaluated, "decision": "rejected", "reasons": reasons})
            else:
                official.append({**evaluated, "decision": "official_locked_pick", "target": "3+ total shots"})
        decision = {
            "status": "confirmed_lineup_decision_locked_before_kickoff",
            "locked_utc": datetime.now(timezone.utc).isoformat(),
            "match_id": match_id,
            "date": environment["date"],
            "league": environment["league"],
            "fixture": environment["fixture"],
            "lineup_source": lineup.get("source"),
            "lineup_type": lineup.get("lineupType"),
            "confirmed_home_starter_ids": sorted(starters),
            "official_picks": official,
            "rejected_provisional_candidates": rejected,
            "replacement_policy": "No promotion from below the frozen provisional top three.",
            "outcome_accessed": False,
        }
        write_once(destination, decision)
        created.append(
            {
                "match_id": match_id,
                "fixture": environment["fixture"],
                "official": [item["player"] for item in official],
                "rejected": [item["player"] for item in rejected],
            }
        )
    print(json.dumps({"created": created, "waiting_for_confirmed_lineups": waiting, "refused_after_start": refused}, indent=2))


def settle(weekend: str) -> None:
    out = BASE / weekend
    decisions_dir = out / "lineup_decisions"
    settled_dir = out / "settled"
    settled_dir.mkdir(exist_ok=True)
    newly_settled = []
    waiting = []
    for decision_path in sorted(decisions_dir.glob("*.json")) if decisions_dir.exists() else []:
        decision = load_json(decision_path)
        destination = settled_dir / decision_path.name
        if destination.exists():
            continue
        detail = get_json(
            "https://www.fotmob.com/api/data/matchDetails?"
            + urllib.parse.urlencode({"matchId": decision["match_id"]})
        )
        general = detail.get("general") or {}
        if not general.get("finished"):
            waiting.append(decision["match_id"])
            continue
        player_stats = (detail.get("content") or {}).get("playerStats") or {}
        outcomes = []
        for pick in decision["official_picks"]:
            stats = player_stats.get(str(pick["player_id"])) or {}
            shots = extract_stat(stats, "total_shots")
            minutes = extract_stat(stats, "minutes_played")
            if shots is None and minutes is not None:
                shots = 0
            outcomes.append(
                {
                    **pick,
                    "minutes": minutes,
                    "shots": shots,
                    "hit_3plus": shots >= 3 if shots is not None else None,
                }
            )
        settlement = {
            **decision,
            "status": "settled",
            "settled_utc": datetime.now(timezone.utc).isoformat(),
            "official_picks": outcomes,
        }
        write_once(destination, settlement)
        newly_settled.append(
            {
                "match_id": decision["match_id"],
                "fixture": decision["fixture"],
                "picks": [(item["player"], item["shots"], item["hit_3plus"]) for item in outcomes],
            }
        )
    all_settlements = [load_json(path) for path in settled_dir.glob("*.json")]
    picks = [pick for result in all_settlements for pick in result["official_picks"]]
    graded = [pick for pick in picks if pick["hit_3plus"] is not None]
    summary = {
        "weekend": weekend,
        "settled_matches": len(all_settlements),
        "official_picks_graded": len(graded),
        "hits": sum(pick["hit_3plus"] for pick in graded),
        "hit_rate": round(100 * sum(pick["hit_3plus"] for pick in graded) / len(graded), 1) if graded else None,
        "newly_settled": newly_settled,
        "waiting": waiting,
    }
    (out / "settlement_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


def dashboard(weekend: str) -> None:
    out = BASE / weekend
    snapshot = load_json(out / "environment_snapshot.json")
    board_file = active_board_path(out)
    board = load_json(board_file) if board_file.exists() else {"candidates": []}
    environments = (
        sorted(board["selected_environments"], key=lambda row: row["environment_rank"])
        if board.get("selected_environments")
        else sorted(
            (row for row in snapshot["fixtures"] if row["selected_environment"]),
            key=lambda row: row["environment_rank"],
        )
    )
    decisions = [load_json(path) for path in sorted((out / "lineup_decisions").glob("*.json"))] if (out / "lineup_decisions").exists() else []
    settlements = [load_json(path) for path in sorted((out / "settled").glob("*.json"))] if (out / "settled").exists() else []
    official_ids = {pick["player_id"] for decision in decisions for pick in decision["official_picks"]}
    rejected = {
        pick["player_id"]: ", ".join(pick["reasons"])
        for decision in decisions
        for pick in decision["rejected_provisional_candidates"]
    }
    outcome_by_id = {
        pick["player_id"]: pick for result in settlements for pick in result["official_picks"]
    }
    environment_rows = "".join(
        f"<tr><td>{row['environment_rank']}</td><td>{escape(row['league'])}</td><td>{escape(row['fixture'])}</td>"
        f"<td>{row['environment_score']:.1f}</td><td>{row['confidence_tier']}</td>"
        f"<td>{row['projected_home_shots']:.1f}</td><td>{row['projected_shot_gap']:.1f}</td></tr>"
        for row in environments
    )
    candidate_rows = ""
    for candidate in board["candidates"]:
        if candidate["player_id"] in outcome_by_id:
            outcome = outcome_by_id[candidate["player_id"]]
            status = f"Settled: {outcome['shots']} shots — {'HIT' if outcome['hit_3plus'] else 'MISS'}"
        elif candidate["player_id"] in official_ids:
            status = "Official pick — confirmed starter"
        elif candidate["player_id"] in rejected:
            status = "Rejected: " + rejected[candidate["player_id"]].replace("_", " ")
        else:
            status = "Provisional — awaiting confirmed lineup"
        candidate_rows += (
            f"<tr><td>{candidate['provisional_rank']}</td><td>{escape(candidate['league'])}</td>"
            f"<td>{escape(candidate['fixture'])}</td><td>{escape(candidate['player'])}</td>"
            f"<td>{candidate['hits_3plus']}/5</td><td>{candidate['hits_2plus']}/5</td>"
            f"<td>{candidate['avg_shots']:.1f}</td><td>{100*candidate['avg_shot_share']:.1f}%</td>"
            f"<td>{escape(status)}</td></tr>"
        )
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Live Plan B 3+ — {escape(weekend)}</title>
<style>
body{{font-family:Inter,Segoe UI,sans-serif;background:#08111f;color:#e8eef8;margin:0;padding:32px}}main{{max-width:1200px;margin:auto}}
h1{{margin-bottom:4px}}.muted{{color:#9aabc3}}.notice{{background:#17243a;border-left:4px solid #f5b942;padding:14px 18px;border-radius:8px;margin:22px 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:20px 0}}.card{{background:#101c2f;border:1px solid #263956;padding:16px;border-radius:12px}}
table{{width:100%;border-collapse:collapse;background:#101c2f;margin:12px 0 28px}}th,td{{padding:11px;border-bottom:1px solid #263956;text-align:left}}th{{color:#92c5ff}}code{{color:#8ee3b0}}
</style></head><body><main>
<h1>Four-league Plan B: 3+ shots</h1><p class="muted">Weekend {escape(weekend)} · Premier League · Serie A · Bundesliga · MLS</p>
<div class="notice"><strong>Prospective research only.</strong> The top three names below are provisional until the player is confirmed in the home starting XI before kickoff. Possible lineups are not official picks. No lower-ranked replacement is promoted after the board is frozen.</div>
<div class="grid"><div class="card"><strong>{len(snapshot['fixtures'])}</strong><br>weekend fixtures scanned</div><div class="card"><strong>{len(environments)}</strong><br>top environments</div><div class="card"><strong>{len(board['candidates'])}</strong><br>frozen provisional candidates</div><div class="card"><strong>{sum(len(item['official_picks']) for item in decisions)}</strong><br>official confirmed picks</div></div>
<h2>Environment ranking</h2><table><thead><tr><th>Rank</th><th>League</th><th>Fixture</th><th>Score</th><th>Tier</th><th>Projected home shots</th><th>Shot gap</th></tr></thead><tbody>{environment_rows}</tbody></table>
<h2>Frozen Plan B top three</h2><table><thead><tr><th>Rank</th><th>League</th><th>Fixture</th><th>Player</th><th>Prior 3+</th><th>Prior 2+</th><th>Avg shots</th><th>Shot share</th><th>Status</th></tr></thead><tbody>{candidate_rows or '<tr><td colspan="9">No candidate passed every Plan B gate.</td></tr>'}</tbody></table>
<p class="muted">Environment version <code>{escape(snapshot['spec_version'])}</code> · active candidate ranking <code>{escape(board.get('ranking_version', snapshot['spec_version']))}</code>. Environment and candidate board files are immutable. This workflow has not yet established an independently validated profit rate for 3+ shots.</p>
</main></body></html>"""
    (out / "index.html").write_text(html, encoding="utf-8")
    print(json.dumps({"dashboard": str(out / "index.html"), "environments": len(environments), "provisional": len(board["candidates"]), "official": sum(len(item["official_picks"]) for item in decisions)}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "possible", "lineups", "settle", "dashboard"))
    parser.add_argument("--weekend", required=True)
    args = parser.parse_args()
    {
        "prepare": prepare,
        "possible": possible,
        "lineups": lineups,
        "settle": settle,
        "dashboard": dashboard,
    }[args.mode](args.weekend)


if __name__ == "__main__":
    main()
