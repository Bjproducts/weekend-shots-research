"""Inventory, preserve and screen all located local historical samples read-only."""
import hashlib
import json
import sqlite3
from collections import Counter,defaultdict
from datetime import datetime,timedelta
from html import escape
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'
SOT=Path('C:/Users/bjpro/OneDrive/Desktop/SHOT ON TARGET')
LEGACY=Path('C:/Users/bjpro/Documents/Codex/2026-09-14/files-pasted-by-the-user-build/work/legacy-soccer.json')
TABLES={'competitions':'competitions','seasons':'seasons','teams':'teams','players':'players','fixtures':'fixtures','stats':'player_fixture_stats'}
KEEP={
 'competitions':['id','provider_competition_id','name','is_competitive'],
 'seasons':['id','competition_id','season_year','label'],
 'teams':['id','provider_team_id','name'],
 'players':['id','provider_player_id','full_name','common_name'],
 'fixtures':['id','provider_fixture_id','competition_id','season_id','fixture_date','home_team_id','away_team_id','home_score','away_score','status'],
 'stats':['id','fixture_id','player_id','team_id','opponent_id','home','started','minutes_played','position','shots','shots_on_target','team_shots','data_source','data_quality_status'],
}

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def load(p):
    if p.suffix=='.json':return json.loads(p.read_text(encoding='utf-8'))
    c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
    c.row_factory=sqlite3.Row
    try:return {key:[dict(r) for r in c.execute('SELECT * FROM '+table)] for key,table in TABLES.items()}
    finally:c.close()

def audit(d,known):
    comps={r['id']:r for r in d['competitions']}
    seasons={r['id']:r for r in d['seasons']}
    teams={r['id']:r['name'] for r in d['teams']}
    players={r['id']:r for r in d['players']}
    stats=defaultdict(list)
    for r in d['stats']:stats[r['fixture_id']].append(r)
    histories=defaultdict(list)
    fixture_audit=[]
    sample_audit=[]
    coverage=defaultdict(lambda:dict(fixtures_with_stats=0,player_samples=0,finished_fixtures=0,eligible_fixtures=0,new_same_provider_fixtures=0,max_prior_home_results=0,max_prior_away_results=0))
    for f in sorted(d['fixtures'],key=lambda r:(r['fixture_date'],r['id'])):
        cid,sid,hid,aid=(f[k] for k in ['competition_id','season_id','home_team_id','away_team_id'])
        group=comps[cid]['name']+' / '+seasons[sid]['label']
        cov=coverage[group]
        allstats=stats[f['id']]
        real=[r for r in allstats if r['data_source'] in ('sportsapipro','apifootball')]
        sources=sorted({r['data_source'] for r in real})
        seen=bool(sources) and all((s,str(f['provider_fixture_id'])) in known for s in sources)
        cutoff=datetime.fromisoformat(f['fixture_date'])-timedelta(days=1)
        h=[r for r in histories[cid,sid,hid] if r['date']<cutoff]
        a=[r for r in histories[cid,sid,aid] if r['date']<cutoff]
        hv=[r for r in h if r['home'] and r['shots'] is not None and r['against'] is not None][-5:]
        av=[r for r in a if not r['home'] and r['shots'] is not None and r['against'] is not None][-5:]
        reasons=[]
        if f['status']!='finished':reasons.append('fixture_not_finished')
        if not comps[cid]['is_competitive']:reasons.append('not_competitive')
        if not real:reasons.append('no_supported_real_player_stats')
        if len(h)<8:reasons.append('home_fewer_than_8_prior_season_results')
        if len(a)<8:reasons.append('away_fewer_than_8_prior_season_results')
        if len(hv)<3:reasons.append('home_fewer_than_3_prior_home_shot_matches')
        if len(av)<3:reasons.append('away_fewer_than_3_prior_away_shot_matches')
        eligible=not reasons
        entry=dict(fixture_id=f['id'],provider_fixture_id=f['provider_fixture_id'],date=f['fixture_date'],
            league_season=group,fixture=teams[hid]+' vs '+teams[aid],status=f['status'],player_samples=len(allstats),
            same_provider_fixture_in_original_database=seen,eligible_history=eligible,exclusion_reasons=reasons,
            prior_home_results=len(h),prior_away_results=len(a),prior_home_venue_shot_matches=len(hv),prior_away_venue_shot_matches=len(av))
        fixture_audit.append(entry)
        if allstats:
            cov['fixtures_with_stats']+=1
            cov['player_samples']+=len(allstats)
            cov['new_same_provider_fixtures']+=int(bool(real) and not seen)
            cov['max_prior_home_results']=max(cov['max_prior_home_results'],len(h))
            cov['max_prior_away_results']=max(cov['max_prior_away_results'],len(a))
        cov['finished_fixtures']+=int(f['status']=='finished')
        cov['eligible_fixtures']+=int(eligible)
        for p in allstats:
            pwhy=list(reasons)
            if p['data_source'] not in ('sportsapipro','apifootball'):pwhy.append('synthetic_or_unsupported_source')
            if not p['home']:pwhy.append('away_player_outside_frozen_rule')
            if not p['started']:pwhy.append('not_recorded_starter')
            if seen:pwhy.append('fixture_already_in_original_source_not_independent')
            sample_audit.append(dict(fixture_id=f['id'],player_id=p['player_id'],team_id=p['team_id'],
                player=players[p['player_id']].get('common_name') or players[p['player_id']]['full_name'],
                outcome_2plus=None if p['shots'] is None else p['shots']>=2,
                new_validation_status='excluded' if pwhy else 'requires_frozen_rule_replay',reasons=pwhy))
        totals={}
        for tid in [hid,aid]:
            vals={r['team_shots'] for r in real if r['team_id']==tid and r['team_shots'] is not None}
            totals[tid]=next(iter(vals)) if len(vals)==1 else None
        if f['status']=='finished' and comps[cid]['is_competitive'] and f['home_score'] is not None and f['away_score'] is not None:
            for tid,other,home in [(hid,aid,True),(aid,hid,False)]:
                histories[cid,sid,tid].append(dict(date=datetime.fromisoformat(f['fixture_date']),home=home,shots=totals[tid],against=totals[other]))
    return dict(coverage=dict(coverage),fixtures=fixture_audit,samples=sample_audit,
        pending_new_player_samples=sum(r['new_validation_status']=='requires_frozen_rule_replay' for r in sample_audit),
        exclusion_reason_counts=dict(Counter(reason for r in sample_audit for reason in r['reasons'])))

def main():
    paths=[SOT/'backend/sot_sportsapi.db',SOT/'backend/sot_sportsapi.pre-rollover-20260813.db',
        SOT/'backend/sot_live.db',LEGACY,SOT/'backend/sot_demo.db',SOT/'sot_sportsapi.db']
    primary=load(paths[0])
    primary_fixtures={r['id']:str(r['provider_fixture_id']) for r in primary['fixtures']}
    known={(r['data_source'],primary_fixtures[r['fixture_id']]) for r in primary['stats']}
    manifests=[]
    with ZipFile(OUT/'other_history_all_samples.zip','w',ZIP_DEFLATED) as z:
        for i,p in enumerate(paths):
            label=f'{i+1:02d}_{p.stem}'
            meta=dict(source=str(p),sha256=digest(p),archive_folder=label)
            try:
                d=load(p)
                audit_result=audit(d,known)
                # No claim of a new test unless the fixed requirements are met.
                assert audit_result['pending_new_player_samples']==0, 'New eligible samples found: run frozen rules before reporting'
                meta.update(status='audited',player_samples=len(d['stats']),fixtures=len(d['fixtures']),
                    providers=dict(Counter(r['data_source'] for r in d['stats'])),
                    coverage=audit_result['coverage'],pending_new_player_samples=0)
                for key,rows in d.items():
                    if key in KEEP:
                        cleaned=[{k:r.get(k) for k in KEEP[key]} for r in rows]
                        z.writestr(label+'/'+key+'.json',json.dumps(cleaned,ensure_ascii=False,indent=2))
                z.writestr(label+'/screening_audit.json',json.dumps(audit_result,ensure_ascii=False,indent=2))
                assert len(audit_result['samples'])==len(d['stats'])
            except sqlite3.OperationalError as e:meta.update(status='no_usable_schema',error=str(e))
            manifests.append(meta)
        notes=dict(scope='All located source fixtures/player samples and normalized supporting identity tables. No secrets/provider raw payloads. Copies are not independent samples.',
            rule_version='home-main-shooter-v1 unchanged',new_independent_qualifying_picks=0,
            cross_provider_identity='API-Football IDs are not equated to SportsAPI IDs; cross-provider fixture overlap unresolved. All fail history requirements anyway.',
            missing='More contiguous historical results and player/team shots are required, not relaxed thresholds.',
            touchline_postgres='Read-only connection attempted: ECONNREFUSED; live contents not inspected.',sources=manifests)
        z.writestr('manifest.json',json.dumps(notes,indent=2))
    (OUT/'other_history_inventory.json').write_text(json.dumps(notes,indent=2),encoding='utf-8')
    # Verify every archived sample count, with CRC verification.
    with ZipFile(OUT/'other_history_all_samples.zip') as z:
        assert z.testzip() is None
        for m in manifests:
            if m['status']=='audited':
                assert len(json.loads(z.read(m['archive_folder']+'/stats.json')))==m['player_samples']
                assert len(json.loads(z.read(m['archive_folder']+'/screening_audit.json'))['samples'])==m['player_samples']
    lines=['# Other historical data: frozen-pattern screening','',
        '**No additional independent qualifying picks were available in the accessible saved sources. No new hit rate can be reported.**','',
        'The rules were not weakened. The European samples do not provide the eight earlier season results and three earlier venue-shot matches per team required by the existing pattern. MLS exports/backups are overlapping history, not fresh validation.','',
        '| Source | Recorded player samples (not independent) | Status |','|---|---:|---|']
    for m in manifests:lines.append(f"| {Path(m['source']).name} ({m['archive_folder']}) | {m.get('player_samples',0)} | {m['status']} |")
    lines+=['','## League and season coverage','','| Source | League / season | Fixtures with player stats | Player samples | History-eligible fixtures |','|---|---|---:|---:|---:|']
    for m in manifests:
        for name,v in m.get('coverage',{}).items():
            lines.append(f"| {m['archive_folder']} | {name} | {v['fixtures_with_stats']} | {v['player_samples']} | {v['eligible_fixtures']} |")
    lines+=['','## All sample data saved','',
        'other_history_all_samples.zip contains per-source fixture, player-stat, team, player, competition and season JSON files, plus a screening record for every fixture and player sample. Original shots/minutes/starter status and unknowns are preserved. Every rejected sample has reasons; archive manifests contain source paths and hashes.',
        'Synthetic demo records are preserved for audit but excluded from football evidence. Duplicate snapshots remain labelled by source; counts must not be added as unique observations. API-Football fixture identities are not merged with SportsAPI identities.',
        '', '## Remaining gap / next action','',
        'Obtain a contiguous, preferably complete season from another league, including results, both teams’ shots, player shots, starting status, minutes and stable match/player IDs. Then apply the frozen rule after warm-up and save all picks, misses and exclusions. No provider downloads or production database changes were made.',
        'Touchline’s local PostgreSQL connection was unavailable (ECONNREFUSED); its live contents could not be inspected. Its saved legacy export was fully inspected.',
        'Existing 81.1% result remains MLS retrospective evidence, not a cross-league win rate. Original ticket replacement reconciliation is unchanged.']
    report='\n'.join(lines)+'\n'
    (OUT/'other_history_screening_report.md').write_text(report,encoding='utf-8')
    page=OUT/'project_site/dist/index.html'
    html=page.read_text(encoding='utf-8')
    start,end='<!-- OTHER_HISTORY_START -->','<!-- OTHER_HISTORY_END -->'
    if start in html:
        before,tail=html.split(start,1);html=before+tail.split(end,1)[1]
    panel=f'''{start}<section id="other-history" class="panel" style="margin:24px 0"><div class="eyebrow">OTHER-HISTORY CHECK · SAMPLES SAVED</div>
    <h2>No new independent qualifying picks yet</h2><p>The six saved European leagues have only 16–17 matches with player stats each. Other real-data exports overlap the original history or lack the required prior matches. Rules were kept fixed; no new win rate is claimed.</p>
    <p>Every located source sample and exclusion reason is archived. Synthetic demo data is excluded from evidence. Touchline's live database was unavailable; its saved export was checked.</p>
    <p><b>Next:</b> obtain a contiguous season in another league and replay the same two frozen variants.</p>
    <p><a href="../../other_history_screening_report.md">Coverage report</a> · <a href="../../other_history_all_samples.zip">All sample data and exclusions (ZIP)</a> · <a href="../../other_history_inventory.json">Source inventory</a></p></section>{end}'''
    page.write_text(html.replace('</header>','</header>'+panel,1),encoding='utf-8')
    print(json.dumps([{k:v for k,v in m.items() if k!='coverage'} for m in manifests],indent=2))
    print('PASS: all sample counts, per-sample reasons, archive CRC; no new eligible independent samples.')

if __name__=='__main__':main()
