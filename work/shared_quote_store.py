"""Immutable provider snapshots shared by prospective strategy ledgers.

One physical player/fixture/stage observation is fetched once.  Strategy
ledgers store references to this evidence instead of independently spending
API quota for the same market subject.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from the_odds_api import TheOddsAPI, extract_exact_quotes, match_event

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs" / "shared_odds"


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def subject_id(weekend: str, match_id: str, player_id: str) -> str:
    return f"{weekend}:{match_id}:{player_id}"


def observation_id(subject: str, stage: str, observed: datetime) -> str:
    stamp = observed.astimezone(timezone.utc).isoformat(timespec="microseconds")
    return hashlib.sha256(f"{subject}|{stage}|{stamp}".encode("utf-8")).hexdigest()


def _write_once(path: Path, payload: Any) -> None:
    if path.exists():
        raise RuntimeError(f"Immutable shared quote file already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _display_path(path: Path) -> str:
    try:
        value = path.relative_to(ROOT)
    except ValueError:
        value = path
    return str(value).replace("\\", "/")


def capture(
    *,
    weekend: str,
    selection: dict,
    stage: str,
    observed: datetime,
    sport_key: str,
    allowed_bookmakers: list[str],
    stale_seconds: int,
    api: TheOddsAPI,
    events: list[dict],
) -> dict:
    """Return one immutable normalized snapshot, fetching only when absent."""
    observed = observed.astimezone(timezone.utc)
    physical_subject = selection.get("quote_subject_id") or subject_id(
        weekend, str(selection["match_id"]), str(selection["player_id"])
    )
    identifier = observation_id(physical_subject, stage, observed)
    folder = BASE / weekend
    normalized_path = folder / "snapshots" / f"{identifier}.json"
    raw_path = folder / "raw" / f"{identifier}.json"
    if normalized_path.exists():
        payload = json.loads(normalized_path.read_text(encoding="utf-8"))
        payload["cache_hit"] = True
        return materialize_reference(payload)

    home, away = selection["fixture"].split(" vs ", 1)
    matched = match_event(events, home, away, selection["kickoff"])
    response = api.event_player_shots(sport_key, str(matched["id"]), allowed_bookmakers)
    raw = {
        "provider": "the_odds_api",
        "fetched_utc": response.fetched_utc,
        "sport_key": sport_key,
        "provider_event_id": str(matched["id"]),
        "quote_subject_id": physical_subject,
        "observation_id": identifier,
        "stage": stage,
        "observed_utc": observed.isoformat(),
        "payload": response.payload,
    }
    _write_once(raw_path, raw)
    quotes, rejections = extract_exact_quotes(
        response.payload, selection["player"], allowed_bookmakers, observed, stale_seconds
    )
    payload = {
        "provider": "the_odds_api",
        "provider_event_id": str(matched["id"]),
        "quote_subject_id": physical_subject,
        "observation_id": identifier,
        "stage": stage,
        "observed_utc": observed.isoformat(),
        "sport_key": sport_key,
        "raw_path": _display_path(raw_path),
        "raw_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "quotes": quotes,
        "rejections": rejections,
        "quota_remaining": response.quota_remaining,
        "quota_used": response.quota_used,
        "cache_hit": False,
    }
    _write_once(normalized_path, payload)
    # The file hash is evidence about the immutable on-disk payload and is not
    # written back into that file (which would make the hash self-referential).
    payload["shared_snapshot_path"] = _display_path(normalized_path)
    payload["shared_snapshot_sha256"] = hashlib.sha256(normalized_path.read_bytes()).hexdigest()
    return payload


def materialize_reference(payload: dict) -> dict:
    """Restore path/hash fields for a cached snapshot loaded from disk."""
    if payload.get("shared_snapshot_path"):
        return payload
    identifier = payload["observation_id"]
    weekend = payload["quote_subject_id"].split(":", 1)[0]
    path = BASE / weekend / "snapshots" / f"{identifier}.json"
    payload["shared_snapshot_path"] = _display_path(path)
    payload["shared_snapshot_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return payload
