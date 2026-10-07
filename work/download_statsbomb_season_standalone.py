"""Cache and normalize one StatsBomb season without touching production databases."""
import argparse,gzip,hashlib,json,math,time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
BASE='https://raw.githubusercontent.com/statsbomb/open-data/master/data/'

def clock(value):
    parts=str(value or '0:0').split(':')
    return int(parts[0])*60+int(float(parts[1]))

def minutes(positions,match_minutes=90):
    end=match_minutes*60;intervals=[]
    for p in positions:
        a=min(max(clock(p.get('from')),0),end)
        b=min(max(clock(p.get('to')) if p.get('to') else end,a),end)
        intervals.append((a,b))
    merged=[]
    for a,b in sorted(intervals):
        if not merged or a>merged[-1][1]:merged.append([a,b])
        else:merged[-1][1]=max(merged[-1][1],b)
    return math.ceil(sum(b-a for a,b in merged)/60)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--competition',type=int,required=True);ap.add_argument('--season',type=int,required=True)
    ap.add_argument('--slug',required=True);ap.add_argument('--expected-matches',type=int,required=True);ap.add_argument('--expected-teams',type=int,required=True)
    ap.add_argument('--allow-unbalanced',action='store_true',help='Allow team home/away counts to differ by at most one for a disclosed partial season')
    args=ap.parse_args();out=ROOT/'outputs'/args.slug;raw=out/'raw';out.mkdir(parents=True,exist_ok=True)
    def get(path):
        dest=raw/(path+'.gz')
        if dest.exists():return json.loads(gzip.decompress(dest.read_bytes()))
        last=None
        for attempt in range(3):
            try:
                req=Request(BASE+path,headers={'User-Agent':'WeekendShotsResearch/1.0 cached validation'})
                with urlopen(req,timeout=45) as response:data=response.read(50_000_001)
                if len(data)>50_000_000:raise ValueError('Response exceeded 50 MB')
                value=json.loads(data)
                if not isinstance(value,list):raise ValueError('Expected a JSON list')
                dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(gzip.compress(data,mtime=0));return value
            except Exception as exc:last=exc;time.sleep(2**attempt)
        raise last
    matches=get(f'matches/{args.competition}/{args.season}.json')
    assert len(matches)==args.expected_matches and len({m['match_id'] for m in matches})==len(matches)
    teams={t for m in matches for t in [m['home_team']['home_team_id'],m['away_team']['away_team_id']]}
    assert len(teams)==args.expected_teams
    home_counts=Counter(m['home_team']['home_team_id'] for m in matches)
    away_counts=Counter(m['away_team']['away_team_id'] for m in matches)
    if args.allow_unbalanced:
        assert max(home_counts.values())-min(home_counts.values())<=1
        assert max(away_counts.values())-min(away_counts.values())<=1
    else:
        expected_each=args.expected_matches//args.expected_teams
        assert set(home_counts.values())=={expected_each}
        assert set(away_counts.values())=={expected_each}
    def one(m):
        mid=m['match_id'];lineups=get(f'lineups/{mid}.json');events=get(f'events/{mid}.json')
        assert all(int(e.get('period') or 0)<=2 for e in events)
        shots=Counter();teamshots=Counter()
        fixture_ids={m['home_team']['home_team_id'],m['away_team']['away_team_id']}
        for e in events:
            if (e.get('type') or {}).get('name')!='Shot':continue
            pid=(e.get('player') or {}).get('id');tid=(e.get('team') or {}).get('id')
            if pid is not None and tid in fixture_ids:shots[int(pid)]+=1;teamshots[int(tid)]+=1
        rows=[]
        for team in lineups:
            tid=int(team['team_id']);opp=next(x for x in fixture_ids if x!=tid)
            for lp in team.get('lineup',[]):
                pos=lp.get('positions') or []
                if not pos:continue
                started=any(p.get('start_reason')=='Starting XI' or p.get('from')=='00:00' for p in pos)
                pid=int(lp['player_id'])
                rows.append(dict(player=dict(id=pid,full_name=str(lp.get('player_name') or 'Unknown player'),common_name=lp.get('player_nickname')),
                    team_id=tid,opponent_id=opp,home=tid==m['home_team']['home_team_id'],started=started,
                    minutes_played=minutes(pos),shots=shots[pid],team_shots=teamshots[tid]))
        assert sum(r['started'] for r in rows)==22
        assert sum(r['shots'] for r in rows)==sum(teamshots.values())
        date=datetime.fromisoformat(str(m['match_date'])+'T'+str(m.get('kick_off') or '00:00:00')).replace(tzinfo=timezone.utc).isoformat()
        return dict(fixture=dict(id=mid,date=date,round=m.get('match_week'),home_team=dict(id=m['home_team']['home_team_id'],name=m['home_team']['home_team_name']),away_team=dict(id=m['away_team']['away_team_id'],name=m['away_team']['away_team_name']),home_score=m.get('home_score'),away_score=m.get('away_score')),players=rows)
    results=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(one,m):m['match_id'] for m in matches}
        for n,f in enumerate(as_completed(futures),1):
            results.append(f.result())
            if n%20==0:print(f'Downloaded and checked {n}/{len(matches)}',flush=True)
    results.sort(key=lambda r:r['fixture']['date'])
    payload=json.dumps(results,indent=2).encode();(out/'normalized_matches.json').write_bytes(payload)
    meta=dict(source=BASE,competition=args.competition,season=args.season,matches=len(results),teams=len(teams),player_appearances=sum(len(r['players']) for r in results),normalized_sha256=hashlib.sha256(payload).hexdigest(),retrieved_at_utc=datetime.now(timezone.utc).isoformat())
    (out/'acquisition.json').write_text(json.dumps(meta,indent=2),encoding='utf-8');print(json.dumps(meta,indent=2))

if __name__=='__main__':main()
