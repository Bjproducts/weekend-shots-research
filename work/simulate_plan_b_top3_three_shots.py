"""Simulate top-three Plan B candidates at a hypothetical 1.40 for 3+ shots."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/plan_b_top3_three_shots_simulation"
PLAN_PATH = ROOT / "work/plan_b_top3_three_shots_simulation_plan.json"
SOURCES = [
    ("2023/24", ROOT / "outputs/big5_2023_ranked_candidate_validation"),
    ("2024/25", ROOT / "outputs/big5_2024_ranked_candidate_validation"),
]
ODDS = 1.4
STAKE = 10.0


def money(value: float) -> float:
    return round(value + 1e-9, 2)


def main() -> None:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    grouped = defaultdict(list)

    for season, folder in SOURCES:
        picks = json.loads((folder / "qualifying_picks.json").read_text(encoding="utf-8"))
        for row in picks:
            if row["B"]:
                grouped[(season, row["weekend"])].append({"season": season, **row})

    weekend_rows = []
    selected = []
    for (season, weekend), candidates in sorted(grouped.items()):
        ranked = sorted(
            candidates,
            key=lambda row: (
                -row["avg_shots"],
                -row["avg_minutes"],
                row["environment_rank"],
                str(row["player_id"]),
            ),
        )
        retained = ranked[:3]
        for rank, row in enumerate(retained, 1):
            selected.append(
                {
                    **row,
                    "top3_rank": rank,
                    "target_3plus": row["shots"] >= 3 if row["shots"] is not None else None,
                }
            )

        outcomes = [row["shots"] >= 3 for row in retained if row["shots"] is not None]
        exact_three = len(retained) == 3 and len(outcomes) == 3
        clean_three = exact_three and all(outcomes)
        weekend_rows.append(
            {
                "season": season,
                "weekend": weekend,
                "available_B_candidates": len(candidates),
                "retained": len(retained),
                "selected_players": [row["player"] for row in retained],
                "three_plus_hits": sum(outcomes),
                "exact_three_eligible": exact_three,
                "clean_three": clean_three if exact_three else None,
                "accumulator_odds": round(ODDS**3, 3) if exact_three else None,
                "accumulator_return": money(STAKE * ODDS**3) if clean_three else 0.0 if exact_three else None,
                "accumulator_profit": money(STAKE * ODDS**3 - STAKE) if clean_three else -STAKE if exact_three else None,
            }
        )

    known = [row for row in selected if row["target_3plus"] is not None]
    hits = sum(row["target_3plus"] for row in known)
    flat_staked = STAKE * len(known)
    flat_return = STAKE * ODDS * hits
    eligible_weekends = [row for row in weekend_rows if row["exact_three_eligible"]]
    clean_weekends = [row for row in eligible_weekends if row["clean_three"]]
    accumulator_staked = STAKE * len(eligible_weekends)
    accumulator_return = sum(row["accumulator_return"] for row in eligible_weekends)

    rollover_cycles = []
    balance = STAKE
    wins = 0
    deposits = STAKE if eligible_weekends else 0.0
    for row in eligible_weekends:
        before = balance
        if row["clean_three"]:
            balance = money(balance * ODDS**3)
            wins += 1
            result = "WIN"
        else:
            balance = 0.0
            result = "LOSS"
        rollover_cycles.append(
            {
                "season": row["season"],
                "weekend": row["weekend"],
                "result": result,
                "stake": before,
                "return": balance,
                "consecutive_clean_weekends": wins,
            }
        )
        if balance == 0 and row is not eligible_weekends[-1]:
            balance = STAKE
            deposits += STAKE
            wins = 0

    result = {
        "classification": plan["classification"],
        "plan_sha256": hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest(),
        "target": "3+ total shots",
        "selection": "Top three Plan B candidates per weekend by frozen pre-match ranking",
        "assumed_decimal_odds": ODDS,
        "weekends_with_B_candidates": len(weekend_rows),
        "selected_candidates": len(selected),
        "flat_singles": {
            "hits": hits,
            "picks": len(known),
            "hit_rate": round(100 * hits / len(known), 1) if known else None,
            "break_even_hit_rate": round(100 / ODDS, 1),
            "staked": money(flat_staked),
            "returned": money(flat_return),
            "profit": money(flat_return - flat_staked),
            "roi_percent": round(100 * (flat_return - flat_staked) / flat_staked, 1) if flat_staked else None,
        },
        "exact_three_accumulators": {
            "eligible_weekends": len(eligible_weekends),
            "clean_weekends": len(clean_weekends),
            "clean_rate": round(100 * len(clean_weekends) / len(eligible_weekends), 1) if eligible_weekends else None,
            "combined_decimal_odds": round(ODDS**3, 3),
            "staked": money(accumulator_staked),
            "returned": money(accumulator_return),
            "profit": money(accumulator_return - accumulator_staked),
            "roi_percent": round(100 * (accumulator_return - accumulator_staked) / accumulator_staked, 1) if accumulator_staked else None,
        },
        "weekend_rollover": {
            "starting_stake_per_cycle": STAKE,
            "total_deposits": money(deposits),
            "ending_active_balance": money(balance),
            "net_against_deposits": money(balance - deposits),
            "cycles": rollover_cycles,
            "warning": "Mathematical fixed-odds diagnostic only; historical availability and same-match correlation are not priced.",
        },
        "weekends": weekend_rows,
        "limits": plan["rules"],
    }

    (OUT / "selected_candidates.json").write_text(json.dumps(selected, indent=2), encoding="utf-8")
    (OUT / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    candidate_rows = "".join(
        f'<tr><td>{row["season"]}</td><td>{row["weekend"]}</td><td>{row["top3_rank"]}</td><td>{escape(row["league"])}</td><td>{escape(row["fixture"])}</td><td>{escape(row["player"])}</td><td>{row["avg_shots"]:.1f}</td><td>{row["avg_minutes"]:.1f}</td><td>{row["shots"]}</td><td>{"HIT" if row["target_3plus"] else "MISS"}</td></tr>'
        for row in selected
    )
    weekend_table = "".join(
        f'<tr><td>{row["season"]}</td><td>{row["weekend"]}</td><td>{row["available_B_candidates"]}</td><td>{row["retained"]}</td><td>{row["three_plus_hits"]}</td><td>{"WIN" if row["clean_three"] else "LOSS" if row["clean_three"] is False else "SKIP"}</td></tr>'
        for row in weekend_rows
    )
    singles = result["flat_singles"]
    acca = result["exact_three_accumulators"]
    html = f'''<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Plan B top-three 3+ simulation</title><style>body{{font:16px/1.55 system-ui;max-width:1200px;margin:30px auto;padding:0 18px;background:#f3f6f8;color:#183142}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}}.card{{background:#fff;padding:18px;border-top:5px solid #23865d}}table{{border-collapse:collapse;background:#fff;width:100%}}th,td{{padding:9px;border-bottom:1px solid #ddd;text-align:left}}.scroll{{overflow:auto}}.warn{{background:#fff3cf;padding:15px;border-left:5px solid #d99200}}</style><h1>Plan B: top three candidates for 3+ shots</h1><p class="warn">Retrospective what-if using hypothetical 1.40 odds. This is a new 3+ target and not an independently validated betting return.</p><div class="cards"><div class="card"><b>Flat singles</b><br>{hits}/{len(known)} — {singles["hit_rate"]}%<br>Profit: ${singles["profit"]:.2f} · ROI {singles["roi_percent"]}%</div><div class="card"><b>Exact three-player weekends</b><br>{len(clean_weekends)}/{len(eligible_weekends)} clean — {acca["clean_rate"]}%<br>Combined odds {acca["combined_decimal_odds"]}</div><div class="card"><b>Accumulator flat stakes</b><br>Staked ${acca["staked"]:.2f}<br>Profit ${acca["profit"]:.2f} · ROI {acca["roi_percent"]}%</div><div class="card"><b>Rollover</b><br>Deposits ${result["weekend_rollover"]["total_deposits"]:.2f}<br>Ending balance ${result["weekend_rollover"]["ending_active_balance"]:.2f}</div></div><h2>Weekend slips</h2><div class="scroll"><table><tr><th>Season</th><th>Weekend</th><th>B available</th><th>Retained</th><th>3+ hits</th><th>Exact-three result</th></tr>{weekend_table}</table></div><h2>Every retained candidate</h2><div class="scroll"><table><tr><th>Season</th><th>Weekend</th><th>Rank</th><th>League</th><th>Fixture</th><th>Player</th><th>Prior avg shots</th><th>Prior avg min</th><th>Match shots</th><th>3+ result</th></tr>{candidate_rows}</table></div><p><a href="results.json">Full simulation</a> · <a href="selected_candidates.json">Selected candidate records</a></p></html>'''
    (OUT / "index.html").write_text(html, encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("flat_singles", "exact_three_accumulators", "weekend_rollover")}, indent=2))


if __name__ == "__main__":
    main()
