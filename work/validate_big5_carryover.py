"""Frozen early-season big-five replay using previous-season carryover."""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from statistics import mean
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/big5_2026_prebreak_carryover"
PLAN_PATH = ROOT / "work/big5_carryover_plan.json"
TARGET_DATES = {"2026-08-29", "2026-08-30", "2026-09-05", "2026-09-06",
                "2026-09-12", "2026-09-13", "2026-09-19", "2026-09-20"}
CURRENT_SEASON = "2026/2027"
PREVIOUS_SEASON = "2025/2026"
WEEK_STARTS = ["2026-08-29", "2026-09-05", "2026-09-12", "2026-09-19"]


def dt(value): return datetime.fromisoformat(value.replace("Z", "+00:00"))
def avg(rows, key):
    vals = [r[key] for r in rows if r.get(key) is not None]
    return mean(vals) if vals else None


def measure(rows):
    known = [r for r in rows if r.get("hit") is not None]
    wins = sum(bool(r["hit"]) for r in known)
    n = len(known)
    if not n:
        return {"hits": 0, "picks": 0, "rate": None, "misses": 0}
    p, z = wins / n, 1.96
    center = (p + z*z/(2*n))/(1+z*z/n)
    half = z*((p*(1-p)/n+z*z/(4*n*n))**.5)/(1+z*z/n)
    return {"hits": wins, "picks": n, "misses": n-wins, "rate": round(100*p, 1),
            "wilson95": [round(100*(center-half), 1), round(100*(center+half), 1)]}


def rollover(rows, odds, stake=10):
    ordered = sorted(rows, key=lambda r: (r["date"], r["match_id"], r["player_id"]))
    cycles, legs, balance, wins = [], [], float(stake), 0
    for r in ordered:
        legs.append({k: r[k] for k in ("date", "league", "fixture", "player", "shots", "hit")})
        if r["hit"]:
            wins += 1; balance *= odds
        else:
            cycles.append({"wins": wins, "peak_before_loss": round(balance, 2), "ended_by_loss": True, "legs": legs})
            legs, balance, wins = [], float(stake), 0
    if legs:
        cycles.append({"wins": wins, "ending_balance": round(balance, 2), "ended_by_loss": False, "legs": legs})
    return {"formula": f"${stake} * {odds}^consecutive_wins", "sequence": "".join("W" if r["hit"] else "L" for r in ordered),
            "cycles": cycles, "max_consecutive_wins": max((c["wins"] for c in cycles), default=0),
            "maximum_balance_reached": round(stake * odds**max((c["wins"] for c in cycles), default=0), 2),
            "note": "A loss after an all-in winning streak reduces that cycle to $0; simultaneous picks are ordered only for this mathematical diagnostic."}


def make_team_row(match, team_id):
    home = team_id == match["home_team_id"]
    own_score = match["home_score"] if home else match["away_score"]
    opp_score = match["away_score"] if home else match["home_score"]
    return {"date": dt(match["date"]), "match_id": match["match_id"], "season": match["season"], "home": home,
            "points": 3 if own_score > opp_score else 1 if own_score == opp_score else 0,
            "shots": match["home_shots"] if home else match["away_shots"],
            "against": match["away_shots"] if home else match["home_shots"]}


def build():
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    matches = json.loads((OUT / "normalized_matches.json").read_text(encoding="utf-8"))
    matches.sort(key=lambda r: (r["date"], r["match_id"]))
    team_history, player_history = defaultdict(list), defaultdict(list)
    samples, picks, environments = [], [], []
    target_matches = 0

    for match in matches:
        date = dt(match["date"])
        date_key = date.date().isoformat()
        cutoff = date - timedelta(days=1)
        target = match["season"] == CURRENT_SEASON and date_key in TARGET_DATES
        hid, aid, league = match["home_team_id"], match["away_team_id"], match["league"]
        if target:
            target_matches += 1
            histories = {}
            for tid in (hid, aid):
                eligible = [r for r in team_history[league, tid] if r["date"] < cutoff and date-r["date"] <= timedelta(days=180)]
                current = [r for r in eligible if r["season"] == CURRENT_SEASON]
                previous = [r for r in eligible if r["season"] == PREVIOUS_SEASON]
                histories[tid] = (previous[-max(0, 8-len(current)):] + current) if len(current) < 8 else current
            home_hist, away_hist = histories[hid], histories[aid]
            home_venue = [r for r in home_hist if r["home"] and r["shots"] is not None and r["against"] is not None][-5:]
            away_venue = [r for r in away_hist if not r["home"] and r["shots"] is not None and r["against"] is not None][-5:]
            enough_team = len(home_hist) >= 8 and len(away_hist) >= 8 and len(home_venue) >= 3 and len(away_venue) >= 3
            env = {"match_id": match["match_id"], "date": match["date"], "league": league,
                   "fixture": match["home_team"] + " vs " + match["away_team"],
                   "history_cutoff": cutoff.isoformat(), "home_history_n": len(home_hist), "away_history_n": len(away_hist),
                   "home_venue_n": len(home_venue), "away_venue_n": len(away_venue), "enough_team_history": enough_team,
                   "home_prior_ids": [r["match_id"] for r in home_hist], "away_prior_ids": [r["match_id"] for r in away_hist]}
            if enough_team:
                env.update(home_ppg=avg(home_hist, "points"), away_ppg=avg(away_hist, "points"),
                           home_recent_ppg=avg(home_hist[-5:], "points"), away_recent_ppg=avg(away_hist[-5:], "points"),
                           home_home_shots=avg(home_venue, "shots"), away_away_shots=avg(away_venue, "shots"),
                           home_home_conceded=avg(home_venue, "against"), away_away_conceded=avg(away_venue, "against"))
                env["projected_home_shots"] = (env["home_home_shots"] + env["away_away_conceded"]) / 2
                env["projected_away_shots"] = (env["away_away_shots"] + env["home_home_conceded"]) / 2
                env["stronger"] = env["home_ppg"] > env["away_ppg"] and env["home_recent_ppg"] > env["away_recent_ppg"]
                env["shooting"] = env["home_home_shots"] >= 12 and env["away_away_conceded"] >= 12 and env["projected_home_shots"] > env["projected_away_shots"]
                env["environment"] = env["stronger"] and env["shooting"]
            else:
                env.update(stronger=False, shooting=False, environment=False)
            environments.append(env)

            ranked = []
            for p in match["players"]:
                if p["team_id"] != hid or not p["started"]:
                    continue
                prior = [r for r in player_history[league, hid, p["player_id"]]
                         if r["date"] < cutoff and date-r["date"] <= timedelta(days=180)][-5:]
                complete = len(prior) == 5 and all(r["shots"] is not None and r["minutes"] is not None for r in prior)
                row = {"match_id": match["match_id"], "date": match["date"], "league": league, "fixture": env["fixture"],
                       "player_id": p["player_id"], "player": p["player"], "started": True, "shots": p["shots"],
                       "hit": p["shots"] >= 2 if p["shots"] is not None else None, "player_history_n": len(prior),
                       "prior_fixture_ids": [r["match_id"] for r in prior], "features": env, "A": False, "B": False,
                       "exclusion_reasons": []}
                if complete:
                    shares = [r["shots"] / r["team_shots"] for r in prior if r.get("team_shots")]
                    row.update(recent_shots=avg(prior, "shots"), recent_minutes=avg(prior, "minutes"),
                               recent_hits=sum(r["shots"] >= 2 for r in prior),
                               recent_share=mean(shares) if len(shares) == 5 else None)
                    ranked.append(row)
                else:
                    row["exclusion_reasons"].append("incomplete_five_start_same_team_history")
                    samples.append(row)
            ranked.sort(key=lambda r: (-r["recent_shots"], -(r["recent_share"] or 0), r["player_id"]))
            for rank, row in enumerate(ranked, 1):
                row["shooter_rank"] = rank
                row["A"] = bool(env["environment"] and rank <= 2 and row["recent_minutes"] >= 70 and row["recent_hits"] >= 4)
                row["B"] = bool(row["A"] and row["recent_shots"] >= 3 and row["recent_minutes"] >= 80)
                if not env["environment"]: row["exclusion_reasons"].append("environment_failed")
                if rank > 2: row["exclusion_reasons"].append("outside_top_two")
                if row["recent_minutes"] < 70: row["exclusion_reasons"].append("minutes_below_70")
                if row["recent_hits"] < 4: row["exclusion_reasons"].append("fewer_than_four_recent_hits")
                samples.append(row)
                if row["A"]: picks.append(row)

        # The current fixture enters history only after feature construction.
        if None not in (match["home_score"], match["away_score"]):
            team_history[league, hid].append(make_team_row(match, hid))
            team_history[league, aid].append(make_team_row(match, aid))
        for p in match["players"]:
            if p["started"] and p["team_id"] in (hid, aid):
                team_shots = match["home_shots"] if p["home"] else match["away_shots"]
                player_history[league, p["team_id"], p["player_id"]].append({
                    "date": date, "match_id": match["match_id"], "shots": p["shots"], "minutes": p["minutes"], "team_shots": team_shots})

    a_rows, b_rows = picks, [r for r in picks if r["B"]]
    weeks = WEEK_STARTS
    def week_of(value):
        d = dt(value).date()
        return next((w for w in weeks if 0 <= (d-datetime.fromisoformat(w).date()).days <= 1), None)
    weekly = []
    for week in weeks:
        weekly.append({"weekend": week, "A": measure([r for r in a_rows if week_of(r["date"]) == week]),
                       "B": measure([r for r in b_rows if week_of(r["date"]) == week])})
    leagues = sorted({m["league"] for m in matches})
    by_league = {league: {"A": measure([r for r in a_rows if r["league"] == league]),
                          "B": measure([r for r in b_rows if r["league"] == league])} for league in leagues}
    summary = {"variant": plan["name"], "classification": "new early-season carryover variant; separate from original model",
               "provider": plan["provider"], "plan_sha256": hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest(),
               "target_fixtures": target_matches, "target_starter_samples": len(samples), "eligible_environments": sum(e["environment"] for e in environments),
               "A": measure(a_rows), "B": measure(b_rows), "by_weekend": weekly, "by_league": by_league,
               "missing_outcomes_A": sum(r["hit"] is None for r in a_rows), "missing_outcomes_B": sum(r["hit"] is None for r in b_rows),
               "exclusions": dict(Counter(reason for r in samples for reason in r["exclusion_reasons"])),
               "limits": plan["limits"] + ["Current lineups are actual historical starters, so this is a retrospective lineup-time replay.",
                   "UTC fixture dates define the weekend buckets.", "Hit rates describe this sample and are not guaranteed future win rates."]}
    betting = {"A": rollover(a_rows, 1.5), "B": rollover(b_rows, 2.0)}
    return plan, environments, samples, picks, summary, betting


def save():
    plan, environments, samples, picks, summary, betting = build()
    outputs = {"frozen_test_plan": plan, "environments": environments, "all_samples": samples,
               "qualifying_picks": picks, "results": summary, "weekly_results": summary["by_weekend"], "betting_simulation": betting}
    for name, data in outputs.items():
        (OUT / f"{name}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    def fmt(m): return "No picks" if not m["picks"] else f'{m["hits"]}/{m["picks"]} ({m["rate"]}%)'
    lines = [f"# {plan['name']}", "",
             "This is a **new early-season variant**, not the original same-season-only model. It fills missing eight-match and five-start history from the immediately previous season under the frozen 180-day, same-team rules.", "",
             f'Coverage: {summary["target_fixtures"]} weekend fixtures; {summary["target_starter_samples"]} home-starter samples; {summary["eligible_environments"]} qualifying environments.', "",
             f'Pattern A: **{fmt(summary["A"])}**. Pattern B: **{fmt(summary["B"])}**.', "", "## By weekend", "",
             "| Weekend | A | B |", "|---|---:|---:|"]
    for row in summary["by_weekend"]: lines.append(f'| {row["weekend"]} | {fmt(row["A"])} | {fmt(row["B"])} |')
    lines += ["", "## By league", "", "| League | A | B |", "|---|---:|---:|"]
    for league, row in summary["by_league"].items(): lines.append(f'| {league} | {fmt(row["A"])} | {fmt(row["B"])} |')
    lines += ["", "## Limits", ""] + ["- " + x for x in summary["limits"]]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    pick_rows = "".join(f'<tr><td>{escape(r["date"][:10])}</td><td>{escape(r["league"])}</td><td>{escape(r["fixture"])}</td><td>{escape(r["player"])}</td><td>{"A+B" if r["B"] else "A"}</td><td>{r["shots"] if r["shots"] is not None else "unknown"}</td><td>{"HIT" if r["hit"] else "MISS" if r["hit"] is False else "UNKNOWN"}</td></tr>' for r in picks)
    week_rows = "".join(f'<tr><td>{r["weekend"]}</td><td>{fmt(r["A"])}</td><td>{fmt(r["B"])}</td></tr>' for r in summary["by_weekend"])
    html = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Big-five carryover backtest</title><style>body{{font:16px/1.55 system-ui;max-width:1200px;margin:30px auto;padding:0 20px;background:#f3f6f8;color:#172b3a}}.card,table{{background:white}}.card{{padding:20px;border-radius:12px;margin:16px 0}}table{{border-collapse:collapse;width:100%}}th,td{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}.scroll{{overflow:auto}}.warn{{border-left:5px solid #db8b19}}a{{color:#176a7a}}</style><h1>Big-five early-season carryover replay</h1><div class="card warn"><b>Separate formula variant.</b> Previous-season data is used only because the original model cannot qualify early-season fixtures. Thresholds were frozen before acquisition.</div><div class="card"><b>{summary["target_fixtures"]}</b> fixtures · <b>{summary["eligible_environments"]}</b> qualifying environments · A: <b>{fmt(summary["A"])}</b> · B: <b>{fmt(summary["B"])}</b></div><h2>Weekend results</h2><table><tr><th>Weekend</th><th>A</th><th>B</th></tr>{week_rows}</table><h2>Every selection</h2><div class="scroll"><table><tr><th>Date</th><th>League</th><th>Fixture</th><th>Player</th><th>Rule</th><th>Shots</th><th>Result</th></tr>{pick_rows}</table></div><p><a href="report.md">Method and limits</a> · <a href="results.json">Results JSON</a> · <a href="qualifying_picks.json">Every pick JSON</a></p></html>'''
    (OUT / "index.html").write_text(html, encoding="utf-8")
    dashboard = OUT.parent / "project_site/dist/index.html"
    if dashboard.exists():
        text = dashboard.read_text(encoding="utf-8")
        replication = "replication" in OUT.name
        start, end = (("<!-- BIG5_REPLICATION_START -->", "<!-- BIG5_REPLICATION_END -->") if replication else ("<!-- BIG5_CARRYOVER_START -->", "<!-- BIG5_CARRYOVER_END -->"))
        if start in text:
            before, tail = text.split(start, 1)
            text = before + tail.split(end, 1)[1]
        panel = f'''{start}<section id="{'big5-replication' if replication else 'big5-carryover'}" class="panel" style="margin:24px 0"><div class="eyebrow">NEW · EARLY-SEASON CARRYOVER {'REPLICATION' if replication else 'REPLAY'}</div><h2>{escape(plan['name'])}</h2><p>A: <b>{fmt(summary["A"])}</b>. B: <b>{fmt(summary["B"])}</b>. The replay covered {summary["target_fixtures"]} fixtures and saved every sample.</p><p class="note"><b>Separate variant:</b> this does not replace the original formula. Small samples are descriptive, not guaranteed rates.</p><p><a href="../../{OUT.name}/index.html">Open weekend results, every selection and limits</a></p></section>{end}'''
        dashboard.write_text(text.replace("</header>", "</header>" + panel, 1), encoding="utf-8")
    with ZipFile(OUT.parent / f"{OUT.name}.zip", "w", ZIP_DEFLATED) as z:
        for p in sorted(OUT.rglob("*")):
            if p.is_file() and "raw" not in p.parts: z.write(p, p.relative_to(OUT))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    import sys
    if "--replication" in sys.argv:
        OUT = ROOT / "outputs/big5_2025_carryover_replication"
        PLAN_PATH = ROOT / "work/big5_carryover_replication_plan.json"
        TARGET_DATES = {"2025-09-13", "2025-09-14", "2025-09-20", "2025-09-21", "2025-09-27", "2025-09-28", "2025-10-04", "2025-10-05"}
        CURRENT_SEASON = "2025/2026"
        PREVIOUS_SEASON = "2024/2025"
        WEEK_STARTS = ["2025-09-13", "2025-09-20", "2025-09-27", "2025-10-04"]
    save()
