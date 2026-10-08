"""Replay frozen v3 official picks with assumed 1.50 prices.

This is a mechanics and streak scenario only.  It deliberately writes outside
the captured-price ledger and cannot count toward the prospective gate.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "outputs" / "season_to_date_plan_b3_league_balanced_v3"
SOURCE = SOURCE_DIR / "official_picks.json"
SOURCE_SUMMARY = SOURCE_DIR / "summary.json"
SPEC_PATH = ROOT / "work" / "hypothetical_v3_combo_1_5_spec.json"
OUT = ROOT / "outputs" / "hypothetical_v3_combo_1_5"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_windows(picks: list[dict], spec: dict) -> tuple[list[dict], list[dict]]:
    """Apply the five-minute window using an explicit historical lineup assumption."""
    by_weekend: dict[str, list[dict]] = defaultdict(list)
    for pick in picks:
        by_weekend[pick["weekend"]].append(dict(pick))
    tickets: list[dict] = []
    no_combo: list[dict] = []
    for weekend, rows in sorted(by_weekend.items()):
        unused = sorted(rows, key=lambda row: (row["date"], row["league"], row["player_id"]))
        ticket_number = 0
        while unused:
            earliest = unused[0]
            earliest_kickoff = parse_time(earliest["date"])
            freeze = earliest_kickoff - timedelta(minutes=spec["freeze_minutes_before_earliest_kickoff"])
            available = [
                row
                for row in unused
                if parse_time(row["date"])
                - timedelta(minutes=spec["assumed_lineup_available_minutes_before_kickoff"])
                <= freeze
            ]
            # The frozen source already has at most one official pick per league;
            # retain a defensive check in the standalone scenario.
            grouped = []
            leagues = set()
            for row in available:
                if row["league"] not in leagues and len(grouped) < spec["maximum_combo_legs"]:
                    grouped.append(row)
                    leagues.add(row["league"])
            if earliest not in grouped or len(grouped) < spec["minimum_combo_legs"]:
                no_combo.append(
                    {
                        "weekend": weekend,
                        "selection_id": f"{weekend}:{earliest['match_id']}:{earliest['player_id']}",
                        "freeze_utc": freeze.isoformat(),
                        "kickoff": earliest["date"],
                        "league": earliest["league"],
                        "fixture": earliest["fixture"],
                        "player": earliest["player"],
                        "actual_shots": earliest["actual_shots"],
                        "hit_3plus": earliest["hit_3plus"],
                        "reason": "fewer_than_two_assumed_confirmed_candidates_at_freeze",
                    }
                )
                unused.remove(earliest)
                continue
            ticket_number += 1
            legs = []
            for row in grouped:
                legs.append(
                    {
                        "selection_id": f"{weekend}:{row['match_id']}:{row['player_id']}",
                        "kickoff": row["date"],
                        "league": row["league"],
                        "fixture": row["fixture"],
                        "player": row["player"],
                        "actual_shots": row["actual_shots"],
                        "hit_3plus": row["hit_3plus"],
                        "assumed_decimal_price": spec["assumed_decimal_price_per_leg"],
                    }
                )
                unused.remove(row)
            latest_kickoff = max(parse_time(row["date"]) for row in grouped)
            tickets.append(
                {
                    "ticket_id": f"{weekend}-{ticket_number}",
                    "weekend": weekend,
                    "created_utc": freeze.isoformat(),
                    "assumed_settled_utc": (
                        latest_kickoff
                        + timedelta(minutes=spec["assumed_settlement_minutes_after_latest_kickoff"])
                    ).isoformat(),
                    "legs": legs,
                    "derived_assumed_odds": round(
                        spec["assumed_decimal_price_per_leg"] ** len(legs), 6
                    ),
                    "result": "win" if all(row["hit_3plus"] for row in grouped) else "loss",
                }
            )
    return sorted(tickets, key=lambda row: row["created_utc"]), no_combo


def simulate_bankroll(tickets: list[dict], spec: dict) -> tuple[list[dict], dict]:
    bankroll = float(spec["starting_bankroll_units"])
    peak = bankroll
    maximum_drawdown = 0.0
    outstanding: list[dict] = []
    settled_rows: list[dict] = []

    def settle_due(cutoff: datetime) -> None:
        nonlocal bankroll, peak, maximum_drawdown, outstanding
        due = sorted(
            [row for row in outstanding if parse_time(row["assumed_settled_utc"]) <= cutoff],
            key=lambda row: (row["assumed_settled_utc"], row["ticket_id"]),
        )
        for row in due:
            before = bankroll
            returned = row["stake"] * row["derived_assumed_odds"] if row["result"] == "win" else 0.0
            bankroll = round(bankroll - row["stake"] + returned, 2)
            peak = max(peak, bankroll)
            drawdown = (peak - bankroll) / peak if peak else 0.0
            maximum_drawdown = max(maximum_drawdown, drawdown)
            row.update(
                bankroll_before_settlement=before,
                returned=round(returned, 2),
                hypothetical_net=round(returned - row["stake"], 2),
                bankroll_after_settlement=bankroll,
                insolvent=bankroll <= 0,
            )
            settled_rows.append(row)
            outstanding.remove(row)

    for source in tickets:
        created = parse_time(source["created_utc"])
        settle_due(created)
        if bankroll <= 0:
            source = {**source, "status": "not_created_bankroll_insolvent"}
            settled_rows.append(source)
            continue
        open_exposure = sum(row["stake"] for row in outstanding)
        stake = round(bankroll * spec["stake_fraction"], 2)
        ticket = {
            **source,
            "bankroll_snapshot": bankroll,
            "stake": stake,
            "open_exposure_before": round(open_exposure, 2),
            "cumulative_exposure_after": round(open_exposure + stake, 2),
            "executability": (
                "non_executable_overlap" if open_exposure + stake > bankroll else "executable"
            ),
            "status": "created_hypothetical",
        }
        outstanding.append(ticket)
    settle_due(datetime.max.replace(tzinfo=timezone.utc))
    settled_rows.sort(key=lambda row: (row.get("assumed_settled_utc", ""), row["ticket_id"]))
    summary = {
        "ending_bankroll": bankroll,
        "peak_bankroll": peak,
        "maximum_drawdown": maximum_drawdown,
        "insolvent": bankroll <= 0,
        "cumulative_exposure": round(sum(row.get("stake", 0) for row in settled_rows), 2),
    }
    return settled_rows, summary


def main() -> None:
    spec = load(SPEC_PATH)
    picks = load(SOURCE)
    source_summary = load(SOURCE_SUMMARY)
    tickets, no_combo = build_windows(picks, spec)
    settled, bankroll = simulate_bankroll(tickets, spec)
    completed = [row for row in settled if row.get("status") == "created_hypothetical"]
    executable = [row for row in completed if row["executability"] == "executable"]
    wins = [row for row in completed if row["result"] == "win"]
    total_staked = sum(row["stake"] for row in completed)
    total_net = sum(row["hypothetical_net"] for row in completed)
    result = {
        "status": "complete_hypothetical_not_price_evidence",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "spec": spec,
        "spec_sha256": sha256(SPEC_PATH),
        "source_sha256": sha256(SOURCE),
        "source_summary_sha256": sha256(SOURCE_SUMMARY),
        "source_official_picks": len(picks),
        "source_active_weekends": source_summary["active_pick_weekends"],
        "source_hits_3plus": source_summary["hits_3plus"],
        "source_hit_rate_3plus": source_summary["hit_rate_3plus"],
        "hypothetical_tickets": len(completed),
        "executable_hypothetical_tickets": len(executable),
        "winning_tickets": len(wins),
        "ticket_hit_rate": round(100 * len(wins) / len(completed), 1) if completed else None,
        "no_combo_selections": len(no_combo),
        "total_hypothetical_staked": round(total_staked, 2),
        "total_hypothetical_net": round(total_net, 2),
        "hypothetical_roi": round(100 * total_net / total_staked, 1) if total_staked else None,
        "bankroll": bankroll,
        "ticket_leg_distribution": dict(Counter(len(row["legs"]) for row in completed)),
        "tickets": completed,
        "no_combo": no_combo,
        "warnings": [
            "Every 1.50 price is assumed, not a historical bookmaker quote.",
            "Historical confirmed-lineup publication timestamps are unavailable; availability is assumed 60 minutes before kickoff.",
            "Derived combination odds are not actual bookmaker parlay quotes.",
            "This scenario cannot establish price edge, closing-line value or realizable profit.",
            "These results never enter the prospective captured-price ledger or the 100-leg activation gate.",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    ticket_rows = "".join(
        f"<tr><td>{escape(row['weekend'])}</td><td>{len(row['legs'])}</td>"
        f"<td>{'<br>'.join(escape(leg['player'] + ' — ' + leg['league'] + ' — ' + str(leg['actual_shots']) + ' shots') for leg in row['legs'])}</td>"
        f"<td>{row['derived_assumed_odds']:.3f}</td><td>{row['stake']:.2f}</td>"
        f"<td>{escape(row['result'].upper())}</td><td>{row['hypothetical_net']:+.2f}</td>"
        f"<td>{row['bankroll_after_settlement']:.2f}</td></tr>"
        for row in completed
    )
    no_combo_rows = "".join(
        f"<tr><td>{escape(row['weekend'])}</td><td>{escape(row['league'])}</td>"
        f"<td>{escape(row['player'])}</td><td>{row['actual_shots']}</td><td>{'Hit' if row['hit_3plus'] else 'Miss'}</td></tr>"
        for row in no_combo
    )
    html = f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>
<title>Hypothetical v3 Combo Replay</title><style>body{{font:16px Inter,Segoe UI,sans-serif;background:#07111f;color:#eaf1fb;margin:0;padding:28px}}main{{max-width:1180px;margin:auto}}.muted{{color:#9badc4}}.warning{{background:#2b1d13;border-left:4px solid #ffb34c;padding:16px;border-radius:8px;margin:18px 0}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}}.card,table{{background:#101d31;border:1px solid #293e5e}}.card{{padding:16px;border-radius:10px}}.big{{font-size:28px;font-weight:700}}table{{width:100%;border-collapse:collapse;margin:12px 0 28px}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #293e5e}}th{{color:#8bc4ff}}</style></head><body><main>
<h1>Frozen v3 combo replay at assumed 1.50 per leg</h1><p class=muted>Mechanics scenario only · no historical bookmaker prices</p>
<div class=warning><strong>Not profit evidence.</strong> Prices and lineup-release timing are assumptions. These results are isolated from the prospective ledger and activation gate.</div>
<div class=grid><div class=card><div class=big>{len(picks)}</div>official historical selections</div><div class=card><div class=big>{len(completed)}</div>combination tickets</div><div class=card><div class=big>{len(no_combo)}</div>no-combo selections</div><div class=card><div class=big>{len(wins)}/{len(completed)}</div>winning tickets</div><div class=card><div class=big>{bankroll['ending_bankroll']:.2f}</div>ending hypothetical bankroll</div><div class=card><div class=big>{result['hypothetical_roi'] if result['hypothetical_roi'] is not None else '—'}%</div>hypothetical ROI</div></div>
<h2>Combination tickets</h2><table><thead><tr><th>Weekend</th><th>Legs</th><th>Selections</th><th>Assumed odds</th><th>Stake</th><th>Result</th><th>Net</th><th>Bankroll</th></tr></thead><tbody>{ticket_rows or '<tr><td colspan=8>No combinations.</td></tr>'}</tbody></table>
<h2>Selections excluded by combo-only rules</h2><table><thead><tr><th>Weekend</th><th>League</th><th>Player</th><th>Shots</th><th>Result</th></tr></thead><tbody>{no_combo_rows}</tbody></table>
<p class=muted>Assumptions: confirmed lineup available 60 minutes before kickoff; ticket frozen five minutes before the earliest kickoff; 90% paper stake; no singles; 1.50 each leg; derived odds only.</p>
</main></body></html>"""
    (OUT / "index.html").write_text(html, encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("hypothetical_tickets", "winning_tickets", "no_combo_selections", "total_hypothetical_net", "hypothetical_roi", "bankroll")}, indent=2))


if __name__ == "__main__":
    main()
