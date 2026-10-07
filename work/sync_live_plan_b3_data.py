"""Acquire bounded FotMob history for the four-league live Plan B 3+ workflow."""
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
SPEC_PATH = ROOT / "work/live_plan_b3_spec.json"
BASE = ROOT / "outputs/live_plan_b3"
REUSE_RAW = [ROOT / "outputs/big5_2026_prebreak_carryover/raw"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weekend", required=True)
    args = parser.parse_args()
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    weekend = datetime.fromisoformat(args.weekend).replace(tzinfo=timezone.utc)
    earliest = weekend - timedelta(days=180)
    latest = weekend - timedelta(days=1)
    out = BASE / args.weekend
    raw = out / "history_raw"
    raw.mkdir(parents=True, exist_ok=True)

    fixture_rows = []
    league_counts = {}
    for league, config in spec["leagues"].items():
        for season in config["history_seasons"]:
            cache = raw / f"league_{config['fotmob_id']}_{season.replace('/', '-')}.json.gz"
            if cache.exists():
                data = json.loads(gzip.decompress(cache.read_bytes()))
            else:
                query = urllib.parse.urlencode(
                    {
                        "id": config["fotmob_id"],
                        "ccode3": config["country"],
                        "season": season,
                    }
                )
                data = get_json("https://www.fotmob.com/api/data/leagues?" + query)
                cache.write_bytes(gzip.compress(json.dumps(data).encode("utf-8")))
            rows = data["fixtures"]["allMatches"]
            league_counts[f"{league} {season}"] = len(rows)
            for row in rows:
                row = dict(row)
                row.update(
                    league=league,
                    league_id=config["fotmob_id"],
                    season=season,
                )
                fixture_rows.append(row)

    selected = []
    seen = set()
    for row in fixture_rows:
        match_id = str(row["id"])
        date = parse_date(row["status"]["utcTime"])
        if (
            match_id not in seen
            and row.get("status", {}).get("finished")
            and earliest <= date < latest
        ):
            selected.append(row)
            seen.add(match_id)
    selected.sort(key=lambda row: (row["status"]["utcTime"], str(row["id"])))

    def fetch(meta: dict) -> dict:
        cache = raw / f"match_{meta['id']}.json.gz"
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
    with ThreadPoolExecutor(max_workers=4) as pool:
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
                print(
                    f"details {number}/{len(selected)}; failures={len(failures)}",
                    flush=True,
                )

    normalized.sort(key=lambda row: (row["date"], row["match_id"]))
    (out / "history_matches.json").write_text(
        json.dumps(normalized, indent=2), encoding="utf-8"
    )
    acquisition = {
        "provider": "FotMob public match pages/data",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "weekend": args.weekend,
        "history_start_utc": earliest.isoformat(),
        "history_end_exclusive_utc": latest.isoformat(),
        "league_fixture_counts": league_counts,
        "selected_match_details": len(selected),
        "normalized_matches": len(normalized),
        "failures": failures,
        "raw_cache": str(raw),
    }
    (out / "acquisition.json").write_text(
        json.dumps(acquisition, indent=2), encoding="utf-8"
    )
    print(json.dumps(acquisition, indent=2))


if __name__ == "__main__":
    main()
