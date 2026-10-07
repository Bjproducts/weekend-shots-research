"""Integrity checks for the untouched 2024/25 ranked-candidate validation."""
import hashlib,json
from collections import defaultdict
from datetime import datetime,timedelta
from pathlib import Path
from zipfile import ZIP_DEFLATED,ZipFile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/big5_2024_ranked_candidate_validation';PLAN=ROOT/'work/big5_ranked_candidate_validation_plan.json'
TARGET={'2024-09-14','2024-09-15','2024-09-21','2024-09-22','2024-09-28','2024-09-29','2024-10-05','2024-10-06'}
def dt(x):return datetime.fromisoformat(x.replace('Z','+00:00'))
def main():
    matches=json.loads((OUT/'normalized_matches.json').read_text(encoding='utf-8'));fixtures=json.loads((OUT/'ranked_fixtures.json').read_text(encoding='utf-8'));samples=json.loads((OUT/'all_candidate_samples.json').read_text(encoding='utf-8'));picks=json.loads((OUT/'qualifying_picks.json').read_text(encoding='utf-8'));result=json.loads((OUT/'results.json').read_text(encoding='utf-8'));acq=json.loads((OUT/'acquisition.json').read_text(encoding='utf-8'));by_id={m['match_id']:m for m in matches};checks={}
    checks['acquisition_complete']=not acq['failures'] and acq['normalized_matches']==len(matches)==770
    checks['plan_hash']=result['plan_sha256']==hashlib.sha256(PLAN.read_bytes()).hexdigest()
    checks['target_dates']=all(dt(r['date']).date().isoformat() in TARGET for r in fixtures)
    checks['counts']=len(fixtures)==result['target_fixtures']==166 and len(samples)==result['candidate_samples']==1139
    grouped=defaultdict(list)
    for r in fixtures:
        if r['eligible']:grouped[r['weekend']].append(r)
    checks['rank_sequences']=all(sorted(r['weekend_rank'] for r in rows)==list(range(1,len(rows)+1)) for rows in grouped.values()) and len(grouped)==4
    qids={r['match_id'] for r in fixtures if r['eligible'] and r['weekend_rank']<=5 and r['confidence_tier'] in ('A','B')}
    checks['twenty_qualifying_environments']=len(qids)==result['qualifying_top_five_A_or_B_environments']==20
    checks['picks_obey_frozen_rule']=all(r['match_id'] in qids and r['shooter_rank']<=2 and r['avg_minutes']>=70 and r['recent_hits']>=4 for r in picks)
    checks['b_subset_and_extra_rule']=all(not r['B'] or (r['A'] and r['avg_shots']>=3 and r['avg_minutes']>=80) for r in picks)
    checks['outcomes_reconcile']=len(picks)==result['A']['picks'] and sum(r['hit'] for r in picks)==result['A']['hits'] and sum(r['B'] for r in picks)==result['B']['picks'] and sum(r['hit'] for r in picks if r['B'])==result['B']['hits']
    history=True;identity=True
    for r in fixtures:
        target=by_id[r['match_id']];cutoff=dt(r['history_cutoff'])
        for side,tid in [('home',target['home_team_id']),('away',target['away_team_id'])]:
            for mid in r[f'{side}_prior_ids']:
                m=by_id[mid];history &= dt(m['date'])<cutoff and dt(target['date'])-dt(m['date'])<=timedelta(days=180);identity &= tid in (m['home_team_id'],m['away_team_id']) and m['league']==target['league']
    for r in samples:
        target=by_id[r['match_id']];cutoff=dt(target['date'])-timedelta(days=1)
        for mid in r['prior_ids']:
            m=by_id[mid];found=[p for p in m['players'] if p['player_id']==r['player_id'] and p['team_id']==target['home_team_id'] and p['started']]
            history &= dt(m['date'])<cutoff and dt(target['date'])-dt(m['date'])<=timedelta(days=180);identity &= bool(found) and m['league']==target['league']
    checks['strict_cutoff_180_days']=bool(history);checks['same_team_league_identity']=bool(identity);checks['known_pick_outcomes']=all(r['hit'] is not None and r['shots'] is not None for r in picks)
    report={'passed':all(checks.values()),'checks':checks,'counts':{'source_matches':len(matches),'target_fixtures':len(fixtures),'ranked':sum(r['eligible'] for r in fixtures),'selected_environments':len(qids),'A_picks':len(picks),'B_picks':sum(r['B'] for r in picks)}};(OUT/'checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with ZipFile(OUT.parent/f'{OUT.name}.zip','w',ZIP_DEFLATED) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file() and 'raw' not in p.parts:z.write(p,p.relative_to(OUT))
    print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)
if __name__=='__main__':main()
