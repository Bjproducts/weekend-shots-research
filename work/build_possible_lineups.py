"""Create versioned, deterministic recent-start XIs and provisional candidate picks."""
import argparse,json
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from statistics import mean

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'outputs/shadow_testing';HISTORY=ROOT/'outputs/big5_2026_prebreak_carryover/normalized_matches.json'
def dt(x):return datetime.fromisoformat(x.replace('Z','+00:00'))
def main():
    p=argparse.ArgumentParser();p.add_argument('--weekend',required=True);a=p.parse_args();out=BASE/a.weekend;snapshot=json.loads((out/'environment_snapshot.json').read_text(encoding='utf-8'));history=json.loads(HISTORY.read_text(encoding='utf-8'));selected=sorted([r for r in snapshot['fixtures'] if r['selected_environment']],key=lambda r:r['weekend_rank']);forecasts=[]
    for env in selected:
        target=dt(env['date']);team_matches=[m for m in history if m['league']==env['league'] and env['home_team_id'] in (m['home_team_id'],m['away_team_id']) and dt(m['date'])<target][-5:]
        appearances=defaultdict(list);names={};positions={}
        for order,m in enumerate(team_matches,1):
            for q in m['players']:
                if q['team_id']==env['home_team_id'] and q['started']:
                    appearances[q['player_id']].append({'match_id':m['match_id'],'order':order,'minutes':q['minutes']});names[q['player_id']]=q['player'];positions[q['player_id']]=q.get('position_id')
        pool=[]
        for pid,apps in appearances.items():
            mins=[x['minutes'] for x in apps if x['minutes'] is not None];pool.append({'player_id':pid,'player':names[pid],'position_id':positions[pid],'starts_in_last_five':len(apps),'recency_score':sum(x['order'] for x in apps),'average_start_minutes':round(mean(mins),1) if mins else None,'source_match_ids':[x['match_id'] for x in apps]})
        pool.sort(key=lambda x:(-x['starts_in_last_five'],-x['recency_score'],-(x['average_start_minutes'] or 0),x['player_id']));xi=pool[:11];xi_ids={x['player_id'] for x in xi}
        eligible=[c for c in env['candidate_pool'] if c['player_id'] in xi_ids];eligible.sort(key=lambda x:(-x['avg_shots'],-x['avg_minutes'],x['player_id']));provisional=[]
        for rank,c in enumerate(eligible,1):
            plan_a=rank<=2 and c['avg_minutes']>=70 and c['recent_hits']>=4;plan_b=plan_a and c['avg_shots']>=3 and c['avg_minutes']>=80
            if plan_a:provisional.append({**c,'shooter_rank_within_possible_XI':rank,'A':True,'B':plan_b})
        forecasts.append({'match_id':env['match_id'],'date':env['date'],'league':env['league'],'fixture':env['fixture'],'environment_rank':env['weekend_rank'],'confidence_tier':env['confidence_tier'],'method':'Top 11 by starts, recency and starting minutes across the team’s last five matches; not an externally published or confirmed lineup.','recent_team_matches':[m['match_id'] for m in team_matches],'possible_XI':xi,'provisional_picks':provisional})
    created=datetime.now(timezone.utc);obj={'status':'provisional_possible_lineups_not_official_picks','created_utc':created.isoformat(),'weekend':a.weekend,'method':'Deterministic recent-start XI. Recompute when desired; confirmed lineup locks remain the official prospective selections.','forecasts':forecasts}
    folder=out/'possible_lineups';folder.mkdir(exist_ok=True);version=folder/(created.strftime('%Y%m%dT%H%M%SZ')+'.json');version.write_text(json.dumps(obj,indent=2),encoding='utf-8');(out/'latest_possible_lineups.json').write_text(json.dumps(obj,indent=2),encoding='utf-8');print(json.dumps({'status':obj['status'],'version':str(version),'fixtures':len(forecasts),'provisional_A':sum(len(x['provisional_picks']) for x in forecasts),'provisional_B':sum(p['B'] for x in forecasts for p in x['provisional_picks'])},indent=2))
if __name__=='__main__':main()
