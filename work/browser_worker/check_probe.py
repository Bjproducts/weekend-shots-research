"""Verify recorded tool evidence and compare the independent extraction with the saved XI."""
import json
from pathlib import Path
import re
from run_probe import ROOT, URL

def check(folder):
    result=json.loads((folder/'result.json').read_text(encoding='utf-8'))
    meta=json.loads((folder/'run.json').read_text(encoding='utf-8'))
    events=[json.loads(line) for line in (folder/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    calls=[e['item'] for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='mcp_tool_call']
    assert meta['exit_code']==0 and result['status']=='observed'
    assert result['source_url']==URL and result['blocker'] is None
    assert len(result['home_starters'])==len(set(result['home_starters']))==11
    assert any(c['tool']=='browser_navigate' and c['status']=='completed' and c['arguments'].get('url')==URL for c in calls)
    assert any(c['tool']=='browser_close' and c['status']=='completed' for c in calls)
    evidence='\n'.join(part.get('text','') for c in calls if c.get('result') for part in c['result'].get('content',[]))
    assert 'Starting Lineups' in evidence
    normalize=lambda name: re.sub(r' \([GC]\)$','',name)
    names=[normalize(n) for n in result['home_starters']]
    assert all(n in evidence for n in names)
    previous=json.loads((ROOT/'outputs/mls_2026_aug22_validation/target_lineups.json').read_text(encoding='utf-8'))
    expected=next(f['starters'] for f in previous['fixtures'] if f['source_url']==URL)
    assert names==expected
    report={'connection_test':'passed','home_starters_matched':11,'browser_calls':len(calls),
        'raw_evidence':'events.jsonl','model_ready':False,
        'notes':['Displayed kickoff timezone not established; do not convert it to UTC.',
                 'Fixture header contains final score; exclude that from pre-match features.',
                 'This test does not establish minutes, shots or five-start histories.']}
    (folder/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))

if __name__=='__main__':
    check(ROOT/'outputs/on_demand/browser_probe/20260928T130759Z')
