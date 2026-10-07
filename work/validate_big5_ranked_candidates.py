"""Untouched 2024/25 validation of ranked environments followed by candidate filters."""
import hashlib,json
from collections import Counter
from html import escape
from pathlib import Path
from zipfile import ZIP_DEFLATED,ZipFile

from build_big5_environment_rankings import process
from validate_big5_carryover import measure,rollover

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/big5_2024_ranked_candidate_validation';PLAN=ROOT/'work/big5_ranked_candidate_validation_plan.json'
CONFIG={'slug':'big5_2024_ranked_candidate_validation','label':'2024/25','current':'2024/2025','previous':'2023/2024','weeks':['2024-09-14','2024-09-21','2024-09-28','2024-10-05']}
def main():
    plan=json.loads(PLAN.read_text(encoding='utf-8'));fixtures=process(CONFIG);samples=[];picks=[]
    qualifying_fixtures=[r for r in fixtures if r['eligible'] and r['weekend_rank']<=5 and r['confidence_tier'] in ('A','B')]
    for env in fixtures:
        fixture_qualifies=env in qualifying_fixtures
        for c in env['ranked_candidates']:
            a=bool(fixture_qualifies and c['shooter_rank']<=2 and c['avg_minutes']>=70 and c['hits_2plus']>=4)
            b=bool(a and c['avg_shots']>=3 and c['avg_minutes']>=80)
            reasons=[]
            if not env['eligible']:reasons.append('environment_history_excluded')
            elif env['weekend_rank']>5:reasons.append('outside_top_five_environments')
            elif env['confidence_tier']=='C':reasons.append('historical_only_tier_C')
            if c['shooter_rank']>2:reasons.append('outside_top_two_shooters')
            if c['avg_minutes']<70:reasons.append('minutes_below_70')
            if c['hits_2plus']<4:reasons.append('fewer_than_four_recent_hits')
            row={'dataset':'2024/25','match_id':env['match_id'],'date':env['date'],'weekend':env['weekend'],'league':env['league'],'fixture':env['fixture'],
                 'environment_rank':env.get('weekend_rank'),'environment_score':env.get('environment_score'),'confidence_tier':env['confidence_tier'],
                 'home_current_matches':env['home_current_matches'],'away_current_matches':env['away_current_matches'],
                 'player_id':c['player_id'],'player':c['player'],'shooter_rank':c['shooter_rank'],'avg_shots':c['avg_shots'],'avg_minutes':c['avg_minutes'],
                 'recent_hits':c['hits_2plus'],'current_season_starts':c['current_season_starts'],'player_confidence':c['player_confidence'],
                 'prior_ids':c['prior_ids'],'shots':c['shots'],'hit':c['hit_2plus'],'A':a,'B':b,'exclusion_reasons':reasons}
            samples.append(row)
            if a:picks.append(row)
    a=picks;b=[r for r in picks if r['B']]
    by_week=[{'weekend':w,'A':measure([r for r in a if r['weekend']==w]),'B':measure([r for r in b if r['weekend']==w])} for w in CONFIG['weeks']]
    leagues=sorted({r['league'] for r in fixtures});by_league={x:{'A':measure([r for r in a if r['league']==x]),'B':measure([r for r in b if r['league']==x])} for x in leagues}
    env_known=[r for r in qualifying_fixtures if r['home_outshot_away'] is not None];env_hits=sum(r['home_outshot_away'] for r in env_known)
    result={'name':plan['name'],'classification':'third-season untouched historical outcome validation of the frozen ranking workflow','plan_sha256':hashlib.sha256(PLAN.read_bytes()).hexdigest(),
            'source_matches':json.loads((OUT/'acquisition.json').read_text(encoding='utf-8'))['normalized_matches'],'target_fixtures':len(fixtures),'ranked_fixtures':sum(r['eligible'] for r in fixtures),
            'qualifying_top_five_A_or_B_environments':len(qualifying_fixtures),'environment_home_outshot':{'hits':env_hits,'fixtures':len(env_known),'rate':round(100*env_hits/len(env_known),1) if env_known else None},
            'candidate_samples':len(samples),'A':measure(a),'B':measure(b),'by_weekend':by_week,'by_league':by_league,
            'confidence_counts':dict(Counter(r['confidence_tier'] for r in fixtures)),'exclusions':dict(Counter(reason for r in samples for reason in r['exclusion_reasons'])),
            'betting':{'A':rollover(a,1.5),'B':rollover(b,2.0)},'limits':plan['limits']+['Multiple players or fixtures in one weekend are correlated.','Hit rates are descriptive historical estimates, not guaranteed probabilities.']}
    for name,obj in [('frozen_test_plan',plan),('ranked_fixtures',fixtures),('all_candidate_samples',samples),('qualifying_picks',picks),('results',result),('betting_simulation',result['betting'])]:(OUT/(name+'.json')).write_text(json.dumps(obj,indent=2),encoding='utf-8')
    def fmt(m):return 'No picks' if not m['picks'] else f'{m["hits"]}/{m["picks"]} ({m["rate"]}%)'
    lines=[f"# {plan['name']}",'',f"{result['source_matches']} source matches; {result['target_fixtures']} target fixtures; {result['qualifying_top_five_A_or_B_environments']} top-five Tier A/B environments.",'',f"Environment check: home outshot away in {env_hits}/{len(env_known)} ({result['environment_home_outshot']['rate']}%).",'',f"Candidate A: **{fmt(result['A'])}**. Candidate B: **{fmt(result['B'])}**.",'','## By weekend','','| Weekend | A | B |','|---|---:|---:|']
    for r in by_week:lines.append(f'| {r["weekend"]} | {fmt(r["A"])} | {fmt(r["B"])} |')
    lines+=['','## Limits','']+['- '+x for x in result['limits']];(OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    pickrows=''.join(f'<tr><td>{r["weekend"]}</td><td>{r["environment_rank"]}</td><td>{escape(r["league"])}</td><td>{escape(r["fixture"])}</td><td>{escape(r["player"])}</td><td>{"A+B" if r["B"] else "A"}</td><td>{r["shots"]}</td><td>{"HIT" if r["hit"] else "MISS"}</td></tr>' for r in picks)
    html=f'''<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ranked candidate validation</title><style>body{{font:16px/1.55 system-ui;max-width:1200px;margin:30px auto;padding:0 18px;background:#f3f6f8;color:#183142}}table{{border-collapse:collapse;background:#fff;width:100%}}th,td{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}.scroll{{overflow:auto}}.card{{background:#fff;padding:18px;margin:15px 0}}a{{color:#176a7a}}</style><h1>Third-season ranked-environment validation</h1><div class="card">{result['target_fixtures']} target fixtures · {result['qualifying_top_five_A_or_B_environments']} selected environments · home outshot away: <b>{env_hits}/{len(env_known)} ({result['environment_home_outshot']['rate']}%)</b><br>Candidate A: <b>{fmt(result['A'])}</b> · Candidate B: <b>{fmt(result['B'])}</b></div><p><a href="report.md">Method and limits</a> · <a href="ranked_fixtures.json">Every environment</a> · <a href="qualifying_picks.json">Every pick</a></p><div class="scroll"><table><tr><th>Weekend</th><th>Env rank</th><th>League</th><th>Fixture</th><th>Player</th><th>Plan</th><th>Shots</th><th>Result</th></tr>{pickrows}</table></div></html>''';(OUT/'index.html').write_text(html,encoding='utf-8')
    page=ROOT/'outputs/project_site/dist/index.html'
    if page.exists():
        text=page.read_text(encoding='utf-8');start,end='<!-- BIG5_RANKED_VALIDATION_START -->','<!-- BIG5_RANKED_VALIDATION_END -->'
        if start in text:before,tail=text.split(start,1);text=before+tail.split(end,1)[1]
        panel=f'''{start}<section id="big5-ranked-validation" class="panel" style="margin:24px 0"><div class="eyebrow">NEW · THIRD-SEASON UNTOUCHED REPLAY</div><h2>Environment rank first, candidates second</h2><p>Top-five Tier A/B environments: {len(qualifying_fixtures)}. Environment home-shot dominance: {env_hits}/{len(env_known)} ({result['environment_home_outshot']['rate']}%). Candidate A: {fmt(result['A'])}; B: {fmt(result['B'])}.</p><p><a href="../../big5_2024_ranked_candidate_validation/index.html">Open every environment and selection</a></p></section>{end}''';page.write_text(text.replace('</header>','</header>'+panel,1),encoding='utf-8')
    with ZipFile(OUT.parent/f'{OUT.name}.zip','w',ZIP_DEFLATED) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file() and 'raw' not in p.parts:z.write(p,p.relative_to(OUT))
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
