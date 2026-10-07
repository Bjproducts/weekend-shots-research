"""Apply unchanged home-main-shooter-v1 to the newly acquired EPL season."""
import hashlib
import argparse
import json
import sqlite3
from collections import defaultdict,Counter
from datetime import datetime,timedelta
from html import escape
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from test_home_pattern import run,measure
from weekly_pattern_replay import choose,RULES,monday

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--competition',type=int,default=2)
parser.add_argument('--slug',default='epl_2015_16_validation')
parser.add_argument('--league',default='Premier League')
args=parser.parse_args()
OUT=ROOT/'outputs'/args.slug

def main():
    source=OUT/'normalized_matches.json'
    records=json.loads(source.read_text(encoding='utf-8'))
    assert len(records)==380
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    c.executescript('''CREATE TABLE competitions(id INTEGER,name TEXT,is_competitive INTEGER);
        CREATE TABLE teams(id INTEGER PRIMARY KEY,name TEXT);
        CREATE TABLE players(id INTEGER PRIMARY KEY,common_name TEXT,full_name TEXT);
        CREATE TABLE fixtures(id INTEGER,fixture_date TEXT,competition_id INTEGER,season_id INTEGER,home_team_id INTEGER,away_team_id INTEGER,home_score INTEGER,away_score INTEGER,status TEXT);
        CREATE TABLE player_fixture_stats(fixture_id INTEGER,player_id INTEGER,team_id INTEGER,opponent_id INTEGER,home INTEGER,started INTEGER,minutes_played REAL,shots INTEGER,team_shots INTEGER,data_source TEXT);
        ''')
    c.execute('INSERT INTO competitions VALUES(?,?,1)',(args.competition,args.league))
    for r in records:
        f=r['fixture']
        for t in [f['home_team'],f['away_team']]:c.execute('INSERT OR IGNORE INTO teams VALUES(?,?)',(t['id'],t['name']))
        c.execute('INSERT INTO fixtures VALUES(?,?,?,?,?,?,?,?,?)',(f['id'],f['date'],args.competition,27,f['home_team']['id'],f['away_team']['id'],f['home_score'],f['away_score'],'finished'))
        for p in r['players']:
            q=p['player']
            c.execute('INSERT OR IGNORE INTO players VALUES(?,?,?)',(q['id'],q['common_name'],q['full_name']))
            c.execute('INSERT INTO player_fixture_stats VALUES(?,?,?,?,?,?,?,?,?,?)',(f['id'],q['id'],p['team_id'],p['opponent_id'],p['home'],p['started'],p['minutes_played'],p['shots'],p['team_shots'],'statsbomb'))
    result=run(connection=c,provider='statsbomb',save=False)
    result['source']=f'StatsBomb Open Data / {args.league} 2015/16 / competition {args.competition} season 27'
    feature_rows={(r['fixture_id'],r['player_id']):r for r in result['rows']}
    env={r['fixture_id']:r for r in result['environments']}
    sample_rows=[]
    picks=[]
    for rec in records:
        f=rec['fixture']
        for p in rec['players']:
            key=(f['id'],p['player']['id'])
            features=feature_rows.get(key)
            reasons=[]
            if not p['home']:reasons.append('away_player_outside_rule')
            if not p['started']:reasons.append('not_starting')
            if f['id'] not in env:reasons.append('insufficient_prior_team_history')
            elif p['home'] and p['started'] and features is None:reasons.append('fewer_than_five_known_prior_starts_within_180_days')
            decision={'full_pattern':False,'benchmark':False}
            if features is not None:
                selection_fields={k:features[k] for k in ['shooter_rank','recent_minutes','recent_hits','environment']}
                decision=choose(selection_fields)
                if features['shooter_rank']>2:reasons.append('not_top_two_eligible_home_shooters')
                if features['recent_minutes'] is None or features['recent_minutes']<70:reasons.append('prior_average_minutes_below_70_or_unknown')
                if features['recent_hits']<4:reasons.append('fewer_than_four_of_five_prior_hits')
                if not features['environment']:reasons.append('home_environment_filter_not_met')
            entry=dict(fixture_id=f['id'],player_id=p['player']['id'],date=f['date'],
                fixture=f['home_team']['name']+' vs '+f['away_team']['name'],
                player=p['player']['common_name'] or p['player']['full_name'],
                team_id=p['team_id'],home=p['home'],started=p['started'],minutes=p['minutes_played'],
                shots=p['shots'],team_shots=p['team_shots'],hit=None if p['shots'] is None else p['shots']>=2,
                week_start=monday(f['date']),features=features,exclusion_reasons=reasons,**decision)
            sample_rows.append(entry)
            if decision['benchmark']:picks.append(entry)
    assert len({(r['fixture_id'],r['player_id']) for r in sample_rows})==len(sample_rows)
    summaries={}
    for version in ['full_pattern','benchmark']:
        selected=[r for r in picks if r[version]]
        summaries[version]=dict(overall=measure(selected),
            autumn=measure([r for r in selected if r['date']<'2016']),
            spring=measure([r for r in selected if r['date']>='2016']))
    weeks=[]
    day=datetime.fromisoformat(monday(records[0]['fixture']['date']))
    end=datetime.fromisoformat(monday(records[-1]['fixture']['date']))
    while day<=end:
        key=day.date().isoformat()
        weeks.append(dict(week_start=key,**{v:measure([r for r in picks if r[v] and r['week_start']==key]) for v in summaries}))
        day+=timedelta(days=7)
    # Reconcile with the original engine's fixed-rule stages.
    assert summaries['full_pattern']['overall']==result['rules']['Full environment + minutes >=70 + 4/5 recent hits']['all']
    assert summaries['benchmark']['overall']==result['rules']['Top 2 + minutes >=70 + 4/5 hits WITHOUT environment filter']['all']
    manifest=dict(source_url='https://github.com/statsbomb/open-data',attribution='StatsBomb Open Data',
        source_season=f'{args.league} 2015/16',rules=RULES,rules_sha256=hashlib.sha256(json.dumps(RULES,sort_keys=True).encode()).hexdigest(),
        normalized_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),matches=380,teams=20,
        total_player_samples=len(sample_rows),eligible_fixtures=len(env),summary=summaries,
        benchmark_only=measure([r for r in picks if not r['full_pattern']]),
        limitations=['Historical external-dataset test, not a live profitability test.',
            'Different provider and older era: StatsBomb shots are counted from event data; blocked shots count, own goals do not.',
            'All player appearances saved; unused substitutes are not player appearances. Zero shots means no shot events in a downloaded complete match.',
            'Minutes use the existing adapter: merged lineup intervals rounded up and capped at 90; stoppage time not added. This differs from some provider minutes.',
            'Published kickoff clock has no timezone; adapter attaches UTC without claiming verified UTC. A >24h history buffer is retained.',
            'Lineup-time selection assumes recorded starters known; historical publication availability is not certified.',
            'The season was chosen for complete coverage before inspecting its pattern results. No threshold tuning. No odds/profit calculation.'],
        raw_files=[dict(path=str(p.relative_to(OUT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted((OUT/'raw').rglob('*.gz'))])
    for name,data in [('manifest',manifest),('all_samples',sample_rows),('qualifying_picks',picks),('weekly_results',weeks),('feature_replay',result)]:
        (OUT/(name+'.json')).write_text(json.dumps(data,indent=2),encoding='utf-8')
    def fmt(m):return f"{m['hits']}/{m['n']} ({m['rate']}%)" if m['n'] else 'No picks'
    lines=[f'# New historical test: {args.league} 2015/16','',
        'Source: [StatsBomb Open Data](https://github.com/statsbomb/open-data). All 380 matches downloaded and checked, 20 teams with 19 home and 19 away fixtures each. Season chosen for coverage before evaluating the pattern.','',
        f"Saved {len(sample_rows)} player appearances, including exclusions. {len(env)} fixtures passed the prior-team-history requirements. Rules: home-main-shooter-v1 unchanged.",'',
        '| Version | Whole season | Before Jan 2016 | Jan 2016 onward |','|---|---:|---:|---:|']
    for v,m in summaries.items():lines.append(f"| {v} | {fmt(m['overall'])} | {fmt(m['autumn'])} | {fmt(m['spring'])} |")
    lines+=['','The original MLS comparison was 150/185 (81.1%) for the full pattern and 523/660 (79.2%) for the benchmark. These results must not be pooled as if leagues/providers were identical.','',
        'The benchmark is consistent HOME main shooters, with the same team-history eligibility, without requiring the stronger-home/shooting conditions. The full pattern is a subset, not an independent comparison group.','',
        '## Limits','']+['- '+x for x in manifest['limitations']]+['','## Files','',
        '- all_samples.json: every player appearance, result, selection flags and exclusion reasons.',
        '- qualifying_picks.json: every qualifying benchmark/full-pattern selection with lagged features.',
        '- weekly_results.json: every calendar week.',
        '- normalized_matches.json: all normalized fixture/player records.',
        '- raw/: all downloaded events, lineups and match-list JSON, gzip compressed.',
        '- manifest.json: source attribution, rules, coverage, hashes and limitations.','']
    (OUT/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    table=''.join(f'<tr><td>{v}</td><td>{fmt(m["overall"])}</td><td>{fmt(m["autumn"])}</td><td>{fmt(m["spring"])}</td></tr>' for v,m in summaries.items())
    picktable=''.join(f'<tr><td>{r["date"][:10]}</td><td>{escape(r["fixture"])}</td><td>{escape(r["player"])}</td><td>{"Full + benchmark" if r["full_pattern"] else "Benchmark only"}</td><td>{r["shots"]}</td><td>{"HIT" if r["hit"] else "MISS"}</td></tr>' for r in picks)
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>EPL external historical test</title><style>body{{font:16px/1.6 system-ui;max-width:1150px;margin:30px auto;padding:0 20px;background:#f2f5f8;color:#182b3e}}.scroll{{overflow:auto}}table{{border-collapse:collapse;background:white;width:100%}}th,td{{padding:12px;border-bottom:1px solid #ddd;text-align:left}}a{{color:#216e83}}</style>
    <h1>Premier League 2015/16: frozen-pattern test</h1><p>All 380 matches · {len(sample_rows)} player appearances saved · {len(env)} fixtures with enough earlier team history.</p><p>Data: <a href="https://github.com/statsbomb/open-data">StatsBomb Open Data</a>. Different provider and era; no tuning or profit claim.</p><div class="scroll"><table><tr><th>Version</th><th>Season</th><th>Before Jan 2016</th><th>Jan onward</th></tr>{table}</table></div>
    <p><a href="report.md">Full report and limitations</a> · <a href="all_samples.json">Every sample and exclusion</a> · <a href="qualifying_picks.json">Pick evidence</a> · <a href="../epl_2015_16_validation.zip">Download all data</a></p>
    <h2>Every qualifying pick</h2><div class="scroll"><table><tr><th>Date</th><th>Fixture</th><th>Player</th><th>Rule</th><th>Shots</th><th>Result</th></tr>{picktable}</table></div></html>'''
    html=html.replace('Premier League',escape(args.league)).replace('EPL external',escape(args.league)+' external').replace('../epl_2015_16_validation.zip','../'+args.slug+'.zip')
    (OUT/'index.html').write_text(html,encoding='utf-8')
    with ZipFile(ROOT/'outputs'/(args.slug+'.zip'),'w',ZIP_DEFLATED) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(OUT))
    page=ROOT/'outputs/project_site/dist/index.html'
    text=page.read_text(encoding='utf-8')
    start,end=f'<!-- {args.slug}_START -->',f'<!-- {args.slug}_END -->'
    if start in text:
        a,b=text.split(start,1);text=a+b.split(end,1)[1]
    panel=f'''{start}<section id="epl-validation" class="panel" style="margin:24px 0"><div class="eyebrow">NEW EXTERNAL HISTORICAL TEST · COMPLETE</div><h2>Premier League 2015/16</h2>
    <p>380 matches downloaded from StatsBomb Open Data. Full frozen pattern: <b>{fmt(summaries['full_pattern']['overall'])}</b>. Consistent home-shooter benchmark: <b>{fmt(summaries['benchmark']['overall'])}</b>. No thresholds changed.</p>
    <p>{len(sample_rows)} player appearances saved, including rejected samples. This is a different-provider historical test, not a promised future win rate.</p><p><a href="../../epl_2015_16_validation/index.html">Results and every qualifying pick</a> · <a href="../../epl_2015_16_validation.zip">All source and sample data</a></p></section>{end}'''
    panel=panel.replace('Premier League',escape(args.league)).replace('id="epl-validation"','id="'+args.slug+'"').replace('epl_2015_16_validation',args.slug)
    page.write_text(text.replace('</header>','</header>'+panel,1),encoding='utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('raw_files','rules')},indent=2))

if __name__=='__main__':main()
