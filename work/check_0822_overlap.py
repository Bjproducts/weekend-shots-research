"""Diagnose reuse of old history; proposed name-based identities NOT approved joins."""
import json,unicodedata
from datetime import datetime,timedelta,timezone
from test_home_pattern import connect
from weekend_0822_audit import OUT
from on_demand import write

def normal(s):
    return ''.join(c for c in unicodedata.normalize('NFKD',s.lower()) if c.isascii() and c.isalnum())

c=connect()
sources=json.loads((OUT/'identity_candidates.json').read_text(encoding='utf-8'))
inventory=json.loads((OUT/'original_history_inventory.json').read_text(encoding='utf-8'))
out=[]
for source,oldteam in [(s,next(t for t in inventory if t['team']['name'].startswith(s['home'].replace(' FC','')) or s['home'].startswith(t['team']['name']))) for s in sources]:
    oldplayers=[]
    for p in oldteam['players']:
        full=dict(c.execute('select * from players where id=?',(p['player_id'],)).fetchone())
        oldplayers.append((p,full))
    for p in source['players']:
        identity=p['identity'];name=normal(identity['player_name'])
        matches=[(op,full) for op,full in oldplayers if name==normal(full.get('full_name') or '')]
        if len(matches)!=1:
            out.append(dict(team=source['home'],asa_id=identity['player_id'],name=identity['player_name'],status='identity_unresolved',candidates=[dict(id=op['player_id'],name=full.get('full_name')) for op,full in oldplayers]))
            continue
        op,full=matches[0]
        checks=[]
        for h in p['history']:
            day=datetime.strptime(h['date'],'%Y-%m-%d %H:%M:%S UTC')
            rows=[dict(r) for r in c.execute('''select p.started,p.shots,p.minutes_played,f.fixture_date,f.id fixture_id
                from player_fixture_stats p join fixtures f on f.id=p.fixture_id
                where p.player_id=? and p.team_id=? and p.data_source='sportsapipro' and f.fixture_date>=? and f.fixture_date<?''',
                (op['player_id'],oldteam['team']['id'],(day-timedelta(hours=3)).isoformat(' '),(day+timedelta(hours=3)).isoformat(' ')))]
            # Time proximity is diagnostic only; opponent and IDs still need verification.
            checks.append(dict(asa=h,old=rows,status='unmatched' if len(rows)!=1 else 'shot_match' if rows[0]['shots']==h['shots'] else 'shot_conflict'))
        out.append(dict(team=source['home'],asa_id=identity['player_id'],name=identity['player_name'],old_id=op['player_id'],status='proposed_full_name_match_not_approved',checks=checks))
write(OUT/'overlap_diagnostic.json',out)
print(json.dumps(dict(identity_unresolved=[(p['team'],p['name']) for p in out if p['status']=='identity_unresolved'],proposed_identities=sum(p['status']!='identity_unresolved' for p in out),shot_matches=sum(h['status']=='shot_match' for p in out for h in p.get('checks',[])),shot_conflicts=sum(h['status']=='shot_conflict' for p in out for h in p.get('checks',[])),unmatched_appearances=sum(h['status']=='unmatched' for p in out for h in p.get('checks',[]))),indent=2))
