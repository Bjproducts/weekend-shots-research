"""Prospective shadow runner: prepare rankings, lock lineup-time picks, then settle."""
from __future__ import annotations
import argparse,hashlib,json,urllib.parse
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
from statistics import mean

from download_fotmob_big5_carryover import LEAGUES,get_json,extract_stat

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'outputs/shadow_testing';HISTORY=ROOT/'outputs/big5_2026_prebreak_carryover/normalized_matches.json'
HEADERS={'User-Agent':'Mozilla/5.0','Referer':'https://www.fotmob.com/'}
def dt(x):return datetime.fromisoformat(x.replace('Z','+00:00'))
def avg(rows,key):
    vals=[r[key] for r in rows if r.get(key) is not None];return mean(vals) if vals else None
def percentile(value,values):
    if len(values)==1:return 50.0
    less=sum(v<value for v in values);equal=sum(v==value for v in values);return 100*(less+(equal-1)/2)/(len(values)-1)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def fetch_leagues():
    rows=[]
    for league,(lid,country) in LEAGUES.items():
        u='https://www.fotmob.com/api/data/leagues?'+urllib.parse.urlencode({'id':lid,'ccode3':country,'season':'2026/2027'});data=get_json(u)
        for r in data['fixtures']['allMatches']:
            r=dict(r);r.update(league=league,league_id=lid,season='2026/2027');rows.append(r)
    return rows
def histories(target_date):
    matches=json.loads(HISTORY.read_text(encoding='utf-8'));matches.sort(key=lambda r:(r['date'],r['match_id']))
    team=defaultdict(list);player=defaultdict(list)
    for m in matches:
        date=dt(m['date'])
        if date>=target_date-timedelta(days=1):continue
        hid,aid,league=m['home_team_id'],m['away_team_id'],m['league']
        if None not in (m['home_score'],m['away_score']):
            for tid,home in ((hid,True),(aid,False)):
                gf=m['home_score'] if home else m['away_score'];ga=m['away_score'] if home else m['home_score']
                team[league,tid].append({'date':date,'match_id':m['match_id'],'season':m['season'],'home':home,'points':3 if gf>ga else 1 if gf==ga else 0,'shots':m['home_shots'] if home else m['away_shots'],'against':m['away_shots'] if home else m['home_shots']})
        for p in m['players']:
            if p['started'] and p['team_id'] in (hid,aid):player[league,p['team_id'],p['player_id']].append({'date':date,'match_id':m['match_id'],'season':m['season'],'player':p['player'],'shots':p['shots'],'minutes':p['minutes']})
    return team,player
def prepare(weekend):
    out=BASE/weekend;out.mkdir(parents=True,exist_ok=True);snapshot=out/'environment_snapshot.json'
    if snapshot.exists():print(json.dumps({'status':'already_locked','snapshot':str(snapshot),'sha256':sha(snapshot)},indent=2));return
    start=datetime.fromisoformat(weekend).replace(tzinfo=timezone.utc);dates={weekend,(start+timedelta(days=1)).date().isoformat()};fixtures=[r for r in fetch_leagues() if r['status']['utcTime'][:10] in dates]
    team,player=histories(start);rows=[]
    for f in fixtures:
        date=dt(f['status']['utcTime']);cutoff=date-timedelta(days=1);league=f['league'];hid=str(f['home']['id']);aid=str(f['away']['id']);hs={}
        for tid in (hid,aid):
            eligible=[r for r in team[league,tid] if r['date']<cutoff and date-r['date']<=timedelta(days=180)];cur=[r for r in eligible if r['season']=='2026/2027'];prev=[r for r in eligible if r['season']=='2025/2026'];hs[tid]=(prev[-max(0,8-len(cur)):] + cur) if len(cur)<8 else cur[-8:]
        h,a=hs[hid],hs[aid];hv=[r for r in h if r['home'] and r['shots'] is not None and r['against'] is not None][-5:];av=[r for r in a if not r['home'] and r['shots'] is not None and r['against'] is not None][-5:];eligible=len(h)>=5 and len(a)>=5 and len(hv)>=2 and len(av)>=2;hc=sum(r['season']=='2026/2027' for r in h);ac=sum(r['season']=='2026/2027' for r in a);tier='A' if hc>=3 and ac>=3 else 'B' if hc>=1 and ac>=1 else 'C'
        row={'match_id':str(f['id']),'date':f['status']['utcTime'],'league':league,'fixture':f['home']['name']+' vs '+f['away']['name'],'home_team_id':hid,'away_team_id':aid,'home_team':f['home']['name'],'away_team':f['away']['name'],'eligible':eligible,'confidence_tier':tier if eligible else 'EXCLUDED','home_current_matches':hc,'away_current_matches':ac,'history_cutoff':cutoff.isoformat(),'home_prior_ids':[r['match_id'] for r in h],'away_prior_ids':[r['match_id'] for r in a]}
        if eligible:
            row.update(overall_ppg_gap=avg(h,'points')-avg(a,'points'),recent_ppg_gap=avg(h[-5:],'points')-avg(a[-5:],'points'),home_home_shots=avg(hv,'shots'),away_away_conceded=avg(av,'against'),away_away_shots=avg(av,'shots'),home_home_conceded=avg(hv,'against'));row['projected_home_shots']=(row['home_home_shots']+row['away_away_conceded'])/2;row['projected_away_shots']=(row['away_away_shots']+row['home_home_conceded'])/2;row['projected_shot_gap']=row['projected_home_shots']-row['projected_away_shots']
        pool=[]
        for (lg,tid,pid),hist in player.items():
            if lg!=league or tid!=hid:continue
            prior=[r for r in hist if r['date']<cutoff and date-r['date']<=timedelta(days=180)][-5:]
            if len(prior)==5 and all(r['shots'] is not None and r['minutes'] is not None for r in prior):pool.append({'player_id':pid,'player':prior[-1]['player'],'avg_shots':avg(prior,'shots'),'avg_minutes':avg(prior,'minutes'),'recent_hits':sum(r['shots']>=2 for r in prior),'current_season_starts':sum(r['season']=='2026/2027' for r in prior),'prior_ids':[r['match_id'] for r in prior]})
        row['candidate_pool']=pool;rows.append(row)
    eligible=[r for r in rows if r['eligible']]
    for key in ('overall_ppg_gap','recent_ppg_gap','projected_home_shots','projected_shot_gap'):
        vals=[r[key] for r in eligible]
        for r in eligible:r[key+'_percentile']=round(percentile(r[key],vals),1)
    for r in eligible:r['environment_score']=round(.30*r['overall_ppg_gap_percentile']+.30*r['recent_ppg_gap_percentile']+.25*r['projected_home_shots_percentile']+.15*r['projected_shot_gap_percentile'],1)
    for rank,r in enumerate(sorted(eligible,key=lambda x:(-x['environment_score'],x['match_id'])),1):r['weekend_rank']=rank;r['selected_environment']=rank<=5 and r['confidence_tier'] in ('A','B')
    for r in rows:
        if not r['eligible']:r['selected_environment']=False
    obj={'status':'environment_locked_awaiting_lineups','prospective':True,'created_utc':datetime.now(timezone.utc).isoformat(),'weekend':weekend,'rules':{'environment':'top five ranked Tier A/B fixtures','A':'confirmed starter; top two eligible shooter; avg minutes >=70; 4/5 recent 2+ hits','B':'A plus avg shots >=3 and avg minutes >=80'},'fixtures':rows}
    snapshot.write_text(json.dumps(obj,indent=2),encoding='utf-8');(out/'manifest.json').write_text(json.dumps({'environment_snapshot_sha256':sha(snapshot),'selected_environment_ids':[r['match_id'] for r in rows if r['selected_environment']],'outcome_accessed':False},indent=2),encoding='utf-8');print(json.dumps({'status':obj['status'],'weekend':weekend,'fixtures':len(rows),'ranked':len(eligible),'selected':sum(r['selected_environment'] for r in rows),'snapshot':str(snapshot),'sha256':sha(snapshot)},indent=2))
def lineup_lock(weekend):
    out=BASE/weekend;snapshot=out/'environment_snapshot.json'
    if not snapshot.exists():raise SystemExit('Prepare the environment snapshot first.')
    obj=json.loads(snapshot.read_text(encoding='utf-8'));lockdir=out/'lineup_locks';lockdir.mkdir(exist_ok=True);created=[];waiting=[];refused=[]
    for env in [r for r in obj['fixtures'] if r['selected_environment']]:
        path=lockdir/f"{env['match_id']}.json"
        if path.exists():continue
        d=get_json('https://www.fotmob.com/api/data/matchDetails?'+urllib.parse.urlencode({'matchId':env['match_id']}));general=d.get('general') or {};lineup=(d.get('content') or {}).get('lineup') or {};home=lineup.get('homeTeam') or {};starters={str(p['id']) for p in home.get('starters') or [] if p.get('id') is not None}
        if general.get('started') or general.get('finished'):refused.append({'match_id':env['match_id'],'reason':'already_started_or_finished'});continue
        if len(starters)<11:waiting.append(env['match_id']);continue
        ranked=[p for p in env['candidate_pool'] if p['player_id'] in starters];ranked.sort(key=lambda p:(-p['avg_shots'],-p['avg_minutes'],p['player_id']))
        picks=[]
        for rank,p in enumerate(ranked,1):
            a=rank<=2 and p['avg_minutes']>=70 and p['recent_hits']>=4;b=a and p['avg_shots']>=3 and p['avg_minutes']>=80
            if a:picks.append({**p,'shooter_rank':rank,'A':True,'B':b})
        lock={'status':'locked_before_kickoff','locked_utc':datetime.now(timezone.utc).isoformat(),'match_id':env['match_id'],'date':env['date'],'league':env['league'],'fixture':env['fixture'],'environment_rank':env['weekend_rank'],'confidence_tier':env['confidence_tier'],'confirmed_home_starter_ids':sorted(starters),'picks':picks,'outcome_accessed':False};path.write_text(json.dumps(lock,indent=2),encoding='utf-8');created.append({'match_id':env['match_id'],'fixture':env['fixture'],'picks':len(picks),'A':[p['player'] for p in picks],'B':[p['player'] for p in picks if p['B']]})
    print(json.dumps({'created':created,'waiting_for_lineups':waiting,'refused_after_start':refused},indent=2))
def settle(weekend):
    out=BASE/weekend;lockdir=out/'lineup_locks';settledir=out/'settled';settledir.mkdir(exist_ok=True);new=[];waiting=[]
    for path in sorted(lockdir.glob('*.json')) if lockdir.exists() else []:
        lock=json.loads(path.read_text(encoding='utf-8'));dest=settledir/path.name
        if dest.exists():continue
        d=get_json('https://www.fotmob.com/api/data/matchDetails?'+urllib.parse.urlencode({'matchId':lock['match_id']}));general=d.get('general') or {}
        if not general.get('finished'):waiting.append(lock['match_id']);continue
        stats=(d.get('content') or {}).get('playerStats') or {};picks=[]
        for p in lock['picks']:
            ps=stats.get(str(p['player_id'])) or {};shots=extract_stat(ps,'total_shots');minutes=extract_stat(ps,'minutes_played')
            if shots is None and minutes is not None:shots=0
            picks.append({**p,'shots':shots,'hit':shots>=2 if shots is not None else None})
        result={**lock,'status':'settled','settled_utc':datetime.now(timezone.utc).isoformat(),'picks':picks};dest.write_text(json.dumps(result,indent=2),encoding='utf-8');new.append({'match_id':lock['match_id'],'fixture':lock['fixture'],'picks':[(p['player'],p['shots'],p['hit']) for p in picks]})
    all_results=[json.loads(p.read_text(encoding='utf-8')) for p in settledir.glob('*.json')];picks=[p for r in all_results for p in r['picks']];summary={'weekend':weekend,'settled_matches':len(all_results),'A':{'hits':sum(p['hit'] is True for p in picks),'picks':sum(p['hit'] is not None for p in picks)},'B':{'hits':sum(p['hit'] is True for p in picks if p['B']),'picks':sum(p['hit'] is not None for p in picks if p['B'])},'newly_settled':new,'waiting':waiting};(out/'settlement_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary,indent=2))
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','lineups','settle']);p.add_argument('--weekend',required=True);a=p.parse_args();{'prepare':prepare,'lineups':lineup_lock,'settle':settle}[a.mode](a.weekend)
if __name__=='__main__':main()
