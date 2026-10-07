import json
from pathlib import Path
from datetime import timedelta
from on_demand import stamp,SOURCES
from weekend_0822_audit import OUT,points
from statistics import mean

d=json.loads((OUT/'strength_audit.json').read_text(encoding='utf-8'))
games=json.loads((SOURCES/'asa_games_2026.json').read_text(encoding='utf-8'))
byid={g['game_id']:g for g in games}
assert d['target_fixtures']==15 and d['strength_passes']==5 and d['environment_passes']==3
for f in d['fixtures']:
    cutoff=stamp(byid[f['game_id']])-timedelta(days=1)
    for side in ['home','away']:
        tid=f[side+'_id'];h=[g for g in sorted(games,key=stamp) if stamp(g)<cutoff and tid in [g['home_team_id'],g['away_team_id']]]
        assert [g['game_id'] for g in h]==f[side+'_form']['prior_ids']
        assert mean(points(g,tid) for g in h)==f[side+'_form']['season_ppg']
    if 'venue_features' in f:
        assert f['venue_player_sum_conflicts']==[]
        v=f['venue_features']
        assert f['shooting_pass']==(v['home_home_shots']>=12 and v['away_away_conceded']>=12 and v['home_proxy']>v['away_proxy'])
lineups=json.loads((OUT/'target_lineups.json').read_text(encoding='utf-8'))
assert len(lineups['fixtures'])==3 and all(len(set(f['starters']))==11 for f in lineups['fixtures'])
assert {f['home'] for f in lineups['fixtures']}=={f['home'] for f in d['fixtures'] if f.get('environment_pass')}
print('PASS: 15 fixtures, strict history cutoff, independent form arithmetic, 5 strength / 3 environment passes, no venue-shot conflicts, 33 distinct starter entries across three fixtures.')
