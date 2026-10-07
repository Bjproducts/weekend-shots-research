import hashlib,json
from datetime import datetime,timedelta
from pathlib import Path
from weekly_pattern_replay import RULES
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/wsl_2020_21_rollover_validation'
def main():
    required=['normalized_matches.json','ab_results.json','betting_simulation.json','all_samples.json','qualifying_picks.json','feature_replay.json','frozen_test_plan.json','report.md','index.html']
    assert all((OUT/x).exists() for x in required)
    rec=json.loads((OUT/'normalized_matches.json').read_text());samples=json.loads((OUT/'all_samples.json').read_text());picks=json.loads((OUT/'qualifying_picks.json').read_text());res=json.loads((OUT/'ab_results.json').read_text());plan=json.loads((OUT/'frozen_test_plan.json').read_text());bet=res['betting']
    rh=hashlib.sha256(json.dumps(RULES,sort_keys=True).encode()).hexdigest();assert plan['rules_sha256']==res['baseline_rules_sha256']==rh
    assert len(rec)==131 and len(samples)==3727 and len({(x['fixture_id'],x['player_id']) for x in samples})==3727
    assert all(x['A'] for x in picks) and all(not x['B'] or x['A'] for x in samples)
    dates={r['fixture']['id']:datetime.fromisoformat(r['fixture']['date']) for r in rec}
    assert all(all(dates[i]<datetime.fromisoformat(r['date'])-timedelta(days=1) for i in r['features']['prior_fixture_ids']) for r in picks)
    b=[x for x in picks if x['B']];assert len(picks)==res['comparison']['A']['n'] and len(b)==res['comparison']['B']['n']
    assert bet['A']['flat']['profit']==round(bet['A']['flat']['total_return']-bet['A']['flat']['total_staked'],2)
    assert bet['B']['flat']['profit']==round(bet['B']['flat']['total_return']-bet['B']['flat']['total_staked'],2)
    assert bet['A']['continuous_rollover']['maximum_balance_reached']==256.29
    assert bet['B']['continuous_rollover']['maximum_balance_reached']==81920.0
    assert bet['A']['continuous_rollover']['maximum_balance_later_lost'] is True
    assert bet['B']['continuous_rollover']['maximum_balance_later_lost'] is True
    for label in ('A','B'):
        for n,obj in bet[label]['fixed_blocks_alternative'].items():
            assert obj['winning_blocks']+obj['losing_blocks']==obj['blocks']
            assert obj['profit']==round(obj['total_return']-obj['total_staked'],2)
            assert all(len(x['legs'])==int(n) for x in obj['block_records'])
    assert (OUT.parent/'wsl_2020_21_rollover_validation.zip').exists()
    print(json.dumps({'status':'PASS','matches':131,'samples':3727,'A':res['comparison']['A'],'B':res['comparison']['B'],'betting':bet},indent=2))
if __name__=='__main__':main()
