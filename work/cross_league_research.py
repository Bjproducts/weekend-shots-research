"""Non-destructive cleaning and descriptive robustness research; no tuning."""
import json
from collections import Counter
from html import escape
from pathlib import Path
from statistics import mean
from zipfile import ZipFile,ZIP_DEFLATED
from test_home_pattern import measure

OUT=Path(__file__).resolve().parents[1]/'outputs'
SLUGS=['epl_2015_16_validation','laliga_2015_16_validation','seriea_2015_16_validation']

def main():
    leagues=[];cleaned=[];seen=set();quarantine=[]
    for slug in SLUGS:
        folder=OUT/slug
        manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        samples=json.loads((folder/'all_samples.json').read_text(encoding='utf-8'))
        raw=json.loads((folder/'normalized_matches.json').read_text(encoding='utf-8'))
        fixture_map={r['fixture']['id']:r for r in raw}
        quality=Counter()
        clean=[]
        for row in samples:
            key=('statsbomb',row['fixture_id'],row['player_id'])
            reasons=[]
            if key in seen:reasons.append('duplicate_provider_fixture_player')
            seen.add(key)
            for field in ['shots','team_shots','minutes']:
                if row[field] is None:quality['unknown_'+field]+=1
                elif row[field]<0:reasons.append('negative_'+field)
            if row['minutes'] is not None and row['minutes']>90:reasons.append('minutes_exceed_regulation')
            if row['shots'] is not None and row['team_shots'] is not None and row['shots']>row['team_shots']:reasons.append('player_shots_exceed_team')
            if row['fixture_id'] not in fixture_map:reasons.append('orphan_fixture')
            if reasons:
                quarantine.append(dict(source=slug,sample=row,reasons=reasons));quality['quarantined']+=1
            else:
                clean.append(dict(row,provider='statsbomb',league_season=manifest['source_season']));quality['accepted']+=1
        # Every fixture should have two complete starting teams and coherent totals.
        for rec in raw:
            for team in [rec['fixture']['home_team']['id'],rec['fixture']['away_team']['id']]:
                ps=[p for p in rec['players'] if p['team_id']==team]
                assert sum(p['started'] for p in ps)==11
                assert len({p['team_shots'] for p in ps})==1
                assert sum(p['shots'] for p in ps)==ps[0]['team_shots']
                assert all(0<=p['shots_on_target']<=p['shots'] for p in ps)
        full=[r for r in clean if r['full_pattern']]
        benchmark=[r for r in clean if r['benchmark']]
        counts=Counter(r['player_id'] for r in full)
        top3=[pid for pid,n in counts.most_common(3)]
        leaders=[dict(player=next(r['player'] for r in full if r['player_id']==pid),picks=n,
            hits=sum(r['hit'] for r in full if r['player_id']==pid)) for pid,n in counts.most_common(10)]
        league=dict(league=manifest['source_season'],slug=slug,quality=dict(quality),
            full=measure(full),benchmark=measure(benchmark),
            benchmark_only=measure([r for r in benchmark if not r['full_pattern']]),
            top_three_player_share_pct=round(100*sum(counts[p] for p in top3)/len(full),1) if full else None,
            without_three_most_selected_players=measure([r for r in full if r['player_id'] not in top3]),
            unique_players=len(counts),leading_players=leaders,
            months={month:measure([r for r in full if r['date'][:7]==month]) for month in sorted({r['date'][:7] for r in full})},
            autumn=measure([r for r in full if r['date']<'2016']),spring=measure([r for r in full if r['date']>='2016']))
        leagues.append(league);cleaned.extend(clean)
    result=dict(purpose='Frozen-rule validation plus exploratory robustness research, not threshold optimization',
        datasets=leagues,total_clean_samples=len(cleaned),quarantined_samples=len(quarantine),
        timing='Each selection uses only lagged history; calendar split already specified. Outcome research does not change rules.',
        cleaning='Raw records unchanged. Provider+fixture+player deduplication, numeric bounds, unknown preservation, team total/SOT and starting-XI checks. Invalid records quarantined, never silently repaired.',
        limits='All three European datasets are 2015/16 StatsBomb, so era/provider effects remain. Leave-top-three-out is exploratory, chosen by selection count, not success. Multiple picks are correlated; no statistical superiority or profitability claim.')
    (OUT/'cross_league_research.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    with ZipFile(OUT/'cross_league_clean_samples.zip','w',ZIP_DEFLATED) as z:
        z.writestr('clean_samples.json',json.dumps(cleaned,ensure_ascii=False))
        z.writestr('quarantined_samples.json',json.dumps(quarantine,ensure_ascii=False))
        z.writestr('research_and_cleaning.json',json.dumps(result,indent=2))
    with ZipFile(OUT/'cross_league_clean_samples.zip') as z:
        assert z.testzip() is None
        assert len(json.loads(z.read('clean_samples.json')))==len(cleaned)
    def fmt(m):return f"{m['hits']}/{m['n']} ({m['rate']}%)" if m['n'] else 'No cases'
    lines=['# Broader test and data cleaning','',
        'Data source: [StatsBomb Open Data](https://github.com/statsbomb/open-data). Original project feed: [SportsAPI Pro](https://sportsapipro.com/). The configured SportsAPI account reported 100 daily requests and 99 remaining after one connection check. No subscription or quota upgrade was made.','',
        'La Liga and Serie A 2015/16 were selected for complete 380-match coverage before their pattern results were computed. The same rule hash was retained from the MLS test. Premier League is the prior external test, not another new sample.','',
        '| Dataset | Full pattern | Consistent home shooters | Full pattern excluding 3 most-selected players |','|---|---:|---:|---:|']
    for r in leagues:lines.append(f"| {r['league']} | {fmt(r['full'])} | {fmt(r['benchmark'])} | {fmt(r['without_three_most_selected_players'])} |")
    lines+=['',f"Cleaning: {len(cleaned)} accepted player appearances; {len(quarantine)} quarantined. Original records preserved. All 1,140 match records passed starter-count and team/player-shot reconciliation checks.",'',
        '## Research: concentration and time stability','','| League | Distinct selected players | Top-three share of picks | Before Jan 2016 | Jan onward |','|---|---:|---:|---:|---:|']
    for r in leagues:lines.append(f"| {r['league']} | {r['unique_players']} | {r['top_three_player_share_pct']}% | {fmt(r['autumn'])} | {fmt(r['spring'])} |")
    lines+=['','## Interpretation and limits','',result['limits'],
        'The full pattern is a subset of the benchmark. Its higher/lower observed rate is not proof the filter causes improvement. Inspect per-league counts and concentration rather than promoting a universal 80% rate.',
        'Missing values are never turned into zero. Event-derived zeros require full downloaded matches. Regulation minutes are rounded up from merged lineup intervals and capped at 90; publication-time availability is not verified. These limitations are preserved in each season manifest.',
        'Next research should add a different era/provider under the same rules; do not tune thresholds on these results. SportsAPI Pro remains usable but needs a staged quota-bounded download to obtain a full contemporary season.','',
        'All cleaned samples and quarantine records: cross_league_clean_samples.zip. Raw evidence, full results and individual picks remain in each season directory/archive.','']
    (OUT/'cross_league_research.md').write_text('\n'.join(lines),encoding='utf-8')
    table=''.join(f'<tr><td>{escape(r["league"])}</td><td>{fmt(r["full"])}</td><td>{fmt(r["benchmark"])}</td><td>{fmt(r["without_three_most_selected_players"])}</td></tr>' for r in leagues)
    links=''.join(f'<li><a href="{r["slug"]}/index.html">{escape(r["league"])} — results and every pick</a> · <a href="{r["slug"]}.zip">all season data</a></li>' for r in leagues)
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Cross-league pattern research</title><style>body{{font:16px/1.6 system-ui;max-width:1150px;margin:30px auto;padding:0 20px;background:#f2f5f8;color:#182b3e}}.scroll{{overflow:auto}}table{{border-collapse:collapse;background:white;width:100%}}th,td{{padding:12px;text-align:left;border-bottom:1px solid #ddd}}a{{color:#216e83}}</style>
    <h1>Broader test: three European leagues</h1><p>Fixed rules, no tuning. Data: <a href="https://github.com/statsbomb/open-data">StatsBomb Open Data</a>. La Liga and Serie A are new tests; Premier League was previously tested.</p><div class="scroll"><table><tr><th>Season</th><th>Full pattern</th><th>Consistent home shooters</th><th>Without 3 most-selected players</th></tr>{table}</table></div>
    <h2>Cleaning and limitations</h2><p>{len(cleaned):,} appearances accepted; {len(quarantine)} quarantined. Duplicate identity, numeric bounds, known/unknown values, 22 starters and shot-total consistency checked. Raw data unchanged.</p><p>{escape(result['limits'])}</p>
    <p><a href="cross_league_research.md">Research report</a> · <a href="cross_league_research.json">Monthly and player-level research</a> · <a href="cross_league_clean_samples.zip">Every cleaned sample and quarantine record</a></p><ul>{links}</ul></html>'''
    (OUT/'cross_league_research.html').write_text(html,encoding='utf-8')
    page=OUT/'project_site/dist/index.html';text=page.read_text(encoding='utf-8')
    start,end='<!-- CROSS_LEAGUE_START -->','<!-- CROSS_LEAGUE_END -->'
    if start in text:
        before,tail=text.split(start,1);text=before+tail.split(end,1)[1]
    panel=f'''{start}<section id="cross-league" class="panel" style="margin:24px 0"><div class="eyebrow">BROADER TEST + CLEANING COMPLETE</div><h2>Three European leagues, unchanged pattern</h2><div class="tablewrap"><table><tr><th>Season</th><th>Full pattern</th><th>Benchmark</th><th>Without top 3 by volume</th></tr>{table}</table></div><p>{len(cleaned):,} player appearances checked and saved; {len(quarantine)} quarantined. All from 2015/16 StatsBomb data: different era/provider evidence is still needed.</p><p><a href="../../cross_league_research.html">Open research and all sample downloads</a></p></section>{end}'''
    page.write_text(text.replace('</header>','</header>'+panel,1),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
