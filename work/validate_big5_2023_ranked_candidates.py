"""Validate the frozen ranked-environment A/B rules on the 2023/24 target window."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from html import escape
from pathlib import Path

from build_big5_environment_rankings import process
from validate_big5_carryover import measure, rollover

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/big5_2023_ranked_candidate_validation"
PLAN = ROOT / "work/big5_2023_ranked_candidate_validation_plan.json"
CONFIG = {
    "slug": "big5_2023_ranked_candidate_validation",
    "label": "2023/24",
    "current": "2023/2024",
    "previous": "2022/2023",
    "weeks": ["2023-09-16", "2023-09-23", "2023-09-30", "2023-10-07"],
}


def fmt(result: dict) -> str:
    if not result["picks"]:
        return "No picks"
    return f'{result["hits"]}/{result["picks"]} ({result["rate"]}%)'


def main() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    acquisition = json.loads((OUT / "acquisition.json").read_text(encoding="utf-8"))
    fixtures = process(CONFIG)
    qualifying = [
        row
        for row in fixtures
        if row["eligible"]
        and row["weekend_rank"] <= 5
        and row["confidence_tier"] in ("A", "B")
    ]

    samples = []
    picks = []
    for environment in fixtures:
        qualifies = environment in qualifying
        for candidate in environment["ranked_candidates"]:
            selected_a = bool(
                qualifies
                and candidate["shooter_rank"] <= 2
                and candidate["avg_minutes"] >= 70
                and candidate["hits_2plus"] >= 4
            )
            selected_b = bool(
                selected_a
                and candidate["avg_shots"] >= 3
                and candidate["avg_minutes"] >= 80
            )
            reasons = []
            if not environment["eligible"]:
                reasons.append("environment_history_excluded")
            elif environment["weekend_rank"] > 5:
                reasons.append("outside_top_five_environments")
            elif environment["confidence_tier"] == "C":
                reasons.append("historical_only_tier_C")
            if candidate["shooter_rank"] > 2:
                reasons.append("outside_top_two_shooters")
            if candidate["avg_minutes"] < 70:
                reasons.append("minutes_below_70")
            if candidate["hits_2plus"] < 4:
                reasons.append("fewer_than_four_recent_hits")

            row = {
                "dataset": CONFIG["label"],
                "match_id": environment["match_id"],
                "date": environment["date"],
                "weekend": environment["weekend"],
                "league": environment["league"],
                "fixture": environment["fixture"],
                "environment_rank": environment.get("weekend_rank"),
                "environment_score": environment.get("environment_score"),
                "confidence_tier": environment["confidence_tier"],
                "home_current_matches": environment["home_current_matches"],
                "away_current_matches": environment["away_current_matches"],
                "player_id": candidate["player_id"],
                "player": candidate["player"],
                "shooter_rank": candidate["shooter_rank"],
                "avg_shots": candidate["avg_shots"],
                "avg_minutes": candidate["avg_minutes"],
                "recent_hits": candidate["hits_2plus"],
                "current_season_starts": candidate["current_season_starts"],
                "player_confidence": candidate["player_confidence"],
                "prior_ids": candidate["prior_ids"],
                "shots": candidate["shots"],
                "hit": candidate["hit_2plus"],
                "A": selected_a,
                "B": selected_b,
                "exclusion_reasons": reasons,
            }
            samples.append(row)
            if selected_a:
                picks.append(row)

    picks_a = picks
    picks_b = [row for row in picks if row["B"]]
    by_weekend = [
        {
            "weekend": week,
            "A": measure([row for row in picks_a if row["weekend"] == week]),
            "B": measure([row for row in picks_b if row["weekend"] == week]),
        }
        for week in CONFIG["weeks"]
    ]
    leagues = sorted({row["league"] for row in fixtures})
    by_league = {
        league: {
            "A": measure([row for row in picks_a if row["league"] == league]),
            "B": measure([row for row in picks_b if row["league"] == league]),
        }
        for league in leagues
    }
    known_environments = [
        row for row in qualifying if row["home_outshot_away"] is not None
    ]
    environment_hits = sum(row["home_outshot_away"] for row in known_environments)

    result = {
        "name": plan["name"],
        "classification": "frozen-before-acquisition historical replication",
        "plan_sha256": hashlib.sha256(PLAN.read_bytes()).hexdigest(),
        "provider": acquisition["provider"],
        "source_matches": acquisition["normalized_matches"],
        "acquisition_failures": len(acquisition["failures"]),
        "target_fixtures": len(fixtures),
        "ranked_fixtures": sum(row["eligible"] for row in fixtures),
        "qualifying_top_five_A_or_B_environments": len(qualifying),
        "environment_home_outshot": {
            "hits": environment_hits,
            "fixtures": len(known_environments),
            "rate": round(100 * environment_hits / len(known_environments), 1)
            if known_environments
            else None,
        },
        "candidate_samples": len(samples),
        "A": measure(picks_a),
        "B": measure(picks_b),
        "by_weekend": by_weekend,
        "by_league": by_league,
        "confidence_counts": dict(Counter(row["confidence_tier"] for row in fixtures)),
        "exclusions": dict(
            Counter(reason for row in samples for reason in row["exclusion_reasons"])
        ),
        "streaks": {"A": rollover(picks_a, 1.5), "B": rollover(picks_b, 2.0)},
        "limits": plan["limits"],
    }

    for name, obj in (
        ("frozen_test_plan", plan),
        ("ranked_fixtures", fixtures),
        ("all_candidate_samples", samples),
        ("qualifying_picks", picks),
        ("results", result),
    ):
        (OUT / f"{name}.json").write_text(json.dumps(obj, indent=2), encoding="utf-8")

    lines = [
        f'# {plan["name"]}',
        "",
        f'{result["source_matches"]} source matches; {result["target_fixtures"]} target fixtures; '
        f'{result["qualifying_top_five_A_or_B_environments"]} qualifying environments.',
        "",
        f'Environment home-shot dominance: **{environment_hits}/{len(known_environments)} '
        f'({result["environment_home_outshot"]["rate"]}%)**.',
        "",
        f'Plan B primary result: **{fmt(result["B"])}**. Plan A comparison: **{fmt(result["A"])}**.',
        "",
        "## By weekend",
        "",
        "| Weekend | Plan A | Plan B |",
        "|---|---:|---:|",
    ]
    for row in by_weekend:
        lines.append(f'| {row["weekend"]} | {fmt(row["A"])} | {fmt(row["B"])} |')
    lines.extend(["", "## Limits", ""] + [f"- {item}" for item in result["limits"]])
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    pick_rows = "".join(
        "<tr>"
        f'<td>{row["weekend"]}</td><td>{row["environment_rank"]}</td>'
        f'<td>{escape(row["league"])}</td><td>{escape(row["fixture"])}</td>'
        f'<td>{escape(row["player"])}</td><td>{"B" if row["B"] else "A only"}</td>'
        f'<td>{row["avg_shots"]:.1f}</td><td>{row["avg_minutes"]:.1f}</td>'
        f'<td>{row["shots"]}</td><td>{"HIT" if row["hit"] else "MISS"}</td>'
        "</tr>"
        for row in picks
    )
    html = f'''<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>2023/24 Plan B replication</title><style>body{{font:16px/1.55 system-ui;max-width:1200px;margin:30px auto;padding:0 18px;background:#f3f6f8;color:#183142}}table{{border-collapse:collapse;background:#fff;width:100%}}th,td{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}.scroll{{overflow:auto}}.card{{background:#fff;padding:18px;margin:15px 0}}.primary{{border-left:6px solid #23865d}}</style><h1>2023/24 ranked-environment replication</h1><div class="card primary"><b>Plan B primary:</b> {fmt(result["B"])}<br><b>Plan A comparison:</b> {fmt(result["A"])}<br>Environment home-shot dominance: {environment_hits}/{len(known_environments)} ({result["environment_home_outshot"]["rate"]}%)</div><p><a href="report.md">Method and limits</a> · <a href="ranked_fixtures.json">Every environment</a> · <a href="qualifying_picks.json">Every pick</a></p><div class="scroll"><table><tr><th>Weekend</th><th>Env rank</th><th>League</th><th>Fixture</th><th>Player</th><th>Plan</th><th>Prior avg shots</th><th>Prior avg min</th><th>Shots</th><th>Result</th></tr>{pick_rows}</table></div></html>'''
    (OUT / "index.html").write_text(html, encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
