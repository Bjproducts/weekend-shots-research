"""Independent checks against read-only source rows and stored research output."""
import json
from datetime import datetime,timedelta
from pathlib import Path
from statistics import mean
from test_home_pattern import connect,measure

result=json.loads((Path(__file__).resolve().parents[1]/'outputs/home_environment_pattern_test.json').read_text(encoding='utf-8'))
c=connect()
rows=result['rows']
assert len({(r['fixture_id'],r['player_id']) for r in rows})==len(rows)
for r in rows:
    current=dict(c.execute('select * from player_fixture_stats where fixture_id=? and player_id=?',(r['fixture_id'],r['player_id'])).fetchone())
    assert current['started'] and current['home']
    assert r['shots']==current['shots']
    assert r['hit']==(current['shots']>=2)
    marks=','.join('?' for _ in r['prior_fixture_ids'])
    prior=list(c.execute(f'''select p.*,f.fixture_date from player_fixture_stats p join fixtures f on f.id=p.fixture_id
        where p.player_id=? and p.fixture_id in ({marks})''',[r['player_id']]+r['prior_fixture_ids']))
    assert len(prior)==5
    assert all(p['team_id']==current['team_id'] and p['started'] for p in prior)
    assert all(datetime.fromisoformat(p['fixture_date'])<datetime.fromisoformat(r['date'])-timedelta(days=1) for p in prior)
    assert r['recent_shots']==mean(p['shots'] for p in prior)
    assert r['recent_hits']==sum(p['shots']>=2 for p in prior)
    if r['recent_minutes'] is not None:
        assert r['recent_minutes']==mean(p['minutes_played'] for p in prior)
    if r['recent_share'] is not None:
        assert abs(r['recent_share']-mean(p['shots']/p['team_shots'] for p in prior))<1e-12
base=[r for r in rows if r['shooter_rank']<=2]
strict=[r for r in base if r['environment'] and r['recent_minutes'] is not None and r['recent_minutes']>=70 and r['recent_hits']>=4]
assert measure(base)==result['rules']['Top 2 home shooters (baseline)']['all']
assert measure(strict)==result['rules']['Full environment + minutes >=70 + 4/5 recent hits']['all']
assert sum(r['date'][:10]>=result['split_date'] for r in strict)==57
assert all(r['stronger'] and r['shooting'] for r in strict)
assert measure([])['rate'] is None
print(f'PASS: {len(rows)} unique player outcomes, starter/home identity, 5-match history, cutoff, shots/minutes/share arithmetic, and summary counts.')
