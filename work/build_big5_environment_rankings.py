"""Build the exploratory fixture ranking layer from the two saved carryover datasets."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from statistics import mean

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/big5_environment_rankings'
SPEC=ROOT/'work/big5_environment_ranking_spec.json'
DATASETS=[
    {'slug':'big5_2026_prebreak_carryover','label':'2026/27','current':'2026/2027','previous':'2025/2026','weeks':['2026-08-29','2026-09-05','2026-09-12','2026-09-19']},
    {'slug':'big5_2025_carryover_replication','label':'2025/26','current':'2025/2026','previous':'2024/2025','weeks':['2025-09-13','2025-09-20','2025-09-27','2025-10-04']},
]
def dt(x):return datetime.fromisoformat(x.replace('Z','+00:00'))
def avg(rows,key):
    vals=[r[key] for r in rows if r.get(key) is not None]
    return mean(vals) if vals else None
def week_of(date,weeks):
    d=dt(date).date()
    return next((w for w in weeks if 0<=(d-datetime.fromisoformat(w).date()).days<=1),None)
def percentile(value,values):
    if len(values)==1:return 50.0
    less=sum(v<value for v in values);equal=sum(v==value for v in values)
    return 100*(less+(equal-1)/2)/(len(values)-1)

def process(config):
    base=ROOT/'outputs'/config['slug']
    matches=json.loads((base/'normalized_matches.json').read_text(encoding='utf-8'))
    matches.sort(key=lambda r:(r['date'],r['match_id']))
    target_dates={d.isoformat() for w in config['weeks'] for d in (datetime.fromisoformat(w).date(),datetime.fromisoformat(w).date()+timedelta(days=1))}
    team_history=defaultdict(list);player_history=defaultdict(list);fixtures=[]
    for m in matches:
        date=dt(m['date']);cutoff=date-timedelta(days=1);league=m['league'];hid=m['home_team_id'];aid=m['away_team_id']
        target=m['season']==config['current'] and date.date().isoformat() in target_dates
        if target:
            histories={}
            for tid in (hid,aid):
                eligible=[r for r in team_history[league,tid] if r['date']<cutoff and date-r['date']<=timedelta(days=180)]
                current=[r for r in eligible if r['season']==config['current']]
                previous=[r for r in eligible if r['season']==config['previous']]
                histories[tid]=(previous[-max(0,8-len(current)):] + current) if len(current)<8 else current[-8:]
            h,a=histories[hid],histories[aid];hv=[r for r in h if r['home'] and r['shots'] is not None and r['against'] is not None][-5:];av=[r for r in a if not r['home'] and r['shots'] is not None and r['against'] is not None][-5:]
            eligible=len(h)>=5 and len(a)>=5 and len(hv)>=2 and len(av)>=2
            hc=sum(r['season']==config['current'] for r in h);ac=sum(r['season']==config['current'] for r in a)
            tier='A' if hc>=3 and ac>=3 else 'B' if hc>=1 and ac>=1 else 'C'
            row={'dataset':config['label'],'weekend':week_of(m['date'],config['weeks']),'match_id':m['match_id'],'date':m['date'],'league':league,
                 'fixture':m['home_team']+' vs '+m['away_team'],'home_team':m['home_team'],'away_team':m['away_team'],'eligible':eligible,
                 'confidence_tier':tier if eligible else 'EXCLUDED','home_current_matches':hc,'away_current_matches':ac,
                 'home_history_n':len(h),'away_history_n':len(a),'home_venue_n':len(hv),'away_venue_n':len(av),
                 'history_cutoff':cutoff.isoformat(),'home_prior_ids':[r['match_id'] for r in h],'away_prior_ids':[r['match_id'] for r in a],
                 'actual_home_shots':m['home_shots'],'actual_away_shots':m['away_shots']}
            row['home_outshot_away']=(m['home_shots']>m['away_shots']) if m['home_shots'] is not None and m['away_shots'] is not None else None
            if eligible:
                row.update(overall_ppg_gap=avg(h,'points')-avg(a,'points'),recent_ppg_gap=avg(h[-5:],'points')-avg(a[-5:],'points'),
                           home_home_shots=avg(hv,'shots'),away_away_conceded=avg(av,'against'),away_away_shots=avg(av,'shots'),home_home_conceded=avg(hv,'against'))
                row['projected_home_shots']=(row['home_home_shots']+row['away_away_conceded'])/2
                row['projected_away_shots']=(row['away_away_shots']+row['home_home_conceded'])/2
                row['projected_shot_gap']=row['projected_home_shots']-row['projected_away_shots']
            candidates=[]
            for p in m['players']:
                if p['team_id']!=hid or not p['started']:continue
                prior=[r for r in player_history[league,hid,p['player_id']] if r['date']<cutoff and date-r['date']<=timedelta(days=180)][-5:]
                complete=len(prior)==5 and all(r['shots'] is not None and r['minutes'] is not None for r in prior)
                c={'player_id':p['player_id'],'player':p['player'],'shots':p['shots'],'hit_2plus':p['shots']>=2 if p['shots'] is not None else None,
                   'history_n':len(prior),'complete_history':complete,'prior_ids':[r['match_id'] for r in prior],
                   'current_season_starts':sum(r['season']==config['current'] for r in prior)}
                if complete:c.update(avg_shots=avg(prior,'shots'),avg_minutes=avg(prior,'minutes'),hits_2plus=sum(r['shots']>=2 for r in prior))
                candidates.append(c)
            ranked=[c for c in candidates if c['complete_history']];ranked.sort(key=lambda c:(-c['avg_shots'],-c['avg_minutes'],c['player_id']))
            for i,c in enumerate(ranked,1):c['shooter_rank']=i;c['player_confidence']='current-supported' if c['current_season_starts']>=2 else 'historical-heavy'
            row['candidates']=candidates;row['ranked_candidates']=ranked
            fixtures.append(row)
        if None not in (m['home_score'],m['away_score']):
            for tid,home in ((hid,True),(aid,False)):
                gf=m['home_score'] if home else m['away_score'];ga=m['away_score'] if home else m['home_score']
                team_history[league,tid].append({'date':date,'match_id':m['match_id'],'season':m['season'],'home':home,'points':3 if gf>ga else 1 if gf==ga else 0,
                    'shots':m['home_shots'] if home else m['away_shots'],'against':m['away_shots'] if home else m['home_shots']})
        for p in m['players']:
            if p['started'] and p['team_id'] in (hid,aid):player_history[league,p['team_id'],p['player_id']].append({'date':date,'match_id':m['match_id'],'season':m['season'],'shots':p['shots'],'minutes':p['minutes']})
    for week in config['weeks']:
        rows=[r for r in fixtures if r['weekend']==week and r['eligible']]
        for key in ('overall_ppg_gap','recent_ppg_gap','projected_home_shots','projected_shot_gap'):
            vals=[r[key] for r in rows]
            for r in rows:r[key+'_percentile']=round(percentile(r[key],vals),1)
        for r in rows:r['environment_score']=round(.30*r['overall_ppg_gap_percentile']+.30*r['recent_ppg_gap_percentile']+.25*r['projected_home_shots_percentile']+.15*r['projected_shot_gap_percentile'],1)
        for rank,r in enumerate(sorted(rows,key=lambda x:(-x['environment_score'],x['match_id'])),1):r['weekend_rank']=rank
    return fixtures

def main():
    OUT.mkdir(parents=True,exist_ok=True);spec=json.loads(SPEC.read_text(encoding='utf-8'));fixtures=[]
    for config in DATASETS:fixtures+=process(config)
    eligible=[r for r in fixtures if r['eligible']]
    top5=[r for r in eligible if r['weekend_rank']<=5]
    def env_measure(rows):
        known=[r for r in rows if r['home_outshot_away'] is not None];hits=sum(r['home_outshot_away'] for r in known)
        return {'fixtures':len(rows),'known':len(known),'home_outshot':hits,'rate':round(100*hits/len(known),1) if known else None}
    tiers={tier:env_measure([r for r in eligible if r['confidence_tier']==tier]) for tier in ('A','B','C')}
    top_candidates=[]
    for r in eligible:
        for c in r['ranked_candidates'][:2]:top_candidates.append({'dataset':r['dataset'],'weekend':r['weekend'],'environment_rank':r['weekend_rank'],'confidence_tier':r['confidence_tier'],'fixture':r['fixture'],**c})
    summary={'specification':spec,'classification':'post-outcome exploratory design; not untouched validation','fixtures':len(fixtures),'eligible_ranked':len(eligible),
             'excluded':len(fixtures)-len(eligible),'confidence_counts':dict(Counter(r['confidence_tier'] for r in fixtures)),
             'environment_diagnostics_by_tier':tiers,'top_five_environment_diagnostic':env_measure(top5),
             'top_two_candidate_samples':len(top_candidates),'limits':['Outcome columns are diagnostic only and never enter ranks.','The weights were designed after viewing earlier carryover results.','Relative percentile scores cannot be compared as absolute probabilities across weekends.','Rank does not equal bet eligibility; confidence must remain visible.']}
    for name,obj in [('ranked_fixtures',fixtures),('ranked_candidates',top_candidates),('summary',summary),('ranking_specification',spec)]:
        (OUT/(name+'.json')).write_text(json.dumps(obj,indent=2),encoding='utf-8')
    rows=''.join(f'<tr><td>{r["dataset"]}</td><td>{r["weekend"]}</td><td>{r["weekend_rank"] if r["eligible"] else "—"}</td><td>{escape(r["fixture"])}</td><td>{r["environment_score"] if r["eligible"] else "excluded"}</td><td>{r["confidence_tier"]}</td><td>{r["home_current_matches"]}/{r["away_current_matches"]}</td><td>{r["projected_home_shots"]:.1f}</td></tr>' if r['eligible'] else f'<tr><td>{r["dataset"]}</td><td>{r["weekend"]}</td><td>—</td><td>{escape(r["fixture"])}</td><td>excluded</td><td>EXCLUDED</td><td>{r["home_current_matches"]}/{r["away_current_matches"]}</td><td>—</td></tr>' for r in sorted(fixtures,key=lambda x:(x['dataset'],x['weekend'],x.get('weekend_rank',999),x['fixture'])))
    html=f'''<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Environment rankings</title><style>body{{font:16px/1.5 system-ui;max-width:1300px;margin:30px auto;padding:0 18px;background:#f3f6f8;color:#183142}}table{{border-collapse:collapse;background:#fff;width:100%}}th,td{{padding:9px;border-bottom:1px solid #ddd;text-align:left}}.scroll{{overflow:auto}}.note{{background:#fff3cf;padding:15px;border-left:5px solid #d99200}}</style><h1>Big-five environment rankings</h1><p class="note"><b>Rank and confidence are separate.</b> Tier C uses historical-only evidence. This is exploratory design on already-seen seasons, not a new win-rate test.</p><p>{len(eligible)} fixtures ranked across eight weekends; {len(fixtures)-len(eligible)} excluded for insufficient comparable history. Tier counts: A {summary['confidence_counts'].get('A',0)}, B {summary['confidence_counts'].get('B',0)}, C {summary['confidence_counts'].get('C',0)}.</p><p><a href="summary.json">Summary</a> · <a href="ranking_specification.json">Exact weights and tiers</a> · <a href="ranked_candidates.json">Candidate layer</a></p><div class="scroll"><table><tr><th>Season</th><th>Weekend</th><th>Rank</th><th>Fixture</th><th>Score</th><th>Confidence</th><th>Current matches H/A</th><th>Projected home shots</th></tr>{rows}</table></div></html>'''
    (OUT/'index.html').write_text(html,encoding='utf-8')
    page=ROOT/'outputs/project_site/dist/index.html'
    if page.exists():
        text=page.read_text(encoding='utf-8');start,end='<!-- BIG5_RANKING_START -->','<!-- BIG5_RANKING_END -->'
        if start in text:before,tail=text.split(start,1);text=before+tail.split(end,1)[1]
        panel=f'''{start}<section id="big5-ranking" class="panel" style="margin:24px 0"><div class="eyebrow">NEW · ENVIRONMENT RANKING LAYER</div><h2>Rank every comparable fixture; show evidence confidence separately</h2><p>{len(eligible)} fixtures ranked across eight historical weekends. Tier A has current-season support; Tier B is limited-current; Tier C is historical-only. Promoted or insufficient-history teams remain excluded.</p><p class="note">Exploratory design on already-seen outcomes—not a new hit-rate validation.</p><p><a href="../../big5_environment_rankings/index.html">Open rankings and candidate layer</a></p></section>{end}'''
        page.write_text(text.replace('</header>','</header>'+panel,1),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='specification'},indent=2))

if __name__=='__main__':main()
