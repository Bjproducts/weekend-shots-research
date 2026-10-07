"""Bounded source collection for only the five strength-pass environments."""
import hashlib,json,urllib.request,urllib.parse
from datetime import datetime,timezone
from weekend_0822_audit import OUT,SOURCES

def fetch(endpoint,params,name):
    path=OUT/'raw'/name
    if path.exists():return json.loads(path.read_text(encoding='utf-8'))
    url='https://app.americansocceranalysis.com/api/v1/'+endpoint+'?'+urllib.parse.urlencode(params)
    with urllib.request.urlopen(url,timeout=30) as response:raw=response.read()
    data=json.loads(raw)
    if not isinstance(data,list) or len(data)>=1000:raise ValueError('Unexpected response or pagination boundary')
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    path.with_suffix('.metadata.json').write_text(json.dumps(dict(source_url=url,retrieved_at_utc=datetime.now(timezone.utc).isoformat(),sha256=hashlib.sha256(raw).hexdigest(),records=len(data)),indent=2))
    print(name,len(data),flush=True)
    return data

if __name__=='__main__':
    audit=json.loads((OUT/'strength_audit.json').read_text())
    selected=[f for f in audit['fixtures'] if f['strength_pass']]
    games={g['game_id']:g for g in json.loads((SOURCES/'asa_games_2026.json').read_text())}
    wanted={i for f in selected for i in f['venue_game_ids']}
    dates=sorted(games[i]['date_time_utc'][:10] for i in wanted)
    fetch('mls/teams',{},'teams.json')
    for side in ['home','away']:
        params=dict(team_id=','.join(sorted({f[side+'_id'] for f in selected})),start_date=dates[0],end_date=dates[-1],split_by_games='true',stage_name='Regular Season')
        params[side+'_only']='true'
        rows=fetch('mls/teams/xgoals',params,'venue_full_'+side+'.json')
        print('schema',list(rows[0]) if rows else [],flush=True)
