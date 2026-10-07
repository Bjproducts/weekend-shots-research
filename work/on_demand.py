"""Local, bounded historical MLS data assistant. No paid API or embedded AI model."""
import argparse
import hashlib
import json
import threading
import subprocess
import sys
import uuid
import re
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / 'outputs/mls_2026_sources'
OUT = ROOT / 'outputs/on_demand'
TZ = ZoneInfo('America/Denver')
LOCK = threading.Lock()
JOB_LOCK = threading.Lock()
ACTIVE_JOB = None
BASE = 'https://app.americansocceranalysis.com/api/v1/'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2), encoding='utf-8')
    tmp.replace(path)

def stamp(game):
    return datetime.strptime(game['date_time_utc'], '%Y-%m-%d %H:%M:%S UTC').replace(tzinfo=timezone.utc)

def weekend(value):
    day = date.fromisoformat(value)
    if day.year != 2026 or day.weekday() != 5:
        raise ValueError('Choose a Saturday in 2026. This version is historical MLS only.')
    if day > datetime.now(TZ).date():
        raise ValueError('Future weekends are not supported by this historical collector.')
    return day

def cached_players():
    rows, conflicts = {}, set()
    paths = sorted(SOURCES.glob('asa_players_*.json')) + sorted((OUT/'cache').glob('*.json'))
    for path in paths:
        if '.metadata.' in path.name:
            continue
        data = read(path)
        if not isinstance(data, list):
            continue
        for row in data:
            if not all(k in row for k in ('game_id', 'team_id', 'player_id', 'shots')):
                continue
            key = (row['game_id'], row['team_id'], row['player_id'])
            if key in rows and rows[key]['value'] != row:
                conflicts.add(row['game_id'])
            rows[key] = {'value': row, 'file': str(path.relative_to(ROOT))}
    return rows, conflicts

def plan(value):
    day = weekend(value)
    games = read(SOURCES/'asa_games_2026.json')
    metadata = read(SOURCES/'asa_games_2026.metadata.json')
    target = [g for g in games if day <= stamp(g).astimezone(TZ).date() <= day+timedelta(days=1)]
    players, conflicts = cached_players()
    bygame = {}
    for item in players.values():
        bygame.setdefault(item['value']['game_id'], []).append(item)
    needed, entries = {}, []
    for game in sorted(target, key=stamp):
        current = stamp(game)
        cutoff = current-timedelta(days=1)
        hid, aid = game['home_team_id'], game['away_team_id']
        prior = [g for g in games if stamp(g)<cutoff]
        # Season results need no player download. Venue shooting needs last five
        # home-home and away-away matches; gaps stay explicit.
        venue = sorted([g for g in prior if g['home_team_id']==hid],key=stamp)[-5:]
        venue += sorted([g for g in prior if g['away_team_id']==aid],key=stamp)[-5:]
        home_history = sorted([g for g in prior if hid in [g['home_team_id'],g['away_team_id']] and stamp(g)>=current-timedelta(days=180)],key=stamp,reverse=True)
        for g in venue:
            needed[g['game_id']] = g
        needed[game['game_id']] = game
        entries.append(dict(game_id=game['game_id'], kickoff_utc=game['date_time_utc'],
            home_team_id=hid, away_team_id=aid, status='insufficient_data',
            cached_player_rows=len(bygame.get(game['game_id'],[])),
            season_result_counts={hid:sum(hid in [g['home_team_id'],g['away_team_id']] for g in prior),aid:sum(aid in [g['home_team_id'],g['away_team_id']] for g in prior)},
            venue_game_ids=list(dict.fromkeys(g['game_id'] for g in venue)),
            home_history_newest_first=[g['game_id'] for g in home_history],
            blockers=['Verified target home starting XI missing from model-ready store',
                'Previous five starts for every eligible home starter require identity mapping and comparable minutes',
                'Team-shot totals and fixture coverage need reconciliation; cached appearances alone do not prove completeness']))
    tasks = []
    for gid,g in sorted(needed.items(),key=lambda x:stamp(x[1])):
        cached=bygame.get(gid,[])
        tasks.append(dict(game_id=gid,utc_date=g['date_time_utc'][:10],
            home_team_id=g['home_team_id'],away_team_id=g['away_team_id'],
            state='conflict' if gid in conflicts else 'cached_unverified' if cached else 'missing',
            cached_rows=len(cached),source_files=sorted({r['file'] for r in cached})))
    replay=read(ROOT/'outputs/mls_2026_weekends/replay.json')
    saved=[p for p in replay['picks'] if p['weekend']==value]
    result=dict(weekend=value,created_at_utc=datetime.now(timezone.utc).isoformat(),
        status='insufficient_data' if target else 'no_fixture_coverage',
        scope='Historical MLS 2026, Saturday/Sunday America/Denver',
        catalog_retrieved_at=metadata['retrieved_at_utc'],
        catalog_warning='Archived completed fixtures only; no games in this catalogue is not proof of no fixtures. No automatic season refresh.',
        fixtures=entries,shooting_tasks=tasks,network_requests=0,
        rules_sha256=replay['rules_sha256'],
        saved_replay=dict(label='Previously studied replay, NOT generated from newly collected ASA/Flashscore data',picks=saved),
        automatic_capability='Fetch absent player-shot records for target and venue-history matches, bounded to four UTC dates per click. Cache reuse; no paid API.',
        manual_capability='Flashscore browser collection is a saved handoff, not an automatically running AI agent.',
        unresolved_original_cases=['Antony','Denis Bouanga','Pep Biel'])
    return result

def fetch_day(day):
    params=dict(start_date=day,end_date=day,split_by_games='true',split_by_teams='true',minimum_minutes=0,minimum_shots=0,minimum_key_passes=0,stage_name='Regular Season')
    url=BASE+'mls/players/xgoals?'+urlencode(params)
    req=Request(url,headers={'User-Agent':'WeekendShotsResearch/1.0 cached personal research'})
    with urlopen(req,timeout=20) as response:
        raw=response.read(10_000_001)
    if len(raw)>10_000_000:
        raise ValueError('Response too large; collection stopped.')
    value=json.loads(raw)
    if not isinstance(value,list) or len(value)>=1000:
        raise ValueError('Unexpected response or pagination boundary; collection stopped, not marked complete.')
    if any(not all(k in r for k in ['game_id','team_id','player_id','shots']) for r in value):
        raise ValueError('Player response schema changed; collection stopped.')
    # Immutable snapshots: new fetches never overwrite an earlier response.
    digest=hashlib.sha256(raw).hexdigest()
    path=OUT/'cache'/f'players_{day}_{digest[:12]}.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(raw)
    write(path.with_suffix('.metadata.json'),dict(source_url=url,retrieved_at_utc=datetime.now(timezone.utc).isoformat(),sha256=digest,records=len(value),raw_unmodified=True))
    return len(value)

def collect(value):
    before=plan(value)
    days=sorted({t['utc_date'] for t in before['shooting_tasks'] if t['state']=='missing'})[:4]
    fetched, errors=[],[]
    for day in days:
        try:
            fetched.append(dict(date=day,rows=fetch_day(day)))
        except Exception as exc:
            errors.append(dict(date=day,error=str(exc)))
            break  # Do not retry rate limits or failures automatically.
    result=plan(value)
    result.update(network_requests=len(fetched)+len(errors),fetched=fetched,collection_errors=errors)
    return result

def handoff(report):
    value=report['weekend']
    text=f'''Continue the existing weekend shots project for MLS weekend {value} in America/Denver.
Read outputs/on_demand/{value}/request.json and outputs/README.md. Do not restart or retune A/B.
This is a data collection request, not a list of selections. There are {len(report['fixtures'])} archived target fixtures.
For each target fixture, verify fixture identity, UTC kickoff and its home starting XI from public Flashscore pages. Preserve source URLs, retrieval date and displayed names/IDs. Do not infer starts from minutes.
Use home_history_newest_first as a discovery list, not an instruction to download everything. Work backwards for each eligible home starter until five verified same-team starts within 180 days and strictly more than 24 hours before kickoff are established, or exhaustion is documented. ASA shot data already cached must be reused; fill only missing records. Verify venue team-shot totals separately.
Preserve Flashscore displayed minutes and ASA expanded minutes separately. Reconcile IDs, minute semantics and shot counts with overlapping original records before using mixed-source data. Dashes are unknown. Do not pick shooters using target-match outcomes. No paid APIs, access bypass, mass season downloads or automation.
Return sourced records and blockers to this folder. Do not mark the request complete or run fresh A/B until the required histories and fixture coverage have been validated. Original 12/15 provisional replacement correction and three unresolved cases remain unchanged.
'''
    folder=OUT/value
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'agent_request.txt').write_text(text,encoding='utf-8')
    return text

def known_lineup_urls(value):
    """Previously verified discovery URLs only; absence stays an explicit blocker."""
    path=ROOT/'outputs/mls_2026_aug22_validation/target_lineups.json'
    if value!='2026-08-22' or not path.exists():
        return []
    return [f['source_url'] for f in read(path).get('fixtures',[]) if f.get('source_url')]

def job_view(job_id):
    if not re.fullmatch(r'\d{8}T\d{6}Z-[0-9a-f]{8}',job_id):
        raise ValueError('Invalid job ID')
    folder=OUT/'jobs'/job_id
    if not folder.is_dir():
        raise ValueError('Unknown job')
    state=read(folder/'job.json')
    if (folder/'result.json').exists():
        try: state['result']=read(folder/'result.json')
        except Exception: state['result_error']='Structured result could not be read'
    return state

def save_job(folder,state):
    write(folder/'job.json',state)

def validate_browser_result(folder,source_url):
    result=read(folder/'result.json')
    names=result.get('home_starters',[])
    if result.get('status')!='observed' or result.get('source_url')!=source_url:
        return False,'Result status or source URL did not match the request'
    if len(names)!=11 or len(set(names))!=11 or any(not isinstance(n,str) or not n.strip() for n in names):
        return False,'Expected eleven unique, non-empty home starter names'
    try:
        events=[json.loads(line) for line in (folder/'events.jsonl').read_text(encoding='utf-8').splitlines()]
        calls=[e['item'] for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='mcp_tool_call']
        navigated=any(c.get('tool')=='browser_navigate' and c.get('status')=='completed' and c.get('arguments',{}).get('url')==source_url for c in calls)
        closed=any(c.get('tool')=='browser_close' and c.get('status')=='completed' for c in calls)
        evidence='\n'.join(part.get('text','') for c in calls if c.get('result') for part in c['result'].get('content',[]))
        clean=lambda n: re.sub(r' \([GC]\)$','',n)
        if not navigated or not closed or 'Starting Lineups' not in evidence or not all(clean(n) in evidence for n in names):
            return False,'Browser tool evidence was incomplete'
    except Exception:
        return False,'Browser event evidence could not be validated'
    return True,None

def monitor_job(folder,process,state):
    global ACTIVE_JOB
    code=process.wait()
    with JOB_LOCK:
        latest=read(folder/'job.json')
        if latest['status']!='cancelled':
            valid,problem=validate_browser_result(folder,latest['source_url']) if code==0 and (folder/'result.json').exists() else (False,'Worker did not produce a structured result')
            latest['status']='completed' if valid else 'failed_validation'
            latest['validation_error']=problem
        latest['exit_code']=code
        latest['finished_at_utc']=datetime.now(timezone.utc).isoformat()
        save_job(folder,latest)
        if ACTIVE_JOB and ACTIVE_JOB['id']==latest['id']:
            ACTIVE_JOB['log'].close()
            ACTIVE_JOB=None

def start_browser_job(value):
    global ACTIVE_JOB
    weekend(value)
    urls=known_lineup_urls(value)
    if not urls:
        raise ValueError('No verified Flashscore fixture URL is saved for this weekend yet')
    with JOB_LOCK:
        if ACTIVE_JOB and ACTIVE_JOB['process'].poll() is None:
            raise RuntimeError('A browser job is already running')
        job_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
        folder=OUT/'jobs'/job_id
        folder.mkdir(parents=True,exist_ok=False)
        state=dict(id=job_id,weekend=value,status='running',scope='one_fixture_lineup_connection_test',
            source_url=urls[0],started_at_utc=datetime.now(timezone.utc).isoformat(),
            model_ready=False,notice='This does not collect previous-five histories or create picks.')
        save_job(folder,state)
        command=[sys.executable,str(ROOT/'work/browser_worker/run_probe.py'),'--url',urls[0],'--folder',str(folder)]
        log=(folder/'launcher.log').open('w',encoding='utf-8')
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
        ACTIVE_JOB={'id':job_id,'process':process,'log':log}
        threading.Thread(target=monitor_job,args=(folder,process,state),daemon=True).start()
        return state

def cancel_browser_job(job_id):
    global ACTIVE_JOB
    with JOB_LOCK:
        if not re.fullmatch(r'\d{8}T\d{6}Z-[0-9a-f]{8}',job_id):
            raise ValueError('Invalid job ID')
        if not ACTIVE_JOB or ACTIVE_JOB['id']!=job_id or ACTIVE_JOB['process'].poll() is not None:
            return job_view(job_id)
        process=ACTIVE_JOB['process']
        if sys.platform=='win32':
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
        else: process.terminate()
        folder=OUT/'jobs'/job_id
        state=read(folder/'job.json');state['status']='cancelled';state['cancelled_at_utc']=datetime.now(timezone.utc).isoformat()
        save_job(folder,state)
        return state

class Handler(BaseHTTPRequestHandler):
    def send(self,status,body,kind='application/json'):
        raw=(json.dumps(body) if kind=='application/json' else body).encode()
        self.send_response(status)
        self.send_header('Content-Type',kind+'; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers();self.wfile.write(raw)

    def safe_host(self):
        return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

    def do_GET(self):
        if not self.safe_host():
            return self.send(403,{'error':'Local host only'})
        if self.path=='/':
            return self.send(200,(OUT/'index.html').read_text(encoding='utf-8'),'text/html')
        if self.path.startswith('/api/job/'):
            try:return self.send(200,job_view(self.path.rsplit('/',1)[-1]))
            except ValueError as exc:return self.send(404,{'error':str(exc)})
        self.send(404,{'error':'Not found'})

    def do_POST(self):
        expected=f'http://127.0.0.1:{self.server.server_port}'
        if not self.safe_host() or self.headers.get('Origin')!=expected or self.headers.get('Content-Type')!='application/json':
            return self.send(403,{'error':'Same-origin JSON requests only'})
        if self.path not in ['/api/check','/api/collect','/api/handoff','/api/browser/start','/api/browser/cancel']:
            return self.send(404,{'error':'Not found'})
        if self.path in ['/api/browser/start','/api/browser/cancel']:
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=1000:raise ValueError('Invalid request size')
                data=json.loads(self.rfile.read(length))
                result=start_browser_job(data['weekend']) if self.path.endswith('start') else cancel_browser_job(data['job_id'])
                return self.send(202 if self.path.endswith('start') else 200,result)
            except RuntimeError as exc:return self.send(409,{'error':str(exc)})
            except (ValueError,KeyError,TypeError) as exc:return self.send(400,{'error':str(exc)})
        if not LOCK.acquire(blocking=False):
            return self.send(409,{'error':'A request is already running'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=1000:raise ValueError('Invalid request size')
            value=json.loads(self.rfile.read(length))['weekend']
            report=collect(value) if self.path=='/api/collect' else plan(value)
            write(OUT/value/'request.json',report)
            if self.path=='/api/handoff':
                report['handoff']=handoff(report)
            self.send(200,report)
        except (ValueError,KeyError,TypeError) as exc:
            self.send(400,{'error':str(exc)})
        except Exception as exc:
            self.send(500,{'error':str(exc)})
        finally:
            LOCK.release()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8766)
    args=parser.parse_args()
    print(f'On-demand assistant: http://127.0.0.1:{args.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
