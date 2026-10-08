"""Assumed-1.50 mechanics replay for the volume-v4 challenger."""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from simulate_hypothetical_v3_combo_1_5 import build_windows, simulate_bankroll

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs/season_to_date_plan_b3_volume_v4/official_picks.json"
SOURCE_SUMMARY = ROOT / "outputs/season_to_date_plan_b3_volume_v4/summary.json"
SPEC_PATH = ROOT / "work/hypothetical_volume_v4_combo_1_5_spec.json"
OUT = ROOT / "outputs/hypothetical_volume_v4_combo_1_5"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    spec = load(SPEC_PATH)
    picks = load(SOURCE)
    source_summary = load(SOURCE_SUMMARY)
    window_spec = {**spec, "stake_fraction": spec["staking_tracks"]["fixed_10"]}
    tickets, no_combo = build_windows(picks, window_spec)
    tracks = {}
    for name, fraction in spec["staking_tracks"].items():
        track_spec = {**window_spec, "stake_fraction": fraction}
        settled, bankroll = simulate_bankroll(copy.deepcopy(tickets), track_spec)
        completed = [row for row in settled if row.get("status") == "created_hypothetical"]
        staked = sum(row["stake"] for row in completed)
        net = sum(row["hypothetical_net"] for row in completed)
        tracks[name] = {
            "staking_track": name,
            "stake_fraction": fraction,
            "tickets": completed,
            "ticket_count": len(completed),
            "wins": sum(row["result"] == "win" for row in completed),
            "ticket_hit_rate": round(100 * sum(row["result"] == "win" for row in completed) / len(completed), 1) if completed else None,
            "total_staked": round(staked, 2),
            "hypothetical_net": round(net, 2),
            "hypothetical_roi": round(100 * net / staked, 1) if staked else None,
            "bankroll": bankroll,
            "rollover_formula": spec.get("full_rollover_formula") if name == "full_rollover_100" else None,
        }
    result = {
        "status": "complete_hypothetical_challenger_not_price_evidence",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "spec": spec,
        "spec_sha256": sha(SPEC_PATH),
        "source_sha256": sha(SOURCE),
        "source_summary_sha256": sha(SOURCE_SUMMARY),
        "source_official_picks": len(picks),
        "source_hits_3plus": source_summary["hits_3plus"],
        "source_hit_rate_3plus": source_summary["hit_rate_3plus"],
        "combination_opportunities": len(tickets),
        "no_combo_selections": len(no_combo),
        "tracks": tracks,
        "no_combo": no_combo,
        "warnings": [
            "All 1.50 prices and lineup-release times are assumptions.",
            "This retrospective structural challenger was designed after prior results were inspected.",
            "Neither track enters the captured-price ledger or prospective promotion gate.",
            "The 90% track is a stress test and is not recommended staking.",
            "The full-rollover track stakes the entire active paper balance and a loss reduces it to zero.",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    ticket_rows = "".join(
        f"<tr><td>{escape(row['weekend'])}</td><td>{len(row['legs'])}</td><td>{'<br>'.join(escape(leg['player'] + ' — ' + leg['league'] + ' — ' + str(leg['actual_shots']) + ' shots') for leg in row['legs'])}</td><td>{row['derived_assumed_odds']:.3f}</td><td>{escape(row['result'].upper())}</td></tr>"
        for row in tickets
    )
    track_cards = "".join(
        f"<div class=card><div class=big>{row['bankroll']['ending_bankroll']:.2f}</div>{escape(name)} ending bankroll<br>{row['wins']}/{row['ticket_count']} tickets · {row['hypothetical_net']:+.2f} net · {row['bankroll']['maximum_drawdown']*100:.1f}% max DD</div>"
        for name, row in tracks.items()
    )
    html = f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Volume v4 Assumed-Odds Replay</title><style>body{{font:16px Inter,Segoe UI,sans-serif;background:#07111f;color:#edf3fc;margin:0;padding:28px}}main{{max-width:1150px;margin:auto}}.warning{{background:#2b1d13;border-left:4px solid #ffb34c;padding:15px;margin:18px 0}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}}.card,table{{background:#101d31;border:1px solid #293e5e}}.card{{padding:16px;border-radius:10px}}.big{{font-size:28px;font-weight:700}}table{{width:100%;border-collapse:collapse;margin-top:16px}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #293e5e}}th{{color:#8bc4ff}}.muted{{color:#9badc4}}</style></head><body><main><h1>Volume-v4 replay at assumed 1.50 per leg</h1><p class=muted>Structural frequency test · 10% benchmark, 90% stress and 100% full-rollover tracks</p><div class=warning><strong>Not profit evidence.</strong> Prices, lineup timing and products are hypothetical. Results remain outside the prospective gate. Full rollover uses <code>100 × 1.5^n</code> while the sequence keeps winning; a loss takes that active balance to zero.</div><div class=grid><div class=card><div class=big>{len(picks)}</div>historical official legs</div><div class=card><div class=big>{len(tickets)}</div>combo opportunities</div><div class=card><div class=big>{len(no_combo)}</div>no-combo legs</div>{track_cards}</div><h2>Hypothetical tickets</h2><table><thead><tr><th>Weekend</th><th>Legs</th><th>Selections</th><th>Derived odds</th><th>Result</th></tr></thead><tbody>{ticket_rows or '<tr><td colspan=5>No combinations.</td></tr>'}</tbody></table></main></body></html>"""
    (OUT / "index.html").write_text(html, encoding="utf-8")
    print(json.dumps({"source_official_picks": len(picks), "combination_opportunities": len(tickets), "no_combo_selections": len(no_combo), "tracks": {name: {key: value for key, value in row.items() if key not in ("tickets",)} for name, row in tracks.items()}}, indent=2))


if __name__ == "__main__":
    main()
