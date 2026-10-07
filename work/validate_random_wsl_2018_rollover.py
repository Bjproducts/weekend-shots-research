"""Randomly selected WSL 2018/19 frozen replay and continuous rollover."""
import hashlib,json,sqlite3
from datetime import datetime,timedelta
from html import escape
from pathlib import Path
from zipfile import ZIP_DEFLATED,ZipFile
from test_home_pattern import run
from weekly_pattern_replay import RULES,choose
from validate_wsl_ab import RULES_HASH,compare,fmt
from validate_wsl_2020_rollover import continuous_rollover,flat,repair_mojibake

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/random_wsl_2018_19_rollover_validation';PLAN=ROOT/'work/random_wsl_2018_19_plan.json'

def main():
    plan=json.loads(PLAN.read_text());assert plan['rules_sha256']==RULES_HASH
    recs=json.loads((OUT/'normalized_matches.json').read_text());ids=[r['fixture']['id'] for r in recs]
    teams={t['id']:t['name'] for r in recs for t in (r['fixture']['home_team'],r['fixture']['away_team'])};keys=[(r['fixture']['id'],p['player']['id']) for r in recs for p in r['players']]
    assert len(recs)==len(set(ids))==107 and len(teams)==11 and len(keys)==len(set(keys))==2872
    pairs={(r['fixture']['home_team']['id'],r['fixture']['away_team']['id']) for r in recs};missing=[{'home':teams[h],'away':teams[a]} for h in teams for a in teams if h!=a and (h,a) not in pairs];assert len(missing)==3
    prior=set()
    old=json.loads((ROOT/'outputs/winning_pattern_research.json').read_text());prior.update(r['fixture_id'] for r in old['rows'] if r['provider']=='statsbomb')
    for path in ['wsl_2023_24_ab_validation','frauen_bundesliga_2023_24_ab_validation','wsl_2020_21_rollover_validation']:
        prior.update(r['fixture']['id'] for r in json.loads((ROOT/'outputs'/path/'normalized_matches.json').read_text()))
    assert not prior.intersection(ids)
    db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
    db.executescript("""CREATE TABLE competitions(id INTEGER,name TEXT,is_competitive INTEGER);CREATE TABLE teams(id INTEGER PRIMARY KEY,name TEXT);CREATE TABLE players(id INTEGER PRIMARY KEY,common_name TEXT,full_name TEXT);CREATE TABLE fixtures(id INTEGER,fixture_date TEXT,competition_id INTEGER,season_id INTEGER,home_team_id INTEGER,away_team_id INTEGER,home_score INTEGER,away_score INTEGER,status TEXT);CREATE TABLE player_fixture_stats(fixture_id INTEGER,player_id INTEGER,team_id INTEGER,opponent_id INTEGER,home INTEGER,started INTEGER,minutes_played REAL,shots INTEGER,team_shots INTEGER,data_source TEXT);INSERT INTO competitions VALUES(37,'FA Women''s Super League',1);""")
    for rec in recs:
        f=rec['fixture']
        for t in (f['home_team'],f['away_team']):db.execute('INSERT OR IGNORE INTO teams VALUES(?,?)',(t['id'],t['name']))
        db.execute('INSERT INTO fixtures VALUES(?,?,?,?,?,?,?,?,?)',(f['id'],f['date'],37,4,f['home_team']['id'],f['away_team']['id'],f['home_score'],f['away_score'],'finished'))
        for p in rec['players']:
            q=p['player'];db.execute('INSERT OR IGNORE INTO players VALUES(?,?,?)',(q['id'],q['common_name'],q['full_name']))
            db.execute('INSERT INTO player_fixture_stats VALUES(?,?,?,?,?,?,?,?,?,?)',(f['id'],q['id'],p['team_id'],p['opponent_id'],p['home'],p['started'],p['minutes_played'],p['shots'],p['team_shots'],'statsbomb'))
    replay=run(connection=db,provider='statsbomb',save=False);replay['source']='StatsBomb WSL 2018/19: 107/110 expected fixtures'
    fmap={(r['fixture_id'],r['player_id']):r for r in replay['rows']};eligible={r['fixture_id'] for r in replay['environments']};samples=[];picks=[]
    for rec in recs:
        f=rec['fixture']
        for p in rec['players']:
            ft=fmap.get((f['id'],p['player']['id']));a=b=False;reasons=[]
            if not p['home']:reasons.append('away_player')
            if not p['started']:reasons.append('not_starter')
            if f['id'] not in eligible:reasons.append('insufficient_team_history')
            elif p['home'] and p['started'] and ft is None:reasons.append('insufficient_player_history')
            if ft:
                a=choose({k:ft[k] for k in ('shooter_rank','recent_minutes','recent_hits','environment')})['full_pattern'];b=a and ft['recent_shots']>=3 and ft['recent_minutes']>=80
                if not a:reasons.append('baseline_conditions_not_met')
                elif not b:reasons.append('challenger_extra_conditions_not_met')
            row=dict(fixture_id=f['id'],player_id=p['player']['id'],date=f['date'],round=f['round'],fixture=f['home_team']['name']+' vs '+f['away_team']['name'],player=p['player']['common_name'] or p['player']['full_name'],home=p['home'],started=p['started'],shots=p['shots'],hit=p['shots']>=2 if p['shots'] is not None else None,A=a,B=b,features=ft,exclusion_reasons=reasons)
            samples.append(row)
            if a:picks.append(row)
    summary=compare(picks);a=picks;b=[r for r in picks if r['B']];policy=plan['betting_policy'];stake=policy['starting_stake']
    betting={'policy':policy,'A':{'flat':flat(a,policy['decimal_odds_A'],stake),'continuous_rollover':continuous_rollover(a,policy['decimal_odds_A'],stake)},'B':{'flat':flat(b,policy['decimal_odds_B'],stake),'continuous_rollover':continuous_rollover(b,policy['decimal_odds_B'],stake)}}
    result=dict(dataset="FA Women's Super League 2018/19",selection='random draw after coverage-only rejection of NWSL 2018',provider='StatsBomb Open Data',matches=107,expected_matches=110,teams=11,missing_fixture_pairs=missing,player_samples=len(samples),eligible_fixtures=len(eligible),rules=RULES,plan=plan,plan_sha256=hashlib.sha256(PLAN.read_bytes()).hexdigest(),baseline_rules_sha256=RULES_HASH,comparison=summary,betting=betting,limits=['Three expected fixture pairings are absent; no data invented.','Random selection was made before player events and outcomes; NWSL 2018 was rejected only for inadequate coverage.','Fixed odds are hypothetical. All-in peak balances are not realized profit unless cashed out.','Same-kickoff selections may not be executable sequentially. Historical starter availability and market prices are not certified.'])
    for name,obj in [('results',result),('betting_simulation',betting),('all_samples',samples),('qualifying_picks',picks),('feature_replay',replay),('frozen_test_plan',plan)]: (OUT/(name+'.json')).write_text(json.dumps(obj,indent=2),encoding='utf-8')
    ca,cb=betting['A']['continuous_rollover'],betting['B']['continuous_rollover']
    lines=['# Random dataset backtest — WSL 2018/19','',f"Random audit: NWSL 2018 was drawn first and rejected for coverage (36 scattered fixtures). WSL 2018/19 was drawn second and accepted at 107/110 fixtures before player events.",'',f"A: {fmt(summary['A'])}. B: {fmt(summary['B'])}.",'','## Continuous $10 all-in rollover','',
        '| Plan | Outcome sequence | Longest winning streak | Maximum balance | Later lost? | Final active balance after restarts | Net after restart deposits |','|---|---|---:|---:|---|---:|---:|',
        f"| A at 1.50 | `{ca['outcome_sequence']}` | {ca['max_consecutive_wins']} | ${ca['maximum_balance_reached']:.2f} | {'Yes' if ca['maximum_balance_later_lost'] else 'No'} | ${ca['final_bankroll']:.2f} | ${ca['net_after_restart_deposits']:.2f} |",
        f"| B at 2.00 | `{cb['outcome_sequence']}` | {cb['max_consecutive_wins']} | ${cb['maximum_balance_reached']:.2f} | {'Yes' if cb['maximum_balance_later_lost'] else 'No'} | ${cb['final_bankroll']:.2f} | ${cb['net_after_restart_deposits']:.2f} |",'',
        'Formula: `$10 × odds^consecutive wins`. A loss after a streak makes the all-in balance $0. A new $10 is deposited only to measure the next streak.','',
        '## Missing fixture pairings','']+['- '+x['home']+' vs '+x['away'] for x in missing]+['','## Limits','']+['- '+x for x in result['limits']]
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    rows=''.join(f'<tr><td>{r["date"][:10]}</td><td>{escape(r["fixture"])}</td><td>{escape(r["player"])}</td><td>{"A + B" if r["B"] else "A only"}</td><td>{r["shots"]}</td><td>{"HIT" if r["hit"] else "MISS"}</td></tr>' for r in picks)
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Random WSL rollover test</title><style>body{{font:16px/1.6 system-ui;max-width:1150px;margin:30px auto;padding:0 20px;background:#f2f5f8;color:#182b3e}}.scroll{{overflow:auto}}table{{border-collapse:collapse;background:white;width:100%}}td,th{{padding:12px;border-bottom:1px solid #ddd;text-align:left}}a{{color:#216e83}}</style><h1>Random backtest: WSL 2018/19</h1><p>Randomly selected before player outcomes; 107/110 expected fixtures. A: <b>{fmt(summary['A'])}</b>. B: <b>{fmt(summary['B'])}</b>.</p><h2>Continuous $10 rollover</h2><table><tr><th>Plan</th><th>Longest run</th><th>Maximum balance</th><th>Later lost?</th><th>Final active balance</th></tr><tr><td>A at 1.50</td><td>{ca['max_consecutive_wins']}</td><td>${ca['maximum_balance_reached']:.2f}</td><td>{'Yes' if ca['maximum_balance_later_lost'] else 'No'}</td><td>${ca['final_bankroll']:.2f}</td></tr><tr><td>B at 2.00</td><td>{cb['max_consecutive_wins']}</td><td>${cb['maximum_balance_reached']:.2f}</td><td>{'Yes' if cb['maximum_balance_later_lost'] else 'No'}</td><td>${cb['final_bankroll']:.2f}</td></tr></table><p>Formula: $10 × odds<sup>consecutive wins</sup>. A later loss wipes out the entire current balance.</p><p><a href="report.md">Full audit</a> · <a href="betting_simulation.json">Every streak</a> · <a href="qualifying_picks.json">Every pick</a> · <a href="../random_wsl_2018_19_rollover_validation.zip">Archive</a></p><h2>Every A pick</h2><div class="scroll"><table><tr><th>Date</th><th>Fixture</th><th>Player</th><th>Rule</th><th>Shots</th><th>Outcome</th></tr>{rows}</table></div></html>''';(OUT/'index.html').write_text(html,encoding='utf-8')
    with ZipFile(OUT.parent/'random_wsl_2018_19_rollover_validation.zip','w',ZIP_DEFLATED) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(OUT))
    page=OUT.parent/'project_site/dist/index.html';text=repair_mojibake(page.read_text(encoding='utf-8'));start,end='<!-- RANDOM_WSL2018_START -->','<!-- RANDOM_WSL2018_END -->'
    if start in text:before,tail=text.split(start,1);text=before+tail.split(end,1)[1]
    panel=f'''{start}<section id="random-wsl2018" class="panel" style="margin:24px 0"><div class="eyebrow">NEW · RANDOM DATASET BACKTEST</div><h2>WSL 2018/19 — continuous rollover</h2><p>A: {fmt(summary['A'])}; longest run {ca['max_consecutive_wins']}, peak ${ca['maximum_balance_reached']:.2f}. B: {fmt(summary['B'])}; longest run {cb['max_consecutive_wins']}, peak ${cb['maximum_balance_reached']:.2f}.</p><p><a href="../../random_wsl_2018_19_rollover_validation/index.html">View random draw, streaks and every pick</a></p></section>{end}''';page.write_text(text.replace('</header>','</header>'+panel,1),encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
