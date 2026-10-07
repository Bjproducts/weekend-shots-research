import json,gzip,hashlib
from pathlib import Path
from datetime import datetime,timedelta
from collections import defaultdict
from statistics import mean
from zipfile import ZipFile
from weekly_pattern_replay import choose

out=Path(__file__).resolve().parents[1]/'outputs/ligue1_2015_16_ab_validation'
records=json.loads((out/'normalized_matches.json').read_text(encoding='utf-8'))
samples=json.loads((out/'all_samples.json').read_text(encoding='utf-8'))
result=json.loads((out/'ab_results.json').read_text(encoding='utf-8'))
replay=json.loads((out/'feature_replay.json').read_text(encoding='utf-8'))
catalog=json.loads(gzip.decompress((out/'raw/matches/7/27.json.gz').read_bytes()))
gaps=json.loads((out/'coverage_audit.json').read_text())
old=json.loads((out.parent/'weekly_pattern_replay.json').read_text(encoding='utf-8'))
assert result['baseline_rules_sha256']==old['rules_sha256']
assert result['plan_sha256']==hashlib.sha256((out.parent.parent/'work/ligue1_ab_plan.json').read_bytes()).hexdigest()
assert len(records)==377 and len(samples)==10479
assert len({(r['fixture_id'],r['player_id']) for r in samples})==len(samples)
rounds={r['match_id']:r['match_week'] for r in catalog};fh={r['fixture']['id']:r['fixture'] for r in records}
hist=defaultdict(list);th=defaultdict(list)
for rec in records:
    f=rec['fixture'];date=datetime.fromisoformat(f['date'])
    for home in [True,False]:
        tid=f['home_team' if home else 'away_team']['id'];other=f['away_team' if home else 'home_team']['id']
        ps=[p for p in rec['players'] if p['team_id']==tid];opp=[p for p in rec['players'] if p['team_id']==other]
        assert sum(p['started'] for p in ps)==11
        assert all(p['team_shots']==sum(q['shots'] for q in ps) for p in ps)
        assert all(0<=p['shots_on_target']<=p['shots'] for p in ps)
        gf,ga=(f['home_score'],f['away_score']) if home else (f['away_score'],f['home_score'])
        th[tid].append(dict(date=date,round=rounds[f['id']],home=home,shots=sum(p['shots'] for p in ps),against=sum(p['shots'] for p in opp),points=3 if gf>ga else 1 if gf==ga else 0))
    for p in rec['players']:
        if p['started']:hist[p['team_id'],p['player']['id']].append(dict(p,date=date,fixture_id=f['id']))
for r in replay['rows']:
    date=datetime.fromisoformat(r['date']);tid=fh[r['fixture_id']]['home_team']['id']
    prior=[p for p in hist[tid,r['player_id']] if date-timedelta(days=180)<=p['date']<date-timedelta(days=1)][-5:]
    assert [p['fixture_id'] for p in prior]==r['prior_fixture_ids'] and len(prior)==5
    assert mean(p['shots'] for p in prior)==r['recent_shots']
    assert mean(p['minutes_played'] for p in prior)==r['recent_minutes']
    assert sum(p['shots']>=2 for p in prior)==r['recent_hits']
for r in replay['environments']:
    f=fh[r['fixture_id']];cutoff=datetime.fromisoformat(r['date'])-timedelta(days=1)
    h=[p for p in th[f['home_team']['id']] if p['date']<cutoff];a=[p for p in th[f['away_team']['id']] if p['date']<cutoff]
    assert r['home_ppg']==mean(p['points'] for p in h) and r['away_ppg']==mean(p['points'] for p in a)
    assert r['home_recent_ppg']==mean(p['points'] for p in h[-5:]) and r['away_recent_ppg']==mean(p['points'] for p in a[-5:])
    hv=[p for p in h if p['home']][-5:];av=[p for p in a if not p['home']][-5:]
    assert r['projected_home_shots']==(mean(p['shots'] for p in hv)+mean(p['against'] for p in av))/2
    assert r['projected_away_shots']==(mean(p['shots'] for p in av)+mean(p['against'] for p in hv))/2
for r in gaps:
    f=fh[r['fixture_id']];cutoff=datetime.fromisoformat(f['date'])-timedelta(days=1)
    absent={t['name']:sorted(set(range(1,rounds[f['id']]))-{p['round'] for p in th[t['id']] if p['date']<cutoff}) for t in [f['home_team'],f['away_team']]}
    assert absent==r['earlier_rounds_absent']
for r in samples:
    if r['features']:
        f=r['features'];a=choose({k:f[k] for k in ['shooter_rank','recent_minutes','recent_hits','environment']})['full_pattern']
        assert r['A']==a and r['B']==(a and f['recent_shots']>=3 and f['recent_minutes']>=80)
    if not r['B']:assert r['exclusion_reasons']
for key in ['A','B']:
    selected=[r for r in samples if r[key]]
    assert len(selected)==result['comparison'][key]['n']
    assert sum(r['hit'] for r in selected)==result['comparison'][key]['hits']
with ZipFile(out.parent/'ligue1_2015_16_ab_validation.zip') as z:assert z.testzip() is None
print('PASS: plan/rule hashes, 10,479 samples, 377 fixture totals, independent lagged features, round-gap sensitivity and A/B settlements.')
