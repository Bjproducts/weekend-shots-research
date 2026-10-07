"""Verify the saved partial replay without any network access."""
import json
from pathlib import Path
from datetime import datetime,timedelta
from statistics import mean
from collections import defaultdict
from zipfile import ZipFile
from weekly_pattern_replay import choose

out=Path(__file__).resolve().parents[1]/'outputs/bundesliga_2024_25_validation'
records=json.loads((out/'normalized_matches.json').read_text(encoding='utf-8'))
catalog=json.loads((out/'fixture_catalog.json').read_text(encoding='utf-8'))
samples=json.loads((out/'all_samples.json').read_text(encoding='utf-8'))
report=json.loads((out/'screening_report.json').read_text(encoding='utf-8'))
features=json.loads((out/'feature_replay.json').read_text(encoding='utf-8'))
audits=json.loads((out/'cleaning_audit.json').read_text(encoding='utf-8'))
old=json.loads((out.parent/'weekly_pattern_replay.json').read_text(encoding='utf-8'))
assert report['rules_sha256']==old['rules_sha256']
assert len(catalog)==306 and len({r['id'] for r in catalog})==306
assert [r['fixture']['id'] for r in records]==[r['id'] for r in catalog[:len(records)]]
assert len(samples)==sum(len(r['players']) for r in records)
assert len(samples)==len({(r['fixture_id'],r['player_id']) for r in samples})
accepted={r['fixture_id'] for r in audits if r['accepted']}
hist=defaultdict(list);team_hist=defaultdict(list);fixtures={r['fixture']['id']:r['fixture'] for r in records}
for r in records:
    f=r['fixture']
    for home in [True,False]:
        tid=f['home_team' if home else 'away_team']['id'];other=f['away_team' if home else 'home_team']['id']
        ps=[p for p in r['players'] if p['team_id']==tid];opp=[p for p in r['players'] if p['team_id']==other]
        gf,ga=(f['home_score'],f['away_score']) if home else (f['away_score'],f['home_score'])
        team_hist[tid].append(dict(date=datetime.fromisoformat(f['date']),home=home,points=3 if gf>ga else 1 if gf==ga else 0,
            shots=sum(p['shots'] for p in ps) if f['id'] in accepted else None,
            against=sum(p['shots'] for p in opp) if f['id'] in accepted else None))
    if r['fixture']['id'] not in accepted:continue
    for p in r['players']:
        if p['started']:hist[p['team_id'],p['player']['id']].append(dict(p,fixture_id=r['fixture']['id'],date=datetime.fromisoformat(r['fixture']['date'])))
for r in features['rows']:
    date=datetime.fromisoformat(r['date']);team=fixtures[r['fixture_id']]['home_team']['id']
    prior=[p for p in hist[team,r['player_id']] if date-timedelta(days=180)<=p['date']<date-timedelta(days=1)][-5:]
    assert len(prior)==5 and [p['fixture_id'] for p in prior]==r['prior_fixture_ids']
    assert r['recent_shots']==mean(p['shots'] for p in prior)
    assert r['recent_hits']==sum(p['shots']>=2 for p in prior)
    if r['recent_minutes'] is not None:assert r['recent_minutes']==mean(p['minutes_played'] for p in prior)
for r in features['environments']:
    f=fixtures[r['fixture_id']];cutoff=datetime.fromisoformat(r['date'])-timedelta(days=1)
    h=[p for p in team_hist[f['home_team']['id']] if p['date']<cutoff]
    a=[p for p in team_hist[f['away_team']['id']] if p['date']<cutoff]
    hv=[p for p in h if p['home'] and p['shots'] is not None][-5:]
    av=[p for p in a if not p['home'] and p['shots'] is not None][-5:]
    assert len(h)>=8 and len(a)>=8 and len(hv)>=3 and len(av)>=3
    assert r['home_ppg']==mean(p['points'] for p in h)
    assert r['away_ppg']==mean(p['points'] for p in a)
    assert r['home_recent_ppg']==mean(p['points'] for p in h[-5:])
    assert r['away_recent_ppg']==mean(p['points'] for p in a[-5:])
    assert r['projected_home_shots']==(mean(p['shots'] for p in hv)+mean(p['against'] for p in av))/2
    assert r['projected_away_shots']==(mean(p['shots'] for p in av)+mean(p['against'] for p in hv))/2
for r in samples:
    if r['features']:
        decision=choose({k:r['features'][k] for k in ['shooter_rank','recent_minutes','recent_hits','environment']})
        assert all(r[k]==v for k,v in decision.items())
    if not r['benchmark']:assert r['exclusion_reasons']
for v,m in report['summary'].items():
    picks=[r for r in samples if r[v]]
    assert m['n']==sum(r['hit'] is not None for r in picks)
    assert m['hits']==sum(r['hit'] is True for r in picks)
with ZipFile(out.parent/'bundesliga_2024_25_validation.zip') as z:assert z.testzip() is None
print(f'PASS: {len(records)} chronological fixtures, {len(samples)} complete sample records, unchanged rules, lagged player features, settlements and archive.')
