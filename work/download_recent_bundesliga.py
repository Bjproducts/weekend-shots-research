"""Resumable, quota-bounded recent-season acquisition; no production DB writes."""
import asyncio,gzip,json,sys
from dataclasses import asdict
from pathlib import Path
sys.path.insert(0,'C:/Users/bjpro/OneDrive/Desktop/SHOT ON TARGET/backend')
from app.core.config import Settings
from app.ingestion.sports_api_pro import SportsApiProProvider

OUT=Path(__file__).resolve().parents[1]/'outputs/bundesliga_2024_25_validation'
RESERVE=10
class BudgetStop(Exception):pass
class Cached(SportsApiProProvider):
    calls=0
    async def _request(self,path,params=None):
        dest=OUT/'raw'/(path+'.json.gz')
        if dest.exists():return json.loads(gzip.decompress(dest.read_bytes()))
        for attempt in range(2):
            if self.calls>=89 or (self.quota and self.quota.daily_remaining is not None and self.quota.daily_remaining<=RESERVE):raise BudgetStop()
            self.calls+=1
            try:
                data=await super()._request(path,params)
                break
            except Exception as e:
                if attempt or getattr(e,'status_code',0) not in (500,502,503,504):raise
                await asyncio.sleep(2)
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(gzip.compress(json.dumps(data).encode(),mtime=0))
        return data

async def main():
    OUT.mkdir(parents=True,exist_ok=True)
    s=Settings()
    p=Cached(api_key=s.sports_api_pro_key.get_secret_value(),base_url=s.sports_api_pro_base_url,calls_per_minute=s.football_api_rate_limit_per_minute,timeout_seconds=20,max_retries=0)
    fixtures=[];samples=[];errors=[];stop='complete'
    try:
        events=[]
        for page in range(20):
            data=await p._request(f'api/tournament/35/season/63516/events/last/{page}')
            rows=p._events(data);events.extend(rows)
            print(f'Fixture catalog page {page}: {len(rows)} matches; quota remaining {p.quota.daily_remaining if p.quota else "unknown"}',flush=True)
            if len(rows)<30:break
        unique={int(r['id']):r for r in events}
        exclusions=[dict(fixture_id=r['id'],reason='promotion_relegation_playoff_not_regular_league',tournament=r['tournament']['name']) for r in unique.values() if r.get('tournament',{}).get('name')!='Bundesliga']
        (OUT/'catalog_exclusions.json').write_text(json.dumps(exclusions,indent=2),encoding='utf-8')
        fixtures=sorted([p._fixture(r,requested_season=2024) for r in unique.values() if r.get('tournament',{}).get('name')=='Bundesliga'],key=lambda r:(r.fixture_date,r.id))
        assert len(fixtures)==306, f'Unexpected season catalog: {len(fixtures)}'
        assert all(f.status.value=='finished' and f.competition.id==35 for f in fixtures)
        catalog=[dict(id=f.id,date=f.fixture_date.isoformat(),home_team=asdict(f.home_team),away_team=asdict(f.away_team),home_score=f.home_score,away_score=f.away_score) for f in fixtures]
        (OUT/'fixture_catalog.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8')
        for f,header in zip(fixtures,catalog):
            stats=await p.get_player_fixture_statistics(f.id,home_team_id=f.home_team.id,away_team_id=f.away_team.id)
            ps=[]
            for player in stats:
                row=asdict(player);row['data_quality_status']=player.data_quality_status.value
                raw=row.pop('raw',{})
                row['starter_flag_explicit']=isinstance(raw.get('substitute'),bool)
                ps.append(row)
            samples.append(dict(fixture=header,players=ps))
            # Checkpoint every completed fixture. Missing stats are not converted to zero.
            (OUT/'normalized_matches.json').write_text(json.dumps(samples,indent=2,default=str),encoding='utf-8')
            if len(samples)%10==0:print(f'Saved {len(samples)}/306 player-stat matches; remaining quota {p.quota.daily_remaining if p.quota else "unknown"}',flush=True)
    except BudgetStop:stop='quota_reserve_or_run_cap'
    except Exception as e:
        stop='provider_or_validation_error';errors.append(dict(type=type(e).__name__,http_status=getattr(e,'status_code',None),message=str(e).replace(s.sports_api_pro_key.get_secret_value(),'[REDACTED]')[:250]))
    finally:
        status=dict(season='Bundesliga 2024/25',provider='SportsAPI Pro',competition_id=35,season_id=63516,
            selection_order='chronological from season start, not chosen by outcomes',catalog_matches=len(fixtures),
            downloaded_matches=len(samples),player_samples=sum(len(r['players']) for r in samples),
            expected_season_matches=306,pending_matches=306-len(samples),calls_this_run=p.calls,reserve=RESERVE,
            quota_remaining=p.quota.daily_remaining if p.quota else None,stop_reason=stop,errors=errors,
            resume='Run the same download script after quota reset; cached requests are reused. No automation scheduled.')
        (OUT/'download_status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
        print(json.dumps(status),flush=True)
        await p.aclose()

if __name__=='__main__':asyncio.run(main())
