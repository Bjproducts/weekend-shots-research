"""Untuned A/B evaluation on a new, explicitly incomplete StatsBomb dataset."""
import gzip,hashlib,json,random,sqlite3
from collections import defaultdict,Counter
from datetime import datetime,timedelta
from pathlib import Path
from statistics import mean
from zipfile import ZipFile,ZIP_DEFLATED
from html import escape
from test_home_pattern import run,measure
from weekly_pattern_replay import choose,RULES,monday

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/ligue1_2015_16_ab_validation'

def comparison(picks):
    a=measure(picks);b=measure([r for r in picks if r['B']])
    groups=defaultdict(list)
    for r in picks:groups[monday(r['date'])].append(r)
    rng=random.Random(27092026);weeks=list(groups);deltas=[]
    for _ in range(3000):
        selected=[r for key in rng.choices(weeks,k=len(weeks)) for r in groups[key]] if weeks else []
        filtered=[r for r in selected if r['B']]
        if filtered and selected:deltas.append(100*(mean(r['hit'] for r in filtered)-mean(r['hit'] for r in selected)))
    deltas.sort()
    return dict(A=a,B=b,excluded=measure([r for r in picks if not r['B']]),
        retained_pct=round(100*b['n']/a['n'],1) if a['n'] else None,
        rate_difference_pp=round(100*(b['hits']/b['n']-a['hits']/a['n']),2) if b['n'] else None,
        paired_week_bootstrap_interval95=[round(deltas[int(len(deltas)*p)],2) for p in [.025,.975]] if deltas else None,
        bootstrap_valid_replicates=len(deltas),active_weeks=len(weeks))

def main():
    plan_path=ROOT/'work/ligue1_ab_plan.json';plan=json.loads(plan_path.read_text())
    records=json.loads((OUT/'normalized_matches.json').read_text(encoding='utf-8'))
    catalog=json.loads(gzip.decompress((OUT/'raw/matches/7/27.json.gz').read_bytes()))
    rounds={r['match_id']:r['match_week'] for r in catalog}
    assert len(records)==377 and len({r['fixture']['id'] for r in records})==377
    teams={t['id']:t['name'] for r in records for t in [r['fixture']['home_team'],r['fixture']['away_team']]}
    pairs={(r['fixture']['home_team']['id'],r['fixture']['away_team']['id']) for r in records}
    missing=[dict(home=teams[h],away=teams[a]) for h in teams for a in teams if h!=a and (h,a) not in pairs]
    assert len(teams)==20 and len(missing)==3
    old=json.loads((ROOT/'outputs/winning_pattern_research.json').read_text(encoding='utf-8'))
    prior_ids={r['fixture_id'] for r in old['rows'] if r['provider']=='statsbomb'}
    assert not prior_ids.intersection(rounds)
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    c.executescript('''CREATE TABLE competitions(id INTEGER,name TEXT,is_competitive INTEGER);
        CREATE TABLE teams(id INTEGER PRIMARY KEY,name TEXT);
        CREATE TABLE players(id INTEGER PRIMARY KEY,common_name TEXT,full_name TEXT);
        CREATE TABLE fixtures(id INTEGER,fixture_date TEXT,competition_id INTEGER,season_id INTEGER,home_team_id INTEGER,away_team_id INTEGER,home_score INTEGER,away_score INTEGER,status TEXT);
        CREATE TABLE player_fixture_stats(fixture_id INTEGER,player_id INTEGER,team_id INTEGER,opponent_id INTEGER,home INTEGER,started INTEGER,minutes_played REAL,shots INTEGER,team_shots INTEGER,data_source TEXT);
        INSERT INTO competitions VALUES(7,'Ligue 1',1);''')
    histories=defaultdict(list);gap_audit=[]
    for rec in records:
        f=rec['fixture'];cutoff=datetime.fromisoformat(f['date'])-timedelta(days=1)
        absent={}
        for t in [f['home_team'],f['away_team']]:
            c.execute('INSERT OR IGNORE INTO teams VALUES(?,?)',(t['id'],t['name']))
            observed={r['round'] for r in histories[t['id']] if r['date']<cutoff}
            absent[t['name']]=sorted(set(range(1,rounds[f['id']]))-observed)
        gap_audit.append(dict(fixture_id=f['id'],round=rounds[f['id']],earlier_rounds_absent=absent,complete_prior_rounds=not any(absent.values())))
        c.execute('INSERT INTO fixtures VALUES(?,?,?,?,?,?,?,?,?)',(f['id'],f['date'],7,27,f['home_team']['id'],f['away_team']['id'],f['home_score'],f['away_score'],'finished'))
        for p in rec['players']:
            q=p['player'];c.execute('INSERT OR IGNORE INTO players VALUES(?,?,?)',(q['id'],q['common_name'],q['full_name']))
            c.execute('INSERT INTO player_fixture_stats VALUES(?,?,?,?,?,?,?,?,?,?)',(f['id'],q['id'],p['team_id'],p['opponent_id'],p['home'],p['started'],p['minutes_played'],p['shots'],p['team_shots'],'statsbomb'))
        for t in [f['home_team'],f['away_team']]:histories[t['id']].append(dict(date=datetime.fromisoformat(f['date']),round=rounds[f['id']]))
    replay=run(connection=c,provider='statsbomb',save=False)
    replay['source']='StatsBomb Ligue 1 2015/16: 377/380 matches'
    fmap={(r['fixture_id'],r['player_id']):r for r in replay['rows']}
    eligible={r['fixture_id'] for r in replay['environments']};gaps={r['fixture_id']:r for r in gap_audit}
    samples=[];picks=[]
    for rec in records:
        f=rec['fixture']
        for p in rec['players']:
            ft=fmap.get((f['id'],p['player']['id']));a=False;b=False;reasons=[]
            if not p['home']:reasons.append('away_player')
            if not p['started']:reasons.append('not_starter')
            if f['id'] not in eligible:reasons.append('insufficient_team_history')
            elif p['home'] and p['started'] and ft is None:reasons.append('insufficient_player_history')
            if ft:
                a=choose({k:ft[k] for k in ['shooter_rank','recent_minutes','recent_hits','environment']})['full_pattern']
                b=a and ft['recent_shots']>=3 and ft['recent_minutes']>=80
                if not a:reasons.append('baseline_conditions_not_met')
                elif not b:reasons.append('challenger_extra_conditions_not_met')
            row=dict(fixture_id=f['id'],player_id=p['player']['id'],date=f['date'],fixture=f['home_team']['name']+' vs '+f['away_team']['name'],
                player=p['player']['common_name'] or p['player']['full_name'],home=p['home'],started=p['started'],shots=p['shots'],
                hit=p['shots']>=2 if p['shots'] is not None else None,A=a,B=b,features=ft,exclusion_reasons=reasons,
                complete_prior_rounds=gaps[f['id']]['complete_prior_rounds'])
            samples.append(row)
            if a:picks.append(row)
    summary=comparison(picks);sensitivity=comparison([r for r in picks if r['complete_prior_rounds']])
    counts=Counter(r['player_id'] for r in picks if r['B']);top3={k for k,n in counts.most_common(3)}
    concentration=comparison([r for r in picks if r['player_id'] not in top3])
    weeks=[];day=datetime.fromisoformat(monday(records[0]['fixture']['date']));end=datetime.fromisoformat(monday(records[-1]['fixture']['date']))
    while day<=end:
        key=day.date().isoformat();rs=[r for r in picks if monday(r['date'])==key]
        weeks.append(dict(week=key,A=measure(rs),B=measure([r for r in rs if r['B']])));day+=timedelta(days=7)
    result=dict(dataset='Ligue 1 2015/16',provider='StatsBomb Open Data',matches=377,expected=380,
        player_samples=len(samples),eligible_fixtures=len(eligible),missing_fixture_pairs=missing,
        rules=RULES,plan=plan,plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        baseline_rules_sha256=hashlib.sha256(json.dumps(RULES,sort_keys=True).encode()).hexdigest(),
        comparison=summary,complete_prior_rounds_sensitivity=sensitivity,
        without_three_most_selected_B_players=concentration,
        top_three_B_players=[dict(player=next(r['player'] for r in picks if r['player_id']==pid),picks=n) for pid,n in counts.most_common(3)],
        limits=['Partial coverage: three expected fixture pairings absent. Missing match dates/stats are not invented.',
            'Prior-round sensitivity is conservative: it also removes picks before postponed earlier rounds were played.',
            'Independent of refinement discovery matches, but same provider and 2015/16 era as other European tests.',
            'Paired weekly bootstrap accounts for within-week dependence, not all persistent player/team dependence. Interval is approximate.',
            'Actual starter assumed known; StatsBomb published clock has no timezone offset; history buffer >24h. Historical publication availability not verified.',
            'Minutes and shots follow the existing StatsBomb adapter. No odds or profit test. No rule promotion or retuning.'])
    for name,obj in [('ab_results',result),('all_samples',samples),('qualifying_picks',picks),('weekly_results',weeks),('coverage_audit',gap_audit),('feature_replay',replay),('frozen_test_plan',plan)]:
        (OUT/(name+'.json')).write_text(json.dumps(obj,indent=2),encoding='utf-8')
    def fmt(m):return f"{m['hits']}/{m['n']} ({m['rate']}%)" if m['n'] else 'No picks'
    lines=['# Fixed A/B validation — Ligue 1 2015/16','',
        'Source: [StatsBomb Open Data](https://github.com/statsbomb/open-data). New evaluation matches relative to refinement discovery; NOT a complete season: 377/380 available.','',
        'A = original frozen pattern. B = A plus at least 3 average shots and 80 average minutes over the previous five starts. No thresholds changed.','',
        '| Check | A: original | B: challenger | B retention |','|---|---:|---:|---:|',
        f"| All available matches | {fmt(summary['A'])} | {fmt(summary['B'])} | {summary['retained_pct']}% |",
        f"| Only complete earlier scheduled rounds | {fmt(sensitivity['A'])} | {fmt(sensitivity['B'])} | {sensitivity['retained_pct']}% |",
        f"| Excluding three most-selected B players | {fmt(concentration['A'])} | {fmt(concentration['B'])} | {concentration['retained_pct']}% |",'',
        f"B minus A: {summary['rate_difference_pp']} percentage points. Approximate paired-week bootstrap 95% interval: {summary['paired_week_bootstrap_interval95']}. Rejected A picks: {fmt(summary['excluded'])}.",'',
        f"Saved {len(samples)} player samples, {len(picks)} A picks and all B decisions. {len(eligible)} fixtures had enough prior history.",'','## Missing fixture pairings','']+['- '+r['home']+' vs '+r['away'] for r in missing]+['','## Limits','']+['- '+s for s in result['limits']]
    (OUT/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    tr=''.join(f'<tr><td>{name}</td><td>{fmt(m["A"])}</td><td>{fmt(m["B"])}</td><td>{m["retained_pct"]}%</td></tr>' for name,m in [('Available matches',summary),('Complete earlier rounds',sensitivity),('Without 3 most-selected B players',concentration)])
    ptr=''.join(f'<tr><td>{r["date"][:10]}</td><td>{escape(r["fixture"])}</td><td>{escape(r["player"])}</td><td>{"A + B" if r["B"] else "A only"}</td><td>{r["shots"]}</td><td>{"HIT" if r["hit"] else "MISS"}</td></tr>' for r in picks)
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ligue 1 A/B validation</title><style>body{{font:16px/1.6 system-ui;max-width:1150px;margin:30px auto;padding:0 20px;background:#f2f5f8;color:#182b3e}}.scroll{{overflow:auto}}table{{border-collapse:collapse;background:white;width:100%}}td,th{{padding:12px;border-bottom:1px solid #ddd;text-align:left}}a{{color:#216e83}}</style><h1>New A/B test: Ligue 1 2015/16</h1><p>377/380 matches, {len(samples):,} appearances. Partial coverage disclosed. Source: <a href="https://github.com/statsbomb/open-data">StatsBomb Open Data</a>.</p><p>A: original pattern. B: A + at least 3 prior average shots and 80 prior average minutes. Rules unchanged.</p><div class="scroll"><table><tr><th>Check</th><th>A</th><th>B</th><th>Retained</th></tr>{tr}</table></div><p>B-minus-A: {summary['rate_difference_pp']} percentage points; approximate paired-week interval {summary['paired_week_bootstrap_interval95']}. This is not a guaranteed future rate or profit estimate.</p><p><a href="report.md">Report and caveats</a> · <a href="all_samples.json">All samples</a> · <a href="ab_results.json">Detailed results</a> · <a href="../ligue1_2015_16_ab_validation.zip">All data</a></p><h2>Every original-pattern pick</h2><div class="scroll"><table><tr><th>Date</th><th>Fixture</th><th>Player</th><th>Rule</th><th>Shots</th><th>Outcome</th></tr>{ptr}</table></div></html>'''
    (OUT/'index.html').write_text(html,encoding='utf-8')
    with ZipFile(OUT.parent/'ligue1_2015_16_ab_validation.zip','w',ZIP_DEFLATED) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(OUT))
    page=OUT.parent/'project_site/dist/index.html';text=page.read_text(encoding='utf-8');start,end='<!-- LIGUE1_AB_START -->','<!-- LIGUE1_AB_END -->'
    if start in text:
        before,tail=text.split(start,1);text=before+tail.split(end,1)[1]
    panel=f'''{start}<section id="ligue1-ab" class="panel" style="margin:24px 0"><div class="eyebrow">NEW FIXED-RULE A/B TEST</div><h2>Ligue 1 2015/16 — 377/380 matches</h2><p>Original A: {fmt(summary['A'])}. Challenger B: {fmt(summary['B'])}. {summary['retained_pct']}% of picks retained. Missing-match sensitivity and every sample saved; no rule change.</p><p><a href="../../ligue1_2015_16_ab_validation/index.html">View A/B results and all evidence</a></p></section>{end}'''
    page.write_text(text.replace('</header>','</header>'+panel,1),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
