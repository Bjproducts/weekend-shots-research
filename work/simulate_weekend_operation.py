"""Descriptive Saturday/Sunday operation replay across frozen validation datasets."""
import json
from collections import Counter,defaultdict
from datetime import datetime
from html import escape
from pathlib import Path
from statistics import mean,median

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/weekend_operation_simulation';OUT.mkdir(exist_ok=True)
SOURCES=[
 ('Ligue 1 2015/16','ligue1_2015_16_ab_validation'),
 ('WSL 2023/24','wsl_2023_24_ab_validation'),
 ('Frauen-Bundesliga 2023/24','frauen_bundesliga_2023_24_ab_validation'),
 ('WSL 2020/21','wsl_2020_21_rollover_validation'),
 ('WSL 2018/19 random','random_wsl_2018_19_rollover_validation')]

def key(value):
    d=datetime.fromisoformat(value);iso=d.isocalendar();return f'{iso.year}-W{iso.week:02d}'
def metric(rows,odds):
    groups=defaultdict(list)
    for r in rows:groups[(r['dataset'],key(r['date']))].append(r)
    weekends=[]
    for (dataset,week),legs in sorted(groups.items()):
        legs=sorted(legs,key=lambda r:(r['date'],r['fixture_id'],r['player_id']));all_hit=all(r['hit'] for r in legs)
        ending=10*(odds**len(legs)) if all_hit else 0
        weekends.append(dict(dataset=dataset,week=week,picks=len(legs),hits=sum(r['hit'] for r in legs),all_hit=all_hit,
            starting_stake=10,ending_balance=round(ending,2),profit=round(ending-10,2),same_kickoff=len({r['date'] for r in legs})<len(legs),
            selections=[{k:r[k] for k in ('date','fixture','player','shots','hit')} for r in legs]))
    n=len(rows);wins=sum(r['hit'] for r in rows);stake=10*len(weekends);returns=sum(w['ending_balance'] for w in weekends)
    return dict(picks=n,hits=wins,hit_rate=round(100*wins/n,1) if n else None,active_weekends=len(weekends),
        average_picks_per_active_weekend=round(n/len(weekends),2) if weekends else None,median_picks_per_active_weekend=median([w['picks'] for w in weekends]) if weekends else None,
        pick_count_distribution=dict(sorted(Counter(w['picks'] for w in weekends).items())),perfect_weekends=sum(w['all_hit'] for w in weekends),
        perfect_weekend_rate=round(100*sum(w['all_hit'] for w in weekends)/len(weekends),1) if weekends else None,
        rollover_total_staked=round(stake,2),rollover_total_return=round(returns,2),rollover_profit=round(returns-stake,2),
        weekends_with_same_kickoff_picks=sum(w['same_kickoff'] for w in weekends),weekends=weekends)

def main():
    all_rows=[];source_summaries={};match_weekends_total=0
    for dataset,slug in SOURCES:
        folder=ROOT/'outputs'/slug;rows=json.loads((folder/'qualifying_picks.json').read_text())
        matches=json.loads((folder/'normalized_matches.json').read_text());match_weeks={key(r['fixture']['date']) for r in matches if datetime.fromisoformat(r['fixture']['date']).weekday()>=5}
        match_weekends_total+=len(match_weeks)
        weekend=[]
        for r in rows:
            if datetime.fromisoformat(r['date']).weekday()>=5:
                q=dict(r);q['dataset']=dataset;weekend.append(q);all_rows.append(q)
        ma=metric(weekend,1.5);mb=metric([r for r in weekend if r['B']],2.0)
        source_summaries[dataset]=dict(match_weekends=len(match_weeks),A={k:v for k,v in ma.items() if k!='weekends'},B={k:v for k,v in mb.items() if k!='weekends'})
    A=metric(all_rows,1.5);B=metric([r for r in all_rows if r['B']],2.0)
    result=dict(scope='Saturday/Sunday only, five frozen non-overlapping validation datasets',datasets=[x[0] for x in SOURCES],
        match_weekends=match_weekends_total,A=A,B=B,by_dataset=source_summaries,
        assumptions=['A weekend is ISO Saturday/Sunday using the saved StatsBomb kickoff offset. Friday/Monday and midweek fixtures are excluded.',
        'Only weekends with at least one qualifying pick require a bet. Match-weekend count is the number of dataset-weeks containing any Saturday/Sunday match.',
        'Each active weekend starts a fresh $10 all-in rollover. Every qualifying selection that weekend is ordered by kickoff, fixture ID and player ID; all must win.',
        'Same-kickoff selections can make the rollover impossible to execute literally. Results are hypothetical at fixed odds A=1.50 and B=2.00.',
        'The five datasets are non-overlapping, but share providers/eras and include women’s leagues; this is not a prospective MLS forecast or market-price test.'])
    (OUT/'weekend_operation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    def row(label,m):return f"| {label} | {m['active_weekends']} | {m['picks']} | {m['average_picks_per_active_weekend']} | {m['hits']}/{m['picks']} ({m['hit_rate']}%) | {m['perfect_weekends']}/{m['active_weekends']} ({m['perfect_weekend_rate']}%) | ${m['rollover_profit']:.2f} |"
    lines=['# Hypothetical every-weekend operation','',f"Five frozen evaluation datasets; Saturday/Sunday only. Across them, {match_weekends_total} calendar weeks contained at least one weekend fixture.",'',
        '| Plan | Active weekends | Picks | Picks / active weekend | Individual hits | Weekends with every pick winning | $10 all-in rollover profit |','|---|---:|---:|---:|---:|---:|---:|',row('A at 1.50',A),row('B at 2.00',B),'',
        'An active weekend means the rule produced at least one selection. A perfect weekend means every selection hit; otherwise the full $10 weekend rollover finished at $0.','',
        '## Dataset detail','', '| Dataset | Match weekends | A active | A hits | B active | B hits |','|---|---:|---:|---:|---:|---:|']
    for name,x in source_summaries.items():lines.append(f"| {name} | {x['match_weekends']} | {x['A']['active_weekends']} | {x['A']['hits']}/{x['A']['picks']} | {x['B']['active_weekends']} | {x['B']['hits']}/{x['B']['picks']} |")
    lines += ['','## Assumptions and limits','']+['- '+x for x in result['assumptions']]
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    detail=''.join(f'<tr><td>{escape(name)}</td><td>{x["match_weekends"]}</td><td>{x["A"]["active_weekends"]}</td><td>{x["A"]["hits"]}/{x["A"]["picks"]}</td><td>{x["B"]["active_weekends"]}</td><td>{x["B"]["hits"]}/{x["B"]["picks"]}</td></tr>' for name,x in source_summaries.items())
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Every-weekend simulation</title><style>body{{font:16px/1.6 system-ui;max-width:1100px;margin:30px auto;padding:0 20px;background:#f2f5f8;color:#182b3e}}table{{border-collapse:collapse;background:#fff;width:100%}}td,th{{padding:12px;border-bottom:1px solid #ddd;text-align:left}}a{{color:#216e83}}</style><h1>What if the model ran every weekend?</h1><p>Saturday/Sunday only across five frozen validation datasets. {match_weekends_total} historical match-weekends were available.</p><table><tr><th>Plan</th><th>Active weekends</th><th>Total picks</th><th>Average picks</th><th>Hit rate</th><th>Perfect weekends</th></tr><tr><td>A</td><td>{A['active_weekends']}</td><td>{A['picks']}</td><td>{A['average_picks_per_active_weekend']}</td><td>{A['hit_rate']}%</td><td>{A['perfect_weekends']}/{A['active_weekends']} ({A['perfect_weekend_rate']}%)</td></tr><tr><td>B</td><td>{B['active_weekends']}</td><td>{B['picks']}</td><td>{B['average_picks_per_active_weekend']}</td><td>{B['hit_rate']}%</td><td>{B['perfect_weekends']}/{B['active_weekends']} ({B['perfect_weekend_rate']}%)</td></tr></table><h2>By dataset</h2><table><tr><th>Dataset</th><th>Match weekends</th><th>A active</th><th>A hits</th><th>B active</th><th>B hits</th></tr>{detail}</table><p><a href="report.md">Method and limits</a> · <a href="weekend_operation.json">Every weekend and selection</a></p>''';(OUT/'index.html').write_text(html,encoding='utf-8')
    page=ROOT/'outputs/project_site/dist/index.html';text=page.read_text(encoding='utf-8');start,end='<!-- WEEKEND_OPERATION_START -->','<!-- WEEKEND_OPERATION_END -->'
    if start in text:before,tail=text.split(start,1);text=before+tail.split(end,1)[1]
    panel=f'''{start}<section id="weekend-operation" class="panel" style="margin:24px 0"><div class="eyebrow">WEEKEND OPERATION SIMULATION</div><h2>Saturday/Sunday replay across five frozen datasets</h2><p>A: {A['picks']} picks over {A['active_weekends']} active weekends, {A['hit_rate']}% individual hits, {A['perfect_weekend_rate']}% perfect weekends. B: {B['picks']} picks over {B['active_weekends']} active weekends, {B['hit_rate']}% hits, {B['perfect_weekend_rate']}% perfect weekends.</p><p><a href="../../weekend_operation_simulation/index.html">Open weekend frequency and performance</a></p></section>{end}'''
    nb_start,nb_end='<!-- RECENT_BIG5_NOBET_START -->','<!-- RECENT_BIG5_NOBET_END -->'
    if nb_start in text:before,tail=text.split(nb_start,1);text=before+tail.split(nb_end,1)[1]
    no_bet=f'''{nb_start}<section id="recent-big5-no-bet" class="panel" style="margin:24px 0"><div class="eyebrow">NEW · RECENT BIG-FIVE TEST</div><h2>Four pre-break weekends — zero eligible picks</h2><p>The exact formula requires eight earlier same-season results per team. The five leagues had reached only Matchdays 4–7, so A and B correctly returned no bet and no hit rate.</p><p><a href="../../recent_big5_prebreak_backtest/index.html">Open dates, rule gate and sources</a></p></section>{nb_end}'''
    page.write_text(text.replace('</header>','</header>'+no_bet+panel,1),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('A','B')}|{'A':{k:v for k,v in A.items() if k!='weekends'},'B':{k:v for k,v in B.items() if k!='weekends'}},indent=2))
if __name__=='__main__':main()
