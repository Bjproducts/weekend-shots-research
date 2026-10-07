"""Offline checks; never calls a remote data provider."""
from unittest.mock import patch
import on_demand as app

for bad in ['2026-08-23','2025-08-23','../../secrets','bad']:
    try:app.weekend(bad)
    except ValueError:pass
    else:raise AssertionError(bad)
p=app.plan('2026-08-22')
assert p['fixtures'] and p['status']=='insufficient_data'
assert p['network_requests']==0
assert all(f['blockers'] for f in p['fixtures'])
assert len({t['game_id'] for t in p['shooting_tasks']})==len(p['shooting_tasks'])
with patch.object(app,'fetch_day',side_effect=AssertionError('Unexpected network')):
    r=app.collect('2026-08-22')
    assert r['network_requests']==0
tasks=[{'state':'missing','utc_date':f'2026-08-{d:02}'} for d in range(1,9)]
with patch.object(app,'plan',return_value={'shooting_tasks':tasks}),patch.object(app,'fetch_day',return_value=3) as fetch:
    assert app.collect('2026-08-22')['network_requests']==4
    assert fetch.call_count==4
with patch.object(app,'plan',return_value={'shooting_tasks':tasks}),patch.object(app,'fetch_day',side_effect=ValueError('rate limited')) as fetch:
    r=app.collect('2026-08-22');assert r['collection_errors'] and fetch.call_count==1
print('PASS: dates, cache reuse, blockers, unique tasks, four-date cap, stop-on-error. No network requests.')
print('August 22 fixtures:',len(p['fixtures']),'target/venue games:',len(p['shooting_tasks']))
