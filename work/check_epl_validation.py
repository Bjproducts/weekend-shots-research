import json
import argparse
from collections import defaultdict
from datetime import datetime,timedelta
from statistics import mean
from pathlib import Path
from zipfile import ZipFile

parser=argparse.ArgumentParser()
parser.add_argument('--slug',default='epl_2015_16_validation')
args=parser.parse_args()
out=Path(__file__).resolve().parents[1]/'outputs'/args.slug
raw=json.loads((out/'normalized_matches.json').read_text(encoding='utf-8'))
features=json.loads((out/'feature_replay.json').read_text(encoding='utf-8'))
samples=json.loads((out/'all_samples.json').read_text(encoding='utf-8'))
picks=json.loads((out/'qualifying_picks.json').read_text(encoding='utf-8'))
original=json.loads((out.parent/'weekly_pattern_replay.json').read_text(encoding='utf-8'))
manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
assert manifest['rules_sha256']==original['rules_sha256']
by_id={r['fixture']['id']:r for r in raw}
player_history=defaultdict(list);team_history=defaultdict(list)
for rec in raw:
    f=rec['fixture'];date=datetime.fromisoformat(f['date'])
    for home in [True,False]:
        tid=f['home_team' if home else 'away_team']['id'];other=f['away_team' if home else 'home_team']['id']
        ps=[p for p in rec['players'] if p['team_id']==tid];op=[p for p in rec['players'] if p['team_id']==other]
        assert sum(p['started'] for p in ps)==11
        assert sum(p['shots'] for p in ps)==ps[0]['team_shots']
        gf,ga=(f['home_score'],f['away_score']) if home else (f['away_score'],f['home_score'])
        team_history[tid].append(dict(date=date,home=home,points=3 if gf>ga else 1 if gf==ga else 0,shots=sum(p['shots'] for p in ps),against=sum(p['shots'] for p in op)))
    for p in rec['players']:
        if p['started']:player_history[p['team_id'],p['player']['id']].append(dict(p,date=date,fixture_id=f['id']))
for r in features['rows']:
    date=datetime.fromisoformat(r['date']);cutoff=date-timedelta(days=1)
    f=by_id[r['fixture_id']]['fixture'];tid=f['home_team']['id']
    prior=[p for p in player_history[tid,r['player_id']] if date-timedelta(days=180)<=p['date']<cutoff][-5:]
    assert len(prior)==5
    assert r['prior_fixture_ids']==[p['fixture_id'] for p in prior]
    assert r['recent_shots']==mean(p['shots'] for p in prior)
    assert r['recent_hits']==sum(p['shots']>=2 for p in prior)
    assert r['recent_minutes']==mean(p['minutes_played'] for p in prior)
for r in features['environments']:
    cutoff=datetime.fromisoformat(r['date'])-timedelta(days=1)
    f=by_id[r['fixture_id']]['fixture']
    h=[x for x in team_history[f['home_team']['id']] if x['date']<cutoff]
    a=[x for x in team_history[f['away_team']['id']] if x['date']<cutoff]
    hv=[x for x in h if x['home']][-5:];av=[x for x in a if not x['home']][-5:]
    assert len(h)>=8 and len(a)>=8 and len(hv)>=3 and len(av)>=3
    assert r['home_ppg']==mean(x['points'] for x in h)
    assert r['away_ppg']==mean(x['points'] for x in a)
    assert r['home_recent_ppg']==mean(x['points'] for x in h[-5:])
    assert r['away_recent_ppg']==mean(x['points'] for x in a[-5:])
    assert r['projected_home_shots']==(mean(x['shots'] for x in hv)+mean(x['against'] for x in av))/2
    assert r['projected_away_shots']==(mean(x['shots'] for x in av)+mean(x['against'] for x in hv))/2
assert len(samples)==sum(len(r['players']) for r in raw)
assert len(picks)==manifest['summary']['benchmark']['overall']['n']
assert sum(r['full_pattern'] for r in picks)==manifest['summary']['full_pattern']['overall']['n']
assert sum(r['full_pattern'] and r['hit'] for r in picks)==manifest['summary']['full_pattern']['overall']['hits']
assert all(r['exclusion_reasons'] for r in samples if not r['benchmark'])
with ZipFile(out.parent/(args.slug+'.zip')) as z:assert z.testzip() is None
print(f'PASS: same frozen rule hash, 380 match totals, {len(samples)} samples, independent lagged player/team feature reconstruction, full ledger, and archive CRC.')
