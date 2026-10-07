"""Combine only identical ranked-Big-Five validation runs for an operational view."""
from __future__ import annotations

import json
import math
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/ranked_plan_b_combined_backtest"
RUNS = [
    ("2023/24", ROOT / "outputs/big5_2023_ranked_candidate_validation"),
    ("2024/25", ROOT / "outputs/big5_2024_ranked_candidate_validation"),
]


def wilson(hits: int, total: int) -> list[float] | None:
    if not total:
        return None
    z = 1.959963984540054
    p = hits / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return [round(100 * (centre - margin), 1), round(100 * (centre + margin), 1)]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    all_b_picks = []
    for label, folder in RUNS:
        result = json.loads((folder / "results.json").read_text(encoding="utf-8"))
        picks = json.loads((folder / "qualifying_picks.json").read_text(encoding="utf-8"))
        b_picks = [row for row in picks if row["B"]]
        active = [row for row in result["by_weekend"] if row["B"]["picks"]]
        clean = [row for row in active if row["B"]["hits"] == row["B"]["picks"]]
        rows.append(
            {
                "season": label,
                "source_matches": result["source_matches"],
                "environments": result["environment_home_outshot"],
                "A": result["A"],
                "B": result["B"],
                "active_B_weekends": len(active),
                "clean_B_weekends": len(clean),
                "longest_B_hit_streak": result["betting"]["B"]["max_consecutive_wins"]
                if "betting" in result
                else result["streaks"]["B"]["max_consecutive_wins"],
            }
        )
        all_b_picks.extend({"season": label, **row} for row in b_picks)

    a_hits = sum(row["A"]["hits"] for row in rows)
    a_picks = sum(row["A"]["picks"] for row in rows)
    b_hits = sum(row["B"]["hits"] for row in rows)
    b_picks = sum(row["B"]["picks"] for row in rows)
    active_weekends = sum(row["active_B_weekends"] for row in rows)
    clean_weekends = sum(row["clean_B_weekends"] for row in rows)
    env_hits = sum(row["environments"]["hits"] for row in rows)
    env_total = sum(row["environments"]["fixtures"] for row in rows)
    misses = [row for row in all_b_picks if row["hit"] is False]
    summary = {
        "scope": "two non-overlapping replications of the identical frozen ranked Big Five workflow",
        "seasons": rows,
        "combined": {
            "environment_home_outshot": {
                "hits": env_hits,
                "fixtures": env_total,
                "rate": round(100 * env_hits / env_total, 1),
            },
            "A": {
                "hits": a_hits,
                "picks": a_picks,
                "rate": round(100 * a_hits / a_picks, 1),
                "wilson95": wilson(a_hits, a_picks),
            },
            "B": {
                "hits": b_hits,
                "picks": b_picks,
                "rate": round(100 * b_hits / b_picks, 1),
                "wilson95": wilson(b_hits, b_picks),
            },
            "B_minus_A_percentage_points": round(
                100 * b_hits / b_picks - 100 * a_hits / a_picks, 1
            ),
            "active_B_weekends": active_weekends,
            "clean_B_weekends": clean_weekends,
            "clean_B_weekend_rate": round(100 * clean_weekends / active_weekends, 1),
            "B_picks_per_active_weekend": round(b_picks / active_weekends, 2),
        },
        "B_misses": [
            {
                key: row[key]
                for key in (
                    "season",
                    "weekend",
                    "league",
                    "fixture",
                    "player",
                    "avg_shots",
                    "avg_minutes",
                    "recent_hits",
                    "shots",
                )
            }
            for row in misses
        ],
        "interpretation": [
            "Plan B remains useful as a stricter primary shortlist, but it was not superior to Plan A in the new 2023/24 replication.",
            "The pooled difference is descriptive because picks share players, fixtures, leagues and weekends.",
            "Clean-weekend frequency is more relevant than individual hit rate for an all-picks-must-win weekend approach.",
            "Historical starting lineups are treated as known; this is not yet prospective proof.",
            "No historical odds or profit are claimed.",
        ],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    season_rows = "".join(
        f'<tr><td>{row["season"]}</td><td>{row["environments"]["hits"]}/{row["environments"]["fixtures"]} ({row["environments"]["rate"]}%)</td><td>{row["A"]["hits"]}/{row["A"]["picks"]} ({row["A"]["rate"]}%)</td><td>{row["B"]["hits"]}/{row["B"]["picks"]} ({row["B"]["rate"]}%)</td><td>{row["clean_B_weekends"]}/{row["active_B_weekends"]}</td><td>{row["longest_B_hit_streak"]}</td></tr>'
        for row in rows
    )
    miss_rows = "".join(
        f'<tr><td>{row["season"]}</td><td>{row["weekend"]}</td><td>{escape(row["league"])}</td><td>{escape(row["fixture"])}</td><td>{escape(row["player"])}</td><td>{row["avg_shots"]:.1f}</td><td>{row["avg_minutes"]:.1f}</td><td>{row["recent_hits"]}/5</td><td>{row["shots"]}</td></tr>'
        for row in summary["B_misses"]
    )
    c = summary["combined"]
    html = f'''<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Plan B combined backtest</title><style>body{{font:16px/1.55 system-ui;max-width:1100px;margin:30px auto;padding:0 18px;background:#f3f6f8;color:#183142}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}}.card{{background:white;padding:18px;border-top:5px solid #23865d}}table{{border-collapse:collapse;background:white;width:100%}}th,td{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}.scroll{{overflow:auto}}.note{{background:#fff3cf;padding:15px;border-left:5px solid #d99200}}</style><h1>Plan B ranked-Big-Five backtest</h1><div class="cards"><div class="card"><b>Plan B</b><br>{b_hits}/{b_picks} — {c["B"]["rate"]}%<br>95% interval {c["B"]["wilson95"][0]}–{c["B"]["wilson95"][1]}%</div><div class="card"><b>Clean weekends</b><br>{clean_weekends}/{active_weekends} — {c["clean_B_weekend_rate"]}%</div><div class="card"><b>Volume</b><br>{c["B_picks_per_active_weekend"]} B picks per active weekend</div><div class="card"><b>Environment</b><br>{env_hits}/{env_total} — {c["environment_home_outshot"]["rate"]}%</div></div><p class="note">Plan B is the stricter shortlist, not a guaranteed winner. The new season was 11/14, so the previous 9/9 should not be treated as the expected rate.</p><h2>By season</h2><div class="scroll"><table><tr><th>Season</th><th>Home outshot</th><th>Plan A</th><th>Plan B</th><th>Clean B weekends</th><th>Longest B streak</th></tr>{season_rows}</table></div><h2>Every Plan B miss</h2><div class="scroll"><table><tr><th>Season</th><th>Weekend</th><th>League</th><th>Fixture</th><th>Player</th><th>Prior avg shots</th><th>Prior avg min</th><th>Prior hits</th><th>Match shots</th></tr>{miss_rows}</table></div><p><a href="summary.json">Full structured summary</a> · <a href="../big5_2023_ranked_candidate_validation/index.html">2023/24 records</a> · <a href="../big5_2024_ranked_candidate_validation/index.html">2024/25 records</a></p></html>'''
    (OUT / "index.html").write_text(html, encoding="utf-8")
    print(json.dumps(summary["combined"], indent=2))


if __name__ == "__main__":
    main()
