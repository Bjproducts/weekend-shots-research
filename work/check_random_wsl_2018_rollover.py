import hashlib,json
from datetime import datetime,timedelta
from pathlib import Path
from weekly_pattern_replay import RULES
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/random_wsl_2018_19_rollover_validation'
def main():
    required=['normalized_matches.json','results.json','betting_simulation.json','all_samples.json','qualifying_picks.json','feature_replay.json','frozen_test_plan.json','report.md','index.html']
    assert all((OUT/x).exists() for x in required)
    rec=json.loads((OUT/'normalized_matches.json').read_text());samples=json.loads((OUT/'all_samples.json').read_text());picks=json.loads((OUT/'qualifying_picks.json').read_text());res=json.loads((OUT/'results.json').read_text());plan=json.loads((OUT/'frozen_test_plan.json').read_text())
    assert len(rec)==107 and len(samples)==2872 and len({(x['fixture_id'],x['player_id']) for x in samples})==2872 and len(res['missing_fixture_pairs'])==3
    rh=hashlib.sha256(json.dumps(RULES,sort_keys=True).encode()).hexdigest();assert plan['rules_sha256']==res['baseline_rules_sha256']==rh
    assert all(x['A'] for x in picks) and all(not x['B'] or x['A'] for x in samples)
    dates={r['fixture']['id']:datetime.fromisoformat(r['fixture']['date']) for r in rec};assert all(all(dates[i]<datetime.fromisoformat(r['date'])-timedelta(days=1) for i in r['features']['prior_fixture_ids']) for r in picks)
    for label in ('A','B'):
        x=res['betting'][label]['continuous_rollover'];assert x['maximum_balance_reached']==round(10*(x['odds']**x['max_consecutive_wins']),2);assert x['cycles_started']==x['losing_cycles']+(1 if x['final_open_streak_wins'] else 0)
    assert (OUT.parent/'random_wsl_2018_19_rollover_validation.zip').exists();print(json.dumps({'status':'PASS','A':res['comparison']['A'],'B':res['comparison']['B'],'rollovers':{x:res['betting'][x]['continuous_rollover'] for x in ('A','B')}},indent=2))
if __name__=='__main__':main()
