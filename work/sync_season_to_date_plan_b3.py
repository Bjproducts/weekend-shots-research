"""Acquire the bounded source data for the four-league season-to-date replay."""
from __future__ import annotations

import argparse
import gzip
import json
import shutil
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

from download_fotmob_big5_carryover import get_json, normalize, parse_date

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/season_to_date_plan_b3"
RAW = OUT / "raw"
SPEC_PATH = ROOT / "work/season_to_date_plan_b3_spec.json"
REUSE_RAW = (
    ROOT / "outputs/live_plan_b3/2026-10-10/history_raw",
    ROOT / "outputs/big5_2026_prebreak_carryover/raw",
)


def weekend_anchor(value: datetime) -> str | None:
    if value.weekday() == 5:
        return value.date().isoformat()
    if value.weekday() == 6:
        return (value - timedelta(days=1)).date().isoformat()
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    end = parse_date(spec["scope"]["end_exclusive_utc"])
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    all_fixtures = []
    catalog_counts = {}
    current_targets = []
    earliest_by_league = {}

    for league, config in spec["scope"]["leagues"].items():
        for season in config["history_seasons"]:
            cache = RAW / f"league_{config['fotmob_id']}_{season.replace('/', '-')}.json.gz"
            if cache.exists():
                data = json.loads(gzip.decompress(cache.read_bytes()))
            else:
                query = urllib.parse.urlencode(
                    {"id": config["fotmob_id"], "ccode3": config["country"], "season": season}
                )
                data = get_json("https://www.fotmob.com/api/data/leagues?" + query)
                cache.write_bytes(gzip.compress(json.dumps(data).encode("utf-8")))
            rows = data["fixtures"]["allMatches"]
            catalog_counts[f"{league} {season}"] = len(rows)
            for source in rows:
                row = dict(source)
                row.update(league=league, league_id=config["fotmob_id"], season=season)
                all_fixtures.append(row)
                date = parse_date(row["status"]["utcTime"])
                if (
                    season == config["current_season"]
                    and row.get("status", {}).get("finished")
                    and date < end
                    and weekend_anchor(date)
                ):
                    current_targets.append(row)
        league_targets = [parse_date(row["status"]["utcTime"]) for row in current_targets if row["league"] == league]
        if league_targets:
            earliest_by_league[league] = min(league_targets) - timedelta(days=180)

    selected = []
    seen = set()
    for row in all_fixtures:
        match_id = str(row["id"])
        date = parse_date(row["status"]["utcTime"])
        if (
            match_id not in seen
            and row.get("status", {}).get("finished")
            and row["league"] in earliest_by_league
            and earliest_by_league[row["league"]] <= date < end
        ):
            selected.append(row)
            seen.add(match_id)
    selected.sort(key=lambda row: (row["status"]["utcTime"], str(row["id"])))

    def fetch(meta: dict) -> dict:
        cache = RAW / f"match_{meta['id']}.json.gz"
        if not cache.exists():
            for source in REUSE_RAW:
                prior = source / cache.name
                if prior.exists():
                    shutil.copy2(prior, cache)
                    break
        if cache.exists():
            detail = json.loads(gzip.decompress(cache.read_bytes()))
        else:
            query = urllib.parse.urlencode({"matchId": meta["id"]})
            detail = get_json("https://www.fotmob.com/api/data/matchDetails?" + query)
            cache.write_bytes(gzip.compress(json.dumps(detail).encode("utf-8")))
            time.sleep(0.05)
        return normalize(meta, detail)

    normalized = []
    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(fetch, row): row for row in selected}
        for number, future in enumerate(as_completed(futures), 1):
            row = futures[future]
            try:
                normalized.append(future.result())
            except Exception as exc:
                failures.append(
                    {
                        "match_id": str(row["id"]),
                        "league": row["league"],
                        "date": row["status"]["utcTime"],
                        "error": repr(exc),
                    }
                )
            if number % 100 == 0:
                print(f"details {number}/{len(selected)}; failures={len(failures)}", flush=True)

    normalized.sort(key=lambda row: (row["date"], row["match_id"]))
    (OUT / "matches.json").write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    target_catalog = []
    for row in sorted(current_targets, key=lambda item: (item["status"]["utcTime"], str(item["id"]))):
        date = parse_date(row["status"]["utcTime"])
        target_catalog.append(
            {
                "match_id": str(row["id"]),
                "date": row["status"]["utcTime"],
                "weekend": weekend_anchor(date),
                "league": row["league"],
                "league_id": row["league_id"],
                "season": row["season"],
                "home_team_id": str(row["home"]["id"]),
                "home_team": row["home"]["name"],
                "away_team_id": str(row["away"]["id"]),
                "away_team": row["away"]["name"],
            }
        )
    (OUT / "target_fixtures.json").write_text(json.dumps(target_catalog, indent=2), encoding="utf-8")
    acquisition = {
        "provider": "FotMob public match pages/data",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "spec_version": spec["version"],
        "end_exclusive_utc": spec["scope"]["end_exclusive_utc"],
        "catalog_counts": catalog_counts,
        "earliest_history_by_league": {key: value.isoformat() for key, value in earliest_by_league.items()},
        "target_weekend_fixtures": len(target_catalog),
        "selected_match_details": len(selected),
        "normalized_matches": len(normalized),
        "failures": failures,
        "raw_cache": str(RAW),
    }
    (OUT / "acquisition.json").write_text(json.dumps(acquisition, indent=2), encoding="utf-8")
    print(json.dumps(acquisition, indent=2))


if __name__ == "__main__":
    main()
