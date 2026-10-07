"""Bounded FotMob acquisition for the frozen big-five carryover replay."""
from __future__ import annotations

import gzip
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/big5_2026_prebreak_carryover"
RAW = OUT / "raw"
LEAGUES = {
    "Premier League": (47, "ENG"),
    "LaLiga": (87, "ESP"),
    "Serie A": (55, "ITA"),
    "Bundesliga": (54, "GER"),
    "Ligue 1": (53, "FRA"),
}
SEASONS = ("2025/2026", "2026/2027")
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.fotmob.com/"}


def get_json(url: str, retries: int = 4):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=35) as response:
                return json.load(response)
        except Exception as exc:  # acquisition log records final failures
            last = exc
            time.sleep(1.2 * (attempt + 1))
    raise last


def parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def extract_stat(player: dict, wanted: str):
    for group in player.get("stats") or []:
        for item in (group.get("stats") or {}).values():
            if item.get("key") == wanted:
                return (item.get("stat") or {}).get("value")
    return None


def team_total_shots(detail: dict):
    periods = ((detail.get("content") or {}).get("stats") or {}).get("Periods") or {}
    for group in ((periods.get("All") or {}).get("stats") or []):
        for item in group.get("stats") or []:
            if item.get("key") == "total_shots":
                values = item.get("stats") or []
                if len(values) == 2:
                    return values
    return [None, None]


def normalize(meta: dict, detail: dict):
    general = detail.get("general") or {}
    content = detail.get("content") or {}
    lineup = content.get("lineup") or {}
    player_stats = content.get("playerStats") or {}
    starter_maps = {}
    for side in ("homeTeam", "awayTeam"):
        team = lineup.get(side) or {}
        starter_maps[str(team.get("id"))] = {
            str(p.get("id")): p for p in team.get("starters") or [] if p.get("id") is not None
        }
    totals = team_total_shots(detail)
    teams = [meta["home"], meta["away"]]
    players = []
    for side_index, team in enumerate(teams):
        tid = str(team["id"])
        starters = starter_maps.get(tid, {})
        ids = set(starters)
        ids.update(k for k, p in player_stats.items() if str(p.get("teamId")) == tid)
        for pid in ids:
            stat = player_stats.get(pid) or player_stats.get(str(pid)) or {}
            starter = starters.get(str(pid)) or {}
            minutes = extract_stat(stat, "minutes_played")
            shots = extract_stat(stat, "total_shots")
            if shots is None and minutes is not None:
                shots = 0
            players.append({
                "player_id": str(pid),
                "player": stat.get("name") or starter.get("name") or "unknown",
                "team_id": tid,
                "team": team["name"],
                "home": side_index == 0,
                "started": str(pid) in starters,
                "minutes": minutes,
                "shots": shots,
                "position_id": stat.get("positionId") or starter.get("positionId"),
            })
    status = meta["status"]
    score = status.get("scoreStr") or ""
    score_parts = [x.strip() for x in score.split("-")]
    try:
        home_score, away_score = int(score_parts[0]), int(score_parts[1])
    except Exception:
        home_score = away_score = None
    return {
        "match_id": str(meta["id"]),
        "league": meta["league"],
        "league_id": meta["league_id"],
        "season": meta["season"],
        "date": status["utcTime"],
        "round": meta.get("round"),
        "home_team_id": str(meta["home"]["id"]),
        "home_team": meta["home"]["name"],
        "away_team_id": str(meta["away"]["id"]),
        "away_team": meta["away"]["name"],
        "home_score": home_score,
        "away_score": away_score,
        "home_shots": totals[0],
        "away_shots": totals[1],
        "players": players,
        "coverage_level": general.get("coverageLevel"),
        "lineup_source": lineup.get("source"),
        "source_url": f"https://www.fotmob.com/matches/x/x#{meta['id']}",
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    fixture_sets = []
    league_counts = {}
    for league, (league_id, country) in LEAGUES.items():
        for season in SEASONS:
            cache = RAW / f"league_{league_id}_{season.replace('/', '-')}.json.gz"
            if cache.exists():
                data = json.loads(gzip.decompress(cache.read_bytes()))
            else:
                query = urllib.parse.urlencode({"id": league_id, "ccode3": country, "season": season})
                data = get_json("https://www.fotmob.com/api/data/leagues?" + query)
                cache.write_bytes(gzip.compress(json.dumps(data).encode("utf-8")))
            rows = data["fixtures"]["allMatches"]
            league_counts[f"{league} {season}"] = len(rows)
            for row in rows:
                row = dict(row)
                row.update(league=league, league_id=league_id, season=season)
                fixture_sets.append(row)

    earliest = datetime(2026, 3, 1, tzinfo=timezone.utc)
    latest = datetime(2026, 9, 21, tzinfo=timezone.utc)
    selected = [r for r in fixture_sets if r.get("status", {}).get("finished") and
                earliest <= parse_date(r["status"]["utcTime"]) < latest]
    selected.sort(key=lambda r: (r["status"]["utcTime"], str(r["id"])))
    failures = []

    def fetch(meta):
        cache = RAW / f"match_{meta['id']}.json.gz"
        if cache.exists():
            detail = json.loads(gzip.decompress(cache.read_bytes()))
        else:
            detail = get_json("https://www.fotmob.com/api/data/matchDetails?" +
                              urllib.parse.urlencode({"matchId": meta["id"]}))
            cache.write_bytes(gzip.compress(json.dumps(detail).encode("utf-8")))
            time.sleep(0.08)
        return normalize(meta, detail)

    normalized = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch, row): row for row in selected}
        for number, future in enumerate(as_completed(futures), 1):
            row = futures[future]
            try:
                normalized.append(future.result())
            except Exception as exc:
                failures.append({"match_id": str(row["id"]), "league": row["league"],
                                 "date": row["status"]["utcTime"], "error": repr(exc)})
            if number % 100 == 0:
                print(f"details {number}/{len(selected)}; failures={len(failures)}", flush=True)
    normalized.sort(key=lambda r: (r["date"], r["match_id"]))
    (OUT / "normalized_matches.json").write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    acquisition = {
        "provider": "FotMob public match pages/data",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "finished top-five-league matches from 2026-03-01 through 2026-09-20 UTC",
        "league_fixture_counts": league_counts,
        "selected_match_details": len(selected),
        "normalized_matches": len(normalized),
        "failures": failures,
        "raw_cache": str(RAW),
    }
    (OUT / "acquisition.json").write_text(json.dumps(acquisition, indent=2), encoding="utf-8")
    print(json.dumps(acquisition, indent=2))


if __name__ == "__main__":
    main()
