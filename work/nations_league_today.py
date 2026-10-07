"""One-day Nations League shadow scan using national-team histories and lineups."""
import gzip,json,urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timedelta,timezone
from html import escape
from pathlib import Path
from statistics import mean

from download_fotmob_big5_carryover import get_json,extract_stat,team_total_shots

ROOT=Path(__file__).resolve().parents[1];DAY='2026-09-29';OUT=ROOT/f'outputs/nations_league_{DAY}';RAW=OUT/'raw';LEAGUES={9806:'A',9807:'B',9808:'C',9809:'D'}
def dt(x):return datetime.fromisoformat(x.replace('Z','+00:00'))
def avg(rows,key):
    vals=[r[key] for r in rows if r.get(key) is not None];return mean(vals) if vals else None
def pct(value,values):
    if len(values)==1:return 50
    return 100*(sum(v<value for v in values)+(sum(v==value for v in values)-1)/2)/(len(values)-1)
def cached_detail(mid):
    p=RAW/f'match_{mid}.json.gz'
    if p.exists():return json.loads(gzip.decompress(p.read_bytes()))
    d=get_json('https://www.fotmob.com/api/data/matchDetails?'+urllib.parse.urlencode({'matchId':mid}));p.write_bytes(gzip.compress(json.dumps(d).encode()));return d
def main():
    OUT.mkdir(parents=True,exist_ok=True);RAW.mkdir(exist_ok=True);targets=[]
    for lid,division in LEAGUES.items():
        data=get_json('https://www.fotmob.com/api/data/leagues?'+urllib.parse.urlencode({'id':lid,'ccode3':'INT','season':'2026/2027'}))
        for m in data['fixtures']['allMatches']:
            if m['status']['utcTime'][:10]==DAY:m=dict(m);m.update(division=division,league_id=lid);targets.append(m)
    team_fixtures={};history_meta={}
    for f in targets:
        for side in ('home','away'):
            tid=str(f[side]['id'])
            if tid in team_fixtures:continue
            data=get_json('https://www.fotmob.com/api/data/teams?'+urllib.parse.urlencode({'id':tid,'ccode3':'INT'}));rows=data['fixtures']['allFixtures']['fixtures'];team_fixtures[tid]=rows
            cutoff=dt(f['status']['utcTime'])-timedelta(days=1);lower=dt(f['status']['utcTime'])-timedelta(days=180)
            for m in rows:
                when=dt(m['status']['utcTime'])
                if m['status'].get('finished') and lower<=when<cutoff:history_meta[str(m['id'])]=m
    details={};all_ids=list(history_meta)+[str(f['id']) for f in targets]
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures={pool.submit(cached_detail,mid):mid for mid in all_ids}
        for future in as_completed(futures):details[futures[future]]=future.result()
    team_hist=defaultdict(list);player_hist=defaultdict(list)
    for mid,m in history_meta.items():
        d=details[mid];g=d.get('general') or {};date=dt(g['matchTimeUTCDate']);totals=team_total_shots(d);home=str(g['homeTeam']['id']);away=str(g['awayTeam']['id']);header=d.get('header') or {};status=header.get('status') or {};score=status.get('scoreStr') or m['status'].get('scoreStr') or ''
        try:hs,ass=map(int,[x.strip() for x in score.split('-')[:2]])
        except:continue
        for tid,is_home,gf,ga,shots,against in ((home,True,hs,ass,totals[0],totals[1]),(away,False,ass,hs,totals[1],totals[0])):team_hist[tid].append({'date':date,'match_id':mid,'home':is_home,'points':3 if gf>ga else 1 if gf==ga else 0,'shots':shots,'against':against,'nations_league':m.get('tournament',{}).get('leagueId') in LEAGUES})
        lineup=(d.get('content') or {}).get('lineup') or {};stats=(d.get('content') or {}).get('playerStats') or {}
        for side in ('homeTeam','awayTeam'):
            team=lineup.get(side) or {};tid=str(team.get('id'))
            for p in team.get('starters') or []:
                q=stats.get(str(p['id'])) or {};minutes=extract_stat(q,'minutes_played');shots=extract_stat(q,'total_shots');shots=0 if shots is None and minutes is not None else shots
                player_hist[tid,str(p['id'])].append({'date':date,'match_id':mid,'player':q.get('name') or p.get('name'),'minutes':minutes,'shots':shots})
    rows=[]
    for f in targets:
        d=details[str(f['id'])];date=dt(f['status']['utcTime']);cutoff=date-timedelta(days=1);hid=str(f['home']['id']);aid=str(f['away']['id']);h=sorted([r for r in team_hist[hid] if r['date']<cutoff],key=lambda r:r['date'])[-8:];a=sorted([r for r in team_hist[aid] if r['date']<cutoff],key=lambda r:r['date'])[-8:];hv=[r for r in h if r['home'] and r['shots'] is not None and r['against'] is not None][-5:];av=[r for r in a if not r['home'] and r['shots'] is not None and r['against'] is not None][-5:];eligible=len(h)>=5 and len(a)>=5 and len(hv)>=2 and len(av)>=2;hc=sum(r['nations_league'] for r in h);ac=sum(r['nations_league'] for r in a);tier='A' if hc>=3 and ac>=3 else 'B' if hc>=1 and ac>=1 else 'C';lineup=(d.get('content') or {}).get('lineup') or {};home_lineup=lineup.get('homeTeam') or {};starters=home_lineup.get('starters') or []
        row={'match_id':str(f['id']),'date':f['status']['utcTime'],'division':f['division'],'fixture':f['home']['name']+' vs '+f['away']['name'],'home':f['home']['name'],'away':f['away']['name'],'eligible':eligible,'confidence_tier':tier if eligible else 'EXCLUDED','lineup_source':lineup.get('source'),'home_starters_count':len(starters),'candidates':[]}
        if eligible:
            row.update(overall_ppg_gap=avg(h,'points')-avg(a,'points'),recent_ppg_gap=avg(h[-5:],'points')-avg(a[-5:],'points'),home_home_shots=avg(hv,'shots'),away_away_conceded=avg(av,'against'),away_away_shots=avg(av,'shots'),home_home_conceded=avg(hv,'against'));row['projected_home_shots']=(row['home_home_shots']+row['away_away_conceded'])/2;row['projected_away_shots']=(row['away_away_shots']+row['home_home_conceded'])/2;row['projected_shot_gap']=row['projected_home_shots']-row['projected_away_shots']
        for p in starters:
            prior=sorted([r for r in player_hist[hid,str(p['id'])] if r['date']<cutoff],key=lambda r:r['date'])[-5:]
            if len(prior)==5 and all(r['shots'] is not None and r['minutes'] is not None for r in prior):row['candidates'].append({'player_id':str(p['id']),'player':p['name'],'avg_shots':avg(prior,'shots'),'avg_minutes':avg(prior,'minutes'),'recent_hits':sum(r['shots']>=2 for r in prior),'prior_ids':[r['match_id'] for r in prior]})
        rows.append(row)
    eligible=[r for r in rows if r['eligible']]
    for key in ('overall_ppg_gap','recent_ppg_gap','projected_home_shots','projected_shot_gap'):
        vals=[r[key] for r in eligible]
        for r in eligible:r[key+'_percentile']=round(pct(r[key],vals),1)
    for r in eligible:r['environment_score']=round(.3*r['overall_ppg_gap_percentile']+.3*r['recent_ppg_gap_percentile']+.25*r['projected_home_shots_percentile']+.15*r['projected_shot_gap_percentile'],1)
    for rank,r in enumerate(sorted(eligible,key=lambda x:(-x['environment_score'],x['match_id'])),1):
        r['rank']=rank;r['selected_environment']=rank<=5 and r['confidence_tier'] in ('A','B');r['candidates'].sort(key=lambda x:(-x['avg_shots'],-x['avg_minutes'],x['player_id']))
        for i,c in enumerate(r['candidates'],1):c['shooter_rank']=i;c['A']=r['selected_environment'] and i<=2 and c['avg_minutes']>=70 and c['recent_hits']>=4;c['B']=c['A'] and c['avg_shots']>=3 and c['avg_minutes']>=80
    picks=[{'environment_rank':r['rank'],'fixture':r['fixture'],'division':r['division'],'confidence_tier':r['confidence_tier'],'lineup_source':r['lineup_source'],**c} for r in eligible if r.get('selected_environment') for c in r['candidates'] if c['A']]
    result={'created_utc':datetime.now(timezone.utc).isoformat(),'date':DAY,'classification':'same-day provisional/lineup-time shadow scan; not part of validated big-five sample','fixtures':rows,'picks':picks,'limits':['National-team histories mix competitions and are sparser than club histories.','enetpulse lineups are treated as confirmed; lastStartingLineups are possible lineups and remain provisional.','Only home-team candidates are considered to preserve the home-environment thesis.','No odds or outcomes entered the selection calculation.']};(OUT/'scan.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    selected=sorted([r for r in eligible if r.get('selected_environment')],key=lambda r:r['rank']);trs=''.join(f'<tr><td>{r["rank"]}</td><td>{escape(r["fixture"])}</td><td>{r["environment_score"]}</td><td>{r["confidence_tier"]}</td><td>{r["lineup_source"]}</td><td>{r["projected_home_shots"]:.1f}</td></tr>' for r in selected);prs=''.join(f'<tr><td>{p["environment_rank"]}</td><td>{escape(p["fixture"])}</td><td>{escape(p["player"])}</td><td>{"A+B" if p["B"] else "A"}</td><td>{p["avg_shots"]:.1f}</td><td>{p["recent_hits"]}/5</td><td>{p["lineup_source"]}</td></tr>' for p in picks)
    html=f'''<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nations League candidates</title><style>body{{font:16px/1.5 system-ui;max-width:1100px;margin:30px auto;padding:0 18px;background:#f3f6f8}}table{{border-collapse:collapse;background:#fff;width:100%;margin-bottom:24px}}td,th{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}.warn{{background:#fff3cf;padding:15px}}</style><h1>UEFA Nations League — {DAY}</h1><p class="warn">One-day shadow scan. <code>lastStartingLineups</code> means possible lineup; <code>enetpulse</code> is treated as confirmed. This does not extend the club-model validation rate.</p><h2>Top environments</h2><table><tr><th>Rank</th><th>Fixture</th><th>Score</th><th>Tier</th><th>Lineup</th><th>Projected home shots</th></tr>{trs}</table><h2>Candidates</h2><table><tr><th>Env</th><th>Fixture</th><th>Player</th><th>Plan</th><th>Avg shots</th><th>2+ history</th><th>Lineup source</th></tr>{prs}</table><p><a href="scan.json">Full scan and histories</a></p></html>''';(OUT/'index.html').write_text(html,encoding='utf-8');print(json.dumps({'fixtures':len(rows),'eligible':len(eligible),'selected_environments':[(r['rank'],r['fixture'],r['lineup_source']) for r in selected],'picks':picks},indent=2))
if __name__=='__main__':main()
