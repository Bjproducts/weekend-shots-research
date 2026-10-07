"""Fetch complete EPL 2015/16 open data; cache all evidence, no production writes."""
import asyncio
import argparse
import gzip
import json
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

BACKEND=Path('C:/Users/bjpro/OneDrive/Desktop/SHOT ON TARGET/backend')
sys.path.insert(0,str(BACKEND))
from app.ingestion.statsbomb import StatsBombOpenDataProvider

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--competition',type=int,default=2)
parser.add_argument('--slug',default='epl_2015_16_validation')
parser.add_argument('--expected-matches',type=int,default=380)
args=parser.parse_args()
OUT=ROOT/'outputs'/args.slug
RAW=OUT/'raw'

class CachedProvider(StatsBombOpenDataProvider):
    async def _request(self,path):
        dest=RAW/(path+'.gz')
        if dest.exists():
            return json.loads(gzip.decompress(dest.read_bytes()))
        rows=await super()._request(path)
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(gzip.compress(json.dumps(rows,ensure_ascii=False).encode(),mtime=0))
        return rows

async def main():
    OUT.mkdir(parents=True,exist_ok=True)
    provider=CachedProvider(max_retries=2)
    fixtures=await provider.get_fixtures(args.competition,27)
    assert len(fixtures)==args.expected_matches
    if args.expected_matches==380:
        assert set(Counter(f.home_team.id for f in fixtures).values())=={19}
        assert set(Counter(f.away_team.id for f in fixtures).values())=={19}
    gate=asyncio.Semaphore(4)
    completed=0
    async def one(f):
        nonlocal completed
        async with gate:
            stats=await provider.get_player_fixture_statistics(f.id,home_team_id=f.home_team.id,away_team_id=f.away_team.id)
            events=await provider._request(f'events/{f.id}.json')
            # This is a league season: no extra time or shootout counting.
            assert all(e.get('period',0)<=2 for e in events)
            assert sum(p.started for p in stats)==22, f'Missing starters: {f.id}'
            assert sum(p.shots for p in stats)==sum(e.get('type',{}).get('name')=='Shot' for e in events)
            assert all(p.minutes_played is not None for p in stats)
            rows=[]
            for p in stats:
                row=asdict(p)
                row.pop('raw',None)
                row['data_quality_status']=str(p.data_quality_status.value)
                rows.append(row)
            completed+=1
            if completed%20==0:print(f'Downloaded and checked {completed}/{args.expected_matches} matches',flush=True)
            return dict(fixture=dict(id=f.id,date=f.fixture_date.isoformat(),home_team=asdict(f.home_team),away_team=asdict(f.away_team),home_score=f.home_score,away_score=f.away_score),players=rows)
    try:
        results=await asyncio.gather(*(one(f) for f in fixtures))
        (OUT/'normalized_matches.json').write_text(json.dumps(sorted(results,key=lambda r:r['fixture']['date']),indent=2),encoding='utf-8')
        print(f'COMPLETE: {len(results)} matches; {sum(len(r["players"]) for r in results)} player appearances.',flush=True)
    finally:await provider.aclose()

if __name__=='__main__':asyncio.run(main())
