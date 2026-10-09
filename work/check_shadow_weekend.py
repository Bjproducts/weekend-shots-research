"""Verify that a prospective weekend snapshot is immutable and outcome-free."""
import argparse,hashlib,json
from datetime import datetime,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'outputs/shadow_testing'
def dt(x):return datetime.fromisoformat(x.replace('Z','+00:00'))
def main():
    p=argparse.ArgumentParser();p.add_argument('--weekend',required=True);a=p.parse_args();out=BASE/a.weekend;snapshot=out/'environment_snapshot.json';obj=json.loads(snapshot.read_text(encoding='utf-8'));manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'));fixtures=obj['fixtures'];eligible=[r for r in fixtures if r['eligible']];selected=[r for r in fixtures if r['selected_environment']];start=datetime.fromisoformat(a.weekend).date();dates={start.isoformat(),(start+timedelta(days=1)).isoformat()};checks={}
    checks['hash_matches_manifest']=hashlib.sha256(snapshot.read_bytes()).hexdigest()==manifest['environment_snapshot_sha256']
    checks['prospective_outcome_free']=obj['prospective'] and not manifest['outcome_accessed'] and all('actual_home_shots' not in r and 'actual_away_shots' not in r for r in fixtures)
    checks['target_dates_only']=all(dt(r['date']).date().isoformat() in dates for r in fixtures)
    checks['rank_sequence']=sorted(r['weekend_rank'] for r in eligible)==list(range(1,len(eligible)+1))
    checks['five_selected']=len(selected)==5 and all(r['weekend_rank']<=5 and r['confidence_tier'] in ('A','B') for r in selected)
    checks['history_before_cutoff']=all(dt(r['date'])>dt(r['history_cutoff']) and all(mid!=r['match_id'] for mid in r['home_prior_ids']+r['away_prior_ids']) for r in fixtures)
    checks['manifest_ids_match']=set(manifest['selected_environment_ids'])=={r['match_id'] for r in selected}
    confirmed=[json.loads(path.read_text(encoding='utf-8')) for path in (out/'confirmed_lineup_locks').glob('*.json')] if (out/'confirmed_lineup_locks').exists() else []
    legacy=[json.loads(path.read_text(encoding='utf-8')) for path in (out/'lineup_locks').glob('*.json')] if (out/'lineup_locks').exists() else []
    quarantined=[row for row in legacy if row.get('lineup_type')!='standard']
    checks['confirmed_locks_are_standard_complete_and_outcome_free']=all(row.get('lineup_type')=='standard' and len(row.get('confirmed_home_starter_ids',[]))>=11 and row.get('outcome_accessed') is False for row in confirmed)
    checks['confirmed_lock_ids_belong_to_snapshot']=all(row['match_id'] in manifest['selected_environment_ids'] for row in confirmed)
    report={'passed':all(checks.values()),'checks':checks,'counts':{'fixtures':len(fixtures),'ranked':len(eligible),'selected':len(selected),'confirmed_standard_lineup_locks':len(confirmed),'quarantined_nonstandard_legacy_locks':len(quarantined)}};(out/'checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)
if __name__=='__main__':main()
