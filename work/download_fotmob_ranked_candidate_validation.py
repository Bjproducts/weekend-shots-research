"""Bounded FotMob acquisition for the frozen 2024/25 ranked-candidate validation."""
from __future__ import annotations

import gzip,json,shutil,time,urllib.parse
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from pathlib import Path
from download_fotmob_big5_carryover import LEAGUES,get_json,normalize,parse_date

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/big5_2024_ranked_candidate_validation';RAW=OUT/'raw'
SOURCE_RAW=ROOT/'outputs/big5_2025_carryover_replication/raw';SEASONS=('2023/2024','2024/2025')
def main():
    OUT.mkdir(parents=True,exist_ok=True);RAW.mkdir(parents=True,exist_ok=True);fixtures=[];counts={}
    for league,(league_id,country) in LEAGUES.items():
        for season in SEASONS:
            cache=RAW/f"league_{league_id}_{season.replace('/','-')}.json.gz";prior=SOURCE_RAW/cache.name
            if not cache.exists() and prior.exists():shutil.copy2(prior,cache)
            if cache.exists():data=json.loads(gzip.decompress(cache.read_bytes()))
            else:
                query=urllib.parse.urlencode({'id':league_id,'ccode3':country,'season':season});data=get_json('https://www.fotmob.com/api/data/leagues?'+query)
                cache.write_bytes(gzip.compress(json.dumps(data).encode('utf-8')))
            rows=data['fixtures']['allMatches'];counts[f'{league} {season}']=len(rows)
            for r in rows:r=dict(r);r.update(league=league,league_id=league_id,season=season);fixtures.append(r)
    earliest=datetime(2024,3,18,tzinfo=timezone.utc);latest=datetime(2024,10,7,tzinfo=timezone.utc)
    selected=[r for r in fixtures if r.get('status',{}).get('finished') and earliest<=parse_date(r['status']['utcTime'])<latest]
    selected.sort(key=lambda r:(r['status']['utcTime'],str(r['id'])));failures=[]
    def fetch(meta):
        cache=RAW/f"match_{meta['id']}.json.gz"
        if cache.exists():detail=json.loads(gzip.decompress(cache.read_bytes()))
        else:
            detail=get_json('https://www.fotmob.com/api/data/matchDetails?'+urllib.parse.urlencode({'matchId':meta['id']}));cache.write_bytes(gzip.compress(json.dumps(detail).encode('utf-8')));time.sleep(.08)
        return normalize(meta,detail)
    normalized=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(fetch,r):r for r in selected}
        for number,future in enumerate(as_completed(futures),1):
            row=futures[future]
            try:normalized.append(future.result())
            except Exception as exc:failures.append({'match_id':str(row['id']),'league':row['league'],'date':row['status']['utcTime'],'error':repr(exc)})
            if number%100==0:print(f'details {number}/{len(selected)}; failures={len(failures)}',flush=True)
    normalized.sort(key=lambda r:(r['date'],r['match_id']));(OUT/'normalized_matches.json').write_text(json.dumps(normalized,indent=2),encoding='utf-8')
    acquisition={'provider':'FotMob public match pages/data','retrieved_utc':datetime.now(timezone.utc).isoformat(),'scope':'finished top-five-league matches from 2024-03-18 through 2024-10-06 UTC','league_fixture_counts':counts,'selected_match_details':len(selected),'normalized_matches':len(normalized),'failures':failures,'raw_cache':str(RAW)}
    (OUT/'acquisition.json').write_text(json.dumps(acquisition,indent=2),encoding='utf-8');print(json.dumps(acquisition,indent=2))
if __name__=='__main__':main()
