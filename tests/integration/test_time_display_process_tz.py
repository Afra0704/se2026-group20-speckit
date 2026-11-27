"""Real host-local timezone changes are confined to POSIX child processes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest


@pytest.mark.skipif(not hasattr(time,'tzset'),reason='Needs a real POSIX tzset runtime; Windows is not cross-TZ evidence')
def test_real_process_timezone_matrix():
    code = """
import json,time
from dataclasses import asdict
from guided_notes.time_display import present_time
time.tzset()
print(json.dumps({'tz':time.tzname,'values':[
 asdict(present_time('2026-11-26 16:03:59',event_kind='closed',source_policy='sqlite_utc')),
 asdict(present_time('2026-11-26T16:03:59.123456Z',event_kind='closed')),
 asdict(present_time('2026-11-26 16:03:59',event_kind='closed'))]}))
"""
    results=[]
    root=Path(__file__).resolve().parents[2]
    for zone in ('UTC','Asia/Taipei','America/New_York'):
        env=dict(os.environ,TZ=zone,PYTHONPATH=str(root/'src'))
        results.append(json.loads(subprocess.check_output([sys.executable,'-c',code],env=env,text=True)))
    print(json.dumps({'platform':sys.platform, 'python':sys.version, 'zones':results}))
    assert results[0]['values']==results[1]['values']==results[2]['values']
    assert results[0]['values'][0]['text']=='2026-11-27 00:03'
    assert results[0]['values'][2]['status']=='unknown_timezone'
    assert len({tuple(row['tz']) for row in results})==3
