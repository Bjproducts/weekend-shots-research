import json,sqlite3
from pathlib import Path
ROOT=Path('C:/Users/bjpro/OneDrive/Desktop/SHOT ON TARGET')
paths=[ROOT/'sot_sportsapi.db']+list((ROOT/'backend').glob('*.db'))
for p in paths:
    print('\nDATABASE',p)
    try:
        c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
        c.row_factory=sqlite3.Row
        print([dict(r) for r in c.execute('select data_source,count(*) n from player_fixture_stats group by data_source')])
        print([dict(r) for r in c.execute('''select c.name,s.label,count(distinct f.id) fixtures,count(p.id) player_rows,min(f.fixture_date) first,max(f.fixture_date) last
            from player_fixture_stats p join fixtures f on f.id=p.fixture_id join competitions c on c.id=f.competition_id
            join seasons s on s.id=f.season_id group by c.name,s.label''')])
        c.close()
    except Exception as e: print(type(e).__name__,str(e))
p=Path('C:/Users/bjpro/Documents/Codex/2026-09-14/files-pasted-by-the-user-build/work/legacy-soccer.json')
d=json.loads(p.read_text(encoding='utf-8'))
print('\nLEGACY',type(d).__name__)
if isinstance(d,dict):
    for k,v in d.items():
        print(k,type(v).__name__,len(v) if hasattr(v,'__len__') else '')
        if isinstance(v,list) and v: print(str(v[0])[:1600])
