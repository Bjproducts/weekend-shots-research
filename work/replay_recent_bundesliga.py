"""Clean and replay the acquired chronological prefix; never claim a full season."""
import json,sqlite3,hashlib
from collections import Counter
from datetime import datetime,timedelta
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from test_home_pattern import run,measure
from weekly_pattern_replay import RULES,choose,monday

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/bundesliga_2024_25_validation'

def main():
    status=json.loads((OUT/'download_status.json').read_text(encoding='utf-8'))
    records=json.loads((OUT/'normalized_matches.json').read_text(encoding='utf-8'))
    catalog=json.loads((OUT/'fixture_catalog.json').read_text(encoding='utf-8'))
    assert [r['fixture']['id'] for r in records]==[r['id'] for r in catalog[:len(records)]]
    c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
    c.executescript('''CREATE TABLE competitions(id INTEGER,name TEXT,is_competitive INTEGER);
        CREATE TABLE teams(id INTEGER PRIMARY KEY,name TEXT);
        CREATE TABLE players(id INTEGER PRIMARY KEY,common_name TEXT,full_name TEXT);
        CREATE TABLE fixtures(id INTEGER,fixture_date TEXT,competition_id INTEGER,season_id INTEGER,home_team_id INTEGER,away_team_id INTEGER,home_score INTEGER,away_score INTEGER,status TEXT);
        CREATE TABLE player_fixture_stats(fixture_id INTEGER,player_id INTEGER,team_id INTEGER,opponent_id INTEGER,home INTEGER,started INTEGER,minutes_played REAL,shots INTEGER,team_shots INTEGER,data_source TEXT);
        INSERT INTO competitions VALUES(35,'Bundesliga',1);''')
    audit=[];all_samples=[];seen=set()
    for rec in records:
        f=rec['fixture'];reasons=[]
        for t in [f['home_team'],f['away_team']]:c.execute('INSERT OR IGNORE INTO teams VALUES(?,?)',(t['id'],t['name']))
        c.execute('INSERT INTO fixtures VALUES(?,?,?,?,?,?,?,?,?)',(f['id'],f['date'],35,63516,f['home_team']['id'],f['away_team']['id'],f['home_score'],f['away_score'],'finished'))
        for tid in [f['home_team']['id'],f['away_team']['id']]:
            ps=[p for p in rec['players'] if p['team_id']==tid]
            if sum(p['started'] for p in ps)!=11:reasons.append('starting_XI_incomplete')
            if any(not p['starter_flag_explicit'] for p in ps):reasons.append('starter_flag_not_explicit')
            if any(p['shots'] is None for p in ps):reasons.append('incomplete_shots_team_total_unknown')
            if ps and all(p['shots'] is not None for p in ps):
                if any(p['team_shots']!=sum(q['shots'] for q in ps) for p in ps):reasons.append('team_shot_sum_conflict')
        for p in rec['players']:
            key=(f['id'],p['player']['id'])
            if key in seen:reasons.append('duplicate_player_fixture')
            seen.add(key)
            if p['shots'] is not None and p['shots']<0:reasons.append('negative_shots')
            if p['minutes_played'] is not None and not 0<=p['minutes_played']<=130:reasons.append('invalid_minutes')
            if p['shots_on_target'] is not None and p['shots'] is not None and not 0<=p['shots_on_target']<=p['shots']:reasons.append('invalid_sot')
        reasons=sorted(set(reasons))
        audit.append(dict(fixture_id=f['id'],date=f['date'],accepted=not reasons,reasons=reasons,player_samples=len(rec['players'])))
        for p in rec['players']:
            sample=dict(fixture_id=f['id'],date=f['date'],fixture=f['home_team']['name']+' vs '+f['away_team']['name'],
                player_id=p['player']['id'],player=p['player']['common_name'] or p['player']['full_name'],
                team_id=p['team_id'],home=p['home'],started=p['started'],minutes=p['minutes_played'],shots=p['shots'],team_shots=p['team_shots'],
                hit=None if p['shots'] is None else p['shots']>=2,quality_reasons=reasons)
            all_samples.append(sample)
            if reasons:continue
            q=p['player'];c.execute('INSERT OR IGNORE INTO players VALUES(?,?,?)',(q['id'],q['common_name'],q['full_name']))
            c.execute('INSERT INTO player_fixture_stats VALUES(?,?,?,?,?,?,?,?,?,?)',(f['id'],q['id'],p['team_id'],p['opponent_id'],p['home'],p['started'],p['minutes_played'],p['shots'],p['team_shots'],'sportsapipro'))
    try:result=run(connection=c,save=False)
    except AssertionError as e:
        if str(e)!='Insufficient team history':raise
        result=dict(rows=[],environments=[],rules={})
    feature_map={(r['fixture_id'],r['player_id']):r for r in result['rows']}
    eligible={r['fixture_id'] for r in result['environments']}
    picks=[]
    for sample in all_samples:
        f=feature_map.get((sample['fixture_id'],sample['player_id']))
        sample['features']=f
        sample['full_pattern']=False;sample['benchmark']=False
        reasons=list(sample['quality_reasons'])
        if not sample['home']:reasons.append('away_player')
        if not sample['started']:reasons.append('not_starting')
        if sample['fixture_id'] not in eligible:reasons.append('insufficient_prior_team_history')
        elif sample['home'] and sample['started'] and f is None:reasons.append('insufficient_known_prior_player_starts')
        if f:
            sample.update(choose({k:f[k] for k in ['shooter_rank','recent_minutes','recent_hits','environment']}))
            if f['shooter_rank']>2:reasons.append('outside_top_two_shooters')
            if f['recent_minutes'] is None or f['recent_minutes']<70:reasons.append('prior_minutes_below70_or_unknown')
            if f['recent_hits']<4:reasons.append('prior_hits_below4of5')
            if not f['environment']:reasons.append('environment_not_met')
        sample['exclusion_reasons']=reasons
        if sample['benchmark']:picks.append(sample)
    summary={v:measure([r for r in picks if r[v]]) for v in ['full_pattern','benchmark']}
    weeks=[dict(week_start=w,**{v:measure([r for r in picks if r[v] and monday(r['date'])==w]) for v in summary}) for w in sorted({monday(r['fixture']['date']) for r in records})]
    report=dict(status=status,rules=RULES,rules_sha256=hashlib.sha256(json.dumps(RULES,sort_keys=True).encode()).hexdigest(),
        scope='Incomplete chronological prefix; exploratory results only, NOT completed season validation.',
        dates=[records[0]['fixture']['date'],records[-1]['fixture']['date']],
        accepted_fixtures=sum(r['accepted'] for r in audit),quarantined_fixtures=sum(not r['accepted'] for r in audit),
        eligible_fixtures=len(eligible),summary=summary,
        limitations=['Daily quota limits acquisition. Never choose matches based on outcome.',
            'Current data begins at season start; most matches only supply warm-up history.',
            'Fixture with missing shot counts or ambiguous starters is quarantined from feature stats; raw data and score history retained.',
            'Team shots are derived sums of player shots, not independently verified team totals.',
            'Provider currently supplies revised historical data, not certified as-of-publication snapshots.',
            'Rules unchanged; no profit calculation and no conclusion from small samples.'])
    for name,obj in [('screening_report',report),('cleaning_audit',audit),('all_samples',all_samples),('qualifying_picks',picks),('weekly_results',weeks),('feature_replay',result)]:
        (OUT/(name+'.json')).write_text(json.dumps(obj,indent=2),encoding='utf-8')
    def fmt(m):return f"{m['hits']}/{m['n']} ({m['rate']}%)" if m['n'] else 'No qualifying cases yet'
    lines=['# Recent-season validation: acquisition in progress','',
        f"Bundesliga 2024/25, SportsAPI Pro. {len(records)}/306 matches with player data downloaded; {status['pending_matches']} remain. Quota remaining at stop: {status['quota_remaining']}. Ten calls reserved.",'',
        f"Coverage: {report['dates'][0][:10]} through {report['dates'][1][:10]}. {len(all_samples)} player appearances saved. {report['accepted_fixtures']} fixtures passed checks; {report['quarantined_fixtures']} quarantined. {len(eligible)} fixtures had enough earlier team history.",'',
        '| Rule | Partial-batch results |','|---|---:|']
    for v,m in summary.items():lines.append(f'| {v} | {fmt(m)} |')
    lines+=['','Do not compare this small opening-season batch as if it were a completed season. Most of the downloaded matches establish earlier history rather than testing the rule.','',
        '## Next action','',f"Resume the cached download after the provider quota resets; {status['pending_matches']} matches still need player stats. No future run is scheduled. The complete fixture catalog is already saved.",'',
        '## Limits','']+['- '+x for x in report['limitations']]
    (OUT/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Recent season: in progress</title><style>body{{font:16px/1.6 system-ui;max-width:1000px;margin:30px auto;padding:0 20px;background:#f2f5f8;color:#182b3e}}a{{color:#216e83}}</style><h1>Bundesliga 2024/25: partial download</h1>
    <p><b>{len(records)}/306 matches</b> with player statistics. {len(all_samples)} appearances saved. {len(eligible)} matches have enough earlier team history.</p><p>Full pattern: <b>{fmt(summary['full_pattern'])}</b>. Benchmark: <b>{fmt(summary['benchmark'])}</b>.</p><p>This is a small opening-season batch, mostly warm-up history—not a completed validation or a dependable new hit rate.</p>
    <p>{status['pending_matches']} matches remain. Quota stopped with {status['quota_remaining']} requests remaining. Downloads are cached and can resume after quota reset; no automation scheduled.</p>
    <p><a href="report.md">Report and next action</a> · <a href="all_samples.json">All samples and exclusions</a> · <a href="qualifying_picks.json">Every qualifying pick</a> · <a href="cleaning_audit.json">Cleaning checks</a> · <a href="../bundesliga_2024_25_validation.zip">All evidence (ZIP)</a></p></html>'''
    (OUT/'index.html').write_text(html,encoding='utf-8')
    with ZipFile(OUT.parent/'bundesliga_2024_25_validation.zip','w',ZIP_DEFLATED) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(OUT))
    page=OUT.parent/'project_site/dist/index.html';text=page.read_text(encoding='utf-8')
    start,end='<!-- RECENT_SEASON_START -->','<!-- RECENT_SEASON_END -->'
    if start in text:
        before,tail=text.split(start,1);text=before+tail.split(end,1)[1]
    panel=f'''{start}<section id="recent-season" class="panel" style="margin:24px 0"><div class="eyebrow">RECENT-DATA VALIDATION · IN PROGRESS</div><h2>Bundesliga 2024/25: {len(records)}/306 matches acquired</h2><p>{len(all_samples)} player appearances saved. {status['pending_matches']} matches still need player data. Quota reserve retained. This is not yet a completed season test.</p><p>Full pattern: {fmt(summary['full_pattern'])}; benchmark: {fmt(summary['benchmark'])}. Small preliminary sample only.</p><p><a href="../../bundesliga_2024_25_validation/index.html">Acquisition status, samples and next action</a></p></section>{end}'''
    page.write_text(text.replace('</header>','</header>'+panel,1),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
