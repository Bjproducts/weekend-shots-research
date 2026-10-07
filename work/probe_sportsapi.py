import asyncio,json,sys
from pathlib import Path
sys.path.insert(0,'C:/Users/bjpro/OneDrive/Desktop/SHOT ON TARGET/backend')
from app.core.config import Settings
from app.ingestion.sports_api_pro import SportsApiProProvider

async def main():
    s=Settings();key=s.sports_api_pro_key.get_secret_value()
    result={'provider':'SportsAPI Pro','configured':bool(key),'calls_per_minute':s.football_api_rate_limit_per_minute}
    if key:
        p=SportsApiProProvider(api_key=key,base_url=s.sports_api_pro_base_url,calls_per_minute=s.football_api_rate_limit_per_minute,timeout_seconds=20,max_retries=0)
        try:
            season=await p._resolve_season(35,2024)
            result.update(status='accessible',season=season)
        except Exception as e:
            result.update(status='unavailable',error_type=type(e).__name__,http_status=getattr(e,'status_code',None))
        finally:
            if p.quota:result.update(quota_limit=p.quota.daily_limit,quota_remaining=p.quota.daily_remaining)
            await p.aclose()
    path=Path(__file__).resolve().parents[1]/'outputs/sportsapi_connection_check.json'
    path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))

asyncio.run(main())
