"""Stage 1 of frozen MLS weekend validation: pre-match result-strength audit.
No target shots or results are used to choose environments. No inferred starts.
"""
import json
from datetime import timedelta
from pathlib import Path
from statistics import mean
from on_demand import plan, stamp, SOURCES, ROOT, write, cached_players

OUT=ROOT/'outputs/mls_2026_aug22_validation'

def points(game,team):
    gf,ga=(game['home_score'],game['away_score']) if game['home_team_id']==team else (game['away_score'],game['home_score'])
    if gf is None or ga is None:raise ValueError('Unknown result')
    return 3 if gf>ga else 1 if gf==ga else 0

def main():
    games=json.loads((SOURCES/'asa_games_2026.json').read_text(encoding='utf-8'))
    byid={g['game_id']:g for g in games}
    request=plan('2026-08-22')
    # Names are populated only from the ASA identity lookup, if available.
    lookup=OUT/'raw/teams.json'
    teams={r['team_id']:r.get('team_name',r.get('name',r['team_id'])) for r in json.loads(lookup.read_text(encoding='utf-8'))} if lookup.exists() else {}
    fixtures=[]
    for target in request['fixtures']:
        g=byid[target['game_id']]; cutoff=stamp(g)-timedelta(days=1)
        histories={tid:sorted([x for x in games if stamp(x)<cutoff and tid in [x['home_team_id'],x['away_team_id']]],key=stamp) for tid in [g['home_team_id'],g['away_team_id']]}
        form={tid:{'n':len(h),'season_ppg':mean(points(x,tid) for x in h) if h else None,'last5_ppg':mean(points(x,tid) for x in h[-5:]) if len(h)>=5 else None,'prior_ids':[x['game_id'] for x in h]} for tid,h in histories.items()}
        h,a=form[g['home_team_id']],form[g['away_team_id']]
        enough=min(h['n'],a['n'])>=8
        strength=(h['season_ppg']>a['season_ppg'] and h['last5_ppg']>a['last5_ppg']) if enough else None
        fixtures.append(dict(game_id=g['game_id'],kickoff=g['date_time_utc'],home=teams.get(g['home_team_id'],g['home_team_id']),away=teams.get(g['away_team_id'],g['away_team_id']),home_id=g['home_team_id'],away_id=g['away_team_id'],home_form=h,away_form=a,strength_pass=strength,
            status='needs_venue_shots_then_lineups' if strength else 'fails_strength' if strength is False else 'insufficient_history',
            venue_game_ids=target['venue_game_ids'] if strength else [],
            home_history_newest_first=target['home_history_newest_first'] if strength else []))
    venue={}
    for side in ['home','away']:
        path=OUT/'raw'/('venue_full_'+side+'.json')
        if path.exists():
            for r in json.loads(path.read_text(encoding='utf-8')):
                key=(r['game_id'],r['team_id'])
                assert key not in venue or venue[key]==r
                venue[key]=r
    appearances,_=cached_players()
    for f in fixtures:
        if not f['strength_pass']:continue
        h=[venue.get((i,f['home_id'])) for i in f['venue_game_ids'] if byid[i]['home_team_id']==f['home_id']]
        a=[venue.get((i,f['away_id'])) for i in f['venue_game_ids'] if byid[i]['away_team_id']==f['away_id']]
        if not (len(h)>=3 and len(a)>=3 and all(h) and all(a)):continue
        hf,ha=mean(r['shots_for'] for r in h),mean(r['shots_against'] for r in h)
        af,aa=mean(r['shots_for'] for r in a),mean(r['shots_against'] for r in a)
        shooting=hf>=12 and aa>=12 and (hf+aa)/2>(af+ha)/2
        conflicts=[]
        for r in h+a:
            rows=[v['value'] for k,v in appearances.items() if k[0]==r['game_id'] and k[1]==r['team_id']]
            if not rows or any(x.get('shots') is None for x in rows) or sum(x['shots'] for x in rows)!=r['shots_for']:
                conflicts.append(r['game_id'])
        f.update(shooting_pass=shooting if not conflicts else None,environment_pass=shooting if not conflicts else None,venue_features=dict(home_home_shots=hf,away_away_conceded=aa,home_proxy=(hf+aa)/2,away_proxy=(af+ha)/2),venue_player_sum_conflicts=conflicts,
            status='source_conflict' if conflicts else 'needs_lineups_and_previous_starts' if shooting else 'fails_shooting')
    result=dict(weekend='2026-08-22',rules_sha256=request['rules_sha256'],stage='Pre-match environment audit; player test not yet completed',
        source_catalog='outputs/mls_2026_sources/asa_games_2026.json',catalog_coverage='Archived completed games; completeness not independently certified',fixtures=fixtures,
        target_fixtures=len(fixtures),strength_passes=sum(f['strength_pass'] is True for f in fixtures),environment_passes=sum(f.get('environment_pass') is True for f in fixtures),
        no_new_win_rate=True,prior_cutoff='strictly earlier than kickoff minus 24 hours')
    write(OUT/'strength_audit.json',result)
    lines=['# August 22–23: pre-match collection shortlist','',result['stage'],'',
        f"{len(fixtures)} archived weekend fixtures; {result['strength_passes']} pass the unchanged overall/recent home-strength condition; {result['environment_passes']} pass both team gates with downloaded venue data. These are environments to investigate, NOT player picks.",'',
        '| Home | Away | Season PPG H/A | Recent PPG H/A | Strength gate |','|---|---|---:|---:|---|']
    for f in fixtures:
        h,a=f['home_form'],f['away_form']
        lines.append(f"| {f['home']} | {f['away']} | {h['season_ppg']:.3f}/{a['season_ppg']:.3f} | {h['last5_ppg']:.3f}/{a['last5_ppg']:.3f} | {f['status']} |")
    lines += ['','## Venue shooting checks','', '| Home | Home shots | Away conceded | Home / away proxy | Player/team shot conflicts |','|---|---:|---:|---:|---|']
    for f in fixtures:
        if 'venue_features' not in f:continue
        v=f['venue_features'];lines.append(f"| {f['home']} | {v['home_home_shots']:.2f} | {v['away_away_conceded']:.2f} | {v['home_proxy']:.2f}/{v['away_proxy']:.2f} | {len(f['venue_player_sum_conflicts'])} |")
    lines += ['','## Remaining work','',
        'Verify venue shooting history for strength-pass fixtures before requesting player lineups. Failing the fixed strength gate rules out A and B regardless of the target result. Do not download player histories for those fixtures.',
        'For environments passing both gates, collect the home starting XI and verified previous five starts for every eligible home starter. Match stable provider identities and minute conventions. Preserve unknowns. Current-match results were not used in this screen.',
        'The complete weekend backtest remains unfinished. No losses, hits, streaks or win rate have been claimed for this new weekend.']
    if (OUT/'target_lineups.json').exists():
        lines += ['','## Collection progress','',
            'All three qualifying home starting XIs are saved in target_lineups.json: 33 starter entries. The Flashscore results page showed the same 15 named weekend pairings as the ASA catalogue. Player histories are still pending reconciliation.',
            'overlap_diagnostic.json tests possible reuse of old history using exact full names, same team and kickoff proximity. It is diagnostic, not an approved cross-provider join: opponent/fixture identity still requires checking. It includes substitutes as well as starters; unmatched appearances are not automatically downloads required for the final shortlist.',
            'Initial venue_home.json / venue_away.json requests explicitly set optional boolean parameters to the string false and returned shot counts inconsistent with player totals. They are retained as rejected diagnostic responses. Only venue_full_home.json / venue_full_away.json, omitting those optional filters, are used; all 50 relevant team-game shot sums agree with cached player totals. Do not reuse the rejected responses or infer their exact server-side interpretation.']
    (OUT/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    assert len({f['game_id'] for f in fixtures})==len(fixtures)
    for f in fixtures:
        cutoff=stamp(byid[f['game_id']])-timedelta(days=1)
        assert all(stamp(byid[i])<cutoff for side in ['home_form','away_form'] for i in f[side]['prior_ids'])
    print(json.dumps({k:v for k,v in result.items() if k!='fixtures'},indent=2))
    print([(f['home'],f['away']) for f in fixtures if f['strength_pass']])

if __name__=='__main__':main()
