"""Assumed-1.50 mechanics replay for the volume-v4 challenger."""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone
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


def simulate_selection_rollover(picks: list[dict], spec: dict) -> dict:
    rule = spec["selection_rollover"]
    start = float(rule["starting_units"])
    price = float(rule["decimal_price_per_selection"])
    ordered = sorted(picks, key=lambda row: (row["date"], row.get("provisional_rank", 999), str(row["player_id"])))
    balance = start
    total_deposits = start
    current_run = 0
    hit_runs = []
    sequence = []
    peak = start
    restarts = 0
    previous_date = None
    same_kickoff_pairs = 0
    settlement_overlap_conflicts = 0
    previous_kickoff = None
    for index, pick in enumerate(ordered, 1):
        restart_deposit = 0.0
        if balance <= 0:
            balance = float(rule["restart_units_after_loss"])
            restart_deposit = balance
            total_deposits += balance
            restarts += 1
        before = balance
        hit = bool(pick["hit_3plus"])
        if hit:
            current_run += 1
            # This uses the user's exact power formula rather than multiplying
            # an already rounded balance at each step.
            balance = round(start * price**current_run, 2)
        else:
            hit_runs.append(current_run)
            current_run = 0
            balance = 0.0
        if previous_date == pick["date"]:
            same_kickoff_pairs += 1
        previous_date = pick["date"]
        kickoff = datetime.fromisoformat(pick["date"].replace("Z", "+00:00"))
        if previous_kickoff is not None and kickoff < previous_kickoff + timedelta(minutes=rule["assumed_settlement_minutes_after_selection"]):
            settlement_overlap_conflicts += 1
        previous_kickoff = kickoff
        peak = max(peak, balance)
        sequence.append(
            {
                "order": index,
                "weekend": pick["weekend"],
                "kickoff": pick["date"],
                "league": pick["league"],
                "fixture": pick["fixture"],
                "player": pick["player"],
                "actual_shots": pick["actual_shots"],
                "result": "win" if hit else "loss",
                "restart_deposit_before": restart_deposit,
                "active_balance_before": round(before, 2),
                "consecutive_wins_after": current_run,
                "active_balance_after": round(balance, 2),
            }
        )
    hit_runs.append(current_run)
    return {
        "status": "hypothetical_selection_by_selection_rollover",
        "formula": rule["formula"],
        "selections": len(ordered),
        "hits": sum(row["hit_3plus"] for row in ordered),
        "misses": sum(not row["hit_3plus"] for row in ordered),
        "hit_runs": hit_runs,
        "longest_hit_run": max(hit_runs, default=0),
        "final_hit_run": hit_runs[-1] if hit_runs else 0,
        "restarts_after_losses": restarts,
        "total_deposits": round(total_deposits, 2),
        "peak_active_balance": round(peak, 2),
        "ending_active_balance": round(balance, 2),
        "ending_balance_minus_total_deposits": round(balance - total_deposits, 2),
        "same_kickoff_sequential_conflicts": same_kickoff_pairs,
        "assumed_settlement_overlap_conflicts": settlement_overlap_conflicts,
        "all_hits_ignoring_losses_counterfactual": round(start * price ** sum(row["hit_3plus"] for row in ordered), 2),
        "sequence": sequence,
        "warnings": [
            "Five losses interrupt the rollover; 100 * 1.5^33 is not an executable path through the observed sequence.",
            "A new 100-unit deposit is assumed before the selection following every loss.",
            "Seven adjacent selections start before the prior assumed 120-minute settlement, so the calculation is mechanics-only rather than an executable rollover.",
        ],
    }


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
        }
    selection_rollover = simulate_selection_rollover(picks, spec)
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
        "selection_rollover_100": selection_rollover,
        "no_combo": no_combo,
        "warnings": [
            "All 1.50 prices and lineup-release times are assumptions.",
            "This retrospective structural challenger was designed after prior results were inspected.",
            "Neither track enters the captured-price ledger or prospective promotion gate.",
            "The 90% track is a stress test and is not recommended staking.",
            "The selection-by-selection rollover uses all 38 selections, restarts with 100 after each loss, and is not executable where kickoffs overlap.",
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
    rollover_rows = "".join(
        f"<tr><td>{row['order']}</td><td>{escape(row['player'])}</td><td>{row['actual_shots']}</td><td>{escape(row['result'].upper())}</td><td>{row['consecutive_wins_after']}</td><td>{row['active_balance_after']:.2f}</td></tr>"
        for row in selection_rollover["sequence"]
    )
    html = f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Volume v4 Assumed-Odds Replay</title><style>body{{font:16px Inter,Segoe UI,sans-serif;background:#07111f;color:#edf3fc;margin:0;padding:28px}}main{{max-width:1150px;margin:auto}}.warning{{background:#2b1d13;border-left:4px solid #ffb34c;padding:15px;margin:18px 0}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}}.card,table{{background:#101d31;border:1px solid #293e5e}}.card{{padding:16px;border-radius:10px}}.big{{font-size:28px;font-weight:700}}table{{width:100%;border-collapse:collapse;margin-top:16px}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #293e5e}}th{{color:#8bc4ff}}.muted{{color:#9badc4}}</style></head><body><main><h1>Volume-v4 replay at assumed 1.50 per selection</h1><p class=muted>Combo mechanics plus an all-38-selection rollover sequence</p><div class=warning><strong>Not profit evidence.</strong> Prices and lineup timing are hypothetical. The rollover uses <code>100 × 1.5^n</code> for consecutive wins, resets to zero on a loss, then assumes a fresh 100-unit deposit before the next selection. {selection_rollover['assumed_settlement_overlap_conflicts']} adjacent selections start before the prior assumed 120-minute settlement, so this ordered calculation is not literally executable.</div><div class=grid><div class=card><div class=big>{len(picks)}</div>historical official legs · {selection_rollover['hits']} hits</div><div class=card><div class=big>{escape(str(selection_rollover['hit_runs']))}</div>ordered hit streaks</div><div class=card><div class=big>{selection_rollover['peak_active_balance']:.2f}</div>highest active rollover balance</div><div class=card><div class=big>{selection_rollover['ending_active_balance']:.2f}</div>ending active balance after final {selection_rollover['final_hit_run']}-win run</div><div class=card><div class=big>{selection_rollover['total_deposits']:.2f}</div>total deposits across restarts</div><div class=card><div class=big>{selection_rollover['ending_balance_minus_total_deposits']:+.2f}</div>ending balance minus deposits</div></div><h2>Kickoff-window combination tracks</h2><div class=grid><div class=card><div class=big>{len(tickets)}</div>combo opportunities</div><div class=card><div class=big>{len(no_combo)}</div>no-combo legs</div>{track_cards}</div><table><thead><tr><th>Weekend</th><th>Legs</th><th>Selections</th><th>Derived odds</th><th>Result</th></tr></thead><tbody>{ticket_rows or '<tr><td colspan=5>No combinations.</td></tr>'}</tbody></table><h2>Selection-by-selection rollover</h2><table><thead><tr><th>#</th><th>Player</th><th>Shots</th><th>Result</th><th>Current win run</th><th>Active balance</th></tr></thead><tbody>{rollover_rows}</tbody></table></main></body></html>"""
    (OUT / "index.html").write_text(html, encoding="utf-8")
    print(json.dumps({"source_official_picks": len(picks), "combination_opportunities": len(tickets), "no_combo_selections": len(no_combo), "tracks": {name: {key: value for key, value in row.items() if key not in ("tickets",)} for name, row in tracks.items()}, "selection_rollover_100": {key: value for key, value in selection_rollover.items() if key != "sequence"}}, indent=2))


if __name__ == "__main__":
    main()
