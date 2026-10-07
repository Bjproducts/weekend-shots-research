import json
from datetime import timedelta
from on_demand import cached_players, stamp, SOURCES, write
from weekend_0822_audit import OUT
from fetch_0822_venue import fetch
from test_home_pattern import connect

audit=json.loads((OUT/'strength_audit.json').read_text())
selected=[f for f in audit['fixtures'] if f.get('environment_pass')]
games={g['game_id']:g for g in json.loads((SOURCES/'asa_games_2026.json').read_text())}
cached,_=cached_players()
ids=sorted({key[2] for f in selected for key in cached if key[0]==f['game_id'] and key[1]==f['home_id']})
names=fetch('mls/players',{'player_id':','.join(ids)},'target_players.json')
lookup={n['player_id']:n for n in names}
c=connect();out=[]
for f in selected:
    time=stamp(games[f['game_id']]);cutoff=time-timedelta(days=1)
    players=[]
    for key in cached:
        if key[0]!=f['game_id'] or key[1]!=f['home_id']:continue
        history=[(games[k[0]],v['value']) for k,v in cached.items() if k[1:]==key[1:] and k[0] in games and time-timedelta(days=180)<=stamp(games[k[0]])<cutoff]
        players.append(dict(identity=lookup.get(key[2]),prior_appearances=len(history),
            history=[dict(date=g['date_time_utc'],game_id=g['game_id'],shots=r['shots'],expanded_minutes=r['minutes_played']) for g,r in sorted(history,key=lambda x:stamp(x[0]),reverse=True)]))
    out.append(dict(home=f['home'],players=players))
write(OUT/'identity_candidates.json',out)
print(json.dumps([dict(home=x['home'],players=[(p['identity']['player_id'],p['identity']['player_name'],p['prior_appearances']) for p in x['players']]) for x in out],indent=2))
