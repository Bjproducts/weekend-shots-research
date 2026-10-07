"""Bounded read-only documented ASA download; preserves raw data, no starters inferred."""
import datetime as dt
import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'outputs' / 'mls_2026_sources'
BASE = 'https://app.americansocceranalysis.com/api/v1/'
OUT.mkdir(parents=True, exist_ok=True)

def fetch(path, params, filename):
    target = OUT / filename
    if target.exists():
        return json.loads(target.read_text(encoding='utf-8'))
    url = BASE + path + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': 'MLSResearch/1.0 personal research; cached bounded requests'})
    with urllib.request.urlopen(req, timeout=40) as response:
        raw = response.read()
    value = json.loads(raw)
    if not isinstance(value, list):
        raise ValueError(f'Unexpected response for {url}')
    target.write_bytes(raw)
    metadata = {'source_url': url, 'retrieved_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                'sha256': hashlib.sha256(raw).hexdigest(), 'records': len(value),
                'source': 'American Soccer Analysis documented public API', 'raw_unmodified': True}
    target.with_suffix('.metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(filename, len(value), flush=True)
    time.sleep(0.6)
    return value

games = fetch('mls/games', {'season_name': '2026', 'status': 'FullTime', 'stage_name': 'Regular Season'}, 'asa_games_2026.json')
dates = sorted(g['date_time_utc'][:10] for g in games if g['date_time_utc'][:10] <= '2026-09-27')
begin, stop = dt.date.fromisoformat(dates[0]), dt.date.fromisoformat(dates[-1])
all_rows = []
manifest = []
while begin <= stop:
    end = min(begin + dt.timedelta(days=6), stop)
    params = {'start_date': str(begin), 'end_date': str(end), 'split_by_games': 'true',
              'split_by_teams': 'true', 'minimum_minutes': 0, 'minimum_shots': 0,
              'minimum_key_passes': 0, 'stage_name': 'Regular Season'}
    offset = 0
    while True:
        query = dict(params)
        if offset:
            query['offset'] = offset
        filename = f'asa_players_{begin}_{end}_{offset}.json'
        rows = fetch('mls/players/xgoals', query, filename)
        manifest.append({'file': filename, 'records': len(rows), 'start': str(begin), 'end': str(end), 'offset': offset})
        all_rows.extend(rows)
        if len(rows) < 1000:
            break
        offset += 1000
        if offset > 5000:
            raise ValueError('Unexpected weekly pagination volume; stop')
    begin = end + dt.timedelta(days=1)

cutoff = dt.datetime(2026, 9, 27, 12, 3, 26, tzinfo=dt.timezone.utc)
game_ids = {g['game_id'] for g in games if dt.datetime.strptime(g['date_time_utc'], '%Y-%m-%d %H:%M:%S UTC').replace(tzinfo=dt.timezone.utc) < cutoff}
keys = [(r['game_id'], r['team_id'], r['player_id']) for r in all_rows]
summary = {'source': 'American Soccer Analysis', 'cutoff_date_utc': '2026-09-27', 'cutoff_utc': cutoff.isoformat(),
           'completed_games': len(game_ids), 'raw_appearance_rows': len(all_rows),
           'unique_appearance_keys': len(set(keys)), 'duplicate_keys': len(keys)-len(set(keys)),
           'covered_game_ids': len({r['game_id'] for r in all_rows} & game_ids),
           'unmatched_game_ids': sorted({r['game_id'] for r in all_rows}-game_ids),
           'missing_game_ids': sorted(game_ids-{r['game_id'] for r in all_rows}),
           'zero_shot_rows': sum(r.get('shots') == 0 for r in all_rows),
           'starter_status': 'not supplied; unknown',
           'minutes_semantics': 'ASA expanded/stoppage-inclusive; not harmonized with prior nominal-minute rules',
           'not_eligible_for_exact_ab_replay_yet': True, 'files': manifest}
(OUT/'asa_player_coverage_2026.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k != 'files'}, indent=2), flush=True)
