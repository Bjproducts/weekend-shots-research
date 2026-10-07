import json
from pathlib import Path
from datetime import datetime,timedelta
from mls_2026_weekends import weekend_key
from weekly_pattern_replay import choose

out=Path(__file__).resolve().parents[1]/'outputs'
d=json.loads((out/'mls_2026_weekends/replay.json').read_text(encoding='utf-8'))
old=json.loads((out/'weekly_pattern_replay.json').read_text(encoding='utf-8'))
assert d['rules_sha256']==old['rules_sha256']
assert len(d['weeks'])==39
assert weekend_key('2026-08-17 02:30:00')=='2026-08-15' # UTC Monday / Denver Sunday
assert weekend_key('2026-08-15 01:00:00') is None # UTC Saturday / Denver Friday
assert len({(r['fixture_id'],r['player_id']) for r in d['samples']})==len(d['samples'])
for left,right in zip(d['weeks'],d['weeks'][1:]):
    assert datetime.fromisoformat(right['saturday'])-datetime.fromisoformat(left['saturday'])==timedelta(days=7)
for r in d['samples']:
    assert weekend_key(r['date'])==r['weekend']
    a=choose({k:r[k] for k in ['shooter_rank','recent_minutes','recent_hits','environment']})['full_pattern']
    assert a==r['A'] and r['B']==(a and r['recent_shots']>=3 and r['recent_minutes']>=80)
for v in ['A','B']:
    picks=[r for r in d['picks'] if r[v]]
    assert len(picks)==d['summary'][v]['n']==sum(w[v]['n'] for w in d['weeks'])
    assert sum(r['hit'] for r in picks)==d['summary'][v]['hits']==sum(w[v]['hits'] for w in d['weeks'])
assert d['summary']['A']['hits']==30 and d['summary']['B']['hits']==21
assert all(r['A'] for r in d['picks'])
assert all('not verified' in w['status'] for w in d['weeks'] if w['saved_fixtures']==0)
print('PASS: 39 weekends, timezone boundary tests, frozen A/B rules, pick identities, totals and coverage labels.')
