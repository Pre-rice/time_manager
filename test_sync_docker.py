"""Test fudan sync - docker version"""
import httpx
import json
from collections import Counter

# Login
tok = httpx.post('http://localhost:8000/api/v1/auth/login', json={'username':'222','password':'222222'}).json()['access_token']
print(f'Token: {tok[:20]}...')

# Connect
r = httpx.post('http://localhost:8000/api/v1/external/fudan/connect',
    headers={'Authorization': f'Bearer {tok}'},
    json={'student_id':'25803050346','password':'Oyzl0817'})
print(f'Connect: {r.json()["success"]}')

# Sync
r = httpx.post('http://localhost:8000/api/v1/external/fudan/sync',
    headers={'Authorization': f'Bearer {tok}'})
data = r.json()
print(f'Sync: success={data["success"]}, created={data["data"]["events_created"]}')
print(f'msg: {data["message"]}')

# Verify
r = httpx.get('http://localhost:8000/api/v1/events/', params={'limit':200},
    headers={'Authorization': f'Bearer {tok}'})
events = r.json()
fudan = [e for e in events if e.get('source') == 'fudan']
print(f'Fudan events in DB: {len(fudan)}')

months = Counter()
for e in fudan:
    if e.get('start_time'):
        months.update([e['start_time'][:7]])
for k,v in sorted(months.items()):
    print(f'  month {k}: {v}')
for e in fudan[:10]:
    desc = (e.get('description') or '')[:80]
    start = e.get('start_time','')[:16] if e.get('start_time') else 'N/A'
    rrule = e.get('rrule', '')
    print(f'  {e["title"][:25]:25s} | {start:16s} | {desc:80s} | {rrule}')