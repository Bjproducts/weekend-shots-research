"""Read-only, pre-match home-strength / main-shooter research."""
import sqlite3
import json
from html import escape
from collections import defaultdict
from datetime import datetime, timedelta
from statistics import mean
from pathlib import Path

DB = Path('C:/Users/bjpro/OneDrive/Desktop/SHOT ON TARGET/backend/sot_sportsapi.db')

def connect():
    c = sqlite3.connect(DB.as_uri() + '?mode=ro', uri=True)
    c.row_factory = sqlite3.Row
    return c

def avg(rows, key):
    vals = [r[key] for r in rows if r[key] is not None]
    return mean(vals) if vals else None

def measure(rows, key='hit'):
    known = [r for r in rows if r[key] is not None]
    n = len(known)
    k = sum(r[key] for r in known)
    if not n:
        return dict(hits=0, n=0, rate=None, missing=len(rows), fixtures=0)
    p = k / n
    z = 1.96
    center = (p + z*z/(2*n))/(1+z*z/n)
    half = z*((p*(1-p)/n+z*z/(4*n*n))**.5)/(1+z*z/n)
    return dict(hits=k, n=n, rate=round(100*p, 1), missing=len(rows)-n,
                fixtures=len({r['fixture_id'] for r in known}),
                wilson95=[round(100*(center-half), 1), round(100*(center+half), 1)])

def run(connection=None, provider='sportsapipro', save=True):
    c = connection if connection is not None else connect()
    fixtures = [dict(r) for r in c.execute('''select f.*, c.name competition,
        h.name home_name, a.name away_name from fixtures f
        join competitions c on c.id=f.competition_id
        join teams h on h.id=f.home_team_id join teams a on a.id=f.away_team_id
        where f.status='finished' and c.is_competitive=1 order by fixture_date,id''')]
    players = defaultdict(list)
    for r in c.execute('''select p.*, coalesce(n.common_name,n.full_name) player
        from player_fixture_stats p join players n on n.id=p.player_id
        where p.data_source=? ''', (provider,)):
        players[r['fixture_id']].append(dict(r))
    team_history, player_history = defaultdict(list), defaultdict(list)
    candidates, environments = [], []
    conflicts = 0
    for f in fixtures:
        date = datetime.fromisoformat(f['fixture_date'])
        # A conservative one-day buffer avoids same-day matches entering history.
        cutoff = date - timedelta(days=1)
        cid, sid, hid, aid = (f[k] for k in ['competition_id','season_id','home_team_id','away_team_id'])
        h = [r for r in team_history[cid,sid,hid] if r['date'] < cutoff]
        a = [r for r in team_history[cid,sid,aid] if r['date'] < cutoff]
        hv = [r for r in h if r['home'] and r['shots'] is not None and r['against'] is not None][-5:]
        av = [r for r in a if not r['home'] and r['shots'] is not None and r['against'] is not None][-5:]
        totals = {}
        for tid in [hid, aid]:
            vals = {p['team_shots'] for p in players[f['id']] if p['team_id']==tid and p['team_shots'] is not None}
            totals[tid] = next(iter(vals)) if len(vals)==1 else None
            conflicts += int(len(vals)>1)
        if len(h)>=8 and len(a)>=8 and len(hv)>=3 and len(av)>=3:
            strength = avg(h,'points') > avg(a,'points') and avg(h[-5:],'points') > avg(a[-5:],'points')
            projected_home = (avg(hv,'shots') + avg(av,'against'))/2
            projected_away = (avg(av,'shots') + avg(hv,'against'))/2
            shooting = avg(hv,'shots')>=12 and avg(av,'against')>=12 and projected_home>projected_away
            env = dict(fixture_id=f['id'], date=f['fixture_date'], competition=f['competition'],
                fixture=f['home_name']+' vs '+f['away_name'], stronger=strength, shooting=shooting,
                environment=strength and shooting, home_ppg=avg(h,'points'), away_ppg=avg(a,'points'),
                home_recent_ppg=avg(h[-5:],'points'), away_recent_ppg=avg(a[-5:],'points'),
                home_home_shots=avg(hv,'shots'), away_away_conceded=avg(av,'against'),
                projected_home_shots=projected_home, projected_away_shots=projected_away,
                actual_home_shots=totals[hid], actual_away_shots=totals[aid],
                home_outshot_away=(totals[hid]>totals[aid]) if all(totals[t] is not None for t in [hid,aid]) else None)
            environments.append(env)
            ranked=[]
            for p in players[f['id']]:
                if p['team_id'] != hid or not p['started']:
                    continue
                prior = [r for r in player_history[cid,hid,p['player_id']]
                         if date-timedelta(days=180) <= r['date'] < cutoff][-5:]
                if len(prior)!=5 or any(r['shots'] is None for r in prior):
                    continue
                assert all(r['date'] < cutoff for r in prior)
                share = [r['shots']/r['team_shots'] for r in prior if r['team_shots'] and r['shots'] is not None]
                ranked.append(dict(player=p['player'], player_id=p['player_id'], shots=p['shots'],
                    prior_fixture_ids=[r['fixture_id'] for r in prior],
                    hit=p['shots']>=2 if p['shots'] is not None else None,
                    recent_shots=avg(prior,'shots'), recent_share=mean(share) if len(share)==5 else None,
                    recent_minutes=avg(prior,'minutes_played') if all(r['minutes_played'] is not None for r in prior) else None,
                    recent_hits=sum(r['shots']>=2 for r in prior)))
            ranked.sort(key=lambda r: (-r['recent_shots'], -(r['recent_share'] or 0), r['player_id']))
            for rank,p in enumerate(ranked,1):
                candidates.append(dict(**env, **p, shooter_rank=rank))
        # Outcomes enter history only after all features for this fixture are built.
        if f['home_score'] is not None and f['away_score'] is not None:
            for tid,other,home in [(hid,aid,True),(aid,hid,False)]:
                gf,ga = (f['home_score'],f['away_score']) if home else (f['away_score'],f['home_score'])
                team_history[cid,sid,tid].append(dict(date=date, home=home,
                    points=3 if gf>ga else 1 if gf==ga else 0, shots=totals[tid],against=totals[other]))
        for p in players[f['id']]:
            if p['started'] and p['team_id'] in [hid,aid]:
                player_history[cid,p['team_id'],p['player_id']].append(dict(p,date=date))
    assert environments, 'Insufficient team history'
    dates=sorted({r['date'][:10] for r in environments})
    split=dates[int(.7*len(dates))]
    rules = {
        'All eligible home starters': lambda r: True,
        'Top 2 home shooters (baseline)': lambda r:r['shooter_rank']<=2,
        'Top 2 + stronger home team': lambda r:r['shooter_rank']<=2 and r['stronger'],
        'Top 2 + full home environment': lambda r:r['shooter_rank']<=2 and r['environment'],
        'Full environment + recent minutes >=70': lambda r:r['shooter_rank']<=2 and r['environment'] and r['recent_minutes'] is not None and r['recent_minutes']>=70,
        'Full environment + minutes >=70 + 4/5 recent hits': lambda r:r['shooter_rank']<=2 and r['environment'] and r['recent_minutes'] is not None and r['recent_minutes']>=70 and r['recent_hits']>=4,
        'Top 2 + minutes >=70 + 4/5 hits WITHOUT environment filter': lambda r:r['shooter_rank']<=2 and r['recent_minutes'] is not None and r['recent_minutes']>=70 and r['recent_hits']>=4,
    }
    result = dict(source=str(DB), target='2+ total shots', split_date=split,
        source_fixtures=len(fixtures), eligible_fixtures=len(environments), conflicting_team_totals=conflicts,
        rules={}, environment_check={}, league_counts={}, environments=environments, rows=candidates)
    for name,rule in rules.items():
        subset=[r for r in candidates if rule(r)]
        result['rules'][name]={label:measure([r for r in subset if test(r)]) for label,test in {
            'all':lambda r:True, 'earlier':lambda r:r['date'][:10]<split, 'later':lambda r:r['date'][:10]>=split}.items()}
    for label,subset in [('all_eligible',environments),('stronger',[r for r in environments if r['stronger']]),('full_environment',[r for r in environments if r['environment']])]:
        result['environment_check'][label]={period:measure([r for r in subset if test(r)],'home_outshot_away') for period,test in {
            'all':lambda r:True,'later':lambda r:r['date'][:10]>=split}.items()}
    for league in sorted({r['competition'] for r in environments}):
        result['league_counts'][league]=sum(r['competition']==league for r in environments)
    if not save:
        return result
    out=Path(__file__).resolve().parents[1]/'outputs'
    (out/'home_environment_pattern_test.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    def cell(m):
        return f"{m['hits']}/{m['n']} ({m['rate']}%)" if m['n'] else 'No cases'
    lines=['# Home strength → main shooter: first historical test','',
        'Question: does a stronger home team with a favourable shooting matchup improve its main shooters’ 2+ shots hit rate?', '',
        '## Finding', '',
        'The full environment plus recent minutes and 4/5 consistency produced 150/185 hits (81.1%); later matches were 46/57 (80.7%). The environment identified home shot dominance in 118/160 matches (73.8%), versus 62.6% across eligible home sides.', '',
        'However, consistent main shooters WITHOUT the environment filter hit 152/184 (82.6%) in later matches. The environment’s extra benefit beyond player consistency is therefore unproven. Keep both versions for a fresh forward check; do not advertise an established 81% win rate.', '',
        f"Eligible fixtures: {len(environments)}. Competitions: {result['league_counts']}. Later-match check starts {split} (last 30% of eligible calendar dates).",'',
        '| Filter | Earlier matches | Later matches | Overall |','|---|---:|---:|---:|']
    for name,counts in result['rules'].items():
        lines.append(f"| {name} | {cell(counts['earlier'])} | {cell(counts['later'])} | {cell(counts['all'])} |")
    lines += ['', '## Does the home team actually take more shots?', '',
        '| Environment | All matches | Later matches |','|---|---:|---:|']
    for name,m in result['environment_check'].items():
        lines.append(f"| {name} | {cell(m['all'])} | {cell(m['later'])} |")
    lines += ['', '## Fixed definitions', '',
        '- Stronger: higher season-to-date points per game AND higher last-five points per game than the away side; at least eight earlier matches per side, within the same competition and season.',
        '- Shooting matchup: home side averages at least 12 shots in its last up-to-five home matches; away side concedes at least 12 in its last up-to-five away matches. Minimum three venue matches each. Home projection (home shots + away conceded)/2 must exceed the analogous away projection. These are simple historical proxies, not a trained forecast.',
        '- Main shooters: top two of the recorded home starters with five earlier starts for that team/competition within 180 days, ranked by last-five average total shots; prior shot share breaks ties, then player ID. Players without five known shot counts are unranked. This ranks eligible confirmed starters, not an inferred whole squad.',
        '- Minutes filter uses prior starts only. Consistency means 2+ shots in at least four of those five earlier starts. No current-match minutes, score, shot share or shot totals select candidates.',
        '- All features use history more than 24 hours before kickoff. Current starting status is assumed known at lineup time. Each player-match counts once; two candidates in one match are correlated.', '',
        '## Limits', '',
        '- This tests the separate saved provider database, not the undated ticket sample or its 79.3% selected-history rate. Replacement reconciliation remains unchanged: 12 provisional original-player totals and three unresolved players.',
        '- Season form means the available saved results, not a independently verified complete league table. Coverage is strongly MLS-weighted; sparse other leagues may fail eligibility.',
        '- Later data is a retrospective stability check, not an untouched prospective trial. Rules were specified before running this script; no threshold sweep was performed. Known completion/publication timestamps are absent, so exact live data availability is not certified.',
        '- Missing outcomes are excluded and counted in JSON; conflicting team totals are treated as unknown. No profit claim: prices and betting returns were not tested.',
        '- A high percentage on a small subset is a hypothesis, not a proven win rate. JSON includes counts, fixture counts and descriptive Wilson intervals; those intervals do not account for within-player/fixture dependence.', '',
        'Detailed per-player features/outcomes and full counts: home_environment_pattern_test.json. Reproduce: python work/test_home_pattern.py.', '']
    (out/'home_environment_pattern_test.md').write_text('\n'.join(lines),encoding='utf-8')
    page=out/'project_site/dist/index.html'
    if page.exists():
        start,end='<!-- HOME_PATTERN_START -->','<!-- HOME_PATTERN_END -->'
        html=page.read_text(encoding='utf-8')
        if start in html:
            before,tail=html.split(start,1)
            html=before+tail.split(end,1)[1]
        table=''.join(f"<tr><td>{escape(name)}</td><td>{cell(m['all'])}</td><td>{cell(m['later'])}</td></tr>" for name,m in result['rules'].items() if name!='All eligible home starters')
        section=f'''{start}<section id="home-pattern" class="panel" style="margin:24px 0">
        <div class="eyebrow">NEW · ENVIRONMENT-FIRST PATTERN TEST · 26 SEP 2026</div>
        <h2>Stronger home team → main shooters</h2>
        <p>665 eligible MLS fixtures. Stronger means better season-to-date and last-five points per game.
        The shooting filter combines home shot creation with away shots conceded. Main shooters are the top two eligible starters by earlier shots per start.</p>
        <div class="tablewrap"><table><thead><tr><th>Filter</th><th>All player-matches</th><th>Later matches (from 26 Oct 2025)</th></tr></thead><tbody>{table}</tbody></table></div>
        <p>The full environment correctly identified the home side taking more shots in <b>118/160 matches (73.8%)</b>; later: <b>32/43 (74.4%)</b>.</p>
        <p class="note"><b>Promising, not proven:</b> the strict pattern hit 150/185 (81.1%), but consistent shooters without the environment filter did slightly better in later matches. The environment's extra value is not established. Retrospective, MLS-only evidence; no odds or profitability tested.</p>
        <p><b>Next:</b> freeze these two versions and compare them on fresh matches. Use confirmed starters; do not tune thresholds to this result. Existing ticket reconciliation stays unchanged.</p>
        <p><a href="../../home_environment_pattern_test.md">Definitions and results</a> · <a href="../../home_environment_pattern_test.json">Detailed match evidence</a></p></section>{end}'''
        assert '</header>' in html
        page.write_text(html.replace('</header>','</header>'+section,1),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','environments')},indent=2))

if __name__ == '__main__':
    run()
