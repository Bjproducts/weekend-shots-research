"""Frozen A/B replay on the complete 2023/24 Frauen-Bundesliga season."""
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from test_home_pattern import measure, run
from weekly_pattern_replay import RULES, choose, monday
from validate_wsl_ab import RULES_HASH, compare, fmt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/frauen_bundesliga_2023_24_ab_validation"
PLAN_PATH = ROOT / "work/frauen_bundesliga_2023_24_ab_plan.json"


def main():
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    assert plan["rules_sha256"] == RULES_HASH
    records = json.loads((OUT / "normalized_matches.json").read_text(encoding="utf-8"))
    fixture_ids = [r["fixture"]["id"] for r in records]
    teams = {t["id"]: t["name"] for r in records for t in (r["fixture"]["home_team"], r["fixture"]["away_team"])}
    home_counts = Counter(r["fixture"]["home_team"]["id"] for r in records)
    away_counts = Counter(r["fixture"]["away_team"]["id"] for r in records)
    sample_keys = [(r["fixture"]["id"], p["player"]["id"]) for r in records for p in r["players"]]
    assert len(records) == len(set(fixture_ids)) == 132 and len(teams) == 12
    assert set(home_counts.values()) == {11} and set(away_counts.values()) == {11}
    assert len(sample_keys) == len(set(sample_keys)) == 4056
    old = json.loads((ROOT / "outputs/winning_pattern_research.json").read_text(encoding="utf-8"))
    prior_ids = {r["fixture_id"] for r in old["rows"] if r["provider"] == "statsbomb"}
    prior_ids.update(r["fixture"]["id"] for r in json.loads((ROOT / "outputs/wsl_2023_24_ab_validation/normalized_matches.json").read_text()))
    assert not prior_ids.intersection(fixture_ids)

    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""CREATE TABLE competitions(id INTEGER,name TEXT,is_competitive INTEGER);
        CREATE TABLE teams(id INTEGER PRIMARY KEY,name TEXT);
        CREATE TABLE players(id INTEGER PRIMARY KEY,common_name TEXT,full_name TEXT);
        CREATE TABLE fixtures(id INTEGER,fixture_date TEXT,competition_id INTEGER,season_id INTEGER,home_team_id INTEGER,away_team_id INTEGER,home_score INTEGER,away_score INTEGER,status TEXT);
        CREATE TABLE player_fixture_stats(fixture_id INTEGER,player_id INTEGER,team_id INTEGER,opponent_id INTEGER,home INTEGER,started INTEGER,minutes_played REAL,shots INTEGER,team_shots INTEGER,data_source TEXT);
        INSERT INTO competitions VALUES(135,'Frauen-Bundesliga',1);""")
    for rec in records:
        f = rec["fixture"]
        for team in (f["home_team"], f["away_team"]):
            db.execute("INSERT OR IGNORE INTO teams VALUES(?,?)", (team["id"], team["name"]))
        db.execute("INSERT INTO fixtures VALUES(?,?,?,?,?,?,?,?,?)", (f["id"], f["date"], 135, 281,
            f["home_team"]["id"], f["away_team"]["id"], f["home_score"], f["away_score"], "finished"))
        for p in rec["players"]:
            q = p["player"]
            db.execute("INSERT OR IGNORE INTO players VALUES(?,?,?)", (q["id"], q["common_name"], q["full_name"]))
            db.execute("INSERT INTO player_fixture_stats VALUES(?,?,?,?,?,?,?,?,?,?)", (f["id"], q["id"], p["team_id"],
                p["opponent_id"], p["home"], p["started"], p["minutes_played"], p["shots"], p["team_shots"], "statsbomb"))
    replay = run(connection=db, provider="statsbomb", save=False)
    replay["source"] = "StatsBomb Frauen-Bundesliga 2023/24: complete 132-match season"
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
            row = {"fixture_id": f["id"], "player_id": p["player"]["id"], "date": f["date"], "round": f["round"],
                "fixture": f['home_team']['name'] + " vs " + f['away_team']['name'],
                "player": p["player"]["common_name"] or p["player"]["full_name"], "home": p["home"],
                "started": p["started"], "shots": p["shots"], "hit": p["shots"] >= 2 if p["shots"] is not None else None,
                "A": a, "B": b, "features": ft, "exclusion_reasons": reasons}
            samples.append(row)
            if a: picks.append(row)

    summary = compare(picks)
    b_counts = Counter(r["player_id"] for r in picks if r["B"])
    top3 = {pid for pid, _ in b_counts.most_common(3)}
    concentration = compare([r for r in picks if r["player_id"] not in top3])
    halves = {"rounds_1_to_11": compare([r for r in picks if r["round"] <= 11]),
              "rounds_12_to_22": compare([r for r in picks if r["round"] >= 12])}
    weeks = []
    day = datetime.fromisoformat(monday(records[0]["fixture"]["date"]))
    end = datetime.fromisoformat(monday(records[-1]["fixture"]["date"]))
    while day <= end:
        key = day.date().isoformat()
        rows = [r for r in picks if monday(r["date"]) == key]
        weeks.append({"week": key, "A": measure(rows), "B": measure([r for r in rows if r["B"]])})
        day += timedelta(days=7)
    top_players = [{"player": next(r["player"] for r in picks if r["player_id"] == pid), "picks": n}
                   for pid, n in b_counts.most_common(3)]
    result = {"dataset": "Frauen-Bundesliga 2023/24", "scope": "external cross-population stress test 2",
        "provider": "StatsBomb Open Data", "matches": 132, "teams": 12, "player_samples": len(samples),
        "eligible_fixtures": len(eligible), "rules": RULES, "plan": plan,
        "plan_sha256": hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest(), "baseline_rules_sha256": RULES_HASH,
        "comparison": summary, "round_split_descriptive_only": halves,
        "without_three_most_selected_B_players": concentration, "top_three_B_players": top_players,
        "limits": [
            "Women's football is a different population; this is not direct proof of a men's MLS betting rate.",
            "Historical replay, not a prospective trial; actual starters are assumed known at lineup time.",
            "Same 2023/24 era and StatsBomb provider family as the WSL test, so the two modern stress tests are not fully independent.",
            "The 132 matches are unused and non-overlapping with all earlier project evaluation matches.",
            "Historical publication timing and published kickoff timezone are not certified; replay uses the same >24-hour cutoff.",
            "No odds or profitability test; weekly bootstrap does not remove all player/team dependence; no retuning.",
        ]}
    for name, obj in (("ab_results", result), ("all_samples", samples), ("qualifying_picks", picks),
                      ("weekly_results", weeks), ("feature_replay", replay), ("frozen_test_plan", plan)):
        (OUT / f"{name}.json").write_text(json.dumps(obj, indent=2), encoding="utf-8")

    report = ["# Frozen A/B stress test — Frauen-Bundesliga 2023/24", "",
        "Source: [StatsBomb Open Data](https://github.com/statsbomb/open-data). Complete 132-match season selected and plan frozen before player-event acquisition.", "",
        "A is the original rule. B is A plus previous-five-start averages of at least 3 shots and 80 minutes. No threshold changed.", "",
        "| Check | A: original | B: challenger | B retention |", "|---|---:|---:|---:|",
        f"| Full season | {fmt(summary['A'])} | {fmt(summary['B'])} | {summary['retained_pct']}% |",
        f"| Rounds 1–11 | {fmt(halves['rounds_1_to_11']['A'])} | {fmt(halves['rounds_1_to_11']['B'])} | {halves['rounds_1_to_11']['retained_pct']}% |",
        f"| Rounds 12–22 | {fmt(halves['rounds_12_to_22']['A'])} | {fmt(halves['rounds_12_to_22']['B'])} | {halves['rounds_12_to_22']['retained_pct']}% |",
        f"| Excluding three most-selected B players | {fmt(concentration['A'])} | {fmt(concentration['B'])} | {concentration['retained_pct']}% |", "",
        f"B minus A: {summary['rate_difference_pp']} points. Paired-week bootstrap 95% interval: {summary['paired_week_bootstrap_interval95']}. A picks rejected by B: {fmt(summary['excluded'])}.", "",
        f"Saved all {len(samples):,} appearances, {len(picks)} A picks and every B decision; {len(eligible)} fixtures had sufficient team history.", "",
        "## Interpretation", "", "Pattern A remained reasonably strong, but Pattern B did not generalise: it retained only five picks, hit three, and removed 14 picks that hit 12 times. This is negative evidence against promoting B over A. It is still a small sample, so it does not prove B is universally harmful.", "", "This is a separate complete league stress test. It tests whether the mechanism travels, but it is not direct men's MLS validation and shares era/provider with the WSL test.", "", "## Limits", ""] + ["- " + x for x in result["limits"]]
    (OUT / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    picks_html = "".join(f'<tr><td>{r["date"][:10]}</td><td>{escape(r["fixture"])}</td><td>{escape(r["player"])}</td><td>{"A + B" if r["B"] else "A only"}</td><td>{r["shots"]}</td><td>{"HIT" if r["hit"] else "MISS"}</td></tr>' for r in picks)
    html = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Frauen-Bundesliga frozen A/B test</title><style>body{{font:16px/1.6 system-ui;max-width:1150px;margin:30px auto;padding:0 20px;background:#f2f5f8;color:#182b3e}}.scroll{{overflow:auto}}table{{border-collapse:collapse;background:white;width:100%}}td,th{{padding:12px;border-bottom:1px solid #ddd;text-align:left}}a{{color:#216e83}}</style><h1>Frozen A/B stress test: Frauen-Bundesliga 2023/24</h1><p>Complete 132-match season; {len(samples):,} appearances. Source: <a href="https://github.com/statsbomb/open-data">StatsBomb Open Data</a>.</p><table><tr><th>Rule</th><th>Result</th></tr><tr><td>A: original</td><td>{fmt(summary['A'])}</td></tr><tr><td>B: ≥3 prior shots + ≥80 prior minutes</td><td>{fmt(summary['B'])}</td></tr><tr><td>A picks excluded by B</td><td>{fmt(summary['excluded'])}</td></tr></table><p>B retained {summary['retained_pct']}% of A picks. B-minus-A: {summary['rate_difference_pp']} points; paired-week interval {summary['paired_week_bootstrap_interval95']}.</p><p><b>Scope:</b> unused complete league, but women's cross-population evidence—not direct men's MLS proof or a profit estimate.</p><p><a href="report.md">Report</a> · <a href="all_samples.json">Every sample</a> · <a href="ab_results.json">Results JSON</a> · <a href="../frauen_bundesliga_2023_24_ab_validation.zip">Archive</a></p><h2>Every A pick</h2><div class="scroll"><table><tr><th>Date</th><th>Fixture</th><th>Player</th><th>Rule</th><th>Shots</th><th>Outcome</th></tr>{picks_html}</table></div></html>'''
    (OUT / "index.html").write_text(html, encoding="utf-8")
    with ZipFile(OUT.parent / "frauen_bundesliga_2023_24_ab_validation.zip", "w", ZIP_DEFLATED) as archive:
        for path in sorted(OUT.rglob("*")):
            if path.is_file(): archive.write(path, path.relative_to(OUT))
    dashboard = OUT.parent / "project_site/dist/index.html"
    text = dashboard.read_text(encoding="utf-8")
    start, end_marker = "<!-- FRAUEN_AB_START -->", "<!-- FRAUEN_AB_END -->"
    if start in text:
        before, tail = text.split(start, 1); text = before + tail.split(end_marker, 1)[1]
    panel = f'''{start}<section id="frauen-ab" class="panel" style="margin:24px 0"><div class="eyebrow">NEW · THIRD FROZEN TEST</div><h2>Frauen-Bundesliga 2023/24 — complete 132-match season</h2><p>Original A: {fmt(summary['A'])}. Challenger B: {fmt(summary['B'])}. B retained {summary['retained_pct']}% of A picks. No retuning; every sample saved.</p><p class="note"><b>Scope:</b> separate complete league, but another women's cross-population test using the same provider/era—not direct men's MLS proof.</p><p><a href="../../frauen_bundesliga_2023_24_ab_validation/index.html">View results and every pick</a></p></section>{end_marker}'''
    dashboard.write_text(text.replace("</header>", "</header>" + panel, 1), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
