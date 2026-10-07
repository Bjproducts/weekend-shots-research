"""Integrity checks for the frozen big-five carryover replay."""
import hashlib, json
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/big5_2026_prebreak_carryover'
PLAN=ROOT/'work/big5_carryover_plan.json'
TARGET={'2026-08-29','2026-08-30','2026-09-05','2026-09-06','2026-09-12','2026-09-13','2026-09-19','2026-09-20'}
def dt(x):return datetime.fromisoformat(x.replace('Z','+00:00'))

def main():
    matches=json.loads((OUT/'normalized_matches.json').read_text(encoding='utf-8'))
    envs=json.loads((OUT/'environments.json').read_text(encoding='utf-8'))
    samples=json.loads((OUT/'all_samples.json').read_text(encoding='utf-8'))
    picks=json.loads((OUT/'qualifying_picks.json').read_text(encoding='utf-8'))
    result=json.loads((OUT/'results.json').read_text(encoding='utf-8'))
    acq=json.loads((OUT/'acquisition.json').read_text(encoding='utf-8'))
    by_id={m['match_id']:m for m in matches}
    checks={}
    checks['acquisition_no_failures']=not acq['failures'] and acq['normalized_matches']==len(matches)
    checks['unique_matches']=len(by_id)==len(matches)
    checks['plan_hash_matches']=result['plan_sha256']==hashlib.sha256(PLAN.read_bytes()).hexdigest()
    checks['target_dates_only']=all(dt(e['date']).date().isoformat() in TARGET for e in envs)
    checks['target_fixture_count']=len(envs)==result['target_fixtures']
    checks['unique_sample_keys']=len(samples)==len({(r['match_id'],r['player_id']) for r in samples})
    checks['b_subset_a']=all(r['A'] for r in picks if r['B'])
    checks['pick_count_reconciles']=sum(r['A'] for r in samples)==len(picks)==result['A']['picks']
    checks['b_count_reconciles']=sum(r['B'] for r in samples)==result['B']['picks']
    checks['outcomes_reconcile']=sum(r['hit'] is True for r in picks)==result['A']['hits'] and sum(r['hit'] is False for r in picks)==result['A']['misses']
    history_ok=True;identity_ok=True
    for e in envs:
        target=by_id[e['match_id']];cutoff=dt(e['history_cutoff'])
        for side,tid in [('home',target['home_team_id']),('away',target['away_team_id'])]:
            for mid in e[f'{side}_prior_ids']:
                m=by_id[mid]
                history_ok &= dt(m['date']) < cutoff and dt(target['date'])-dt(m['date']) <= timedelta(days=180)
                identity_ok &= tid in (m['home_team_id'],m['away_team_id']) and m['league']==target['league']
    for r in samples:
        target=by_id[r['match_id']];cutoff=dt(r['features']['history_cutoff'])
        for mid in r['prior_fixture_ids']:
            m=by_id[mid]
            history_ok &= dt(m['date']) < cutoff and dt(target['date'])-dt(m['date']) <= timedelta(days=180)
            found=[p for p in m['players'] if p['player_id']==r['player_id'] and p['team_id']==target['home_team_id'] and p['started']]
            identity_ok &= bool(found) and m['league']==target['league']
    checks['strict_cutoff_and_180_days']=bool(history_ok)
    checks['same_team_league_player_identity']=bool(identity_ok)
    checks['no_current_match_in_history']=all(e['match_id'] not in e['home_prior_ids']+e['away_prior_ids'] for e in envs) and all(r['match_id'] not in r['prior_fixture_ids'] for r in samples)
    checks['known_pick_outcomes']=all(r['hit'] is not None and r['shots'] is not None for r in picks)
    report={'passed':all(checks.values()),'checks':checks,'counts':{'matches':len(matches),'target_fixtures':len(envs),'samples':len(samples),'A_picks':len(picks),'B_picks':sum(r['B'] for r in picks)}}
    (OUT/'checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with ZipFile(OUT.parent/f'{OUT.name}.zip','w',ZIP_DEFLATED) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file() and 'raw' not in p.parts:z.write(p,p.relative_to(OUT))
    print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':
    import sys
    if '--replication' in sys.argv:
        OUT=ROOT/'outputs/big5_2025_carryover_replication'
        PLAN=ROOT/'work/big5_carryover_replication_plan.json'
        TARGET={'2025-09-13','2025-09-14','2025-09-20','2025-09-21','2025-09-27','2025-09-28','2025-10-04','2025-10-05'}
    main()
