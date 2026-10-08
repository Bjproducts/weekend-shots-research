"""Replay the frozen four-league Plan B 3+ engine over current seasons."""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from statistics import mean, pstdev

from live_plan_b3 import average, bounded_team_history, build_indexes, dt, percentile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/season_to_date_plan_b3"
SOURCE = OUT
SPEC_PATH = ROOT / "work/season_to_date_plan_b3_spec.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(hits: int, total: int) -> list[float | None]:
    if not total:
        return [None, None]
    z = 1.959963984540054
    p = hits / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [round(100 * (center - margin), 1), round(100 * (center + margin), 1)]


def longest_streak(rows: list[dict], key: str, desired: bool) -> int:
    longest = current = 0
    for row in rows:
        if row[key] is desired:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def candidate_pool(
    league: str,
    home_id: str,
    target: datetime,
    cutoff: datetime,
    current_season: str,
    player_index: dict,
) -> list[dict]:
    pool = []
    for (player_league, team_id, player_id), appearances in player_index.items():
        if player_league != league or team_id != home_id:
            continue
        prior = [
            item
            for item in appearances
            if item["date"] < cutoff and target - item["date"] <= timedelta(days=180)
        ][-5:]
        if len(prior) != 5 or not all(
            None not in (item["shots"], item["minutes"], item["shot_share"]) for item in prior
        ):
            continue
        shot_values = [item["shots"] for item in prior]
        pool.append(
            {
                "player_id": player_id,
                "player": prior[-1]["player"],
                "position_id": prior[-1].get("position_id"),
                "avg_shots": round(average(prior, "shots"), 3),
                "avg_minutes": round(average(prior, "minutes"), 3),
                "hits_2plus": sum(item["shots"] >= 2 for item in prior),
                "hits_3plus": sum(item["shots"] >= 3 for item in prior),
                "avg_shot_share": round(average(prior, "shot_share"), 5),
                "shot_floor": min(shot_values),
                "shot_stddev": round(pstdev(shot_values), 5),
                "candidate_side": "home",
                "home_team_id": home_id,
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
    return pool


def rank_plan_b_candidates(candidates: list[dict], spec: dict) -> list[dict]:
    """Rank candidates, optionally applying the v2 similarity/consistency rule."""
    if spec.get("ranking_mode") != "similar_average_then_consistency":
        return sorted(
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
    similarity = spec["consistency_rule"]["similar_average_shots_max_difference"]
    remaining = sorted(candidates, key=lambda item: (-item["avg_shots"], item["player_id"]))
    ranked = []
    while remaining:
        anchor = remaining[0]["avg_shots"]
        group = [item for item in remaining if anchor - item["avg_shots"] <= similarity]
        group_ids = {(item["match_id"], item["player_id"]) for item in group}
        remaining = [
            item for item in remaining if (item["match_id"], item["player_id"]) not in group_ids
        ]
        group.sort(
            key=lambda item: (
                -item["hits_3plus"],
                -item["shot_floor"],
                item["shot_stddev"],
                -item["hits_2plus"],
                -item["avg_shot_share"],
                -item["avg_shots"],
                -item["avg_minutes"],
                item["environment_rank"],
                item["player_id"],
            )
        )
        ranked.extend(group)
    return ranked


def possible_xi(home_id: str, league: str, cutoff: datetime, target: datetime, team_matches: dict) -> tuple[list[dict], list[str]]:
    prior_matches = [
        match
        for match in team_matches[league, home_id]
        if dt(match["date"]) < cutoff and target - dt(match["date"]) <= timedelta(days=180)
    ][-5:]
    appearances = defaultdict(list)
    names = {}
    positions = {}
    for order, match in enumerate(prior_matches, 1):
        for person in match["players"]:
            if person["team_id"] == home_id and person["started"]:
                appearances[person["player_id"]].append(
                    {"match_id": match["match_id"], "order": order, "minutes": person["minutes"]}
                )
                names[person["player_id"]] = person["player"]
                positions[person["player_id"]] = person.get("position_id")
    rows = []
    for player_id, starts in appearances.items():
        minutes = [item["minutes"] for item in starts if item["minutes"] is not None]
        rows.append(
            {
                "player_id": player_id,
                "player": names[player_id],
                "position_id": positions[player_id],
                "starts_in_last_five": len(starts),
                "recency_score": sum(item["order"] for item in starts),
                "average_start_minutes": round(mean(minutes), 1) if minutes else None,
            }
        )
    rows.sort(
        key=lambda item: (
            -item["starts_in_last_five"],
            -item["recency_score"],
            -(item["average_start_minutes"] or 0),
            item["player_id"],
        )
    )
    return rows[:11], [match["match_id"] for match in prior_matches]


def make_environment(
    fixture: dict,
    cutoff: datetime,
    spec: dict,
    team_index: dict,
    player_index: dict,
) -> dict:
    target = dt(fixture["date"])
    league = fixture["league"]
    current_season = spec["scope"]["leagues"][league]["current_season"]
    home_id = fixture["home_team_id"]
    away_id = fixture["away_team_id"]
    boundary = spec["information_boundary"]
    home_history = bounded_team_history(
        team_index[league, home_id], target, cutoff, current_season, boundary["maximum_team_matches"]
    )
    away_history = bounded_team_history(
        team_index[league, away_id], target, cutoff, current_season, boundary["maximum_team_matches"]
    )
    home_venue = [
        row for row in home_history if row["home"] and None not in (row["shots"], row["against"])
    ][-5:]
    away_venue = [
        row for row in away_history if not row["home"] and None not in (row["shots"], row["against"])
    ][-5:]
    eligible = (
        len(home_history) >= boundary["minimum_team_matches"]
        and len(away_history) >= boundary["minimum_team_matches"]
        and len(home_venue) >= boundary["minimum_venue_matches"]
        and len(away_venue) >= boundary["minimum_venue_matches"]
    )
    home_current = sum(row["season"] == current_season for row in home_history)
    away_current = sum(row["season"] == current_season for row in away_history)
    tier = "A" if home_current >= 3 and away_current >= 3 else "B" if home_current >= 1 and away_current >= 1 else "C"
    row = {
        **fixture,
        "fixture": f"{fixture['home_team']} vs {fixture['away_team']}",
        "history_cutoff": cutoff.isoformat(),
        "eligible": eligible,
        "confidence_tier": tier if eligible else "EXCLUDED",
        "home_current_matches": home_current,
        "away_current_matches": away_current,
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
    row["candidate_pool"] = candidate_pool(
        league, home_id, target, cutoff, current_season, player_index
    )
    return row


def main() -> None:
    spec = load(SPEC_PATH)
    acquisition = load(SOURCE / "acquisition.json")
    if acquisition["failures"]:
        raise SystemExit("Acquisition failures must be resolved before replay.")
    matches = load(SOURCE / "matches.json")
    fixtures = load(SOURCE / "target_fixtures.json")
    OUT.mkdir(parents=True, exist_ok=True)
    match_by_id = {match["match_id"]: match for match in matches}
    missing_targets = [fixture["match_id"] for fixture in fixtures if fixture["match_id"] not in match_by_id]
    if missing_targets:
        raise SystemExit(f"Missing target match details: {missing_targets[:10]}")
    team_index, player_index = build_indexes(matches)
    team_matches = defaultdict(list)
    for match in matches:
        team_matches[match["league"], match["home_team_id"]].append(match)
        team_matches[match["league"], match["away_team_id"]].append(match)
    for rows in team_matches.values():
        rows.sort(key=lambda item: (item["date"], item["match_id"]))
    grouped = defaultdict(list)
    for fixture in fixtures:
        grouped[fixture["weekend"]].append(fixture)

    weekend_records = []
    official_picks = []
    provisional_count = 0
    selected_environment_count = 0
    lineup_data_gaps = 0
    for weekend in sorted(grouped):
        saturday = datetime.fromisoformat(weekend).replace(tzinfo=timezone.utc)
        cutoff = saturday - timedelta(days=1)
        environments = [
            make_environment(fixture, cutoff, spec, team_index, player_index)
            for fixture in grouped[weekend]
        ]
        eligible = [row for row in environments if row["eligible"]]
        for key in ("overall_ppg_gap", "recent_five_ppg_gap", "projected_home_shots", "projected_shot_gap"):
            values = [row[key] for row in eligible]
            for row in eligible:
                row[key + "_percentile"] = round(percentile(row[key], values), 1)
        weights = spec["environment"]["weights"]
        for row in eligible:
            row["environment_score"] = round(
                weights["overall_ppg_gap_percentile"] * row["overall_ppg_gap_percentile"]
                + weights["recent_five_ppg_gap_percentile"] * row["recent_five_ppg_gap_percentile"]
                + weights["projected_home_shots_percentile"] * row["projected_home_shots_percentile"]
                + weights["projected_shot_gap_percentile"] * row["projected_shot_gap_percentile"],
                1,
            )
        ranked = sorted(eligible, key=lambda item: (-item["environment_score"], item["match_id"]))
        selectable_rank = 0
        for overall_rank, environment in enumerate(ranked, 1):
            environment["overall_environment_rank"] = overall_rank
            if environment["confidence_tier"] in ("A", "B"):
                selectable_rank += 1
                environment["environment_rank"] = selectable_rank
                environment["selected_environment"] = selectable_rank <= 5
            else:
                environment["environment_rank"] = None
                environment["selected_environment"] = False
        for environment in environments:
            if not environment["eligible"]:
                environment["environment_rank"] = None
                environment["selected_environment"] = False
        selected = sorted(
            (row for row in environments if row["selected_environment"]),
            key=lambda item: item["environment_rank"],
        )
        selected_environment_count += len(selected)

        plan_b_candidates = []
        selected_summaries = []
        for environment in selected:
            target = dt(environment["date"])
            xi, recent_match_ids = possible_xi(
                environment["home_team_id"], environment["league"], cutoff, target, team_matches
            )
            possible_ids = {item["player_id"] for item in xi}
            candidates = [
                item for item in environment["candidate_pool"] if item["player_id"] in possible_ids
            ]
            candidates.sort(key=lambda item: (-item["avg_shots"], -item["avg_minutes"], item["player_id"]))
            evaluated = []
            for shooter_rank, candidate in enumerate(candidates, 1):
                plan_b = (
                    shooter_rank <= 2
                    and candidate["hits_2plus"] >= 4
                    and candidate["avg_shots"] >= 3
                    and candidate["avg_minutes"] >= 80
                )
                value = {
                    **candidate,
                    "shooter_rank_within_possible_XI": shooter_rank,
                    "plan_B": plan_b,
                }
                evaluated.append(value)
                if plan_b:
                    plan_b_candidates.append(
                        {
                            **value,
                            "weekend": weekend,
                            "match_id": environment["match_id"],
                            "date": environment["date"],
                            "league": environment["league"],
                            "fixture": environment["fixture"],
                            "home_team_id": environment["home_team_id"],
                            "environment_rank": environment["environment_rank"],
                            "environment_score": environment["environment_score"],
                        }
                    )
            selected_summaries.append(
                {
                    "match_id": environment["match_id"],
                    "date": environment["date"],
                    "league": environment["league"],
                    "fixture": environment["fixture"],
                    "environment_rank": environment["environment_rank"],
                    "environment_score": environment["environment_score"],
                    "confidence_tier": environment["confidence_tier"],
                    "projected_home_shots": environment["projected_home_shots"],
                    "projected_shot_gap": environment["projected_shot_gap"],
                    "history_cutoff": environment["history_cutoff"],
                    "home_prior_ids": environment["home_prior_ids"],
                    "away_prior_ids": environment["away_prior_ids"],
                    "recent_team_match_ids": recent_match_ids,
                    "possible_XI_ids": [item["player_id"] for item in xi],
                    "plan_B_candidates": [item for item in evaluated if item["plan_B"]],
                }
            )
        plan_b_candidates = rank_plan_b_candidates(plan_b_candidates, spec)
        provisional = [
            {**item, "provisional_rank": rank}
            for rank, item in enumerate(plan_b_candidates[:3], 1)
        ]
        provisional_count += len(provisional)
        decisions = []
        for candidate in provisional:
            result = match_by_id[candidate["match_id"]]
            starters = {
                person["player_id"]
                for person in result["players"]
                if person["team_id"] == candidate["home_team_id"] and person["started"]
            }
            if len(starters) < 11:
                lineup_data_gaps += 1
                decisions.append({**candidate, "decision": "lineup_data_gap", "actual_home_starters": len(starters)})
                continue
            environment = next(row for row in selected if row["match_id"] == candidate["match_id"])
            confirmed = [item for item in environment["candidate_pool"] if item["player_id"] in starters]
            confirmed.sort(key=lambda item: (-item["avg_shots"], -item["avg_minutes"], item["player_id"]))
            rank_by_id = {item["player_id"]: rank for rank, item in enumerate(confirmed, 1)}
            confirmed_rank = rank_by_id.get(candidate["player_id"])
            reasons = []
            if candidate["player_id"] not in starters:
                reasons.append("not_in_confirmed_home_starting_XI")
            if confirmed_rank is None or confirmed_rank > 2:
                reasons.append("outside_top_two_confirmed_home_shooters")
            if reasons:
                decisions.append(
                    {**candidate, "decision": "rejected_at_lineup", "confirmed_shooter_rank": confirmed_rank, "reasons": reasons}
                )
                continue
            person = next(
                (
                    item
                    for item in result["players"]
                    if item["team_id"] == candidate["home_team_id"]
                    and item["player_id"] == candidate["player_id"]
                ),
                None,
            )
            if person is None or person["shots"] is None:
                decisions.append({**candidate, "decision": "outcome_data_gap", "confirmed_shooter_rank": confirmed_rank})
                continue
            official = {
                **candidate,
                "decision": "official_pick",
                "confirmed_shooter_rank": confirmed_rank,
                "actual_minutes": person["minutes"],
                "actual_shots": person["shots"],
                "hit_2plus": person["shots"] >= 2,
                "hit_3plus": person["shots"] >= 3,
            }
            decisions.append(official)
            official_picks.append(official)
        weekend_official = [item for item in decisions if item["decision"] == "official_pick"]
        weekend_records.append(
            {
                "weekend": weekend,
                "history_cutoff": cutoff.isoformat(),
                "fixture_count": len(grouped[weekend]),
                "leagues": sorted({item["league"] for item in grouped[weekend]}),
                "eligible_environment_count": len(eligible),
                "ranked_environments": [
                    {
                        "match_id": item["match_id"],
                        "league": item["league"],
                        "fixture": item["fixture"],
                        "overall_environment_rank": item["overall_environment_rank"],
                        "environment_rank": item["environment_rank"],
                        "environment_score": item["environment_score"],
                        "confidence_tier": item["confidence_tier"],
                        "selected_environment": item["selected_environment"],
                    }
                    for item in ranked
                ],
                "selected_environments": selected_summaries,
                "provisional_board": provisional,
                "lineup_decisions": decisions,
                "official_picks": len(weekend_official),
                "hits_3plus": sum(item["hit_3plus"] for item in weekend_official),
                "clean_3plus_weekend": bool(weekend_official) and all(item["hit_3plus"] for item in weekend_official),
            }
        )

    official_picks.sort(
        key=lambda item: (item["date"], item["match_id"], item["provisional_rank"], item["player_id"])
    )
    hits_3 = sum(item["hit_3plus"] for item in official_picks)
    hits_2 = sum(item["hit_2plus"] for item in official_picks)
    active = [record for record in weekend_records if record["official_picks"]]
    clean = sum(record["clean_3plus_weekend"] for record in active)
    full_three = [record for record in weekend_records if record["official_picks"] == 3]
    clean_full_three = sum(record["hits_3plus"] == 3 for record in full_three)
    by_league = []
    for league in spec["scope"]["leagues"]:
        rows = [item for item in official_picks if item["league"] == league]
        by_league.append(
            {
                "league": league,
                "picks": len(rows),
                "hits_3plus": sum(item["hit_3plus"] for item in rows),
                "hit_rate_3plus": round(100 * sum(item["hit_3plus"] for item in rows) / len(rows), 1) if rows else None,
                "wilson_95": wilson(sum(item["hit_3plus"] for item in rows), len(rows)),
            }
        )
    by_player = []
    for (player_id, player), rows in sorted(
        defaultdict(list, {
            key: [item for item in official_picks if (item["player_id"], item["player"]) == key]
            for key in {(item["player_id"], item["player"]) for item in official_picks}
        }).items(),
        key=lambda pair: (-len(pair[1]), pair[0][1]),
    ):
        by_player.append(
            {
                "player_id": player_id,
                "player": player,
                "picks": len(rows),
                "hits_3plus": sum(item["hit_3plus"] for item in rows),
                "hit_rate_3plus": round(100 * sum(item["hit_3plus"] for item in rows) / len(rows), 1),
            }
        )
    rejection_counts = Counter(
        reason
        for record in weekend_records
        for decision in record["lineup_decisions"]
        for reason in decision.get("reasons", [])
    )
    summary = {
        "status": "retrospective_season_to_date_replay_complete",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "spec_version": spec["version"],
        "spec_sha256": digest(SPEC_PATH),
        "source_retrieved_utc": acquisition["retrieved_utc"],
        "source_matches": len(matches),
        "target_weekend_fixtures": len(fixtures),
        "calendar_weekends": len(weekend_records),
        "selected_environments": selected_environment_count,
        "provisional_candidates": provisional_count,
        "official_picks": len(official_picks),
        "hits_3plus": hits_3,
        "misses_3plus": len(official_picks) - hits_3,
        "hit_rate_3plus": round(100 * hits_3 / len(official_picks), 1) if official_picks else None,
        "wilson_95_3plus": wilson(hits_3, len(official_picks)),
        "hits_2plus": hits_2,
        "hit_rate_2plus": round(100 * hits_2 / len(official_picks), 1) if official_picks else None,
        "active_pick_weekends": len(active),
        "clean_3plus_weekends": clean,
        "clean_3plus_weekend_rate": round(100 * clean / len(active), 1) if active else None,
        "average_picks_per_active_weekend": round(len(official_picks) / len(active), 2) if active else None,
        "weekends_with_three_official_picks": len(full_three),
        "clean_three_pick_weekends": clean_full_three,
        "clean_three_pick_weekend_rate": round(100 * clean_full_three / len(full_three), 1) if full_three else None,
        "longest_individual_hit_streak_3plus": longest_streak(official_picks, "hit_3plus", True),
        "longest_individual_miss_streak_3plus": longest_streak(official_picks, "hit_3plus", False),
        "lineup_data_gaps": lineup_data_gaps,
        "rejection_reasons": dict(rejection_counts),
        "shots_distribution": dict(sorted(Counter(str(item["actual_shots"]) for item in official_picks).items(), key=lambda pair: int(pair[0]))),
        "by_league": by_league,
        "by_player": by_player,
        "interpretation": spec["interpretation"],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUT / "weekends.json").write_text(json.dumps(weekend_records, indent=2), encoding="utf-8")
    (OUT / "official_picks.json").write_text(json.dumps(official_picks, indent=2), encoding="utf-8")
    build_dashboard(summary, weekend_records, official_picks)
    print(json.dumps(summary, indent=2))


def pct(value):
    return "—" if value is None else f"{value:.1f}%"


def build_dashboard(summary: dict, weekends: list[dict], picks: list[dict]) -> None:
    league_rows = "".join(
        f"<tr><td>{escape(row['league'])}</td><td>{row['hits_3plus']}/{row['picks']}</td><td>{pct(row['hit_rate_3plus'])}</td><td>{row['wilson_95'][0]}–{row['wilson_95'][1]}%</td></tr>"
        for row in summary["by_league"]
    )
    weekend_rows = "".join(
        f"<tr><td>{row['weekend']}</td><td>{', '.join(row['leagues'])}</td><td>{row['fixture_count']}</td><td>{len(row['selected_environments'])}</td><td>{len(row['provisional_board'])}</td><td>{row['official_picks']}</td><td>{row['hits_3plus']}</td><td>{'Yes' if row['clean_3plus_weekend'] else 'No' if row['official_picks'] else '—'}</td></tr>"
        for row in reversed(weekends)
    )
    pick_rows = "".join(
        f"<tr><td>{row['weekend']}</td><td>{escape(row['league'])}</td><td>{escape(row['fixture'])}</td><td>{escape(row['player'])}</td><td>{row['provisional_rank']}</td><td>{row['hits_3plus']}/5</td><td>{row['avg_shots']:.1f}</td><td>{row['actual_shots']}</td><td class={'hit' if row['hit_3plus'] else 'miss'}>{'HIT' if row['hit_3plus'] else 'MISS'}</td></tr>"
        for row in reversed(picks)
    )
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Season-to-date Plan B 3+ replay</title>
<style>body{{font-family:Inter,Segoe UI,sans-serif;background:#07111f;color:#e7eef9;margin:0;padding:30px}}main{{max-width:1250px;margin:auto}}.muted{{color:#9eacc0}}.warning{{background:#1b2738;border-left:4px solid #f4bb44;padding:14px 18px;border-radius:8px;margin:20px 0}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:22px 0}}.card{{background:#101d30;border:1px solid #263953;border-radius:12px;padding:16px}}.big{{font-size:26px;font-weight:700}}table{{width:100%;border-collapse:collapse;background:#101d30;margin:12px 0 30px}}th,td{{padding:10px;border-bottom:1px solid #263953;text-align:left}}th{{color:#91c7ff;position:sticky;top:0;background:#101d30}}.scroll{{max-height:520px;overflow:auto}}.hit{{color:#70e3a5;font-weight:700}}.miss{{color:#ff8f8f;font-weight:700}}</style></head><body><main>
<h1>Season-to-date Plan B 3+ engine replay</h1><p class="muted">MLS · Premier League · Serie A · Bundesliga · completed Saturday/Sunday fixtures through 7 October 2026</p>
<div class="warning"><strong>Retrospective simulation, not a blind future test.</strong> Every selection feature is restricted to Friday's pre-weekend information. Historical confirmed starters then apply the same lineup gate. No lower-ranked candidate replaces a rejected top-three name.</div>
<div class="grid"><div class="card"><div class="big">{summary['target_weekend_fixtures']}</div>fixtures replayed</div><div class="card"><div class="big">{summary['official_picks']}</div>official simulated picks</div><div class="card"><div class="big">{summary['hits_3plus']}/{summary['official_picks']}</div>3+ hits</div><div class="card"><div class="big">{pct(summary['hit_rate_3plus'])}</div>3+ hit rate</div><div class="card"><div class="big">{summary['clean_3plus_weekends']}/{summary['active_pick_weekends']}</div>clean active weekends</div><div class="card"><div class="big">{summary['clean_three_pick_weekends']}/{summary['weekends_with_three_official_picks']}</div>clean three-pick weekends</div><div class="card"><div class="big">{summary['longest_individual_hit_streak_3plus']}</div>longest hit streak</div></div>
<p>95% Wilson interval: <strong>{summary['wilson_95_3plus'][0]}–{summary['wilson_95_3plus'][1]}%</strong>. The interval and the retrospective design matter more than the headline percentage.</p>
<h2>Performance by league</h2><table><thead><tr><th>League</th><th>Hits / picks</th><th>Hit rate</th><th>95% interval</th></tr></thead><tbody>{league_rows}</tbody></table>
<h2>Every replayed weekend</h2><div class="scroll"><table><thead><tr><th>Weekend</th><th>Active leagues</th><th>Fixtures</th><th>Environments</th><th>Provisional</th><th>Official</th><th>3+ hits</th><th>Clean</th></tr></thead><tbody>{weekend_rows}</tbody></table></div>
<h2>Every official simulated selection</h2><div class="scroll"><table><thead><tr><th>Weekend</th><th>League</th><th>Fixture</th><th>Player</th><th>Board rank</th><th>Prior 3+</th><th>Prior avg</th><th>Actual shots</th><th>Result</th></tr></thead><tbody>{pick_rows or '<tr><td colspan="9">No official picks.</td></tr>'}</tbody></table></div>
<p class="muted">Formula: {escape(summary['spec_version'])}. Source records: {summary['source_matches']}. Lineup data gaps: {summary['lineup_data_gaps']}. Historical pricing was not collected, so this report measures hit consistency rather than profit.</p>
</main></body></html>"""
    (OUT / "index.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
