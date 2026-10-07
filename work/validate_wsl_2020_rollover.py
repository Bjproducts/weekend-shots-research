"""Frozen A/B replay plus user-specified fixed-odds rollover simulation."""
import hashlib, json, sqlite3
from collections import Counter
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from test_home_pattern import measure, run
from weekly_pattern_replay import RULES, choose, monday
from validate_wsl_ab import RULES_HASH, compare, fmt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/wsl_2020_21_rollover_validation'
PLAN_PATH=ROOT/'work/wsl_2020_21_rollover_plan.json'

def money(x): return round(x+0.000000001,2)

def repair_mojibake(text):
    """Repair earlier UTF-8 bytes decoded once as Windows-1252, without touching valid punctuation."""
    out=[];i=0
    while i<len(text):
        size=3 if text[i]=='â' else 2 if text[i]=='Â' else 0
        if size and i+size<=len(text):
            part=text[i:i+size]
            try:
                fixed=part.encode('cp1252').decode('utf-8')
                out.append(fixed);i+=size;continue
            except (UnicodeEncodeError,UnicodeDecodeError):pass
        out.append(text[i]);i+=1
    return ''.join(out)

def flat(rows,odds,stake=10):
    invested=stake*len(rows);returns=sum(stake*odds for r in rows if r['hit']);profit=returns-invested
    return dict(bets=len(rows),wins=sum(r['hit'] for r in rows),losses=sum(not r['hit'] for r in rows),stake_per_bet=stake,
        total_staked=money(invested),total_return=money(returns),profit=money(profit),roi_pct=round(100*profit/invested,1) if invested else None)

def rollovers(rows,odds,length,stake=10):
    ordered=sorted(rows,key=lambda r:(r['date'],r['fixture_id'],r['player_id']))
    count=len(ordered)//length;blocks=[]
    for number in range(count):
        legs=ordered[number*length:(number+1)*length];won=all(r['hit'] for r in legs)
        returned=stake*(odds**length) if won else 0
        same_time=len({r['date'] for r in legs})<len(legs)
        blocks.append(dict(block=number+1,won=won,stake=stake,return_amount=money(returned),profit=money(returned-stake),
            contains_same_kickoff=same_time,legs=[{k:r[k] for k in ('date','fixture_id','fixture','player','shots','hit')} for r in legs]))
    invested=stake*count;returns=sum(b['return_amount'] for b in blocks);profit=returns-invested
    return dict(length=length,odds_per_leg=odds,blocks=count,winning_blocks=sum(b['won'] for b in blocks),
        losing_blocks=sum(not b['won'] for b in blocks),incomplete_selections_ignored=len(ordered)%length,
        blocks_with_same_kickoff=sum(b['contains_same_kickoff'] for b in blocks),total_staked=money(invested),
        total_return=money(returns),profit=money(profit),roi_pct=round(100*profit/invested,1) if invested else None,block_records=blocks)

def continuous_rollover(rows,odds,stake=10):
    """User-defined all-in rollover; restart with a new stake only after a loss."""
    ordered=sorted(rows,key=lambda r:(r['date'],r['fixture_id'],r['player_id']))
    cycles=[];legs=[];wins=0;balance=stake
    for row in ordered:
        leg={k:row[k] for k in ('date','fixture_id','fixture','player','shots','hit')};legs.append(leg)
        if row['hit']:
            wins+=1;balance*=odds
        else:
            cycles.append(dict(cycle=len(cycles)+1,consecutive_wins=wins,peak_before_loss=money(balance),ended_by_loss=True,
                ending_balance=0.0,legs=legs));legs=[];wins=0;balance=stake
    if legs:
        cycles.append(dict(cycle=len(cycles)+1,consecutive_wins=wins,peak_before_loss=None,ended_by_loss=False,
            ending_balance=money(balance),legs=legs))
    max_cycle=max(cycles,key=lambda c:c['consecutive_wins']) if cycles else None
    deposits=stake*len(cycles);final=sum(c['ending_balance'] for c in cycles)
    return dict(formula=f'{stake} * {odds}^n',odds=odds,selections=len(ordered),outcome_sequence=''.join('W' if r['hit'] else 'L' for r in ordered),
        cycles_started=len(cycles),total_deposited=money(deposits),losing_cycles=sum(c['ended_by_loss'] for c in cycles),
        max_consecutive_wins=max_cycle['consecutive_wins'] if max_cycle else 0,
        maximum_balance_reached=money(stake*(odds**max_cycle['consecutive_wins'])) if max_cycle else 0,
        maximum_balance_later_lost=bool(max_cycle and max_cycle['ended_by_loss']),final_open_streak_wins=cycles[-1]['consecutive_wins'] if cycles and not cycles[-1]['ended_by_loss'] else 0,
        final_bankroll=money(final),net_after_restart_deposits=money(final-deposits),cycles=cycles,
        note='No profit is realized unless cash is removed. A loss after a winning streak reduces the all-in balance to $0.')

def main():
    plan=json.loads(PLAN_PATH.read_text());assert plan['rules_sha256']==RULES_HASH
    records=json.loads((OUT/'normalized_matches.json').read_text());fixture_ids=[r['fixture']['id'] for r in records]
    teams={t['id']:t['name'] for r in records for t in (r['fixture']['home_team'],r['fixture']['away_team'])}
    keys=[(r['fixture']['id'],p['player']['id']) for r in records for p in r['players']]
    assert len(records)==len(set(fixture_ids))==131 and len(teams)==12 and len(keys)==len(set(keys))==3727
    pairs={(r['fixture']['home_team']['id'],r['fixture']['away_team']['id']) for r in records}
    missing=[{'home':teams[h],'away':teams[a]} for h in teams for a in teams if h!=a and (h,a) not in pairs]
    assert len(missing)==1
    prior_ids=set()
    for path in [ROOT/'outputs/winning_pattern_research.json']:
        obj=json.loads(path.read_text());prior_ids.update(r['fixture_id'] for r in obj['rows'] if r['provider']=='statsbomb')
    for path in [ROOT/'outputs/wsl_2023_24_ab_validation/normalized_matches.json',ROOT/'outputs/frauen_bundesliga_2023_24_ab_validation/normalized_matches.json']:
        prior_ids.update(r['fixture']['id'] for r in json.loads(path.read_text()))
    assert not prior_ids.intersection(fixture_ids)

    db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
    db.executescript("""CREATE TABLE competitions(id INTEGER,name TEXT,is_competitive INTEGER);
    CREATE TABLE teams(id INTEGER PRIMARY KEY,name TEXT);CREATE TABLE players(id INTEGER PRIMARY KEY,common_name TEXT,full_name TEXT);
    CREATE TABLE fixtures(id INTEGER,fixture_date TEXT,competition_id INTEGER,season_id INTEGER,home_team_id INTEGER,away_team_id INTEGER,home_score INTEGER,away_score INTEGER,status TEXT);
    CREATE TABLE player_fixture_stats(fixture_id INTEGER,player_id INTEGER,team_id INTEGER,opponent_id INTEGER,home INTEGER,started INTEGER,minutes_played REAL,shots INTEGER,team_shots INTEGER,data_source TEXT);
    INSERT INTO competitions VALUES(37,'FA Women''s Super League',1);""")
    for rec in records:
        f=rec['fixture']
        for t in (f['home_team'],f['away_team']):db.execute('INSERT OR IGNORE INTO teams VALUES(?,?)',(t['id'],t['name']))
        db.execute('INSERT INTO fixtures VALUES(?,?,?,?,?,?,?,?,?)',(f['id'],f['date'],37,90,f['home_team']['id'],f['away_team']['id'],f['home_score'],f['away_score'],'finished'))
        for p in rec['players']:
            q=p['player'];db.execute('INSERT OR IGNORE INTO players VALUES(?,?,?)',(q['id'],q['common_name'],q['full_name']))
            db.execute('INSERT INTO player_fixture_stats VALUES(?,?,?,?,?,?,?,?,?,?)',(f['id'],q['id'],p['team_id'],p['opponent_id'],p['home'],p['started'],p['minutes_played'],p['shots'],p['team_shots'],'statsbomb'))
    replay=run(connection=db,provider='statsbomb',save=False);replay['source']='StatsBomb WSL 2020/21: 131/132 expected matches'
    fmap={(r['fixture_id'],r['player_id']):r for r in replay['rows']};eligible={r['fixture_id'] for r in replay['environments']}
    samples=[];picks=[]
    for rec in records:
        f=rec['fixture']
        for p in rec['players']:
            ft=fmap.get((f['id'],p['player']['id']));a=b=False;reasons=[]
            if not p['home']:reasons.append('away_player')
            if not p['started']:reasons.append('not_starter')
            if f['id'] not in eligible:reasons.append('insufficient_team_history')
            elif p['home'] and p['started'] and ft is None:reasons.append('insufficient_player_history')
            if ft:
                a=choose({k:ft[k] for k in ('shooter_rank','recent_minutes','recent_hits','environment')})['full_pattern']
                b=a and ft['recent_shots']>=3 and ft['recent_minutes']>=80
                if not a:reasons.append('baseline_conditions_not_met')
                elif not b:reasons.append('challenger_extra_conditions_not_met')
            row=dict(fixture_id=f['id'],player_id=p['player']['id'],date=f['date'],round=f['round'],fixture=f['home_team']['name']+' vs '+f['away_team']['name'],
                player=p['player']['common_name'] or p['player']['full_name'],home=p['home'],started=p['started'],shots=p['shots'],hit=p['shots']>=2 if p['shots'] is not None else None,A=a,B=b,features=ft,exclusion_reasons=reasons)
            samples.append(row)
            if a:picks.append(row)
    summary=compare(picks);a_rows=picks;b_rows=[r for r in picks if r['B']]
    policy=plan['betting_policy'];stake=policy['starting_stake_per_bet_or_block']
    betting={'policy':policy,'method_correction':json.loads((ROOT/'work/wsl_2020_21_rollover_method_correction.json').read_text()),
        'A':{'flat':flat(a_rows,policy['decimal_odds_A'],stake),'continuous_rollover':continuous_rollover(a_rows,policy['decimal_odds_A'],stake),'fixed_blocks_alternative':{}},
        'B':{'flat':flat(b_rows,policy['decimal_odds_B'],stake),'continuous_rollover':continuous_rollover(b_rows,policy['decimal_odds_B'],stake),'fixed_blocks_alternative':{}}}
    for length in policy['rollover_lengths']:
        betting['A']['fixed_blocks_alternative'][str(length)]=rollovers(a_rows,policy['decimal_odds_A'],length,stake)
        betting['B']['fixed_blocks_alternative'][str(length)]=rollovers(b_rows,policy['decimal_odds_B'],length,stake)
    result=dict(dataset="FA Women's Super League 2020/21",provider='StatsBomb Open Data',matches=131,expected_matches=132,teams=12,
        missing_fixture_pair=missing[0],player_samples=len(samples),eligible_fixtures=len(eligible),rules=RULES,plan=plan,
        plan_sha256=hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest(),baseline_rules_sha256=RULES_HASH,comparison=summary,betting=betting,
        limits=['One expected fixture is absent; no missing date or result was invented.','Fixed odds are hypothetical user inputs, not historical market prices.',
        'Rollover blocks use deterministic selection order and can contain simultaneous selections; they are mathematical simulations, not necessarily executable live sequences.',
        'No commission, limits, voids, stake caps or bookmaker settlement differences. Historical replay assumes actual starters are known.',
        "Women's football and repeated StatsBomb data do not directly validate men's MLS. No retuning after outcomes."])
    for name,obj in [('ab_results',result),('betting_simulation',betting),('all_samples',samples),('qualifying_picks',picks),('feature_replay',replay),('frozen_test_plan',plan)]:
        (OUT/(name+'.json')).write_text(json.dumps(obj,indent=2),encoding='utf-8')
    def betrow(label,obj):return f"| {label} | ${obj['total_staked']:.2f} | ${obj['total_return']:.2f} | ${obj['profit']:.2f} | {obj['roi_pct']}% |"
    ca,cb=betting['A']['continuous_rollover'],betting['B']['continuous_rollover']
    lines=['# Frozen WSL 2020/21 backtest + $10 rollover simulation','',f"Coverage: 131/132 expected matches. Missing pairing: {missing[0]['home']} vs {missing[0]['away']}. No data invented.",'',
        f"A: {fmt(summary['A'])} at hypothetical decimal odds 1.50. B: {fmt(summary['B'])} at hypothetical decimal odds 2.00.",'','## Betting results','',
        '| Strategy | Staked | Returned | Profit | ROI |','|---|---:|---:|---:|---:|',betrow('A flat $10',betting['A']['flat']),betrow('B flat $10',betting['B']['flat']),'',
        '## Continuous rollover — corrected user definition','',
        '| Plan | Outcome sequence | Winning streaks | Maximum balance | What happened next | Final active balance after restarts |','|---|---|---|---:|---|---:|',
        f"| A at 1.50 | `{ca['outcome_sequence']}` | 6, 8, 2, 0, 4, then 3 | ${ca['maximum_balance_reached']:.2f} after 8 wins | Next pick lost it | ${ca['final_bankroll']:.2f} after final 3 wins |",
        f"| B at 2.00 | `{cb['outcome_sequence']}` | 13, then 1 | ${cb['maximum_balance_reached']:.2f} after 13 wins | Next pick lost it | ${cb['final_bankroll']:.2f} after restarting and winning once |",'',
        '**This is the actual rollover formula requested:** `$10 × odds^number of consecutive wins`. If the next bet loses and the whole balance was staked, that streak ends at $0. The maximum balance is not realized profit unless it is cashed out before the loss.','',
        '## Alternative fixed-size block diagnostics (not the user-defined continuous rollover)','']
    for label in ('A','B'):
        for length,obj in betting[label]['fixed_blocks_alternative'].items():lines.append(betrow(f'{label} {length}-selection block',obj))
    lines += ['','Each rollover uses non-overlapping chronological blocks. A block wins only if every selection hits; the entire return is rolled through the block. Incomplete final blocks are ignored.','',
        '**Important:** some blocks contain selections with the same kickoff and therefore may not have been executable sequentially. These figures are mathematical diagnostics. The supplied fixed odds are not historical prices.','',
        '## Limits','']+['- '+x for x in result['limits']]
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    trs=''.join(f'<tr><td>{escape(label)}</td><td>${obj["total_staked"]:.2f}</td><td>${obj["total_return"]:.2f}</td><td>${obj["profit"]:.2f}</td><td>{obj["roi_pct"]}%</td></tr>' for label,obj in [('A flat $10',betting['A']['flat']),('B flat $10',betting['B']['flat'])])
    picktrs=''.join(f'<tr><td>{r["date"][:10]}</td><td>{escape(r["fixture"])}</td><td>{escape(r["player"])}</td><td>{"A + B" if r["B"] else "A only"}</td><td>{r["shots"]}</td><td>{"HIT" if r["hit"] else "MISS"}</td></tr>' for r in picks)
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>WSL rollover backtest</title><style>body{{font:16px/1.6 system-ui;max-width:1150px;margin:30px auto;padding:0 20px;background:#f2f5f8;color:#182b3e}}.scroll{{overflow:auto}}table{{border-collapse:collapse;background:white;width:100%}}td,th{{padding:12px;border-bottom:1px solid #ddd;text-align:left}}a{{color:#216e83}}</style><h1>WSL 2020/21: frozen backtest + $10 rollovers</h1><p>131/132 expected fixtures; {len(samples):,} appearances. A at 1.50: <b>{fmt(summary['A'])}</b>. B at 2.00: <b>{fmt(summary['B'])}</b>.</p><div class="scroll"><table><tr><th>Strategy</th><th>Staked</th><th>Returned</th><th>Profit</th><th>ROI</th></tr>{trs}</table></div><h2>Continuous all-in rollover</h2><p><b>Formula:</b> $10 × odds<sup>consecutive wins</sup>. A reached <b>${ca['maximum_balance_reached']:.2f}</b> after 8 wins, then the next loss reduced it to $0. B reached <b>${cb['maximum_balance_reached']:.2f}</b> after 13 wins, then the next loss reduced it to $0.</p><p>After depositing a new $10 following each loss, the season ended with an active A balance of ${ca['final_bankroll']:.2f} and B balance of ${cb['final_bankroll']:.2f}. Maximum displayed balances were never cashed out in this all-in simulation.</p><p><a href="report.md">Method and limits</a> · <a href="betting_simulation.json">Every streak and leg</a> · <a href="qualifying_picks.json">Every pick</a> · <a href="../wsl_2020_21_rollover_validation.zip">Archive</a></p><h2>Every A pick</h2><div class="scroll"><table><tr><th>Date</th><th>Fixture</th><th>Player</th><th>Rule</th><th>Shots</th><th>Outcome</th></tr>{picktrs}</table></div></html>'''
    (OUT/'index.html').write_text(html,encoding='utf-8')
    with ZipFile(OUT.parent/'wsl_2020_21_rollover_validation.zip','w',ZIP_DEFLATED) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(OUT))
    page=OUT.parent/'project_site/dist/index.html';text=repair_mojibake(page.read_text(encoding='utf-8'));start,end='<!-- WSL2020_ROLLOVER_START -->','<!-- WSL2020_ROLLOVER_END -->'
    if start in text:before,tail=text.split(start,1);text=before+tail.split(end,1)[1]
    panel=f'''{start}<section id="wsl2020-rollover" class="panel" style="margin:24px 0"><div class="eyebrow">NEW · FROZEN BACKTEST + CORRECTED ROLLOVER</div><h2>WSL 2020/21 — continuous $10 all-in rollover</h2><p>A at 1.50 reached ${ca['maximum_balance_reached']:.2f} after 8 straight wins, then lost it. B at 2.00 reached ${cb['maximum_balance_reached']:.2f} after 13 straight wins, then lost it. Maximum balances are not realized profit without a cash-out.</p><p><a href="../../wsl_2020_21_rollover_validation/index.html">View every streak and selection</a></p></section>{end}'''
    page.write_text(text.replace('</header>','</header>'+panel,1),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
