"""Historical MLS weekend scanner: frozen A/B rules; no network or paid API."""
import json,hashlib
from collections import Counter
from datetime import datetime,date,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from html import escape
from test_home_pattern import connect,run,measure
from weekly_pattern_replay import choose,RULES

OUT=Path(__file__).resolve().parents[1]/'outputs/mls_2026_weekends'
TZ=ZoneInfo('America/Denver')
AS_OF=date(2026,9,27)

def local_stamp(s):
    d=datetime.fromisoformat(s)
    if d.tzinfo is None:d=d.replace(tzinfo=timezone.utc)
    return d.astimezone(TZ)

def weekend_key(s):
    d=local_stamp(s)
    if d.year!=2026 or d.weekday() not in [5,6] or d.date()>AS_OF:return None
    return (d.date()-timedelta(days=d.weekday()-5)).isoformat()

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    c=connect()
    full=run(connection=c,save=False)
    fixtures=[dict(r) for r in c.execute('''select f.*,h.name home_name,a.name away_name,
        (select count(*) from player_fixture_stats p where p.fixture_id=f.id and p.data_source='sportsapipro') player_records
        from fixtures f join competitions co on co.id=f.competition_id
        join teams h on h.id=f.home_team_id join teams a on a.id=f.away_team_id
        where co.name='MLS' and f.fixture_date>='2026-01-01' and f.fixture_date<'2027-01-01' order by f.fixture_date''')]
    features=[dict(r,weekend=weekend_key(r['date'])) for r in full['rows'] if r['competition']=='MLS' and weekend_key(r['date'])]
    environments=[dict(r,weekend=weekend_key(r['date'])) for r in full['environments'] if r['competition']=='MLS' and weekend_key(r['date'])]
    samples=[];by_fixture={r['id']:r for r in fixtures}
    for r in fixtures:
        r['weekend']=weekend_key(r['fixture_date']);r['local_kickoff']=local_stamp(r['fixture_date']).isoformat()
    for r in features:
        # Current outcomes deliberately excluded from selection input.
        a=choose({k:r[k] for k in ['shooter_rank','recent_minutes','recent_hits','environment']})['full_pattern']
        b=a and r['recent_shots']>=3 and r['recent_minutes']>=80
        sample=dict(r,A=a,B=b,provider_fixture_id=by_fixture[r['fixture_id']]['provider_fixture_id'],
            local_kickoff=local_stamp(r['date']).isoformat())
        samples.append(sample)
    picks=[r for r in samples if r['A']]
    weeks=[];d=date(2026,1,3)
    while d<=AS_OF:
        key=d.isoformat();fs=[r for r in fixtures if r['weekend']==key]
        stats=[r for r in fs if r['status']=='finished' and r['player_records']>0]
        es=[r for r in environments if r['weekend']==key]
        ps=[r for r in picks if r['weekend']==key]
        weeks.append(dict(saturday=key,sunday=(d+timedelta(days=1)).isoformat(),
            saved_fixtures=len(fs),finished_with_player_stats=len(stats),
            saved_fixtures_without_finished_stats=len(fs)-len(stats),eligible_environments=len(es),
            favourable_environments=sum(r['environment'] for r in es),A=measure(ps),B=measure([r for r in ps if r['B']]),
            status='No saved fixture coverage; not verified as no games' if not fs else
                'Saved fixtures lack finished player data' if not stats else
                'Partial stored results; some fixtures unresolved' if len(stats)<len(fs) else
                'Replay from available results; full league coverage not certified'))
        d+=timedelta(days=7)
    for e in environments:
        e['candidate_ids']=[r['player_id'] for r in picks if r['fixture_id']==e['fixture_id']]
    summary=dict(A=measure(picks),B=measure([r for r in picks if r['B']]),
        excluded_by_B=measure([r for r in picks if not r['B']]),
        active_A_weekends=sum(w['A']['n']>0 for w in weeks),active_B_weekends=sum(w['B']['n']>0 for w in weeks),
        A_weekends_below70=sum(w['A']['n']>0 and w['A']['rate']<70 for w in weeks),
        B_weekends_below70=sum(w['B']['n']>0 and w['B']['rate']<70 for w in weeks))
    stats_dates=[r['fixture_date'] for r in fixtures if r['status']=='finished' and r['player_records']]
    result=dict(as_of=AS_OF.isoformat(),timezone=str(TZ),scope='Saturday/Sunday MLS 2026, historical lineup-time replay',
        source='Previously saved SportsAPI Pro records; no new API requests',rules=RULES,
        rules_sha256=hashlib.sha256(json.dumps(RULES,sort_keys=True).encode()).hexdigest(),
        challenger='A plus previous-five-start average shots >=3 AND average minutes >=80',
        summary=summary,latest_saved_match_with_stats=max(stats_dates) if stats_dates else None,
        saved_2026_matches_with_stats=sum(r['status']=='finished' and r['player_records']>0 for r in fixtures),
        saved_weekend_matches_with_stats=sum(w['finished_with_player_stats'] for w in weeks),
        eligible_weekend_player_rows=len(samples),weeks=weeks,fixtures=fixtures,environments=environments,samples=samples,picks=picks,
        limitations=['MLS 2026 was already used in discovery; this is a workflow/stability replay, not unseen validation.',
        'Stored results stop before the current date. Missing or stale records are not losses or zero-opportunity weekends.',
        'Confirmed historical starters assumed known at lineup time. This is not an advance lineup forecast.',
        'All earlier finished matches, including midweek, may inform features; outcomes within 24h of kickoff are excluded.',
        'Environment ranking uses the pre-match home shot proxy; it is not a calibrated forecast or new selection filter.',
        'Full league coverage and exact historical data-publication timing remain unverified. No odds, profit or automation.'])
    (OUT/'replay.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    def fmt(m):return f"{m['hits']}/{m['n']} ({m['rate']}%)" if m['n'] else 'No settled picks'
    lines=['# MLS 2026: historical weekend scanner','',
        f"Saturday/Sunday in America/Denver; through {AS_OF}. Existing saved data only. No new paid API calls or future monitoring.",'',
        f"A: {fmt(summary['A'])}. B: {fmt(summary['B'])}. B excludes: {fmt(summary['excluded_by_B'])}.",
        f"{summary['active_A_weekends']} weekends with A picks; {summary['active_B_weekends']} with B picks. Latest saved fixture with player stats: {result['latest_saved_match_with_stats']} (UTC).",'',
        'These MLS data were already used in discovery; do not present the replay as independent validation. The remaining 2026 weekends require new fixtures AND player/team stats, not just a fixture list.','',
        '| Weekend starting | Saved fixtures | Finished with stats | A | B | Coverage |','|---|---:|---:|---:|---:|---|']
    for w in weeks:lines.append(f"| {w['saturday']} | {w['saved_fixtures']} | {w['finished_with_player_stats']} | {fmt(w['A'])} | {fmt(w['B'])} | {w['status']} |")
    lines+=['','## Limits','']+['- '+s for s in result['limitations']]
    (OUT/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    payload=json.dumps(result).replace('<','\\u003c')
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MLS 2026 weekend scanner</title><style>body{font:16px/1.6 system-ui;max-width:1200px;margin:28px auto;padding:0 20px;background:#f2f5f8;color:#182b3e}table{border-collapse:collapse;background:white;width:100%}td,th{padding:10px;border-bottom:1px solid #ddd;text-align:left}.scroll{overflow:auto}select,button{font:inherit;padding:8px}.note{padding:16px;background:#fff2cb}a{color:#216e83}.cards{display:flex;gap:20px;flex-wrap:wrap}.cards p{padding:15px;background:white}h1{line-height:1.2}</style>
    <h1>MLS 2026 — historical weekend scanner</h1><p>Saturday/Sunday, America/Denver. A = original pattern; B = A + 3 prior shots and 80 prior minutes.</p><p class="note">Historical lineup-time replay, not live picks or independent validation. Coverage is incomplete. Missing data is not a loss or a quiet weekend.</p><div id="summary" class="cards"></div><p><a href="report.md">Coverage report</a> · <a href="replay.json">Every fixture, feature and candidate</a> · <a href="../mls_2026_source_research.md">Internet source research</a></p><label for="week">Choose weekend </label><select id="week"></select><p id="coverage"></p><h2>1. Favourable environments — ranked by prior shot proxy</h2><div class="scroll"><table><thead><tr><th>Fixture</th><th>Home proxy</th><th>Away proxy</th><th>Season PPG H/A</th><th>Qualifying players</th></tr></thead><tbody id="env"></tbody></table></div><h2>2. Candidate replay and settlement</h2><div class="scroll"><table><thead><tr><th>Local kickoff</th><th>Fixture / player</th><th>Rule</th><th>Prior shots</th><th>Prior minutes</th><th>Prior hits</th><th>Outcome</th></tr></thead><tbody id="picks"></tbody></table></div><h2>Every weekend, including gaps</h2><div class="scroll"><table><thead><tr><th>Saturday</th><th>Saved / with stats</th><th>A</th><th>B</th><th>Coverage</th></tr></thead><tbody id="weeks"></tbody></table></div><script id="data" type="application/json">PAYLOAD</script><script>
    const d=JSON.parse(document.querySelector('#data').textContent),esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),rate=m=>m.n?`${m.hits}/${m.n} (${m.rate}%)`:'No picks';
    document.querySelector('#summary').innerHTML=`<p><b>A: ${rate(d.summary.A)}</b><br>${d.summary.active_A_weekends} active weekends</p><p><b>B: ${rate(d.summary.B)}</b><br>${d.summary.active_B_weekends} active weekends</p><p>Latest saved stats match:<br>${esc(d.latest_saved_match_with_stats)} UTC</p>`;
    const select=document.querySelector('#week');select.innerHTML=d.weeks.map(w=>`<option value="${w.saturday}">${w.saturday} — ${w.sunday}</option>`).join('');
    const last=d.weeks.filter(w=>w.finished_with_player_stats).at(-1);if(last)select.value=last.saturday;
    document.querySelector('#weeks').innerHTML=d.weeks.map(w=>`<tr><td>${w.saturday}</td><td>${w.saved_fixtures} / ${w.finished_with_player_stats}</td><td>${rate(w.A)}</td><td>${rate(w.B)}</td><td>${esc(w.status)}</td></tr>`).join('');
    function render(){let w=d.weeks.find(w=>w.saturday===select.value);document.querySelector('#coverage').textContent=`${w.status}. A: ${rate(w.A)}; B: ${rate(w.B)}.`;
    let es=d.environments.filter(e=>e.weekend===select.value&&e.environment).sort((a,b)=>b.projected_home_shots-a.projected_home_shots);
    document.querySelector('#env').innerHTML=es.map(e=>`<tr><td>${esc(e.fixture)}</td><td>${e.projected_home_shots.toFixed(1)}</td><td>${e.projected_away_shots.toFixed(1)}</td><td>${e.home_ppg.toFixed(2)} / ${e.away_ppg.toFixed(2)}</td><td>${e.candidate_ids.length}</td></tr>`).join('')||'<tr><td colspan="5">No favourable environment recorded for this weekend.</td></tr>';
    let ps=d.picks.filter(p=>p.weekend===select.value).sort((a,b)=>b.projected_home_shots-a.projected_home_shots||a.shooter_rank-b.shooter_rank);
    document.querySelector('#picks').innerHTML=ps.map(p=>`<tr><td>${esc(p.local_kickoff.slice(0,16))}</td><td>${esc(p.fixture)}<br><b>${esc(p.player)}</b></td><td>${p.B?'A + B':'A only'}</td><td>${p.recent_shots.toFixed(1)}</td><td>${p.recent_minutes.toFixed(1)}</td><td>${p.recent_hits}/5</td><td>${p.hit===null?'UNKNOWN':p.hit?'HIT':'MISS'} (${p.shots??'?'})</td></tr>`).join('')||'<tr><td colspan="7">No qualifying player recorded. Check coverage above.</td></tr>';}
    select.addEventListener('change',render);render();</script></html>'''.replace('PAYLOAD',payload)
    source_path=OUT.parent/'mls_2026_sources/asa_player_coverage_2026.json'
    if source_path.exists():
        source=json.loads(source_path.read_text(encoding='utf-8-sig'))
        notice=f'''<p class="note">Separate newer ASA archive: {source['completed_games']:,} completed matches, {source['raw_appearance_rows']:,} player appearances, including {source['zero_shot_rows']:,} zero-shot appearances. Not included in A/B results: starter status is unknown and minutes include stoppage time. <a href="../mls_2026_sources/asa_player_coverage_2026.json">Archive coverage and file manifest</a>.</p>'''
        html=html.replace('<label for="week">',notice+'<label for="week">',1)
    html=html.replace('<label for="week">','<p><a href="http://127.0.0.1:8766">Open local on-demand data assistant</a> (start with <code>python work/on_demand.py</code>). Cache checks and bounded shot collection; browser-agent handoff is not automatic.</p><label for="week">',1)
    (OUT/'index.html').write_text(html,encoding='utf-8')
    page=OUT.parent/'project_site/dist/index.html';text=page.read_text(encoding='utf-8');start,end='<!-- MLS_WEEKEND_START -->','<!-- MLS_WEEKEND_END -->'
    if start in text:
        before,tail=text.split(start,1);text=before+tail.split(end,1)[1]
    panel=f'''{start}<section id="mls-weekends" class="panel" style="margin:24px 0"><div class="eyebrow">MLS 2026 · HISTORICAL WEEKENDS</div><h2>Environment-first A/B replay</h2><p>A: {fmt(summary['A'])}. B: {fmt(summary['B'])}. This is previously inspected saved history, not independent validation or live coverage.</p><p><a href="../../mls_2026_weekends/index.html">Open weekend scanner, coverage and candidates</a></p></section>{end}'''
    panel=panel.replace('</section>','<p><a href="http://127.0.0.1:8766">On-demand local data assistant</a> — requires <code>python work/on_demand.py</code>; Flashscore agent requests are saved handoffs, not automatically dispatched.</p></section>')
    page.write_text(text.replace('</header>','</header>'+panel,1),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['rules','weeks','fixtures','environments','samples','picks']},indent=2))

if __name__=='__main__':main()
