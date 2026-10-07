"""Integrity checks for the frozen Frauen-Bundesliga A/B test."""
import hashlib, json
from datetime import datetime, timedelta
from pathlib import Path
from weekly_pattern_replay import RULES

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/frauen_bundesliga_2023_24_ab_validation'
def main():
    names=['acquisition.json','normalized_matches.json','frozen_test_plan.json','ab_results.json','all_samples.json','qualifying_picks.json','weekly_results.json','feature_replay.json','report.md','index.html']
    assert all((OUT/n).exists() for n in names)
    records=json.loads((OUT/'normalized_matches.json').read_text());samples=json.loads((OUT/'all_samples.json').read_text());picks=json.loads((OUT/'qualifying_picks.json').read_text());result=json.loads((OUT/'ab_results.json').read_text());plan=json.loads((OUT/'frozen_test_plan.json').read_text())
    rule_hash=hashlib.sha256(json.dumps(RULES,sort_keys=True).encode()).hexdigest()
    assert len(records)==132 and len(samples)==4056 and len({r['fixture']['id'] for r in records})==132
    assert len({(r['fixture_id'],r['player_id']) for r in samples})==4056
    assert plan['rules_sha256']==result['baseline_rules_sha256']==rule_hash
    assert all(r['A'] for r in picks) and all(not r['B'] or r['A'] for r in samples)
    dates={r['fixture']['id']:datetime.fromisoformat(r['fixture']['date']) for r in records}
    assert all(all(dates[x]<datetime.fromisoformat(r['date'])-timedelta(days=1) for x in r['features']['prior_fixture_ids']) for r in picks)
    b=[r for r in picks if r['B']]
    assert (sum(r['hit'] for r in picks),len(picks))==(result['comparison']['A']['hits'],result['comparison']['A']['n'])
    assert (sum(r['hit'] for r in b),len(b))==(result['comparison']['B']['hits'],result['comparison']['B']['n'])
    assert (OUT.parent/'frauen_bundesliga_2023_24_ab_validation.zip').exists()
    html=(OUT.parent/'project_site/dist/index.html').read_text();assert html.count('<!-- FRAUEN_AB_START -->')==html.count('<!-- FRAUEN_AB_END -->')==1
    print(json.dumps({'status':'PASS','matches':132,'samples':4056,'A':result['comparison']['A'],'B':result['comparison']['B']},indent=2))
if __name__=='__main__':main()
