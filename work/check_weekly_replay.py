import json
from datetime import datetime,timedelta
from weekly_pattern_replay import OUT,choose

d=json.loads((OUT/'weekly_pattern_replay.json').read_text(encoding='utf-8'))
assert len(d['weeks'])==101
assert len(d['picks'])==660
for left,right in zip(d['weeks'],d['weeks'][1:]):
    assert datetime.fromisoformat(right['week_start'])-datetime.fromisoformat(left['week_start'])==timedelta(days=7)
for version in ['full_pattern','benchmark']:
    selected=[p for p in d['picks'] if p[version]]
    assert sum(p['hit'] for p in selected)==d['summary'][version]['all']['hits']
    assert len(selected)==sum(w[version]['n'] for w in d['weeks'])
    assert sum(p['outcome']=='MISS' for p in selected)==len(selected)-sum(p['hit'] for p in selected)
for p in d['picks']:
    f={k:p[k] for k in ['shooter_rank','recent_minutes','recent_hits','environment']}
    assert choose(f)=={k:p[k] for k in ['full_pattern','benchmark']}
    # A current result cannot affect the selector.
    assert choose(dict(f,hit=False,shots=0))==choose(dict(f,hit=True,shots=20))
assert choose(dict(shooter_rank=2,recent_minutes=70,recent_hits=4,environment=True))['full_pattern']
assert not choose(dict(shooter_rank=2,recent_minutes=69.9,recent_hits=4,environment=True))['full_pattern']
assert not choose(dict(shooter_rank=2,recent_minutes=None,recent_hits=4,environment=True))['benchmark']
assert not choose(dict(shooter_rank=3,recent_minutes=90,recent_hits=5,environment=True))['benchmark']
print('PASS: continuous weeks, complete pick ledger, settlement totals, frozen rule boundaries, and outcome-independent selection.')
