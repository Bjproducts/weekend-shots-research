"""Confirmed-lineup locking, settlement and dashboard for volume-v4 challenger."""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from download_fotmob_big5_carryover import extract_stat, get_json

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs/live_plan_b3"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_once(path: Path, payload: dict) -> None:
    if path.exists():
        raise RuntimeError(f"Immutable file already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lineups(weekend: str) -> dict:
    folder = BASE / weekend
    board_path = folder / "frozen_board_volume_v4.json"
    board = load(board_path)
    environments = {str(row["match_id"]): row for row in board["selected_environments"]}
    decisions = folder / "lineup_decisions_volume_v4"
    refusals = folder / "lineup_refusals_volume_v4"
    created, waiting, refused = [], [], []
    for candidate in board["candidates"]:
        match_id = str(candidate["match_id"])
        destination = decisions / f"{match_id}.json"
        refusal_path = refusals / f"{match_id}.json"
        if destination.exists() or refusal_path.exists():
            continue
        detail = get_json("https://www.fotmob.com/api/data/matchDetails?" + urllib.parse.urlencode({"matchId": match_id}))
        general = detail.get("general") or {}
        if general.get("started") or general.get("finished"):
            environment = environments[match_id]
            reason = "kickoff_window_missed_already_started_or_finished"
            payload = {
                "status": "volume_v4_prospective_lineup_lock_refused",
                "strategy_id": "volume_v4",
                "refused_utc": datetime.now(timezone.utc).isoformat(),
                "match_id": match_id,
                "date": environment["date"],
                "league": environment["league"],
                "fixture": environment["fixture"],
                "candidate": candidate,
                "reason": reason,
                "official_selection_eligible": False,
                "replacement_policy": "No promotion after the frozen challenger board.",
                "outcome_accessed": False,
            }
            write_once(refusal_path, payload)
            refused.append({"match_id": match_id, "player": candidate["player"], "reason": reason})
            continue
        lineup = (detail.get("content") or {}).get("lineup") or {}
        home = lineup.get("homeTeam") or {}
        starters = {str(row["id"]) for row in home.get("starters") or [] if row.get("id") is not None}
        if lineup.get("lineupType") != "standard" or len(starters) < 11:
            waiting.append(match_id)
            continue
        environment = environments[match_id]
        confirmed = [row for row in environment["plan_B_candidates"] if str(row["player_id"]) in starters]
        confirmed.sort(key=lambda row: (-row["avg_shots"], -row["avg_minutes"], row["player_id"]))
        rank_by_player = {str(row["player_id"]): rank for rank, row in enumerate(confirmed, 1)}
        shooter_rank = rank_by_player.get(str(candidate["player_id"]))
        reasons = []
        if str(candidate["player_id"]) not in starters:
            reasons.append("not_in_confirmed_home_starting_XI")
        if shooter_rank is None or shooter_rank > 2:
            reasons.append("outside_top_two_confirmed_home_shooters")
        if candidate.get("candidate_side") != "home":
            reasons.append("not_home_player")
        if not candidate.get("plan_B"):
            reasons.append("not_plan_b_qualified")
        evaluated = {**candidate, "confirmed_shooter_rank": shooter_rank}
        official = [] if reasons else [{**evaluated, "decision": "official_locked_pick", "target": "3+ total shots"}]
        rejected = [{**evaluated, "decision": "rejected", "reasons": reasons}] if reasons else []
        payload = {
            "status": "volume_v4_confirmed_lineup_decision_locked_before_kickoff",
            "strategy_id": "volume_v4",
            "locked_utc": datetime.now(timezone.utc).isoformat(),
            "match_id": match_id,
            "date": environment["date"],
            "league": environment["league"],
            "fixture": environment["fixture"],
            "lineup_source": lineup.get("source"),
            "lineup_type": lineup.get("lineupType"),
            "confirmed_home_starter_ids": sorted(starters),
            "official_picks": official,
            "rejected_provisional_candidates": rejected,
            "replacement_policy": "No promotion after the frozen challenger board.",
            "outcome_accessed": False,
        }
        write_once(destination, payload)
        created.append({"match_id": match_id, "player": candidate["player"], "decision": "rejected" if reasons else "official_locked_pick", "reasons": reasons})
    result = {"created": created, "waiting_for_confirmed_lineups": waiting, "refused_after_start": refused}
    print(json.dumps(result, indent=2))
    return result


def settle(weekend: str) -> dict:
    folder = BASE / weekend
    source = folder / "lineup_decisions_volume_v4"
    target = folder / "settled_volume_v4"
    newly_settled, waiting = [], []
    for path in sorted(source.glob("*.json")) if source.exists() else []:
        decision = load(path)
        destination = target / path.name
        if destination.exists():
            continue
        detail = get_json("https://www.fotmob.com/api/data/matchDetails?" + urllib.parse.urlencode({"matchId": decision["match_id"]}))
        if not (detail.get("general") or {}).get("finished"):
            waiting.append(decision["match_id"])
            continue
        stats_by_player = (detail.get("content") or {}).get("playerStats") or {}
        outcomes = []
        for pick in decision["official_picks"]:
            stats = stats_by_player.get(str(pick["player_id"])) or {}
            shots = extract_stat(stats, "total_shots")
            minutes = extract_stat(stats, "minutes_played")
            if shots is None and minutes is not None:
                shots = 0
            outcomes.append({**pick, "minutes": minutes, "shots": shots, "hit_3plus": shots >= 3 if shots is not None else None})
        payload = {**decision, "status": "settled", "settled_utc": datetime.now(timezone.utc).isoformat(), "official_picks": outcomes}
        write_once(destination, payload)
        newly_settled.append({"match_id": decision["match_id"], "picks": [(row["player"], row["shots"], row["hit_3plus"]) for row in outcomes]})
    result = {"weekend": weekend, "newly_settled": newly_settled, "waiting": waiting}
    print(json.dumps(result, indent=2))
    return result


def dashboard(weekend: str) -> dict:
    folder = BASE / weekend
    board = load(folder / "frozen_board_volume_v4.json")
    decisions = [load(path) for path in sorted((folder / "lineup_decisions_volume_v4").glob("*.json"))] if (folder / "lineup_decisions_volume_v4").exists() else []
    refusals = [load(path) for path in sorted((folder / "lineup_refusals_volume_v4").glob("*.json"))] if (folder / "lineup_refusals_volume_v4").exists() else []
    settlements = [load(path) for path in sorted((folder / "settled_volume_v4").glob("*.json"))] if (folder / "settled_volume_v4").exists() else []
    official = {str(row["player_id"]) for item in decisions for row in item["official_picks"]}
    rejected = {str(row["player_id"]): row["reasons"] for item in decisions for row in item["rejected_provisional_candidates"]}
    refused = {str(item["candidate"]["player_id"]): item["reason"] for item in refusals}
    outcomes = {str(row["player_id"]): row for item in settlements for row in item["official_picks"]}
    rows = ""
    for candidate in board["candidates"]:
        key = str(candidate["player_id"])
        if key in outcomes:
            status = f"Settled: {outcomes[key]['shots']} shots — {'HIT' if outcomes[key]['hit_3plus'] else 'MISS'}"
        elif key in official:
            status = "Official challenger leg"
        elif key in rejected:
            status = "Rejected: " + ", ".join(rejected[key]).replace("_", " ")
        elif key in refused:
            status = "Prospective lock missed — excluded: " + refused[key].replace("_", " ")
        else:
            status = "Provisional — awaiting confirmed lineup"
        rows += f"<tr><td>{candidate['provisional_rank']}</td><td>{escape(candidate['league'])}</td><td>{escape(candidate['fixture'])}</td><td>{escape(candidate['player'])}</td><td>{candidate['hits_3plus']}/5</td><td>{candidate['avg_shots']:.1f}</td><td>{escape(status)}</td></tr>"
    html = f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Volume v4 Challenger</title><style>body{{font:16px Inter,Segoe UI,sans-serif;background:#07111f;color:#edf3fc;margin:0;padding:28px}}main{{max-width:1100px;margin:auto}}.note{{background:#17243a;border-left:4px solid #ffb84d;padding:15px;margin:20px 0}}table{{width:100%;border-collapse:collapse;background:#101d31}}th,td{{padding:11px;text-align:left;border-bottom:1px solid #293e5e}}th{{color:#8bc4ff}}.muted{{color:#9badc4}}</style></head><body><main><h1>Higher-volume Plan B challenger</h1><p class=muted>Weekend {escape(weekend)} · separate from frozen v3 control</p><div class=note><strong>Prospective paper research only.</strong> Maximum three candidates, maximum two per league and one per fixture. No rejected player is replaced.</div><table><thead><tr><th>Rank</th><th>League</th><th>Fixture</th><th>Player</th><th>Prior 3+</th><th>Avg shots</th><th>Status</th></tr></thead><tbody>{rows or '<tr><td colspan=7>No challenger candidates.</td></tr>'}</tbody></table><p class=muted>Board hash: <code>{sha(folder / 'frozen_board_volume_v4.json')}</code></p></main></body></html>"""
    destination = folder / "volume_v4.html"
    destination.write_text(html, encoding="utf-8")
    result = {"dashboard": str(destination), "provisional": len(board["candidates"]), "official": len(official), "refused": len(refused), "settled": len(outcomes)}
    print(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lineups", "settle", "dashboard"))
    parser.add_argument("--weekend", required=True)
    args = parser.parse_args()
    {"lineups": lineups, "settle": settle, "dashboard": dashboard}[args.mode](args.weekend)


if __name__ == "__main__":
    main()
