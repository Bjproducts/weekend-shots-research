import json
from test_home_pattern import connect
from weekend_0822_audit import OUT
c=connect()
teams=[dict(r) for r in c.execute("select id,name from teams where name like '%Charlotte%' or name like '%Miami%' or name like '%Atlanta%'")]
result=[]
for t in teams:
    rows=[dict(r) for r in c.execute('''select p.player_id,coalesce(n.common_name,n.full_name) name,
    count(*) appearances,sum(p.started) starts,max(f.fixture_date) latest,
    min(f.fixture_date) earliest from player_fixture_stats p join players n on n.id=p.player_id
    join fixtures f on f.id=p.fixture_id
    where p.team_id=? and f.fixture_date>='2026-02-23' and f.fixture_date<'2026-08-21'
    and p.data_source='sportsapipro' group by p.player_id''',(t['id'],))]
    result.append(dict(team=t,players=rows))
(OUT/'original_history_inventory.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
