"""Separate real-price prospective ledger for the volume-v4 challenger.

The selection and odds mechanics reuse the audited control implementation,
but all events, tickets, settlements and dashboards live in a separate hash-
chained ledger.  Quotes point to the common immutable physical quote store.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from statistics import mean, median

import profit_validation as engine
from the_odds_api import parse_time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs" / "profit_challenger"
LEDGER = BASE / "ledger.jsonl"
CONFIG_PATH = ROOT / "work" / "profit_challenger_config.json"


@contextmanager
def challenger_context():
    previous = (engine.BASE, engine.LEDGER, engine.CONFIG_PATH)
    engine.BASE, engine.LEDGER, engine.CONFIG_PATH = BASE, LEDGER, CONFIG_PATH
    try:
        yield
    finally:
        engine.BASE, engine.LEDGER, engine.CONFIG_PATH = previous


def config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def read_ledger() -> list[dict]:
    with challenger_context():
        return engine.read_ledger()


def sync_official_selections(weekend: str) -> dict:
    with challenger_context():
        return engine.sync_official_selections(weekend)


def provisional_market_subjects(weekend: str) -> list[dict]:
    with challenger_context():
        return engine.provisional_market_subjects(weekend)


def locked_selections(records: list[dict] | None = None, weekend: str | None = None) -> list[dict]:
    with challenger_context():
        return engine.locked_selections(records, weekend)


def collect_quotes(weekend: str, stage: str, observed: datetime | None = None, api=None) -> dict:
    with challenger_context():
        return engine.collect_quotes(weekend, stage, observed, api)


def freeze_due_tickets(weekend: str, observed: datetime | None = None) -> dict:
    with challenger_context():
        return engine.freeze_due_tickets(weekend, observed)


def settle_tickets(weekend: str, observed: datetime | None = None) -> dict:
    with challenger_context():
        return engine.settle_tickets(weekend, observed)


def bankroll_state(records: list[dict] | None = None, staking_track: str = "fixed_10") -> dict:
    with challenger_context():
        return engine.bankroll_state(records, staking_track)


def build_summary() -> dict:
    cfg = config()
    with challenger_context():
        records = engine.read_ledger()
        selections = engine.locked_selections(records)
        tickets = engine.ticket_events(records)
        settlements = engine.settlement_events(records)
        ledger_errors = engine.reconcile_ledger(records)
        outcomes = {}
        for weekend in {row["weekend"] for row in selections}:
            outcomes.update(engine._settled_pick_map(weekend))

    graded = [outcomes[row["selection_id"]] for row in selections if row["selection_id"] in outcomes]
    hits = sum(row.get("shots") is not None and row["shots"] >= 3 for row in graded)
    league_counts = Counter(row["league"] for row in selections)
    combos = {row.get("combo_id", row["ticket_id"]) for row in tickets}
    tracks = {}
    for track, fraction in cfg["staking_tracks"].items():
        track_tickets = [row for row in tickets if row.get("staking_track") == track]
        track_settlements = [row for row in settlements if row.get("staking_track") == track]
        executable_tickets = [row for row in track_tickets if row["executability"] == "executable"]
        executable_settlements = [row for row in track_settlements if row["executability"] == "executable"]
        staked = sum(float(row["stake"]) for row in track_settlements)
        net = sum(float(row["net_profit"]) for row in track_settlements)
        executable_staked = sum(float(row["stake"]) for row in executable_settlements)
        executable_net = sum(float(row["net_profit"]) for row in executable_settlements)
        clvs = [float(row["combo_clv"]) for row in executable_settlements if row.get("combo_clv") is not None]
        state = bankroll_state(records, track)
        tracks[track] = {
            "stake_fraction": fraction,
            "ticket_records": len(track_tickets),
            "combination_tickets": len({row.get("combo_id", row["ticket_id"]) for row in track_tickets}),
            "executable_tickets": len(executable_tickets),
            "settled_tickets": len(track_settlements),
            "wins": sum(row["result"] == "win" for row in track_settlements),
            "staked": round(staked, 2),
            "net_profit": round(net, 2),
            "roi": net / staked if staked else None,
            "executable_staked": round(executable_staked, 2),
            "executable_net_profit": round(executable_net, 2),
            "executable_roi": executable_net / executable_staked if executable_staked else None,
            "average_clv": mean(clvs) if clvs else None,
            "median_clv": median(clvs) if clvs else None,
            "tickets_beating_close_share": sum(value > 0 for value in clvs) / len(clvs) if clvs else None,
            "bankroll": state,
        }

    unresolved = list(ledger_errors)
    current = engine.now_utc()
    for selection in selections:
        if parse_time(selection["kickoff"]) + timedelta(hours=4) < current and selection["selection_id"] not in outcomes:
            unresolved.append(f"missing_selection_settlement:{selection['selection_id']}")
    successful_quote_times = {}
    for row in records:
        if row["event_type"] == "quote_snapshot" and row["payload"].get("quotes"):
            successful_quote_times.setdefault(row["payload"]["selection_id"], []).append(parse_time(row["recorded_utc"]))
        if row["event_type"] == "quote_snapshot":
            reference = row["payload"].get("shared_snapshot_path")
            referenced_path = Path(reference) if reference else None
            if referenced_path is not None and not referenced_path.is_absolute():
                referenced_path = ROOT / referenced_path
            if referenced_path is None or not referenced_path.exists():
                unresolved.append(f"missing_shared_quote_snapshot:{row['event_id']}")
            elif hashlib.sha256(referenced_path.read_bytes()).hexdigest() != row["payload"].get("shared_snapshot_sha256"):
                unresolved.append(f"shared_quote_hash_mismatch:{row['event_id']}")
    for row in records:
        if row["event_type"] not in {"collector_error", "missing_market"}:
            continue
        selection_key = row["payload"]["selection_id"]
        issue_time = parse_time(row["recorded_utc"])
        if not any(value > issue_time for value in successful_quote_times.get(selection_key, [])):
            unresolved.append(f"unresolved_{row['event_type']}:{selection_key}:{row['event_id']}")
    settled_ticket_ids = {row["ticket_id"] for row in settlements}
    for ticket in tickets:
        latest_kickoff = max((parse_time(leg["kickoff"]) for leg in ticket.get("legs", [])), default=None)
        if latest_kickoff and latest_kickoff + timedelta(hours=4) < current and ticket["ticket_id"] not in settled_ticket_ids:
            unresolved.append(f"missing_ticket_settlement:{ticket['ticket_id']}")
    primary = tracks[cfg["primary_staking_track"]]
    gate = cfg["activation_gate"]
    official = len(selections)
    active_weekends = len({row["weekend"] for row in selections})
    checks = {
        "official_legs": official >= gate["official_legs"],
        "executable_tickets": primary["executable_tickets"] >= gate["executable_tickets"],
        "active_weekends": active_weekends >= gate["active_weekends"],
        "league_representation": len(league_counts) >= gate["minimum_leagues"],
        "league_concentration": bool(official) and max(league_counts.values(), default=0) / official <= gate["maximum_league_share"],
        "positive_real_price_roi": primary["executable_roi"] is not None and primary["executable_roi"] > 0,
        "positive_average_clv": primary["average_clv"] is not None and primary["average_clv"] > 0,
        "ticket_clv_beat_share": primary["tickets_beating_close_share"] is not None and primary["tickets_beating_close_share"] > gate["minimum_ticket_clv_beat_share"],
        "maximum_drawdown": primary["bankroll"]["maximum_drawdown"] <= gate["maximum_drawdown"],
        "zero_unresolved_discrepancies": not unresolved,
    }
    return {
        "generated_utc": engine.now_utc().isoformat(),
        "version": cfg["version"],
        "strategy_id": cfg["strategy_id"],
        "control_strategy": "league_balanced_v3",
        "paper_only": True,
        "historical_assumed_prices_included": False,
        "official_legs": official,
        "graded_official_legs": len(graded),
        "selection_hits": hits,
        "selection_hit_rate": hits / len(graded) if graded else None,
        "combination_tickets": len(combos),
        "active_weekends": active_weekends,
        "leagues": dict(sorted(league_counts.items())),
        "staking_tracks": tracks,
        "missing_market_records": sum(row["event_type"] == "missing_market" for row in records),
        "unresolved_discrepancies": unresolved,
        "promotion_checks": checks,
        "promotion_gate_passed": all(checks.values()),
        "promotion_effect": "manual strategy review only; never automatic betting",
    }


def _pct(value) -> str:
    return "—" if value is None else f"{100 * value:.1f}%"


def build_dashboard() -> dict:
    summary = build_summary()
    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    cards = "".join(
        f"<div class=card><h3>{escape(name)}</h3><div class=big>{row['bankroll']['bankroll']:.2f}</div>bankroll · {_pct(row['executable_roi'])} executable ROI<br>{_pct(row['bankroll']['maximum_drawdown'])} max drawdown · {row['executable_tickets']} executable tickets</div>"
        for name, row in summary["staking_tracks"].items()
    )
    checks = "".join(
        f"<tr><td>{escape(name.replace('_', ' ').title())}</td><td class={'pass' if value else 'wait'}>{'PASS' if value else 'WAIT'}</td></tr>"
        for name, value in summary["promotion_checks"].items()
    )
    leagues = "".join(f"<tr><td>{escape(name)}</td><td>{count}</td></tr>" for name, count in summary["leagues"].items())
    html = f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Volume v4 Profit Challenger</title><style>body{{font:16px Inter,Segoe UI,sans-serif;background:#07111f;color:#edf3fc;margin:0;padding:28px}}main{{max-width:1120px;margin:auto}}.warning{{background:#2a1d13;border-left:4px solid #ffb84d;padding:15px;margin:18px 0}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}}.card,table{{background:#101d31;border:1px solid #293e5e}}.card{{padding:16px;border-radius:10px}}.big{{font-size:28px;font-weight:700}}table{{width:100%;border-collapse:collapse;margin:16px 0}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #293e5e}}th{{color:#8bc4ff}}.pass{{color:#69e49a}}.wait{{color:#ffbd66}}.muted{{color:#9badc4}}</style></head><body><main><h1>Higher-volume profitability challenger</h1><p class=muted>Volume v4 · separate ledger · shared physical odds evidence</p><div class=warning><strong>Paper testing only.</strong> Fixed 10% is the primary benchmark. The 90% track is a non-recommended stress test. Historical assumed prices are excluded.</div><div class=grid><div class=card><div class=big>{summary['official_legs']} / 100</div>prospective official legs</div><div class=card><div class=big>{summary['combination_tickets']}</div>real-price combinations</div><div class=card><div class=big>{summary['active_weekends']}</div>active weekends</div><div class=card><div class=big>{_pct(summary['selection_hit_rate'])}</div>official-leg 3+ rate</div>{cards}</div><h2>Promotion gate</h2><table><thead><tr><th>Requirement</th><th>Status</th></tr></thead><tbody>{checks}</tbody></table><h2>League representation</h2><table><thead><tr><th>League</th><th>Official legs</th></tr></thead><tbody>{leagues or '<tr><td colspan=2>No official legs locked yet</td></tr>'}</tbody></table><p class=muted>Passing this gate triggers manual review only. No wagers are placed automatically.</p></main></body></html>"""
    (BASE / "index.html").write_text(html, encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("sync", "tickets", "settle"):
        item = commands.add_parser(name)
        item.add_argument("--weekend", required=True)
        item.add_argument("--now")
    collect = commands.add_parser("collect")
    collect.add_argument("--weekend", required=True)
    collect.add_argument("--stage", required=True, choices=("first_market", "lineup_lock", "ticket_creation", "final_pre_kickoff", "poll"))
    collect.add_argument("--now")
    commands.add_parser("dashboard")
    commands.add_parser("status")
    args = parser.parse_args()
    observed = parse_time(args.now) if getattr(args, "now", None) else None
    if args.command == "sync":
        result = sync_official_selections(args.weekend)
    elif args.command == "collect":
        result = collect_quotes(args.weekend, args.stage, observed)
    elif args.command == "tickets":
        result = freeze_due_tickets(args.weekend, observed)
    elif args.command == "settle":
        result = settle_tickets(args.weekend, observed)
    elif args.command == "dashboard":
        result = build_dashboard()
    else:
        result = build_summary()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
