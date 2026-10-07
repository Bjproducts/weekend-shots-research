import json
from pathlib import Path
from study_winning_picks import FILTERS
p=Path(__file__).resolve().parents[1]/'outputs/winning_pattern_research.json'
d=json.loads(p.read_text(encoding='utf-8'));rows=d['rows']
assert len(rows)==431 and sum(r['hit'] for r in rows)==353
assert len({(r['provider'],r['fixture_id'],r['player_id']) for r in rows})==431
for name,fn in FILTERS.items():
    selected=[r for r in rows if fn(r)];m=d['filters'][name]
    assert len(selected)==m['all']['n'] and sum(r['hit'] for r in selected)==m['all']['hits']
    assert m['all']['n']+m['excluded']['all']['n']==431
    assert m['all']['hits']+m['excluded']['all']['hits']==353
    assert m['earlier']['n']+m['later']['n']==m['all']['n']
    for r in rows:
        # Enforce that selectors still work with outcome fields unavailable.
        blind={k:v for k,v in r.items() if k not in ['hit','shots','actual_home_shots','actual_away_shots','home_outshot_away','outcome','filter_matches']}
        assert fn(blind)==fn(r)==r['filter_matches'][name]
for league,date in d['splits'].items():
    early=[r['date'][:10] for r in rows if r['dataset']==league and r['period']=='earlier']
    late=[r['date'][:10] for r in rows if r['dataset']==league and r['period']=='later']
    assert max(early)<min(late)
candidates=[n for n,m in d['filters'].items() if m['earlier']['n']>=80 and m['earlier']['n']>=.35*d['baseline']['earlier']['n'] and len({r['dataset'] for r in rows if r['period']=='earlier' and FILTERS[n](r)})>=3]
winner=max(candidates,key=lambda n:(d['filters'][n]['earlier']['hits']/d['filters'][n]['earlier']['n'],d['filters'][n]['earlier']['n'],n))
assert winner==d['earlier_only_choice']
print('PASS: all 431 picks, ten outcome-blind filters, discarded outcomes, date separation and earlier-only candidate selection.')
