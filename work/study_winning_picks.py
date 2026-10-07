"""Bounded, exploratory winner-vs-miss research; never edits production rules."""
import json
from collections import Counter
from html import escape
from pathlib import Path
from statistics import mean
from test_home_pattern import measure

OUT=Path(__file__).resolve().parents[1]/'outputs'
# These ten filters are declared before results; no grid search or adaptive tuning.
FILTERS={
 'Top-ranked shooter only':lambda r:r['shooter_rank']==1,
 'Previous five starts: 5/5 hits':lambda r:r['recent_hits']==5,
 'Prior average shots >=3':lambda r:r['recent_shots']>=3,
 'Prior average shot share >=25%':lambda r:r['recent_share'] is not None and r['recent_share']>=.25,
 'Prior average minutes >=80':lambda r:r['recent_minutes']>=80,
 'Projected home shots >=16':lambda r:r['projected_home_shots']>=16,
 'Projected home shot advantage >=4':lambda r:r['projected_home_shots']-r['projected_away_shots']>=4,
 'Season PPG advantage >=0.5':lambda r:r['home_ppg']-r['away_ppg']>=.5,
 'Prior shots >=3 AND minutes >=80':lambda r:r['recent_shots']>=3 and r['recent_minutes']>=80,
 '5/5 prior hits AND top-ranked shooter':lambda r:r['recent_hits']==5 and r['shooter_rank']==1,
}

def main():
    rows=[]
    w=json.loads((OUT/'weekly_pattern_replay.json').read_text(encoding='utf-8'))
    for r in w['picks']:
        if r['full_pattern']:rows.append(dict(r,dataset='MLS',provider='sportsapipro'))
    for slug in ['epl_2015_16_validation','laliga_2015_16_validation','seriea_2015_16_validation']:
        for r in json.loads((OUT/slug/'qualifying_picks.json').read_text(encoding='utf-8')):
            if r['full_pattern']:rows.append(dict(r['features'],dataset=r['features']['competition'],provider='statsbomb'))
    assert len(rows)==431 and sum(r['hit'] for r in rows)==353
    splits={}
    for league in sorted({r['dataset'] for r in rows}):
        # Full fixture dates stay together. 70% of qualifying dates, per league.
        dates=sorted({r['date'][:10] for r in rows if r['dataset']==league})
        splits[league]=dates[int(.7*len(dates))]
    for r in rows:
        r['period']='earlier' if r['date'][:10]<splits[r['dataset']] else 'later'
        r['filter_matches']={name:bool(fn(r)) for name,fn in FILTERS.items()}
    def stats(subset):
        return dict(all=measure(subset),earlier=measure([r for r in subset if r['period']=='earlier']),
            later=measure([r for r in subset if r['period']=='later']),
            by_league={league:measure([r for r in subset if r['dataset']==league]) for league in splits},
            later_by_league={league:measure([r for r in subset if r['dataset']==league and r['period']=='later']) for league in splits})
    baseline=stats(rows)
    findings={}
    for name,fn in FILTERS.items():
        subset=[r for r in rows if fn(r)]
        excluded=[r for r in rows if not fn(r)]
        counts=Counter((r['provider'],r['player_id']) for r in subset)
        top3={pid for pid,n in counts.most_common(3)}
        m=stats(subset)
        m.update(excluded=stats(excluded),retained_pct=round(100*len(subset)/len(rows),1),
            without_three_most_selected_players=measure([r for r in subset if (r['provider'],r['player_id']) not in top3]),
            top_three_pick_share_pct=round(100*sum(counts[k] for k in top3)/len(subset),1) if subset else None)
        findings[name]=m
    # Discovery choice uses EARLIER data only, with a fixed volume/coverage floor.
    candidates=[name for name,m in findings.items() if m['earlier']['n']>=80
        and m['earlier']['n']>=.35*baseline['earlier']['n']
        and len({r['dataset'] for r in rows if r['period']=='earlier' and FILTERS[name](r)})>=3]
    chosen=max(candidates,key=lambda name:(findings[name]['earlier']['hits']/findings[name]['earlier']['n'],findings[name]['earlier']['n'],name)) if candidates else None
    fields=['recent_shots','recent_share','recent_minutes','recent_hits','home_home_shots','away_away_conceded','projected_home_shots','home_ppg','away_ppg']
    contrasts={}
    for key in fields:
        contrasts[key]={label:dict(n=len(vals),mean=round(mean(vals),4) if vals else None)
            for label,vals in [(label,[r[key] for r in rows if r['hit']==hit and r[key] is not None]) for label,hit in [('wins',True),('misses',False)]]}
    result=dict(scope='Existing 431 full-pattern selections; Bundesliga two-pick batch excluded.',
        baseline=baseline,pre_match_winner_vs_miss=contrasts,filters=findings,earlier_only_choice=chosen,
        splits=splits,selection_policy='Highest earlier hit rate with >=80 earlier picks, >=35% of earlier baseline volume, and >=3 earlier leagues; ties use volume then name.',
        limitations=['Exploratory re-analysis of already inspected history, NOT an independent holdout or promised future probability.',
        'Ten predeclared filters, so multiple-comparison/overfitting risk remains. Later results do not choose the discovery winner.',
        'The last 30% of qualifying calendar dates per league is a stability check; these splits differ from previous reports.',
        'Only pre-match features select picks; no current shots, minutes, score or realised shot share is used.',
        'Player/fixture observations are correlated; displayed Wilson intervals are descriptive and ignore clustering.',
        'Higher rate can mean fewer opportunities; discarded picks and per-league results are reported. No odds or profit calculation.',
        'European data shares the 2015/16 era/provider. Rules and earlier published results remain unchanged.'],rows=rows)
    (OUT/'winning_pattern_research.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    def fmt(m):return f"{m['hits']}/{m['n']} ({m['rate']}%)" if m['n'] else 'No cases'
    lines=['# Winning-pick research: can we improve the pattern?','',
        '**Exploratory, not a proven upgrade.** Compared every existing full-pattern win with every miss; no wins-only success denominator. Bundesliga’s two preliminary picks are excluded.','',
        f"Baseline: {fmt(baseline['all'])}. Earlier: {fmt(baseline['earlier'])}; later: {fmt(baseline['later'])}.",'',
        '| Additional pre-match filter | All picks | Earlier | Later | Picks retained |','|---|---:|---:|---:|---:|']
    for name,m in findings.items():lines.append(f"| {name} | {fmt(m['all'])} | {fmt(m['earlier'])} | {fmt(m['later'])} | {m['retained_pct']}% |")
    lines+=['','## Practical findings','',
        'Prior shooting involvement is the strongest descriptive lead: winners averaged 3.63 shots per earlier start versus 3.12 for misses; prior shot share averaged 25.1% versus 22.0%. These are associations within our already-selected cohort, not causal effects.',
        'The 25% prior-share filter keeps only 38.5% of picks and improves the pooled rate, but Premier League performance falls to 19/24 (79.2%); its later subset is only 3/5. It is not a universal improvement.',
        'The shots >=3 plus minutes >=80 combination retains more opportunities (61.0%) and reaches 230/263 (87.5%), with 57/64 (89.1%) later. It is a second exploratory candidate, not the winner selected by the earlier-only ranking.',
        'A larger team-strength gap alone looks good earlier but drops to 59/73 (80.8%) later, below the later baseline. Do not tighten that rule just because it sounds plausible.',
        '', '## Candidate chosen using earlier results only','',str(chosen),result['selection_policy'],'']
    if chosen:
        m=findings[chosen]
        lines+=[f"Later check: {fmt(m['later'])}, versus baseline {fmt(baseline['later'])}. Discarded later picks: {fmt(m['excluded']['later'])}.",
            f"Without the three most-selected players: {fmt(m['without_three_most_selected_players'])}. Their share of selected picks was {m['top_three_pick_share_pct']}%.",'',
            '| League | Baseline overall | Filter overall | Baseline later | Filter later |','|---|---:|---:|---:|---:|']
        for league in splits:lines.append(f"| {league} | {fmt(baseline['by_league'][league])} | {fmt(m['by_league'][league])} | {fmt(baseline['later_by_league'][league])} | {fmt(m['later_by_league'][league])} |")
    lines+=['','## What winners looked like before kickoff','', '| Feature | Wins: average | Misses: average |','|---|---:|---:|']
    for key,v in contrasts.items():lines.append(f"| {key} | {v['wins']['mean']} (n={v['wins']['n']}) | {v['misses']['mean']} (n={v['misses']['n']}) |")
    lines+=['','## Limitations','']+['- '+x for x in result['limitations']]+['',
        'Next: keep the original rule as the benchmark and test this candidate unchanged on a genuinely untouched dataset. Do not retrospectively overwrite the baseline or discard its misses.','']
    (OUT/'winning_pattern_research.md').write_text('\n'.join(lines),encoding='utf-8')
    tr=''.join(f'<tr><td>{escape(name)}</td><td>{fmt(m["all"])}</td><td>{fmt(m["earlier"])}</td><td>{fmt(m["later"])}</td><td>{m["retained_pct"]}%</td></tr>' for name,m in findings.items())
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Winning-pick research</title><style>body{{font:16px/1.6 system-ui;max-width:1200px;margin:30px auto;padding:0 20px;background:#f2f5f8;color:#182b3e}}.scroll{{overflow:auto}}table{{border-collapse:collapse;background:white;width:100%}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #ddd}}a{{color:#216e83}}</style><h1>What separates our wins from misses?</h1><p>Baseline: <b>{fmt(baseline['all'])}</b>. Ten bounded pre-match filter tests; all losses retained in the comparison.</p><p><b>Exploratory only:</b> this history has already been inspected. No production rule changes, no new independent validation, no profit claim.</p><div class="scroll"><table><tr><th>Additional filter</th><th>Overall</th><th>Earlier</th><th>Later</th><th>Volume retained</th></tr>{tr}</table></div><h2>Earlier-data-only candidate</h2><p>{escape(str(chosen))}</p><p>The report shows per-league results, rejected picks and the effect of excluding the three most-selected players.</p><p><a href="winning_pattern_research.md">Full findings and limits</a> · <a href="winning_pattern_research.json">All 431 picks, features and filter decisions</a></p></html>'''
    html=html.replace('<h2>Earlier-data-only candidate</h2>', '<h2>Practical reading</h2><p>Prior shooting involvement separates wins from misses more clearly than simply increasing team strength. A 25% prior shot-share filter improves the pooled result, but keeps only 38.5% of picks and worsens Premier League results (19/24). Three prior shots per start plus 80 average minutes is a second research lead (230/263), retaining 61% of picks.</p><h2>Earlier-data-only candidate</h2>')
    (OUT/'winning_pattern_research.html').write_text(html,encoding='utf-8')
    page=OUT/'project_site/dist/index.html';text=page.read_text(encoding='utf-8')
    start,end='<!-- WINNING_RESEARCH_START -->','<!-- WINNING_RESEARCH_END -->'
    if start in text:
        before,tail=text.split(start,1);text=before+tail.split(end,1)[1]
    panel=f'''{start}<section id="winning-research" class="panel" style="margin:24px 0"><div class="eyebrow">WIN VS MISS RESEARCH · EXPLORATORY</div><h2>Testing improvements without changing the baseline</h2><p>431 picks analysed; ten pre-match filters compared with the original rule. Earlier-only candidate: <b>{escape(str(chosen))}</b>. Existing history is not independent validation.</p><p><a href="../../winning_pattern_research.html">Results, volume trade-offs and every sample</a></p></section>{end}'''
    page.write_text(text.replace('</header>','</header>'+panel,1),encoding='utf-8')
    print(json.dumps(dict(baseline=baseline,contrasts=contrasts,chosen=chosen,filters={n:{k:m[k] for k in ['all','earlier','later','retained_pct','without_three_most_selected_players']} for n,m in findings.items()}),indent=2))

if __name__=='__main__':main()
