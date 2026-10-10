"""Prospective price, ticket and paper-bankroll validation for frozen Plan B v3.

This module never places a wager.  Its JSONL ledger is append-only and hash
chained; immutable source snapshots live beside it for auditability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable

from the_odds_api import (
    OddsAPIError,
    TheOddsAPI,
    extract_exact_quotes,
    load_local_env,
    match_event,
    parse_time,
)
import shared_quote_store

ROOT = Path(__file__).resolve().parents[1]
LIVE_BASE = ROOT / "outputs" / "live_plan_b3"
BASE = ROOT / "outputs" / "profit_validation"
LEDGER = BASE / "ledger.jsonl"
CONFIG_PATH = ROOT / "work" / "profit_validation_config.json"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def config() -> dict:
    return load_json(CONFIG_PATH)


def staking_tracks(cfg: dict | None = None) -> dict[str, float]:
    cfg = cfg or config()
    if "staking_tracks" in cfg:
        return {str(key): float(value) for key, value in cfg["staking_tracks"].items()}
    return {str(cfg.get("primary_staking_track", "stress_90")): float(cfg["stake_fraction"])}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def timestamp_slug(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def write_once(path: Path, payload: Any) -> None:
    if path.exists():
        raise RuntimeError(f"Immutable file already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def read_ledger(path: Path | None = None) -> list[dict]:
    path = path or LEDGER
    if not path.exists():
        return []
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid ledger JSON at line {line_number}") from exc
    return records


def reconcile_ledger(records: list[dict] | None = None) -> list[str]:
    records = read_ledger() if records is None else records
    errors: list[str] = []
    previous = "GENESIS"
    ids: set[str] = set()
    for index, record in enumerate(records, 1):
        if record.get("sequence") != index:
            errors.append(f"sequence_mismatch:{index}")
        if record.get("previous_hash") != previous:
            errors.append(f"previous_hash_mismatch:{index}")
        body = {key: value for key, value in record.items() if key != "record_hash"}
        calculated = digest(body)
        if calculated != record.get("record_hash"):
            errors.append(f"record_hash_mismatch:{index}")
        event_id = record.get("event_id")
        if event_id in ids:
            errors.append(f"duplicate_event_id:{event_id}")
        ids.add(event_id)
        previous = record.get("record_hash", "")
    return errors


def append_event(event_type: str, payload: dict, event_id: str | None = None, observed: datetime | None = None) -> dict:
    BASE.mkdir(parents=True, exist_ok=True)
    records = read_ledger()
    errors = reconcile_ledger(records)
    if errors:
        raise RuntimeError("Ledger validation failed: " + ", ".join(errors))
    event_id = event_id or digest({"event_type": event_type, "payload": payload})
    existing = next((row for row in records if row["event_id"] == event_id), None)
    if existing:
        return existing
    record = {
        "sequence": len(records) + 1,
        "event_id": event_id,
        "event_type": event_type,
        "recorded_utc": (observed or now_utc()).isoformat(),
        "previous_hash": records[-1]["record_hash"] if records else "GENESIS",
        "payload": payload,
    }
    record["record_hash"] = digest(record)
    with LEDGER.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return record


def split_fixture(fixture: str) -> tuple[str, str]:
    if " vs " not in fixture:
        raise ValueError(f"Unrecognized fixture: {fixture}")
    return tuple(fixture.split(" vs ", 1))  # type: ignore[return-value]


def selection_id(weekend: str, match_id: str, player_id: str) -> str:
    return f"{weekend}:{match_id}:{player_id}"


def discover_weekends() -> list[str]:
    return sorted(path.name for path in LIVE_BASE.iterdir() if path.is_dir()) if LIVE_BASE.exists() else []


def sync_official_selections(weekend: str) -> dict:
    """Import only immutable confirmed-lineup decisions from active v3 weekends."""
    cfg = config()
    folder = LIVE_BASE / weekend
    board_path = folder / cfg.get("board_filename", "frozen_board_league_balanced_v3.json")
    if not board_path.exists():
        return {"weekend": weekend, "imported": 0, "rejected": 0, "status": "no_frozen_v3_board"}
    board = load_json(board_path)
    if board.get("ranking_version") != cfg["selection_version"]:
        raise RuntimeError("Active board is not the frozen league-balanced v3 version")
    board_players = {(str(row["match_id"]), str(row["player_id"])) for row in board.get("candidates", [])}
    imported = rejected = 0
    existing_records = read_ledger()
    prior_locked = [
        row["payload"] for row in existing_records
        if row["event_type"] == "selection_locked" and row["payload"].get("weekend") == weekend
    ]
    league_counts: Counter = Counter(row["league"] for row in prior_locked)
    fixtures_seen: set[str] = {str(row["match_id"]) for row in prior_locked}
    accepted_count = len(prior_locked)
    processed_selection_ids = {
        row["payload"].get("selection_id") for row in existing_records
        if row["event_type"] in {"selection_locked", "selection_rejected"}
        and row["payload"].get("weekend") == weekend
    }
    decisions_dir = folder / cfg.get("lineup_decisions_dir", "lineup_decisions")
    for path in sorted(decisions_dir.glob("*.json")) if decisions_dir.exists() else []:
        decision = load_json(path)
        base_reasons = []
        if decision.get("lineup_type") != "standard" or len(decision.get("confirmed_home_starter_ids", [])) < 11:
            base_reasons.append("not_complete_confirmed_standard_home_lineup")
        if decision.get("league") not in cfg["sport_keys"]:
            base_reasons.append("league_not_in_frozen_v3_scope")
        for pick in decision.get("official_picks", []):
            reasons = list(base_reasons)
            key = (str(decision["match_id"]), str(pick["player_id"]))
            current_selection_id = selection_id(weekend, str(decision["match_id"]), str(pick["player_id"]))
            if current_selection_id in processed_selection_ids:
                continue
            if key not in board_players:
                reasons.append("not_on_frozen_v3_candidate_board")
            if pick.get("candidate_side") != "home":
                reasons.append("not_home_player")
            if not pick.get("plan_B"):
                reasons.append("not_plan_b_qualified")
            if str(pick["player_id"]) not in {str(x) for x in decision.get("confirmed_home_starter_ids", [])}:
                reasons.append("not_confirmed_home_starter")
            if league_counts[decision["league"]] >= cfg.get("maximum_candidates_per_league", 1):
                reasons.append("above_maximum_candidates_for_league")
            if str(decision["match_id"]) in fixtures_seen:
                reasons.append("second_candidate_from_same_fixture")
            if accepted_count >= cfg["maximum_candidates"]:
                reasons.append("above_maximum_three_official_candidates")
            payload = {
                "strategy_id": cfg.get("strategy_id", "league_balanced_v3"),
                "weekend": weekend,
                "selection_id": current_selection_id,
                "quote_subject_id": shared_quote_store.subject_id(weekend, str(decision["match_id"]), str(pick["player_id"])),
                "ranking_version": board["ranking_version"],
                "board_sha256": hashlib.sha256(board_path.read_bytes()).hexdigest(),
                "decision_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "match_id": str(decision["match_id"]),
                "kickoff": decision["date"],
                "league": decision["league"],
                "fixture": decision["fixture"],
                "player_id": str(pick["player_id"]),
                "player": pick["player"],
                "lineup_type": decision["lineup_type"],
                "lineup_locked_utc": decision["locked_utc"],
                "home_only": pick.get("candidate_side") == "home",
                "plan_b": bool(pick.get("plan_B")),
                "target": "Over 2.5 total shots",
                "reasons": reasons,
            }
            if reasons:
                append_event("selection_rejected", payload, f"selection-rejected:{payload['selection_id']}")
                rejected += 1
            else:
                append_event("selection_locked", payload, f"selection-locked:{payload['selection_id']}")
                league_counts[decision["league"]] += 1
                fixtures_seen.add(str(decision["match_id"]))
                accepted_count += 1
                imported += 1
        for pick in decision.get("rejected_provisional_candidates", []):
            payload = {
                "strategy_id": cfg.get("strategy_id", "league_balanced_v3"),
                "weekend": weekend,
                "match_id": str(decision["match_id"]),
                "league": decision["league"],
                "fixture": decision["fixture"],
                "player_id": str(pick["player_id"]),
                "player": pick["player"],
                "reasons": pick.get("reasons", ["rejected_by_frozen_lineup_rules"]),
            }
            event_id = f"provisional-rejected:{weekend}:{decision['match_id']}:{pick['player_id']}"
            append_event("provisional_rejected", payload, event_id)
            rejected += 1

    refusals_name = cfg.get("lineup_refusals_dir")
    refusals_dir = folder / refusals_name if refusals_name else None
    for path in sorted(refusals_dir.glob("*.json")) if refusals_dir and refusals_dir.exists() else []:
        refusal = load_json(path)
        pick = refusal.get("candidate") or {}
        if not pick.get("player_id"):
            continue
        current_selection_id = selection_id(weekend, str(refusal["match_id"]), str(pick["player_id"]))
        if current_selection_id in processed_selection_ids:
            continue
        key = (str(refusal["match_id"]), str(pick["player_id"]))
        reasons = [refusal.get("reason") or "prospective_lineup_lock_refused"]
        if key not in board_players:
            reasons.append("not_on_frozen_candidate_board")
        payload = {
            "strategy_id": cfg.get("strategy_id", "league_balanced_v3"),
            "weekend": weekend,
            "selection_id": current_selection_id,
            "quote_subject_id": shared_quote_store.subject_id(weekend, str(refusal["match_id"]), str(pick["player_id"])),
            "ranking_version": board["ranking_version"],
            "board_sha256": hashlib.sha256(board_path.read_bytes()).hexdigest(),
            "refusal_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "match_id": str(refusal["match_id"]),
            "kickoff": refusal["date"],
            "league": refusal["league"],
            "fixture": refusal["fixture"],
            "player_id": str(pick["player_id"]),
            "player": pick["player"],
            "home_only": pick.get("candidate_side") == "home",
            "plan_b": bool(pick.get("plan_B")),
            "target": "Over 2.5 total shots",
            "official_selection_eligible": False,
            "reasons": reasons,
        }
        append_event("selection_rejected", payload, f"selection-rejected:{current_selection_id}")
        processed_selection_ids.add(current_selection_id)
        rejected += 1
    return {"weekend": weekend, "imported": imported, "rejected": rejected, "status": "ok"}


def locked_selections(records: list[dict] | None = None, weekend: str | None = None) -> list[dict]:
    records = read_ledger() if records is None else records
    rows = [row["payload"] for row in records if row["event_type"] == "selection_locked"]
    if weekend:
        rows = [row for row in rows if row["weekend"] == weekend]
    return sorted(rows, key=lambda row: (row["kickoff"], row["selection_id"]))


def provisional_market_subjects(weekend: str) -> list[dict]:
    """Return frozen v3 names for pre-lineup market observation only.

    These rows are never appended as official selections and never count toward
    the validation gate.  Their stable identity joins to a later official lock.
    """
    cfg = config()
    path = LIVE_BASE / weekend / cfg.get("board_filename", "frozen_board_league_balanced_v3.json")
    if not path.exists():
        return []
    board = load_json(path)
    if board.get("ranking_version") != cfg["selection_version"]:
        return []
    return sorted(
        [
            {
                "strategy_id": cfg.get("strategy_id", "league_balanced_v3"),
                "weekend": weekend,
                "selection_id": selection_id(weekend, str(row["match_id"]), str(row["player_id"])),
                "quote_subject_id": shared_quote_store.subject_id(weekend, str(row["match_id"]), str(row["player_id"])),
                "match_id": str(row["match_id"]),
                "kickoff": row["date"],
                "league": row["league"],
                "fixture": row["fixture"],
                "player_id": str(row["player_id"]),
                "player": row["player"],
                "market_subject_status": "frozen_provisional_not_official",
            }
            for row in board.get("candidates", [])
        ],
        key=lambda row: (row["kickoff"], row["selection_id"]),
    )


def quote_events(records: list[dict] | None = None, weekend: str | None = None) -> list[dict]:
    records = read_ledger() if records is None else records
    rows = [row["payload"] for row in records if row["event_type"] == "quote_snapshot"]
    if weekend:
        rows = [row for row in rows if row["weekend"] == weekend]
    return rows


def latest_usable_quote(selection: dict, at: datetime, records: list[dict] | None = None) -> dict | None:
    cfg = config()
    choices = []
    for snapshot in quote_events(records, selection["weekend"]):
        if snapshot["selection_id"] != selection["selection_id"] or not snapshot.get("quotes"):
            continue
        observed = parse_time(snapshot["observed_utc"])
        if observed > at:
            continue
        if (at - observed).total_seconds() > cfg["quote_stale_seconds"]:
            continue
        choices.append(snapshot)
    return max(choices, key=lambda row: row["observed_utc"], default=None)


def _stage_already_captured(selection: dict, stage: str, records: list[dict]) -> bool:
    return any(
        row["event_type"] == "quote_snapshot"
        and row["payload"]["selection_id"] == selection["selection_id"]
        and row["payload"]["stage"] == stage
        and (stage != "first_market" or bool(row["payload"].get("quotes")))
        for row in records
    )


def collect_quotes(weekend: str, stage: str, observed: datetime | None = None, api: TheOddsAPI | None = None) -> dict:
    cfg = config()
    observed = (observed or now_utc()).astimezone(timezone.utc)
    if stage not in {"first_market", "lineup_lock", "ticket_creation", "final_pre_kickoff", "poll"}:
        raise ValueError("Unknown quote snapshot stage")
    sync_official_selections(weekend)
    records = read_ledger()
    selections = provisional_market_subjects(weekend) if stage == "first_market" else locked_selections(records, weekend)
    if not selections:
        return {"status": "no_official_selections", "weekend": weekend, "captured": 0}
    if api is None:
        load_local_env(ROOT)
        api = TheOddsAPI(os.getenv("THE_ODDS_API_KEY", ""))

    captured = errors = 0
    events_cache: dict[str, list[dict]] = {}
    for selection in selections:
        if stage != "poll" and _stage_already_captured(selection, stage, records):
            continue
        kickoff = parse_time(selection["kickoff"])
        if observed >= kickoff:
            continue
        sport_key = cfg["sport_keys"][selection["league"]]
        try:
            if sport_key not in events_cache:
                response = api.events(sport_key)
                events_cache[sport_key] = response.payload
            shared = shared_quote_store.capture(
                weekend=weekend,
                selection=selection,
                stage=stage,
                observed=observed,
                sport_key=sport_key,
                allowed_bookmakers=cfg["allowed_bookmakers"],
                stale_seconds=cfg["quote_stale_seconds"],
                api=api,
                events=events_cache[sport_key],
            )
            shared = shared_quote_store.materialize_reference(shared)
            payload = {
                "strategy_id": cfg.get("strategy_id", "league_balanced_v3"),
                "weekend": weekend,
                "selection_id": selection["selection_id"],
                "quote_subject_id": selection["quote_subject_id"],
                "match_id": selection["match_id"],
                "league": selection["league"],
                "fixture": selection["fixture"],
                "kickoff": selection["kickoff"],
                "player_id": selection["player_id"],
                "player": selection["player"],
                "provider": "the_odds_api",
                "provider_event_id": shared["provider_event_id"],
                "stage": stage,
                "observed_utc": observed.isoformat(),
                "raw_sha256": shared["raw_sha256"],
                "shared_snapshot_path": shared["shared_snapshot_path"],
                "shared_snapshot_sha256": shared["shared_snapshot_sha256"],
                "observation_id": shared["observation_id"],
                "quotes": shared["quotes"],
                "rejections": shared["rejections"],
                "quota_remaining": shared.get("quota_remaining"),
                "quota_used": shared.get("quota_used"),
                "shared_cache_hit": shared.get("cache_hit", False),
            }
            append_event("quote_snapshot", payload, f"quote:{weekend}:{selection['selection_id']}:{stage}:{timestamp_slug(observed)}", observed)
            if not shared["quotes"]:
                append_event(
                    "missing_market",
                    {"strategy_id": cfg.get("strategy_id", "league_balanced_v3"), "weekend": weekend, "selection_id": selection["selection_id"], "quote_subject_id": selection["quote_subject_id"], "stage": stage, "reasons": shared["rejections"]},
                    f"missing-market:{weekend}:{selection['selection_id']}:{stage}:{timestamp_slug(observed)}",
                    observed,
                )
            captured += 1
        except OddsAPIError as exc:
            errors += 1
            append_event(
                "collector_error",
                {
                    "strategy_id": cfg.get("strategy_id", "league_balanced_v3"),
                    "weekend": weekend,
                    "selection_id": selection["selection_id"],
                    "quote_subject_id": selection.get("quote_subject_id"),
                    "stage": stage,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                },
                f"collector-error:{weekend}:{selection['selection_id']}:{stage}:{timestamp_slug(observed)}",
                observed,
            )
    return {"status": "ok" if not errors else "partial_error", "weekend": weekend, "captured": captured, "errors": errors}


def common_book_price(selections: list[dict], snapshots: dict[str, dict], allowed_books: list[str]) -> dict | None:
    price_maps: dict[str, dict[str, dict]] = {}
    for selection in selections:
        snapshot = snapshots.get(selection["selection_id"])
        if not snapshot:
            return None
        by_book = {}
        for quote in snapshot.get("quotes", []):
            if quote["bookmaker"] in allowed_books:
                current = by_book.get(quote["bookmaker"])
                if current is None or quote["price"] > current["price"]:
                    by_book[quote["bookmaker"]] = quote
        price_maps[selection["selection_id"]] = by_book
    common = set(allowed_books)
    for mapping in price_maps.values():
        common &= set(mapping)
    if not common:
        return None
    candidates = []
    for book in sorted(common):
        legs = []
        product = 1.0
        for selection in selections:
            quote = price_maps[selection["selection_id"]][book]
            product *= quote["price"]
            legs.append({**selection, "bookmaker": book, "price": quote["price"], "quote_last_update": quote["last_update"]})
        candidates.append({"bookmaker": book, "derived_product_price": product, "legs": legs})
    return max(candidates, key=lambda row: (row["derived_product_price"], row["bookmaker"]))


def ticket_events(records: list[dict] | None = None) -> list[dict]:
    records = read_ledger() if records is None else records
    return [row["payload"] for row in records if row["event_type"] == "ticket_created"]


def settlement_events(records: list[dict] | None = None) -> list[dict]:
    records = read_ledger() if records is None else records
    return [row["payload"] for row in records if row["event_type"] == "ticket_settled"]


def bankroll_state(records: list[dict] | None = None, staking_track: str | None = None) -> dict:
    cfg = config()
    records = read_ledger() if records is None else records
    staking_track = staking_track or cfg.get("primary_staking_track", next(iter(staking_tracks(cfg))))
    bankroll = float(cfg["starting_bankroll_units"])
    peak = bankroll
    maximum_drawdown = 0.0
    settled_ids = set()
    track_settlements = [row for row in settlement_events(records) if row.get("staking_track", staking_track) == staking_track]
    for settlement in track_settlements:
        bankroll = float(settlement["bankroll_after"])
        peak = max(peak, bankroll)
        maximum_drawdown = max(maximum_drawdown, (peak - bankroll) / peak if peak > 0 else 0)
        settled_ids.add(settlement["ticket_id"])
    outstanding = [
        ticket for ticket in ticket_events(records)
        if ticket["ticket_id"] not in settled_ids and ticket.get("staking_track", staking_track) == staking_track
    ]
    exposure = sum(float(ticket["stake"]) for ticket in outstanding)
    return {
        "bankroll": bankroll,
        "peak_bankroll": peak,
        "maximum_drawdown": maximum_drawdown,
        "outstanding_exposure": exposure,
        "insolvent": bankroll <= 0,
        "staking_track": staking_track,
    }


def freeze_due_tickets(weekend: str, observed: datetime | None = None) -> dict:
    cfg = config()
    observed = (observed or now_utc()).astimezone(timezone.utc)
    sync_official_selections(weekend)
    records = read_ledger()
    selections = locked_selections(records, weekend)
    assigned = {
        leg["selection_id"] for ticket in ticket_events(records) for leg in ticket.get("legs", [])
    } | {
        row["payload"]["selection_id"]
        for row in records
        if row["event_type"] == "no_combo"
    }
    unused = [row for row in selections if row["selection_id"] not in assigned and parse_time(row["kickoff"]) > observed]
    if not unused:
        return {"status": "nothing_due", "created": 0, "no_combo": 0}
    unused.sort(key=lambda row: (row["kickoff"], row["selection_id"]))
    earliest = parse_time(unused[0]["kickoff"])
    freeze = earliest - timedelta(minutes=cfg["freeze_minutes_before_kickoff"])
    if observed < freeze:
        return {"status": "waiting_for_freeze", "freeze_utc": freeze.isoformat(), "created": 0, "no_combo": 0}
    if observed >= earliest:
        due = [row for row in unused if parse_time(row["kickoff"]) <= observed]
        for row in due:
            append_event(
                "no_combo",
                {"weekend": weekend, "selection_id": row["selection_id"], "reason": "freeze_window_missed"},
                f"no-combo:{row['selection_id']}", observed,
            )
        return {"status": "missed_freeze", "created": 0, "no_combo": len(due)}

    snapshots = {row["selection_id"]: latest_usable_quote(row, observed, records) for row in unused}
    eligible = [row for row in unused if snapshots[row["selection_id"]] is not None]
    # Defensive enforcement even though frozen v3 already applies these limits.
    unique = []
    league_counts: Counter = Counter()
    seen_fixtures = set()
    for row in eligible:
        if (
            league_counts[row["league"]] < cfg.get("maximum_candidates_per_league", 1)
            and row["match_id"] not in seen_fixtures
            and len(unique) < cfg["maximum_candidates"]
        ):
            unique.append(row)
            league_counts[row["league"]] += 1
            seen_fixtures.add(row["match_id"])
    earliest_id = unused[0]["selection_id"]
    if len(unique) < cfg["minimum_combo_legs"] or earliest_id not in {row["selection_id"] for row in unique}:
        append_event(
            "no_combo",
            {"weekend": weekend, "selection_id": earliest_id, "reason": "fewer_than_two_fresh_same_window_candidates"},
            f"no-combo:{earliest_id}", observed,
        )
        return {"status": "no_combo", "created": 0, "no_combo": 1}
    choice = common_book_price(unique, snapshots, cfg["allowed_bookmakers"])
    if choice is None:
        append_event(
            "no_combo",
            {"weekend": weekend, "selection_id": earliest_id, "reason": "no_common_allowed_bookmaker"},
            f"no-combo:{earliest_id}", observed,
        )
        return {"status": "no_common_book", "created": 0, "no_combo": 1}

    combo_id = f"{weekend}:{timestamp_slug(observed)}:{digest([row['selection_id'] for row in unique])[:12]}"
    created_tickets = []
    for track, fraction in staking_tracks(cfg).items():
        current_records = read_ledger()
        state = bankroll_state(current_records, track)
        if state["insolvent"]:
            continue
        stake = round(state["bankroll"] * fraction, 2)
        overlap = state["outstanding_exposure"] + stake > state["bankroll"] + 1e-9
        ticket_id = f"{combo_id}:{track}"
        legs = [
            {
                **leg,
                "strategy_id": cfg.get("strategy_id", "league_balanced_v3"),
                "quote_subject_id": leg.get("quote_subject_id") or shared_quote_store.subject_id(weekend, str(leg["match_id"]), str(leg["player_id"])),
            }
            for leg in choice["legs"]
        ]
        payload = {
            "strategy_id": cfg.get("strategy_id", "league_balanced_v3"),
            "staking_track": track,
            "weekend": weekend,
            "combo_id": combo_id,
            "ticket_id": ticket_id,
            "created_utc": observed.isoformat(),
            "freeze_for_earliest_kickoff": earliest.isoformat(),
            "bookmaker": choice["bookmaker"],
            "price_type": "derived_product_price",
            "derived_product_price": round(choice["derived_product_price"], 6),
            "implied_break_even_probability": round(1 / choice["derived_product_price"], 8),
            "legs": legs,
            "bankroll_snapshot": state["bankroll"],
            "stake_fraction": fraction,
            "stake": stake,
            "outstanding_exposure_before": round(state["outstanding_exposure"], 2),
            "cumulative_exposure_after": round(state["outstanding_exposure"] + stake, 2),
            "executability": "non_executable_overlap" if overlap else "executable",
            "paper_only": True,
            "actual_parlay_quote": False,
        }
        path = BASE / weekend / "tickets" / f"{timestamp_slug(observed)}_{track}_{digest(ticket_id)[:12]}.json"
        write_once(path, payload)
        payload["ticket_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        append_event("ticket_created", payload, f"ticket-created:{ticket_id}", observed)
        created_tickets.append(payload)
    if not created_tickets:
        return {"status": "insolvent", "created": 0, "no_combo": 0}
    primary = cfg.get("primary_staking_track", next(iter(staking_tracks(cfg))))
    primary_ticket = next((row for row in created_tickets if row["staking_track"] == primary), created_tickets[0])
    return {"status": "created", "created": len(created_tickets), "combinations_created": 1, "no_combo": 0, "ticket": primary_ticket, "tickets": created_tickets}


def _settled_pick_map(weekend: str) -> dict[str, dict]:
    folder = LIVE_BASE / weekend / config().get("settled_dir", "settled")
    result = {}
    for path in sorted(folder.glob("*.json")) if folder.exists() else []:
        payload = load_json(path)
        for pick in payload.get("official_picks", []):
            result[selection_id(weekend, str(payload["match_id"]), str(pick["player_id"]))] = pick
    return result


def closing_price_for_leg(leg: dict, bookmaker: str, records: list[dict]) -> float | None:
    candidates = []
    kickoff = parse_time(leg["kickoff"])
    for snapshot in quote_events(records, leg["weekend"]):
        if snapshot["selection_id"] != leg["selection_id"] or snapshot["stage"] != "final_pre_kickoff":
            continue
        observed = parse_time(snapshot["observed_utc"])
        if observed >= kickoff:
            continue
        for quote in snapshot.get("quotes", []):
            if quote["bookmaker"] == bookmaker:
                candidates.append((observed, float(quote["price"])))
    return max(candidates, default=(None, None))[1]


def settle_tickets(weekend: str, observed: datetime | None = None) -> dict:
    observed = (observed or now_utc()).astimezone(timezone.utc)
    records = read_ledger()
    outcomes = _settled_pick_map(weekend)
    already = {row["ticket_id"] for row in settlement_events(records)}
    created = 0
    unresolved = []
    for ticket in [row for row in ticket_events(records) if row["weekend"] == weekend and row["ticket_id"] not in already]:
        if any(leg["selection_id"] not in outcomes for leg in ticket["legs"]):
            unresolved.append(ticket["ticket_id"])
            continue
        graded_legs = []
        for leg in ticket["legs"]:
            outcome = outcomes[leg["selection_id"]]
            status = "void" if outcome.get("shots") is None else "win" if outcome["shots"] >= 3 else "loss"
            close = closing_price_for_leg(leg, ticket["bookmaker"], records)
            graded_legs.append(
                {
                    **leg,
                    "shots": outcome.get("shots"),
                    "minutes": outcome.get("minutes"),
                    "result": status,
                    "closing_price": close,
                    "clv": round(leg["price"] / close - 1, 8) if close else None,
                }
            )
        active = [leg for leg in graded_legs if leg["result"] != "void"]
        if len(active) < 2:
            result = "void"
            repriced = None
            returned = float(ticket["stake"])
        else:
            repriced = math.prod(leg["price"] for leg in active)
            result = "loss" if any(leg["result"] == "loss" for leg in active) else "win"
            returned = float(ticket["stake"]) * repriced if result == "win" else 0.0
        track = ticket.get("staking_track", config().get("primary_staking_track", "stress_90"))
        before = bankroll_state(records, track)["bankroll"]
        after = round(before - float(ticket["stake"]) + returned, 2)
        closing_prices = [leg["closing_price"] for leg in active]
        combo_closing = math.prod(closing_prices) if active and all(value is not None for value in closing_prices) else None
        combo_clv = repriced / combo_closing - 1 if repriced and combo_closing else None
        payload = {
            "strategy_id": ticket.get("strategy_id", config().get("strategy_id", "league_balanced_v3")),
            "staking_track": track,
            "weekend": weekend,
            "combo_id": ticket.get("combo_id", ticket["ticket_id"]),
            "ticket_id": ticket["ticket_id"],
            "settled_utc": observed.isoformat(),
            "bookmaker": ticket["bookmaker"],
            "result": result,
            "legs": graded_legs,
            "settled_leg_count": len(active),
            "repriced_derived_odds": round(repriced, 6) if repriced else None,
            "closing_derived_odds": round(combo_closing, 6) if combo_closing else None,
            "combo_clv": round(combo_clv, 8) if combo_clv is not None else None,
            "stake": ticket["stake"],
            "returned": round(returned, 2),
            "net_profit": round(returned - float(ticket["stake"]), 2),
            "bankroll_before": before,
            "bankroll_after": after,
            "insolvent": after <= 0,
            "executability": ticket["executability"],
            "paper_only": True,
        }
        for leg in graded_legs:
            append_event(
                "leg_settled",
                {
                    "strategy_id": ticket.get("strategy_id", config().get("strategy_id", "league_balanced_v3")),
                    "staking_track": track,
                    "weekend": weekend,
                    "ticket_id": ticket["ticket_id"],
                    "selection_id": leg["selection_id"],
                    "player": leg["player"],
                    "league": leg["league"],
                    "result": leg["result"],
                    "shots": leg["shots"],
                    "opening_price": leg["price"],
                    "closing_price": leg["closing_price"],
                    "clv": leg["clv"],
                },
                f"leg-settled:{ticket['ticket_id']}:{leg['selection_id']}",
                observed,
            )
        append_event("ticket_settled", payload, f"ticket-settled:{ticket['ticket_id']}", observed)
        records = read_ledger()
        created += 1
    return {"weekend": weekend, "settled": created, "unresolved": unresolved}


def build_summary(records: list[dict] | None = None) -> dict:
    cfg = config()
    load_local_env(ROOT)
    records = read_ledger() if records is None else records
    selections = locked_selections(records)
    tickets = ticket_events(records)
    settlements = settlement_events(records)
    selection_results = {}
    for weekend in {row["weekend"] for row in selections}:
        selection_results.update(_settled_pick_map(weekend))
    graded = [selection_results[row["selection_id"]] for row in selections if row["selection_id"] in selection_results]
    hits = sum(row.get("shots") is not None and row["shots"] >= 3 for row in graded)
    executable = [row for row in tickets if row["executability"] == "executable"]
    settled_executable = [row for row in settlements if row["executability"] == "executable"]
    paper_profit = sum(float(row["net_profit"]) for row in settlements)
    paper_staked = sum(float(row["stake"]) for row in settlements)
    executable_profit = sum(float(row["net_profit"]) for row in settled_executable)
    executable_staked = sum(float(row["stake"]) for row in settled_executable)
    clvs = [float(row["combo_clv"]) for row in settlements if row.get("combo_clv") is not None]
    league_counts = Counter(row["league"] for row in selections)
    total = len(selections)
    state = bankroll_state(records)
    unresolved = reconcile_ledger(records)
    successful_quote_times = defaultdict(list)
    for row in records:
        if row["event_type"] == "quote_snapshot" and row["payload"].get("quotes"):
            successful_quote_times[row["payload"]["selection_id"]].append(parse_time(row["recorded_utc"]))
    for row in records:
        if row["event_type"] != "collector_error":
            continue
        error_time = parse_time(row["recorded_utc"])
        selection_key = row["payload"]["selection_id"]
        if not any(value > error_time for value in successful_quote_times[selection_key]):
            unresolved.append(f"unresolved_collector_error:{selection_key}:{row['event_id']}")
    current = now_utc()
    for selection in selections:
        if parse_time(selection["kickoff"]) + timedelta(hours=4) < current and selection["selection_id"] not in selection_results:
            unresolved.append(f"missing_selection_settlement:{selection['selection_id']}")
    settled_ticket_ids = {row["ticket_id"] for row in settlements}
    for ticket in tickets:
        latest_kickoff = max(parse_time(leg["kickoff"]) for leg in ticket["legs"])
        if latest_kickoff + timedelta(hours=4) < current and ticket["ticket_id"] not in settled_ticket_ids:
            unresolved.append(f"missing_ticket_settlement:{ticket['ticket_id']}")
    missing = [row for row in records if row["event_type"] == "missing_market"]
    active_weekends = len({row["weekend"] for row in selections})
    selection_by_league = {}
    for league in sorted(league_counts):
        league_selections = [row for row in selections if row["league"] == league]
        league_graded = [selection_results[row["selection_id"]] for row in league_selections if row["selection_id"] in selection_results]
        league_hits = sum(row.get("shots") is not None and row["shots"] >= 3 for row in league_graded)
        selection_by_league[league] = {
            "official_legs": len(league_selections),
            "graded": len(league_graded),
            "hits": league_hits,
            "hit_rate": league_hits / len(league_graded) if league_graded else None,
        }
    ticket_result_by_bookmaker = {}
    for bookmaker in sorted({row["bookmaker"] for row in tickets}):
        book_tickets = [row for row in tickets if row["bookmaker"] == bookmaker]
        book_settled = [row for row in settlements if row["bookmaker"] == bookmaker]
        staked = sum(float(row["stake"]) for row in book_settled)
        profit = sum(float(row["net_profit"]) for row in book_settled)
        ticket_result_by_bookmaker[bookmaker] = {
            "tickets": len(book_tickets),
            "settled": len(book_settled),
            "wins": sum(row["result"] == "win" for row in book_settled),
            "net_profit": round(profit, 2),
            "roi": profit / staked if staked else None,
        }
    settlement_by_ticket = {row["ticket_id"]: row for row in settlements}
    ticket_result_by_window = {}
    for ticket in tickets:
        window = ticket["freeze_for_earliest_kickoff"]
        aggregate = ticket_result_by_window.setdefault(window, {"tickets": 0, "settled": 0, "wins": 0, "net_profit": 0.0, "staked": 0.0})
        aggregate["tickets"] += 1
        settlement = settlement_by_ticket.get(ticket["ticket_id"])
        if settlement:
            aggregate["settled"] += 1
            aggregate["wins"] += settlement["result"] == "win"
            aggregate["net_profit"] += float(settlement["net_profit"])
            aggregate["staked"] += float(settlement["stake"])
    for aggregate in ticket_result_by_window.values():
        aggregate["net_profit"] = round(aggregate["net_profit"], 2)
        aggregate["roi"] = aggregate["net_profit"] / aggregate.pop("staked") if aggregate["staked"] else None
    gate = cfg["activation_gate"]
    checks = {
        "official_legs": total >= gate["official_legs"],
        "executable_tickets": len(executable) >= gate["executable_tickets"],
        "active_weekends": active_weekends >= gate["active_weekends"],
        "league_representation": len(league_counts) >= gate["minimum_leagues"],
        "league_concentration": bool(total) and max(league_counts.values(), default=0) / total <= gate["maximum_league_share"],
        "positive_paper_roi": bool(executable_staked) and executable_profit / executable_staked > 0,
        "positive_average_clv": bool(clvs) and mean(clvs) > 0,
        "ticket_clv_beat_share": bool(clvs) and sum(value > 0 for value in clvs) / len(clvs) > gate["minimum_ticket_clv_beat_share"],
        "zero_unresolved_discrepancies": not unresolved,
    }
    return {
        "generated_utc": now_utc().isoformat(),
        "version": cfg["version"],
        "paper_only": True,
        "odds_api_configured": bool(os.getenv("THE_ODDS_API_KEY")),
        "official_legs": total,
        "official_leg_target": gate["official_legs"],
        "graded_official_legs": len(graded),
        "selection_hits": hits,
        "selection_hit_rate": hits / len(graded) if graded else None,
        "tickets": len(tickets),
        "executable_tickets": len(executable),
        "settled_tickets": len(settlements),
        "settled_executable_tickets": len(settled_executable),
        "ticket_wins": sum(row["result"] == "win" for row in settlements),
        "ticket_hit_rate": sum(row["result"] == "win" for row in settlements) / len(settlements) if settlements else None,
        "paper_net_profit": round(paper_profit, 2),
        "paper_staked": round(paper_staked, 2),
        "paper_roi": paper_profit / paper_staked if paper_staked else None,
        "executable_paper_net_profit": round(executable_profit, 2),
        "executable_paper_staked": round(executable_staked, 2),
        "executable_paper_roi": executable_profit / executable_staked if executable_staked else None,
        "average_clv": mean(clvs) if clvs else None,
        "median_clv": median(clvs) if clvs else None,
        "tickets_beating_close_share": sum(value > 0 for value in clvs) / len(clvs) if clvs else None,
        "bankroll": state,
        "active_weekends": active_weekends,
        "leagues": dict(sorted(league_counts.items())),
        "selection_results_by_league": selection_by_league,
        "bookmakers": dict(sorted(Counter(row["bookmaker"] for row in tickets).items())),
        "ticket_results_by_bookmaker": ticket_result_by_bookmaker,
        "kickoff_windows": dict(sorted(Counter(row["freeze_for_earliest_kickoff"] for row in tickets).items())),
        "ticket_results_by_kickoff_window": ticket_result_by_window,
        "cumulative_ticket_exposure": round(sum(float(row["stake"]) for row in tickets), 2),
        "missing_market_records": len(missing),
        "collector_error_records": sum(row["event_type"] == "collector_error" for row in records),
        "unresolved_discrepancies": unresolved,
        "activation_checks": checks,
        "activation_gate_passed": all(checks.values()),
        "activation_effect": "review_survivable_real_money_stake_only; never automatic betting",
    }


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{100 * value:.1f}%"


def build_dashboard() -> dict:
    summary = build_summary()
    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    check_rows = "".join(
        f"<tr><td>{escape(name.replace('_', ' ').title())}</td><td class={'pass' if passed else 'wait'}>{'PASS' if passed else 'WAIT'}</td></tr>"
        for name, passed in summary["activation_checks"].items()
    )
    league_rows = "".join(f"<tr><td>{escape(name)}</td><td>{count}</td></tr>" for name, count in summary["leagues"].items())
    book_rows = "".join(f"<tr><td>{escape(name)}</td><td>{count}</td></tr>" for name, count in summary["bookmakers"].items())
    league_result_rows = "".join(
        f"<tr><td>{escape(name)}</td><td>{row['official_legs']}</td><td>{row['graded']}</td><td>{row['hits']}</td><td>{_pct(row['hit_rate'])}</td></tr>"
        for name, row in summary["selection_results_by_league"].items()
    )
    bookmaker_result_rows = "".join(
        f"<tr><td>{escape(name)}</td><td>{row['tickets']}</td><td>{row['settled']}</td><td>{row['wins']}</td><td>{_pct(row['roi'])}</td></tr>"
        for name, row in summary["ticket_results_by_bookmaker"].items()
    )
    window_result_rows = "".join(
        f"<tr><td>{escape(name)}</td><td>{row['tickets']}</td><td>{row['settled']}</td><td>{row['wins']}</td><td>{_pct(row['roi'])}</td></tr>"
        for name, row in summary["ticket_results_by_kickoff_window"].items()
    )
    html = f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>
<title>Plan B Profit Validation</title><style>
body{{font:16px Inter,Segoe UI,sans-serif;background:#07111f;color:#eaf1fb;margin:0;padding:28px}}main{{max-width:1180px;margin:auto}}h1{{margin-bottom:4px}}.muted{{color:#9badc4}}.warning{{background:#261d12;border-left:4px solid #ffb84d;padding:16px;border-radius:8px;margin:20px 0}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}}.card,table{{background:#101d31;border:1px solid #293e5e;border-radius:10px}}.card{{padding:16px}}.big{{font-size:28px;font-weight:700}}table{{width:100%;border-collapse:collapse;margin:12px 0 26px}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #293e5e}}th{{color:#8bc4ff}}.pass{{color:#69e49a}}.wait{{color:#ffbd66}}.columns{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}}code{{color:#8de0bd}}
</style></head><body><main><h1>Frozen v3 profit-and-consistency validation</h1><p class=muted>Prospective 3+ total-shots combinations · captured US-book prices · append-only evidence</p>
<div class=warning><strong>Paper experiment only.</strong> The 90% bankroll stake is an intentionally destructive stress test. Derived products and overlapping exposure are not realizable profit. This system cannot place bets.<br><strong>Odds collector:</strong> {'configured' if summary['odds_api_configured'] else 'THE_ODDS_API_KEY still required in local .env'}.</div>
<h2>Model quality</h2><div class=grid><div class=card><div class=big>{summary['official_legs']} / {summary['official_leg_target']}</div>official legs</div><div class=card><div class=big>{summary['graded_official_legs']}</div>graded legs</div><div class=card><div class=big>{_pct(summary['selection_hit_rate'])}</div>3+ selection hit rate</div><div class=card><div class=big>{summary['active_weekends']}</div>active weekends</div></div>
<h2>Bookmaker price quality</h2><div class=grid><div class=card><div class=big>{summary['executable_tickets']}</div>executable tickets</div><div class=card><div class=big>{_pct(summary['executable_paper_roi'])}</div>executable-only paper ROI</div><div class=card><div class=big>{_pct(summary['paper_roi'])}</div>90% stress-test ROI</div><div class=card><div class=big>{_pct(summary['average_clv'])}</div>average CLV</div><div class=card><div class=big>{_pct(summary['tickets_beating_close_share'])}</div>tickets beating close</div><div class=card><div class=big>{summary['missing_market_records']}</div>missing-market records</div></div>
<h2>Bankroll risk</h2><div class=grid><div class=card><div class=big>{summary['bankroll']['bankroll']:.2f}</div>paper bankroll</div><div class=card><div class=big>{summary['paper_net_profit']:.2f}</div>paper net result</div><div class=card><div class=big>{_pct(summary['bankroll']['maximum_drawdown'])}</div>maximum drawdown</div><div class=card><div class=big>{'YES' if summary['bankroll']['insolvent'] else 'NO'}</div>insolvent</div><div class=card><div class=big>{summary['bankroll']['outstanding_exposure']:.2f}</div>open paper exposure</div></div>
<div class=columns><section><h2>Activation gate</h2><table><thead><tr><th>Requirement</th><th>Status</th></tr></thead><tbody>{check_rows}</tbody></table></section><section><h2>Sample mix</h2><table><thead><tr><th>League</th><th>Official legs</th></tr></thead><tbody>{league_rows or '<tr><td colspan=2>No official legs yet</td></tr>'}</tbody></table><table><thead><tr><th>Bookmaker</th><th>Tickets</th></tr></thead><tbody>{book_rows or '<tr><td colspan=2>No tickets yet</td></tr>'}</tbody></table></section></div>
<h2>Results by league</h2><table><thead><tr><th>League</th><th>Official</th><th>Graded</th><th>Hits</th><th>Hit rate</th></tr></thead><tbody>{league_result_rows or '<tr><td colspan=5>No graded league results yet</td></tr>'}</tbody></table>
<h2>Results by bookmaker</h2><table><thead><tr><th>Book</th><th>Tickets</th><th>Settled</th><th>Wins</th><th>Paper ROI</th></tr></thead><tbody>{bookmaker_result_rows or '<tr><td colspan=5>No settled bookmaker results yet</td></tr>'}</tbody></table>
<h2>Results by kickoff window</h2><table><thead><tr><th>Window</th><th>Tickets</th><th>Settled</th><th>Wins</th><th>Paper ROI</th></tr></thead><tbody>{window_result_rows or '<tr><td colspan=5>No settled kickoff-window results yet</td></tr>'}</tbody></table>
<p class=muted>Rule version <code>{escape(summary['version'])}</code>. Passing every gate triggers a separate staking review; it never activates live betting or approves 90% staking.</p></main></body></html>"""
    (BASE / "index.html").write_text(html, encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("sync", "tickets", "settle"):
        item = sub.add_parser(command)
        item.add_argument("--weekend", required=True)
        item.add_argument("--now", help="ISO timestamp for deterministic testing")
    collect = sub.add_parser("collect")
    collect.add_argument("--weekend", required=True)
    collect.add_argument("--stage", required=True, choices=("first_market", "lineup_lock", "ticket_creation", "final_pre_kickoff", "poll"))
    collect.add_argument("--now", help="ISO timestamp for deterministic testing")
    sub.add_parser("dashboard")
    sub.add_parser("status")
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
