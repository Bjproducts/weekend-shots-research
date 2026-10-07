"""Integrity checks for the exploratory big-five ranking layer."""
import json
from collections import Counter,defaultdict
from datetime import datetime,timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/big5_environment_rankings'
def dt(x):return datetime.fromisoformat(x.replace('Z','+00:00'))
def main():
    fixtures=json.loads((OUT/'ranked_fixtures.json').read_text(encoding='utf-8'));summary=json.loads((OUT/'summary.json').read_text(encoding='utf-8'));spec=json.loads((OUT/'ranking_specification.json').read_text(encoding='utf-8'))
    sources={}
    for label,slug in [('2026/27','big5_2026_prebreak_carryover'),('2025/26','big5_2025_carryover_replication')]:sources[label]={m['match_id']:m for m in json.loads((ROOT/'outputs'/slug/'normalized_matches.json').read_text(encoding='utf-8'))}
    checks={};eligible=[r for r in fixtures if r['eligible']]
    checks['weights_sum_to_one']=abs(sum(spec['ranking_components'].values())-1)<1e-9
    checks['fixture_counts_reconcile']=len(fixtures)==summary['fixtures'] and len(eligible)==summary['eligible_ranked'] and len(fixtures)-len(eligible)==summary['excluded']
    checks['unique_fixture_dataset_keys']=len(fixtures)==len({(r['dataset'],r['match_id']) for r in fixtures})
    checks['scores_bounded']=all(0<=r['environment_score']<=100 for r in eligible)
    checks['excluded_unranked']=all('environment_score' not in r and 'weekend_rank' not in r and r['confidence_tier']=='EXCLUDED' for r in fixtures if not r['eligible'])
    grouped=defaultdict(list)
    for r in eligible:grouped[r['dataset'],r['weekend']].append(r)
    checks['ranks_consecutive']=all(sorted(r['weekend_rank'] for r in rows)==list(range(1,len(rows)+1)) for rows in grouped.values())
    checks['eight_weekends']=len(grouped)==8
    checks['tier_counts_reconcile']=dict(Counter(r['confidence_tier'] for r in fixtures))==summary['confidence_counts']
    checks['tier_logic']=all(r['confidence_tier']==('A' if r['home_current_matches']>=3 and r['away_current_matches']>=3 else 'B' if r['home_current_matches']>=1 and r['away_current_matches']>=1 else 'C') for r in eligible)
    history=True;identity=True;candidates=True
    for r in fixtures:
        source=sources[r['dataset']];target=source[r['match_id']];cutoff=dt(r['history_cutoff'])
        for side,tid in [('home',target['home_team_id']),('away',target['away_team_id'])]:
            for mid in r[f'{side}_prior_ids']:
                m=source[mid];history &= dt(m['date'])<cutoff and dt(target['date'])-dt(m['date'])<=timedelta(days=180)
                identity &= tid in (m['home_team_id'],m['away_team_id']) and m['league']==target['league']
        for c in r['ranked_candidates']:
            for mid in c['prior_ids']:
                m=source[mid];found=[p for p in m['players'] if p['player_id']==c['player_id'] and p['team_id']==target['home_team_id'] and p['started']]
                candidates &= bool(found) and dt(m['date'])<cutoff and dt(target['date'])-dt(m['date'])<=timedelta(days=180)
    checks['strict_cutoff_and_180_days']=bool(history);checks['same_team_and_league_history']=bool(identity);checks['candidate_identity_and_cutoff']=bool(candidates)
    report={'passed':all(checks.values()),'checks':checks,'counts':{'fixtures':len(fixtures),'ranked':len(eligible),'excluded':len(fixtures)-len(eligible),'weekends':len(grouped)}}
    (OUT/'checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)
if __name__=='__main__':main()
