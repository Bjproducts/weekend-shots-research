"""Rerank Plan B candidates with previous-five features matched to a 3+ target."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from html import escape
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/plan_b_top3_three_shots_reranked"
PLAN_PATH = ROOT / "work/plan_b_top3_three_shots_rerank_plan.json"
OLD_SELECTIONS = ROOT / "outputs/plan_b_top3_three_shots_simulation/selected_candidates.json"
SOURCES = [
    ("2023/24", ROOT / "outputs/big5_2023_ranked_candidate_validation"),
    ("2024/25", ROOT / "outputs/big5_2024_ranked_candidate_validation"),
]
ODDS = 1.4
STAKE = 10.0


def money(value: float) -> float:
    return round(value + 1e-9, 2)


def enrich(row: dict, matches: dict[str, dict]) -> dict:
    prior_rows = []
    for match_id in row["prior_ids"]:
        match = matches.get(str(match_id))
        if not match:
            continue
        player = next(
            (p for p in match["players"] if str(p["player_id"]) == str(row["player_id"])),
            None,
        )
        if not player or player["shots"] is None or player["minutes"] is None:
            continue
        team_shots = match["home_shots"] if player["home"] else match["away_shots"]
        share = player["shots"] / team_shots if team_shots else None
        prior_rows.append(
            {
                "match_id": str(match_id),
                "shots": player["shots"],
                "minutes": player["minutes"],
                "team_shots": team_shots,
                "shot_share": share,
            }
        )

    shares = [prior["shot_share"] for prior in prior_rows if prior["shot_share"] is not None]
    complete = len(prior_rows) == 5 and len(shares) == 5
    return {
        **row,
        "prior_feature_rows": prior_rows,
        "prior_features_complete": complete,
        "prior_3plus_hits": sum(prior["shots"] >= 3 for prior in prior_rows) if complete else None,
        "prior_avg_shot_share": mean(shares) if complete else None,
        "verified_avg_shots": mean(prior["shots"] for prior in prior_rows) if complete else None,
        "verified_avg_minutes": mean(prior["minutes"] for prior in prior_rows) if complete else None,
    }


def summarize_stakes(selected: list[dict], weekends: list[dict]) -> dict:
    known = [row for row in selected if row["target_3plus"] is not None]
    hits = sum(row["target_3plus"] for row in known)
    flat_staked = STAKE * len(known)
    flat_return = STAKE * ODDS * hits
    eligible = [row for row in weekends if row["exact_three_eligible"]]
    clean = [row for row in eligible if row["clean_three"]]
    acca_staked = STAKE * len(eligible)
    acca_return = sum(row["accumulator_return"] for row in eligible)

    cycles = []
    balance = STAKE
    deposits = STAKE if eligible else 0.0
    consecutive = 0
    for index, row in enumerate(eligible):
        before = balance
        if row["clean_three"]:
            balance = money(balance * ODDS**3)
            consecutive += 1
            result = "WIN"
        else:
            balance = 0.0
            consecutive = 0
            result = "LOSS"
        cycles.append(
            {
                "season": row["season"],
                "weekend": row["weekend"],
                "result": result,
                "stake": before,
                "return": balance,
                "consecutive_clean_weekends": consecutive,
            }
        )
        if balance == 0 and index < len(eligible) - 1:
            balance = STAKE
            deposits += STAKE

    return {
        "flat_singles": {
            "hits": hits,
            "picks": len(known),
            "hit_rate": round(100 * hits / len(known), 1) if known else None,
            "break_even_hit_rate": round(100 / ODDS, 1),
            "staked": money(flat_staked),
            "returned": money(flat_return),
            "profit": money(flat_return - flat_staked),
            "roi_percent": round(100 * (flat_return - flat_staked) / flat_staked, 1)
            if flat_staked
            else None,
        },
        "exact_three_accumulators": {
            "eligible_weekends": len(eligible),
            "clean_weekends": len(clean),
            "clean_rate": round(100 * len(clean) / len(eligible), 1) if eligible else None,
            "combined_decimal_odds": round(ODDS**3, 3),
            "staked": money(acca_staked),
            "returned": money(acca_return),
            "profit": money(acca_return - acca_staked),
            "roi_percent": round(100 * (acca_return - acca_staked) / acca_staked, 1)
            if acca_staked
            else None,
        },
        "weekend_rollover": {
            "starting_stake_per_cycle": STAKE,
            "total_deposits": money(deposits),
            "ending_active_balance": money(balance),
            "net_against_deposits": money(balance - deposits),
            "cycles": cycles,
        },
    }


def main() -> None:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    grouped = defaultdict(list)
    incomplete = []

    for season, folder in SOURCES:
        matches_list = json.loads((folder / "normalized_matches.json").read_text(encoding="utf-8"))
        matches = {str(match["match_id"]): match for match in matches_list}
        picks = json.loads((folder / "qualifying_picks.json").read_text(encoding="utf-8"))
        for row in picks:
            if not row["B"]:
                continue
            enriched = enrich({"season_label": season, **row}, matches)
            if not enriched["prior_features_complete"]:
                incomplete.append(
                    {"season": season, "weekend": row["weekend"], "player": row["player"]}
                )
                continue
            grouped[(season, row["weekend"])].append(enriched)

    selected = []
    weekend_rows = []
    for (season, weekend), candidates in sorted(grouped.items()):
        ranked = sorted(
            candidates,
            key=lambda row: (
                -row["prior_3plus_hits"],
                -row["prior_avg_shot_share"],
                -row["verified_avg_shots"],
                -row["verified_avg_minutes"],
                row["environment_rank"],
                str(row["player_id"]),
            ),
        )
        retained = ranked[:3]
        final_rows = []
        for rank, row in enumerate(retained, 1):
            final_row = {
                **row,
                "reranked_top3_rank": rank,
                "target_3plus": row["shots"] >= 3 if row["shots"] is not None else None,
            }
            selected.append(final_row)
            final_rows.append(final_row)
        outcomes = [row["target_3plus"] for row in final_rows if row["target_3plus"] is not None]
        exact_three = len(final_rows) == 3 and len(outcomes) == 3
        clean_three = exact_three and all(outcomes)
        weekend_rows.append(
            {
                "season": season,
                "weekend": weekend,
                "available_complete_B_candidates": len(candidates),
                "retained": len(final_rows),
                "selected_players": [row["player"] for row in final_rows],
                "three_plus_hits": sum(outcomes),
                "exact_three_eligible": exact_three,
                "clean_three": clean_three if exact_three else None,
                "accumulator_odds": round(ODDS**3, 3) if exact_three else None,
                "accumulator_return": money(STAKE * ODDS**3)
                if clean_three
                else 0.0
                if exact_three
                else None,
            }
        )

    stakes = summarize_stakes(selected, weekend_rows)
    old = json.loads(OLD_SELECTIONS.read_text(encoding="utf-8")) if OLD_SELECTIONS.exists() else []
    old_keys = {(row["season"], row["weekend"], str(row["player_id"])) for row in old}
    new_keys = {
        (row["season_label"], row["weekend"], str(row["player_id"])) for row in selected
    }
    result = {
        "classification": plan["classification"],
        "plan_sha256": hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest(),
        "target": plan["target"],
        "ranking": plan["ranking"],
        "assumed_decimal_odds": ODDS,
        "incomplete_prior_features": incomplete,
        "selection_changes": {
            "retained_from_old": len(old_keys & new_keys),
            "newly_selected": len(new_keys - old_keys),
            "removed_from_old": len(old_keys - new_keys),
        },
        **stakes,
        "weekends": weekend_rows,
        "limits": plan["limits"],
    }
    (OUT / "selected_candidates.json").write_text(json.dumps(selected, indent=2), encoding="utf-8")
    (OUT / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    singles = result["flat_singles"]
    acca = result["exact_three_accumulators"]
    rows = "".join(
        f'<tr><td>{row["season_label"]}</td><td>{row["weekend"]}</td><td>{row["reranked_top3_rank"]}</td><td>{escape(row["player"])}</td><td>{row["prior_3plus_hits"]}/5</td><td>{100*row["prior_avg_shot_share"]:.1f}%</td><td>{row["verified_avg_shots"]:.1f}</td><td>{row["verified_avg_minutes"]:.1f}</td><td>{row["environment_rank"]}</td><td>{row["shots"]}</td><td>{"HIT" if row["target_3plus"] else "MISS"}</td></tr>'
        for row in selected
    )
    html = f'''<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Plan B 3+ reranked</title><style>body{{font:16px/1.55 system-ui;max-width:1200px;margin:30px auto;padding:0 18px;background:#f3f6f8;color:#183142}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}}.card{{background:#fff;padding:18px;border-top:5px solid #23865d}}table{{border-collapse:collapse;background:#fff;width:100%}}th,td{{padding:9px;border-bottom:1px solid #ddd;text-align:left}}.scroll{{overflow:auto}}.warn{{background:#fff3cf;padding:15px;border-left:5px solid #d99200}}</style><h1>Plan B top-three: 3+-specific reranking</h1><p class="warn">Retrospective refinement, not untouched validation. Ranking now uses previous-five 3+ frequency and shot share before average shots and minutes.</p><div class="cards"><div class="card"><b>Reranked singles</b><br>{singles["hits"]}/{singles["picks"]} — {singles["hit_rate"]}%<br>Profit ${singles["profit"]:.2f} · ROI {singles["roi_percent"]}%</div><div class="card"><b>Exact-three weekends</b><br>{acca["clean_weekends"]}/{acca["eligible_weekends"]} clean — {acca["clean_rate"]}%<br>Profit ${acca["profit"]:.2f}</div><div class="card"><b>Selection changes</b><br>{result["selection_changes"]["newly_selected"]} added · {result["selection_changes"]["removed_from_old"]} removed</div><div class="card"><b>Feature coverage</b><br>{len(incomplete)} incomplete candidates</div></div><h2>Reranked candidates</h2><div class="scroll"><table><tr><th>Season</th><th>Weekend</th><th>Rank</th><th>Player</th><th>Prior 3+ hits</th><th>Shot share</th><th>Avg shots</th><th>Avg min</th><th>Env rank</th><th>Shots</th><th>Result</th></tr>{rows}</table></div><p><a href="results.json">Full results</a> · <a href="selected_candidates.json">Every enriched candidate</a> · <a href="../plan_b_top3_three_shots_simulation/index.html">Original ranking comparison</a></p></html>'''
    (OUT / "index.html").write_text(html, encoding="utf-8")
    print(json.dumps({"selection_changes": result["selection_changes"], **stakes}, indent=2))


if __name__ == "__main__":
    main()
