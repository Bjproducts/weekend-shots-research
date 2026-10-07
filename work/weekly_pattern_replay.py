"""Fixed-rule, lineup-time historical replay. No model fitting or threshold search."""
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from statistics import mean

from test_home_pattern import connect, measure

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs'
RULES = {
    'version': 'home-main-shooter-v1',
    'target': '2+ total shots',
    'main_shooter_rank_max': 2,
    'prior_starts': 5,
    'prior_start_lookback_days': 180,
    'prior_average_minutes_min': 70,
    'prior_hits_min': 4,
    'team_season_history_min': 8,
    'venue_history_min': 3,
    'venue_history_max': 5,
    'home_shots_min': 12,
    'away_conceded_min': 12,
    'strength': 'strictly higher season PPG AND last-five PPG',
    'shooting': 'home/away venue shot proxy favours home',
    'timing': 'recorded starters assumed available at lineup time; history >24h before kickoff',
    'benchmark_universe': 'same home starters and team-history eligibility; no strength/shooting filter',
}


def choose(features):
    # Deliberately receives no current result, current shots, minutes or score.
    consistent = (features['shooter_rank'] <= RULES['main_shooter_rank_max']
        and features['recent_minutes'] is not None
        and features['recent_minutes'] >= RULES['prior_average_minutes_min']
        and features['recent_hits'] >= RULES['prior_hits_min'])
    return {'benchmark': consistent, 'full_pattern': consistent and features['environment']}


def monday(value):
    date = datetime.fromisoformat(value[:10])
    return (date - timedelta(days=date.weekday())).date().isoformat()


def rate(rows):
    m = measure(rows)
    return f"{m['hits']}/{m['n']} ({m['rate']}%)" if m['n'] else 'No settled picks'


def verify_team_features(data):
    """Independently reconstruct all team-form features from the read-only DB."""
    c = connect()
    history = defaultdict(list)
    source_counts = defaultdict(int)
    for f in c.execute('''select f.*, c.name competition from fixtures f
        join competitions c on c.id=f.competition_id where status='finished'
        and c.is_competitive=1 order by fixture_date,id'''):
        if f['competition']=='MLS':
            source_counts[monday(f['fixture_date'])] += 1
        for home in [True, False]:
            team = f['home_team_id'] if home else f['away_team_id']
            opponent = f['away_team_id'] if home else f['home_team_id']
            totals = {}
            for tid in [team, opponent]:
                values = {r[0] for r in c.execute('''select team_shots from player_fixture_stats
                    where fixture_id=? and team_id=? and data_source='sportsapipro'
                    and team_shots is not null''', (f['id'], tid))}
                totals[tid] = next(iter(values)) if len(values)==1 else None
            gf,ga = (f['home_score'],f['away_score']) if home else (f['away_score'],f['home_score'])
            if gf is None or ga is None:
                continue
            history[f['competition_id'],f['season_id'],team].append(dict(
                fixture_id=f['id'],date=f['fixture_date'],home=home,
                points=3 if gf>ga else 1 if gf==ga else 0,
                shots=totals[team],against=totals[opponent]))
    for env in data['environments']:
        f=c.execute('select * from fixtures where id=?',(env['fixture_id'],)).fetchone()
        cutoff=datetime.fromisoformat(env['date'])-timedelta(days=1)
        h=[r for r in history[f['competition_id'],f['season_id'],f['home_team_id']] if datetime.fromisoformat(r['date'])<cutoff]
        a=[r for r in history[f['competition_id'],f['season_id'],f['away_team_id']] if datetime.fromisoformat(r['date'])<cutoff]
        assert len(h)>=8 and len(a)>=8
        assert env['home_ppg']==mean(r['points'] for r in h)
        assert env['away_ppg']==mean(r['points'] for r in a)
        assert env['home_recent_ppg']==mean(r['points'] for r in h[-5:])
        assert env['away_recent_ppg']==mean(r['points'] for r in a[-5:])
        hv=[r for r in h if r['home'] and r['shots'] is not None and r['against'] is not None][-5:]
        av=[r for r in a if not r['home'] and r['shots'] is not None and r['against'] is not None][-5:]
        assert len(hv)>=3 and len(av)>=3
        assert env['home_home_shots']==mean(r['shots'] for r in hv)
        assert env['away_away_conceded']==mean(r['against'] for r in av)
        assert env['projected_home_shots']==(mean(r['shots'] for r in hv)+mean(r['against'] for r in av))/2
        assert env['projected_away_shots']==(mean(r['shots'] for r in av)+mean(r['against'] for r in hv))/2
        strong=env['home_ppg']>env['away_ppg'] and env['home_recent_ppg']>env['away_recent_ppg']
        shooting=env['home_home_shots']>=12 and env['away_away_conceded']>=12 and env['projected_home_shots']>env['projected_away_shots']
        assert env['environment']==(strong and shooting)
    c.close()
    return source_counts


def main():
    source=OUT/'home_environment_pattern_test.json'
    data=json.loads(source.read_text(encoding='utf-8'))
    source_counts=verify_team_features(data)
    ledger=[]
    for row in sorted(data['rows'],key=lambda r:(r['date'],r['fixture_id'],r['player_id'])):
        features={k:row[k] for k in ('shooter_rank','recent_minutes','recent_hits','environment')}
        selected=choose(features)
        if not selected['benchmark']:
            continue
        ledger.append(dict(row,week_start=monday(row['date']),**selected,
            outcome='UNKNOWN' if row['hit'] is None else 'HIT' if row['hit'] else 'MISS'))
    assert len({(r['fixture_id'],r['player_id']) for r in ledger})==len(ledger)
    weeks=[]
    cursor=datetime.fromisoformat(min(monday(r['date']) for r in data['environments']))
    end=datetime.fromisoformat(max(monday(r['date']) for r in data['environments']))
    while cursor<=end:
        start=cursor.date().isoformat()
        picks=[r for r in ledger if r['week_start']==start]
        eligible=sum(monday(r['date'])==start for r in data['environments'])
        weeks.append(dict(week_start=start,source_finished_mls_fixtures=source_counts[start],
            eligible_fixtures=eligible, full_pattern=measure([r for r in picks if r['full_pattern']]),
            benchmark=measure(picks),
            coverage='eligible fixtures present' if eligible else 'no eligible fixtures; not proof of no real-world opportunities'))
        cursor+=timedelta(days=7)
    summary={}
    for version in ['full_pattern','benchmark']:
        picks=[r for r in ledger if r[version]]
        summary[version]=dict(all=measure(picks),
            later=measure([r for r in picks if r['date'][:10]>=data['split_date']]),
            active_weeks=sum(w[version]['n']>0 for w in weeks),
            zero_pick_weeks=sum(w[version]['n']==0 for w in weeks),
            weeks_below_70pct=sum(w[version]['n']>0 and w[version]['rate']<70 for w in weeks),
            by_year={year:measure([r for r in picks if r['date'][:4]==year]) for year in sorted({r['date'][:4] for r in ledger})})
    outside=[r for r in ledger if not r['full_pattern']]
    result=dict(rules=RULES, source_feature_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        rules_sha256=hashlib.sha256(json.dumps(RULES,sort_keys=True).encode()).hexdigest(),
        interpretation='Retrospective stability replay of previously inspected data, not new independent validation.',
        time_basis='UTC Monday-Sunday, rolling match-time histories (not a frozen Monday shortlist)',
        split_date=data['split_date'], summary=summary, weeks=weeks, picks=ledger,
        excluded_by_environment=dict(all=measure(outside),later=measure([r for r in outside if r['date'][:10]>=data['split_date']])))
    assert summary['full_pattern']['all']['n']==185
    assert summary['benchmark']['all']['n']==660
    assert sum(w['full_pattern']['hits'] for w in weeks)==150
    assert sum(w['benchmark']['hits'] for w in weeks)==523
    (OUT/'weekly_pattern_replay.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    def fmt(m):
        return f"{m['hits']}/{m['n']} ({m['rate']}%)" if m['n'] else '—'
    lines=['# Fixed-rule weekly backtest','',
        'Completed retrospective replay of the existing MLS sample. Rules unchanged; no threshold optimisation. This breaks the earlier result into weeks, not a new independent sample.','',
        '| Version | All picks | Later picks | Active weeks | Active weeks below 70% |',
        '|---|---:|---:|---:|---:|']
    for name,m in summary.items():
        lines.append(f"| {name} | {fmt(m['all'])} | {fmt(m['later'])} | {m['active_weeks']} | {m['weeks_below_70pct']} |")
    lines+=['','## Year-by-year stability','','| Year | Full pattern | Consistent-shooter benchmark |','|---|---:|---:|']
    for year in summary['benchmark']['by_year']:
        lines.append(f"| {year} | {fmt(summary['full_pattern']['by_year'][year])} | {fmt(summary['benchmark']['by_year'][year])} |")
    lines+=['','## Meaning','',
        'The full pattern remains promising, but the home-environment filter has not demonstrated additional value beyond consistent main shooters in later matches. Both versions use eligible HOME starters; the benchmark is not an all-home-and-away player pool.',
        f"The environment filtered out {fmt(result['excluded_by_environment']['all'])} overall and {fmt(result['excluded_by_environment']['later'])} in the later period. These are disjoint from the full-pattern picks; the benchmark includes both groups.",
        '', '## Replay rules and limitations','',
        '- Full pattern: home side stronger on season and last-five PPG; home venue shots >=12, away venue shots conceded >=12, home shot proxy exceeds away; top-two eligible home starters by prior shots per start; prior five-start average minutes >=70; at least four of five starts with 2+ shots.',
        '- At least eight saved season results and three venue matches per team. Player history: five starts in 180 days, same team/competition. Rank ties use earlier shot share then ID. No threshold changes.',
        '- Monday–Sunday UTC weeks, including zero-pick weeks. Histories roll forward at each match with a >24-hour buffer. This is a lineup-time replay, not a Saturday-morning shortlist: actual starting status is assumed available.',
        '- Current results never enter selection. Personal and team features independently checked against read-only source records. Actual publication timestamps and historic lineup announcements are not available, so live availability cannot be certified.',
        '- All qualifying picks appear in the JSON/HTML ledger. Missing outcomes stay unknown and are not losses. No odds or return calculations.',
        '- Saved match coverage is incomplete; a zero-pick week does not prove zero opportunities in the full league. Offseason/gaps remain visible. Short weeks can have very volatile rates; picks share players and fixtures.',
        '- Later period starts '+data['split_date']+' and was already examined. Freeze both variants for fresh forward testing. Existing replacement reconciliation is unchanged.',
        '', '## Every week','', '| Week starting (UTC) | Saved finished MLS fixtures | Eligible fixtures | Full pattern | Benchmark |','|---|---:|---:|---:|---:|']
    for w in weeks:
        lines.append(f"| {w['week_start']} | {w['source_finished_mls_fixtures']} | {w['eligible_fixtures']} | {fmt(w['full_pattern'])} | {fmt(w['benchmark'])} |")
    (OUT/'weekly_pattern_replay.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    tr=''.join(f"<tr><td>{w['week_start']}</td><td>{w['eligible_fixtures']}</td><td>{fmt(w['full_pattern'])}</td><td>{fmt(w['benchmark'])}</td></tr>" for w in weeks)
    details=''
    for w in weeks:
        picks=[r for r in ledger if r['week_start']==w['week_start']]
        if not picks:
            continue
        body=''.join(f"<tr><td>{r['date'][:16]}</td><td>{escape(r['fixture'])}</td><td>{escape(r['player'])}</td><td>{'Full + benchmark' if r['full_pattern'] else 'Benchmark only'}</td><td>{r['recent_hits']}/5</td><td>{r['recent_minutes']:.1f}</td><td>{r['shots']}</td><td>{r['outcome']}</td></tr>" for r in picks)
        details+=f'<details><summary>{w["week_start"]} · {len(picks)} benchmark picks</summary><div class="scroll"><table><tr><th>UTC kickoff</th><th>Fixture</th><th>Player</th><th>Version</th><th>Prior hits</th><th>Prior avg minutes</th><th>Shots</th><th>Result</th></tr>{body}</table></div></details>'
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Weekly pattern replay</title>
    <style>body{{font:16px/1.6 system-ui;margin:24px auto;padding:0 20px;max-width:1150px;color:#182b3e;background:#f2f5f8}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #ddd}}.scroll{{overflow:auto}}details{{margin:12px 0;background:white;padding:12px}}summary{{cursor:pointer}}h1{{line-height:1.2}}a{{color:#216e83}}</style>
    <h1>Fixed-rule weekly backtest</h1><p>Full pattern: <b>150/185 — 81.1%</b>. Consistent home-shooter benchmark: <b>523/660 — 79.2%</b>.</p>
    <p>Later matches: full pattern <b>46/57 — 80.7%</b>; benchmark <b>152/184 — 82.6%</b>. The environment's additional value remains unproven.</p>
    <p>Previously inspected MLS data, not new independent validation. Rolling lineup-time replay; UTC weeks. Zero picks may reflect missing history. No odds/profit test.</p>
    <p><a href="weekly_pattern_replay.md">Rules and weekly report</a> · <a href="weekly_pattern_replay.json">Every pick and pre-match features</a> · <a href="project_site/dist/index.html#weekly-replay">Project dashboard</a></p>
    <h2>Every week</h2><div class="scroll"><table><tr><th>Week starting</th><th>Eligible fixtures</th><th>Full pattern</th><th>Benchmark</th></tr>{tr}</table></div>
    <h2>Every qualifying player: expand a week</h2>{details}</html>'''
    (OUT/'weekly_pattern_replay.html').write_text(html,encoding='utf-8')
    page=OUT/'project_site/dist/index.html'
    html=page.read_text(encoding='utf-8')
    start,end='<!-- WEEKLY_REPLAY_START -->','<!-- WEEKLY_REPLAY_END -->'
    if start in html:
        before,tail=html.split(start,1)
        html=before+tail.split(end,1)[1]
    panel=f'''{start}<section id="weekly-replay" class="panel" style="margin:24px 0"><div class="eyebrow">FIXED-RULE WEEKLY BACKTEST · COMPLETE</div>
    <h2>81.1% overall; 80.7% in the later sample</h2><p>Full pattern: 150/185 hits across {summary['full_pattern']['active_weeks']} active weeks. Consistent home-shooter benchmark: 523/660 (79.2%); later 152/184 (82.6%). Every qualifying player and every calendar week are saved.</p>
    <p class="note">This replays previously inspected MLS data, not new proof. Home-environment filtering has not shown a clear improvement beyond player consistency in later matches. Next: compare both frozen rules on fresh matches.</p>
    <p><a href="../../weekly_pattern_replay.html">Open weekly backtest and every pick</a> · <a href="../../weekly_pattern_replay.md">Read report</a></p></section>{end}'''
    page.write_text(html.replace('</header>','</header>'+panel,1),encoding='utf-8')
    print(json.dumps(dict(summary=summary,calendar_weeks=len(weeks),excluded=result['excluded_by_environment']),indent=2))


if __name__=='__main__':
    main()
