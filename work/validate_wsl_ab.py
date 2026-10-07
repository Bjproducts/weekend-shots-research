"""Frozen A/B replay on the complete 2023/24 Women's Super League season."""
import hashlib
import json
import random
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from statistics import mean
from zipfile import ZIP_DEFLATED, ZipFile

from test_home_pattern import measure, run
from weekly_pattern_replay import RULES, choose, monday

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/wsl_2023_24_ab_validation"
PLAN_PATH = ROOT / "work/wsl_2023_24_ab_plan.json"
RULES_HASH = hashlib.sha256(json.dumps(RULES, sort_keys=True).encode()).hexdigest()


def compare(picks):
    a = measure(picks)
    b_rows = [r for r in picks if r["B"]]
    b = measure(b_rows)
    groups = defaultdict(list)
    for row in picks:
        groups[monday(row["date"])].append(row)
    weeks = sorted(groups)
    rng = random.Random(28092026)
    deltas = []
    for _ in range(5000):
        sampled = [r for w in rng.choices(weeks, k=len(weeks)) for r in groups[w]] if weeks else []
        filtered = [r for r in sampled if r["B"]]
        if sampled and filtered:
            deltas.append(100 * (mean(r["hit"] for r in filtered) - mean(r["hit"] for r in sampled)))
    deltas.sort()
    return {
        "A": a,
        "B": b,
        "excluded": measure([r for r in picks if not r["B"]]),
        "retained_pct": round(100 * b["n"] / a["n"], 1) if a["n"] else None,
        "rate_difference_pp": round(b["rate"] - a["rate"], 1) if b["rate"] is not None and a["rate"] is not None else None,
        "paired_week_bootstrap_interval95": [round(deltas[int(len(deltas) * p)], 2) for p in (.025, .975)] if deltas else None,
        "bootstrap_valid_replicates": len(deltas),
        "active_weeks": len(weeks),
    }


def fmt(metric):
    return f'{metric["hits"]}/{metric["n"]} ({metric["rate"]}%)' if metric["n"] else "No picks"


def main():
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    assert plan["rules_sha256"] == RULES_HASH
    records = json.loads((OUT / "normalized_matches.json").read_text(encoding="utf-8"))
    assert len(records) == 132
    fixture_ids = [r["fixture"]["id"] for r in records]
    assert len(set(fixture_ids)) == 132
    teams = {t["id"]: t["name"] for rec in records for t in (rec["fixture"]["home_team"], rec["fixture"]["away_team"])}
    assert len(teams) == 12
    home_counts = Counter(r["fixture"]["home_team"]["id"] for r in records)
    away_counts = Counter(r["fixture"]["away_team"]["id"] for r in records)
    assert set(home_counts.values()) == {11} and set(away_counts.values()) == {11}
    sample_keys = [(r["fixture"]["id"], p["player"]["id"]) for r in records for p in r["players"]]
    assert len(sample_keys) == len(set(sample_keys)) == 3984
    old = json.loads((ROOT / "outputs/winning_pattern_research.json").read_text(encoding="utf-8"))
    old_statsbomb = {r["fixture_id"] for r in old["rows"] if r["provider"] == "statsbomb"}
    assert not old_statsbomb.intersection(fixture_ids)

    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""CREATE TABLE competitions(id INTEGER,name TEXT,is_competitive INTEGER);
        CREATE TABLE teams(id INTEGER PRIMARY KEY,name TEXT);
        CREATE TABLE players(id INTEGER PRIMARY KEY,common_name TEXT,full_name TEXT);
        CREATE TABLE fixtures(id INTEGER,fixture_date TEXT,competition_id INTEGER,season_id INTEGER,home_team_id INTEGER,away_team_id INTEGER,home_score INTEGER,away_score INTEGER,status TEXT);
        CREATE TABLE player_fixture_stats(fixture_id INTEGER,player_id INTEGER,team_id INTEGER,opponent_id INTEGER,home INTEGER,started INTEGER,minutes_played REAL,shots INTEGER,team_shots INTEGER,data_source TEXT);
        INSERT INTO competitions VALUES(37,'FA Women''s Super League',1);""")
    for rec in records:
        f = rec["fixture"]
        for team in (f["home_team"], f["away_team"]):
            db.execute("INSERT OR IGNORE INTO teams VALUES(?,?)", (team["id"], team["name"]))
        db.execute("INSERT INTO fixtures VALUES(?,?,?,?,?,?,?,?,?)", (f["id"], f["date"], 37, 281,
            f["home_team"]["id"], f["away_team"]["id"], f["home_score"], f["away_score"], "finished"))
        for p in rec["players"]:
            q = p["player"]
            db.execute("INSERT OR IGNORE INTO players VALUES(?,?,?)", (q["id"], q["common_name"], q["full_name"]))
            db.execute("INSERT INTO player_fixture_stats VALUES(?,?,?,?,?,?,?,?,?,?)", (f["id"], q["id"], p["team_id"],
                p["opponent_id"], p["home"], p["started"], p["minutes_played"], p["shots"], p["team_shots"], "statsbomb"))
    replay = run(connection=db, provider="statsbomb", save=False)
    replay["source"] = "StatsBomb FA Women's Super League 2023/24: complete 132-match season"
    features = {(r["fixture_id"], r["player_id"]): r for r in replay["rows"]}
    eligible = {r["fixture_id"] for r in replay["environments"]}

    samples, picks = [], []
    for rec in records:
        f = rec["fixture"]
        for p in rec["players"]:
            ft = features.get((f["id"], p["player"]["id"]))
            a = b = False
            reasons = []
            if not p["home"]: reasons.append("away_player")
            if not p["started"]: reasons.append("not_starter")
            if f["id"] not in eligible: reasons.append("insufficient_team_history")
            elif p["home"] and p["started"] and ft is None: reasons.append("insufficient_player_history")
            if ft:
                a = choose({k: ft[k] for k in ("shooter_rank", "recent_minutes", "recent_hits", "environment")})["full_pattern"]
                b = a and ft["recent_shots"] >= 3 and ft["recent_minutes"] >= 80
                if not a: reasons.append("baseline_conditions_not_met")
                elif not b: reasons.append("challenger_extra_conditions_not_met")
            name = p["player"]["common_name"] or p["player"]["full_name"]
            row = {"fixture_id": f["id"], "player_id": p["player"]["id"], "date": f["date"], "round": f["round"],
                "fixture": f['home_team']['name'] + " vs " + f['away_team']['name'], "player": name, "home": p["home"],
                "started": p["started"], "shots": p["shots"], "hit": p["shots"] >= 2 if p["shots"] is not None else None,
                "A": a, "B": b, "features": ft, "exclusion_reasons": reasons}
            samples.append(row)
            if a: picks.append(row)

    summary = compare(picks)
    b_counts = Counter(r["player_id"] for r in picks if r["B"])
    top3 = {pid for pid, _ in b_counts.most_common(3)}
    concentration = compare([r for r in picks if r["player_id"] not in top3])
    split_round = 12
    halves = {
        "rounds_1_to_11": compare([r for r in picks if r["round"] <= 11]),
        "rounds_12_to_22": compare([r for r in picks if r["round"] >= split_round]),
    }
    weeks = []
    first = datetime.fromisoformat(monday(records[0]["fixture"]["date"]))
    last = datetime.fromisoformat(monday(records[-1]["fixture"]["date"]))
    while first <= last:
        key = first.date().isoformat()
        rows = [r for r in picks if monday(r["date"]) == key]
        weeks.append({"week": key, "A": measure(rows), "B": measure([r for r in rows if r["B"]])})
        first += timedelta(days=7)
    top_players = [{"player": next(r["player"] for r in picks if r["player_id"] == pid), "picks": n}
                   for pid, n in b_counts.most_common(3)]
    result = {
        "dataset": "FA Women's Super League 2023/24", "scope": "external cross-population stress test",
        "provider": "StatsBomb Open Data", "matches": 132, "teams": 12, "player_samples": len(samples),
        "eligible_fixtures": len(eligible), "rules": RULES, "plan": plan,
        "plan_sha256": hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest(), "baseline_rules_sha256": RULES_HASH,
        "comparison": summary, "round_split_descriptive_only": halves,
        "without_three_most_selected_B_players": concentration, "top_three_B_players": top_players,
        "limits": [
            "This is women's football: it is an external mechanism/portability stress test, not direct proof of a men's MLS betting rate.",
            "Historical replay, not a prospective trial; actual starters are assumed known at lineup time.",
            "Same StatsBomb provider as prior European research, although the 132 matches are unused and non-overlapping.",
            "The >24-hour history buffer is conservative; historical publication timing and kickoff timezone publication are not certified.",
            "StatsBomb shot and minutes definitions follow the saved adapter; no odds or profitability test was performed.",
            "The paired-week bootstrap does not remove all persistent player/team dependence. No threshold was changed after outcomes.",
        ],
    }
    for name, obj in (("ab_results", result), ("all_samples", samples), ("qualifying_picks", picks),
                      ("weekly_results", weeks), ("feature_replay", replay), ("frozen_test_plan", plan)):
        (OUT / f"{name}.json").write_text(json.dumps(obj, indent=2), encoding="utf-8")

    report = ["# Frozen A/B stress test — FA Women's Super League 2023/24", "",
        "Source: [StatsBomb Open Data](https://github.com/statsbomb/open-data). Complete 132-match season selected and the plan frozen before player outcomes were replayed.", "",
        "A is the original environment-first rule. B is A plus previous-five-start averages of at least 3 shots and 80 minutes. Neither rule was changed.", "",
        "| Check | A: original | B: challenger | B retention |", "|---|---:|---:|---:|",
        f"| Full season | {fmt(summary['A'])} | {fmt(summary['B'])} | {summary['retained_pct']}% |",
        f"| Rounds 1–11 | {fmt(halves['rounds_1_to_11']['A'])} | {fmt(halves['rounds_1_to_11']['B'])} | {halves['rounds_1_to_11']['retained_pct']}% |",
        f"| Rounds 12–22 | {fmt(halves['rounds_12_to_22']['A'])} | {fmt(halves['rounds_12_to_22']['B'])} | {halves['rounds_12_to_22']['retained_pct']}% |",
        f"| Excluding three most-selected B players | {fmt(concentration['A'])} | {fmt(concentration['B'])} | {concentration['retained_pct']}% |", "",
        f"B minus A was {summary['rate_difference_pp']} percentage points. Paired-week bootstrap 95% interval: {summary['paired_week_bootstrap_interval95']}. A picks rejected by B: {fmt(summary['excluded'])}.", "",
        f"Saved all {len(samples):,} player appearances, {len(picks)} A picks and every B decision. {len(eligible)} fixtures had sufficient team history.", "",
        "## Interpretation", "",
        "This is another independent dataset and a useful test of whether the mechanism travels, but it is not direct confirmation for men's MLS because the population differs. Treat the result as stress-test evidence, not a guaranteed future rate.", "",
        "## Limits", ""] + ["- " + item for item in result["limits"]]
    (OUT / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    rows_html = "".join(f'<tr><td>{r["date"][:10]}</td><td>{escape(r["fixture"])}</td><td>{escape(r["player"])}</td><td>{"A + B" if r["B"] else "A only"}</td><td>{r["shots"]}</td><td>{"HIT" if r["hit"] else "MISS"}</td></tr>' for r in picks)
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>WSL frozen A/B stress test</title><style>body{{font:16px/1.6 system-ui;max-width:1150px;margin:30px auto;padding:0 20px;background:#f2f5f8;color:#182b3e}}.scroll{{overflow:auto}}table{{border-collapse:collapse;background:white;width:100%}}td,th{{padding:12px;border-bottom:1px solid #ddd;text-align:left}}a{{color:#216e83}}</style><h1>Frozen A/B stress test: WSL 2023/24</h1><p>Complete 132-match season; {len(samples):,} appearances. Source: <a href="https://github.com/statsbomb/open-data">StatsBomb Open Data</a>.</p><table><tr><th>Rule</th><th>Result</th></tr><tr><td>A: original</td><td>{fmt(summary['A'])}</td></tr><tr><td>B: ≥3 prior shots + ≥80 prior minutes</td><td>{fmt(summary['B'])}</td></tr><tr><td>A picks excluded by B</td><td>{fmt(summary['excluded'])}</td></tr></table><p>B retained {summary['retained_pct']}% of A picks. B-minus-A: {summary['rate_difference_pp']} points; paired-week interval {summary['paired_week_bootstrap_interval95']}.</p><p><b>Scope:</b> independent cross-population stress test, not direct proof for men's MLS and not a profit estimate.</p><p><a href="report.md">Report and caveats</a> · <a href="all_samples.json">Every sample</a> · <a href="ab_results.json">Results JSON</a> · <a href="../wsl_2023_24_ab_validation.zip">Archive</a></p><h2>Every A pick</h2><div class="scroll"><table><tr><th>Date</th><th>Fixture</th><th>Player</th><th>Rule</th><th>Shots</th><th>Outcome</th></tr>{rows_html}</table></div></html>'''
    (OUT / "index.html").write_text(page, encoding="utf-8")
    with ZipFile(OUT.parent / "wsl_2023_24_ab_validation.zip", "w", ZIP_DEFLATED) as archive:
        for path in sorted(OUT.rglob("*")):
            if path.is_file(): archive.write(path, path.relative_to(OUT))

    dashboard = OUT.parent / "project_site/dist/index.html"
    text = dashboard.read_text(encoding="utf-8")
    start, end = "<!-- WSL_AB_START -->", "<!-- WSL_AB_END -->"
    if start in text:
        before, tail = text.split(start, 1)
        text = before + tail.split(end, 1)[1]
    panel = f'''{start}<section id="wsl-ab" class="panel" style="margin:24px 0"><div class="eyebrow">NEW · FROZEN EXTERNAL STRESS TEST</div><h2>WSL 2023/24 — complete 132-match season</h2><p>Original A: {fmt(summary['A'])}. Challenger B: {fmt(summary['B'])}. B retained {summary['retained_pct']}% of A picks. Rules were frozen before replay and every sample is saved.</p><p class="note"><b>Scope:</b> this tests portability in a different football population. It is not direct proof of the men's MLS rate or profitability.</p><p><a href="../../wsl_2023_24_ab_validation/index.html">View results and every pick</a></p></section>{end}'''
    dashboard.write_text(text.replace("</header>", "</header>" + panel, 1), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
