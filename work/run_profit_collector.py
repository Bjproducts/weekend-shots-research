"""Run the deterministic prospective collector.

Scheduled mode may use --watch: once a frozen candidate enters the two-hour
horizon, the process polls every ten minutes and also wakes exactly at the
five-minute ticket freeze.  With no nearby candidate it exits immediately.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from profit_validation import (
    BASE,
    ROOT,
    build_dashboard,
    collect_quotes,
    config,
    freeze_due_tickets,
    locked_selections,
    now_utc,
    parse_time,
    provisional_market_subjects,
    read_ledger,
    settle_tickets,
    sync_official_selections,
    discover_weekends,
)
from the_odds_api import OddsAPIError, load_local_env
import profit_challenger as challenger

LOCK = BASE / "collector.lock"


def run_live(mode: str, weekend: str) -> dict:
    command = [sys.executable, str(ROOT / "work" / "live_plan_b3.py"), mode, "--weekend", weekend]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90)
    return {
        "mode": mode,
        "returncode": result.returncode,
        "stdout": result.stdout[-3000:],
        "stderr": result.stderr[-1500:],
    }


def run_challenger_live(mode: str, weekend: str) -> dict:
    command = [sys.executable, str(ROOT / "work" / "live_plan_b3_volume_v4.py"), mode, "--weekend", weekend]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90)
    return {"mode": mode, "returncode": result.returncode, "stdout": result.stdout[-3000:], "stderr": result.stderr[-1500:]}


def ensure_challenger_board(weekend: str) -> dict:
    destination = ROOT / "outputs" / "live_plan_b3" / weekend / "frozen_board_volume_v4.json"
    if destination.exists():
        return {"status": "already_frozen"}
    command = [sys.executable, str(ROOT / "work" / "build_live_plan_b3_volume_board.py"), "--weekend", weekend]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise RuntimeError("Unable to freeze challenger board: " + result.stderr[-1500:])
    return {"status": "created", "stdout": result.stdout[-3000:]}


def acquire_lock() -> int:
    BASE.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            age = now_utc().timestamp() - LOCK.stat().st_mtime
        except OSError:
            age = 0
        if age <= 4 * 60 * 60:
            raise SystemExit("collector_already_running")
        LOCK.unlink(missing_ok=True)
        descriptor = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(descriptor, json.dumps({"pid": os.getpid(), "started_utc": now_utc().isoformat()}).encode())
    return descriptor


def seconds_until_next_action(weekend: str, observed: datetime) -> float:
    cfg = config()
    candidates = provisional_market_subjects(weekend)
    if (ROOT / "outputs" / "live_plan_b3" / weekend / "frozen_board_volume_v4.json").exists():
        candidates += challenger.provisional_market_subjects(weekend)
    future = [parse_time(row["kickoff"]) for row in candidates if parse_time(row["kickoff"]) > observed]
    if not future:
        return 600
    freeze_times = [kickoff - timedelta(minutes=cfg["freeze_minutes_before_kickoff"]) for kickoff in future]
    positive = [(value - observed).total_seconds() for value in freeze_times if value > observed]
    return max(1, min([600.0, *positive]))


def in_horizon(weekend: str, observed: datetime) -> bool:
    horizon = timedelta(minutes=config()["collector_horizon_minutes"])
    subjects = provisional_market_subjects(weekend)
    if (ROOT / "outputs" / "live_plan_b3" / weekend / "frozen_board_volume_v4.json").exists():
        subjects += challenger.provisional_market_subjects(weekend)
    return any(observed < parse_time(row["kickoff"]) <= observed + horizon for row in subjects)


def choose_weekend(observed: datetime) -> str | None:
    choices = []
    for weekend in discover_weekends():
        subjects = provisional_market_subjects(weekend)
        future = [parse_time(row["kickoff"]) for row in subjects if parse_time(row["kickoff"]) > observed]
        if future:
            choices.append((min(future), weekend))
    return min(choices, default=(None, None))[1]


def one_cycle(weekend: str, observed: datetime) -> dict:
    board = ensure_challenger_board(weekend)
    # Pre-lineup first-market observations are allowed but never become picks.
    first = collect_quotes(weekend, "first_market", observed)
    challenger_first = challenger.collect_quotes(weekend, "first_market", observed)
    lineup = run_live("lineups", weekend)
    challenger_lineup = run_challenger_live("lineups", weekend)
    synced = sync_official_selections(weekend)
    challenger_synced = challenger.sync_official_selections(weekend)
    records = read_ledger()
    official = locked_selections(records, weekend)
    challenger_records = challenger.read_ledger()
    challenger_official = challenger.locked_selections(challenger_records, weekend)
    lineup_quotes = collect_quotes(weekend, "lineup_lock", observed) if official else {"status": "no_official_selections"}
    poll = collect_quotes(weekend, "poll", observed) if official else {"status": "no_official_selections"}
    challenger_lineup_quotes = challenger.collect_quotes(weekend, "lineup_lock", observed) if challenger_official else {"status": "no_official_selections"}
    challenger_poll = challenger.collect_quotes(weekend, "poll", observed) if challenger_official else {"status": "no_official_selections"}

    due = False
    future_official = [parse_time(row["kickoff"]) for row in official if parse_time(row["kickoff"]) > observed]
    if future_official:
        earliest_unused = min(future_official)
        due = observed >= earliest_unused - timedelta(minutes=config()["freeze_minutes_before_kickoff"])
    ticket = {"status": "not_due"}
    if due:
        creation_quotes = collect_quotes(weekend, "ticket_creation", observed)
        close_quotes = collect_quotes(weekend, "final_pre_kickoff", observed)
        ticket = freeze_due_tickets(weekend, observed)
    else:
        creation_quotes = close_quotes = {"status": "not_due"}
    challenger_due = False
    challenger_future = [parse_time(row["kickoff"]) for row in challenger_official if parse_time(row["kickoff"]) > observed]
    if challenger_future:
        challenger_due = observed >= min(challenger_future) - timedelta(minutes=config()["freeze_minutes_before_kickoff"])
    challenger_ticket = {"status": "not_due"}
    if challenger_due:
        challenger_creation_quotes = challenger.collect_quotes(weekend, "ticket_creation", observed)
        challenger_close_quotes = challenger.collect_quotes(weekend, "final_pre_kickoff", observed)
        challenger_ticket = challenger.freeze_due_tickets(weekend, observed)
    else:
        challenger_creation_quotes = challenger_close_quotes = {"status": "not_due"}
    result = {
        "observed_utc": observed.isoformat(),
        "challenger_board": board,
        "first_market": first,
        "challenger_first_market": challenger_first,
        "lineup_check": lineup,
        "challenger_lineup_check": challenger_lineup,
        "selection_sync": synced,
        "challenger_selection_sync": challenger_synced,
        "lineup_quotes": lineup_quotes,
        "poll": poll,
        "ticket_creation_quotes": creation_quotes,
        "final_pre_kickoff_quotes": close_quotes,
        "ticket": ticket,
        "challenger_lineup_quotes": challenger_lineup_quotes,
        "challenger_poll": challenger_poll,
        "challenger_ticket_creation_quotes": challenger_creation_quotes,
        "challenger_final_pre_kickoff_quotes": challenger_close_quotes,
        "challenger_ticket": challenger_ticket,
    }
    build_dashboard()
    challenger.build_dashboard()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weekend", help="Frozen weekend date; omit to select the nearest active v3 board")
    parser.add_argument("--watch", action="store_true", help="Remain active through nearby kickoff windows")
    parser.add_argument("--now", help="One-cycle deterministic timestamp; incompatible with --watch")
    args = parser.parse_args()
    if args.watch and args.now:
        raise SystemExit("--now cannot be combined with --watch")
    descriptor = acquire_lock()
    try:
        weekend = args.weekend or choose_weekend(parse_time(args.now) if args.now else now_utc())
        if not weekend:
            print(json.dumps({"status": "idle_no_active_frozen_weekend"}, indent=2))
            return
        observed = parse_time(args.now) if args.now else now_utc()
        if not in_horizon(weekend, observed):
            print(json.dumps({"status": "idle_no_candidate_within_two_hours"}, indent=2))
            return
        # Settlement normally comes from the heartbeat after matches finish.
        # During an active collection window, reconcile any outcomes that the
        # immutable live workflow has already produced.
        settle_tickets(weekend)
        challenger.settle_tickets(weekend)
        build_dashboard()
        challenger.build_dashboard()
        load_local_env(ROOT)
        if not os.getenv("THE_ODDS_API_KEY"):
            print(json.dumps({"status": "configuration_required", "missing": "THE_ODDS_API_KEY"}, indent=2))
            return
        while True:
            observed = parse_time(args.now) if args.now else now_utc()
            result = one_cycle(weekend, observed)
            print(json.dumps(result, indent=2))
            if not args.watch or not in_horizon(weekend, now_utc()):
                return
            time.sleep(seconds_until_next_action(weekend, now_utc()))
    except OddsAPIError as exc:
        print(json.dumps({"status": "provider_error", "message": str(exc)}, indent=2))
        raise SystemExit(2) from None
    finally:
        os.close(descriptor)
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
