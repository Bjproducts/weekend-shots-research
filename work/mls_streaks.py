"""Describe fixed-rule saved MLS weekend replay; no fitting or new selection."""
import json
from collections import Counter
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/mls_2026_weekends'

def runs(rows):
    result = []
    for row in rows:
        if row['hit'] is None:
            result.append(dict(hit=None, length=1, entries=[row]))
        elif result and result[-1]['hit'] == row['hit']:
            result[-1]['length'] += 1
            result[-1]['entries'].append(row)
        else:
            result.append(dict(hit=row['hit'], length=1, entries=[row]))
    return result

def describe(rows):
    rr = runs(rows)
    return dict(n=len(rows), hits=sum(r['hit'] is True for r in rows),
        longest_hit_run=max((r['length'] for r in rr if r['hit'] is True),default=0),
        longest_miss_run=max((r['length'] for r in rr if r['hit'] is False),default=0),
        hit_run_lengths=dict(sorted(Counter(r['length'] for r in rr if r['hit'] is True).items())),
        miss_run_lengths=dict(sorted(Counter(r['length'] for r in rr if r['hit'] is False).items())),
        ending_run=({k:rr[-1][k] for k in ['hit','length']} if rr else None), runs=rr)

def main():
    data=json.loads((OUT/'replay.json').read_text(encoding='utf-8'))
    result={'scope':'Previously studied MLS 2026 Saturday/Sunday selections only; not fresh validation.',
        'rules_sha256':data['rules_sha256'], 'latest_saved_match_with_stats':data['latest_saved_match_with_stats'],
        'order':'Kickoff UTC, fixture ID, pre-match shooter rank, player ID. Same-kickoff order is arbitrary; pick streaks are descriptive, not a sequence of available reinvestments.',
        'coverage':'No-pick weekends skipped; missing coverage is not a loss or a verified no-pick weekend. Streaks describe observed selections only, not complete-season streaks.',
        'rules':{}, 'no_new_backtest_results':True}
    for rule in ['A','B']:
        pp=sorted([p for p in data['picks'] if p[rule]],key=lambda r:(r['date'],r['fixture_id'],r['shooter_rank'],r['player_id']))
        assert all(p['hit'] is not None for p in pp)
        picks=[dict(hit=bool(p['hit']),date=p['date'],weekend=p['weekend'],fixture_id=p['fixture_id'],fixture=p['fixture'],player=p['player'],player_id=p['player_id'],shots=p['shots']) for p in pp]
        batches=[]
        for stamp in sorted({p['date'] for p in pp}):
            batch=[p for p in pp if p['date']==stamp]
            batches.append(dict(date=stamp,hit=all(p['hit'] for p in batch),hits=sum(p['hit'] for p in batch),n=len(batch),fixtures=sorted({p['fixture'] for p in batch})))
        fixtures=[]
        for fid in dict.fromkeys(p['fixture_id'] for p in pp):
            ff=[p for p in pp if p['fixture_id']==fid]
            fixtures.append(dict(date=ff[0]['date'],fixture=ff[0]['fixture'],hit=all(p['hit'] for p in ff),hits=sum(p['hit'] for p in ff),n=len(ff)))
        weekends=[]
        for week in sorted({p['weekend'] for p in pp}):
            ww=[p for p in pp if p['weekend']==week]
            weekends.append(dict(date=week,hit=all(p['hit'] for p in ww),hits=sum(p['hit'] for p in ww),n=len(ww)))
        result['rules'][rule]=dict(picks=describe(picks),fixtures=describe(fixtures),kickoff_batches=describe(batches),active_weekends=describe(weekends),sequence=''.join('H' if p['hit'] else 'M' for p in pp))
    # Unit checks: runs stop at a miss/unknown; no off-by-one at either edge.
    assert describe([{'hit':v} for v in [True,True,False,False,True]])['longest_hit_run']==2
    assert describe([{'hit':v} for v in [True,None,True]])['longest_hit_run']==1
    assert describe([])['longest_hit_run']==0
    assert result['rules']['A']['picks']['hits']==30 and result['rules']['B']['picks']['hits']==21
    (OUT/'streaks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    lines=['# MLS 2026 consecutive-hit research','',result['scope'],'',result['order'],'',result['coverage'],'',
        'H = 2+ shots; M = fewer than 2 shots. A is the original thesis; B adds prior-five-start averages of at least 3 shots and 80 minutes. Rules unchanged.','',
        '| Version | Hits / picks | Longest hit streak | Longest miss streak | All-hit kickoff batches / total | Longest all-hit batch streak |',
        '|---|---:|---:|---:|---:|---:|']
    for rule,r in result['rules'].items():
        p,b=r['picks'],r['kickoff_batches']
        lines.append(f"| {rule} | {p['hits']}/{p['n']} | {p['longest_hit_run']} | {p['longest_miss_run']} | {b['hits']}/{b['n']} | {b['longest_hit_run']} |")
    for rule,r in result['rules'].items():
        lines += ['',f'## {rule}: observed chronological sequence','',r['sequence'],'','### Hit runs','',str(r['picks']['hit_run_lengths']),'',
            'Run-length counts include incomplete runs at the data boundaries; they are not probabilities of future streaks.','',
            '### Active weekends','', '| Weekend | Hits | Picks | All hit? |','|---|---:|---:|---|']
        for run in r['active_weekends']['runs']:
            for w in run['entries']:lines.append(f"| {w['date']} | {w['hits']} | {w['n']} | {'Yes' if w['hit'] else 'No'} |")
        lines += ['', '### Every selection','', '| UTC kickoff | Fixture | Player | Shots | Result |','|---|---|---|---:|---|']
        for run in r['picks']['runs']:
            for p in run['entries']:lines.append(f"| {p['date']} | {p['fixture']} | {p['player']} | {p['shots']} | {'H' if p['hit'] else 'M'} |")
    lines += ['','## Interpretation','',
        'Same-match player outcomes are correlated. A kickoff batch counts as all-hit only when every qualifying pick at that kickoff hits; a failed batch can contain winning picks. Batch streaks avoid arbitrary ordering within simultaneous fixtures. Fixture-order streaks retain ties and should not be interpreted as independent trials.',
        'The small previously inspected sample cannot establish future streak probabilities, profitability, or reliable accumulators. No odds or staking simulation. New Flashscore feasibility examples are not model selections and are excluded.']
    (OUT/'streaks.md').write_text('\n'.join(lines),encoding='utf-8')
    cards=''
    for rule,r in result['rules'].items():
        p=r['picks'];cards+=f"<section><h2>{rule}: {p['hits']}/{p['n']} hits</h2><p>Longest: {p['longest_hit_run']} hits · {p['longest_miss_run']} misses</p><div class='sequence'>"+''.join(f"<span class='{ 'hit' if ch=='H' else 'miss'}'>{ch}</span>" for ch in r['sequence'])+'</div></section>'
    html='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MLS hit streaks</title><style>body{font:17px/1.6 system-ui;max-width:1000px;margin:32px auto;padding:20px;background:#eef3f7;color:#192e40}section{background:white;padding:20px;margin:20px 0}.sequence{display:flex;flex-wrap:wrap;gap:5px}span{padding:7px 10px;border-radius:5px}.hit{background:#d7efdc}.miss{background:#f6d2cc}.note{background:#fff0c7;padding:16px}a{color:#14657a}</style><h1>MLS 2026: consecutive hits</h1><p class="note">Previously studied, incomplete historical sample—not a fresh backtest. Same-kickoff pick order is arbitrary. No-pick weeks are skipped; coverage gaps remain unknown.</p>'+cards+'<p>A = original pattern; B = stricter prior-shot/minutes filters. H = hit, M = miss.</p><p><a href="streaks.md">Full streak analysis and every selection</a> · <a href="streaks.json">Structured data, runs and kickoff batches</a> · <a href="index.html">Weekend scanner</a></p></html>'
    (OUT/'streaks.html').write_text(html,encoding='utf-8')
    print(json.dumps({k:{q:{a:b for a,b in v[q].items() if a!='runs'} for q in ['picks','kickoff_batches','active_weekends']} for k,v in result['rules'].items()},indent=2))

if __name__=='__main__':main()
