"""Test fudan sync"""
import requests
import json
import sys

# Login
tok = requests.post('http://localhost:8000/api/v1/auth/login', json={'username':'222','password':'222222'}).json()['access_token']
sys.stdout.reconfigure(encoding='utf-8')
print(f'Token: {tok[:20]}...')

# Connect
r = requests.post('http://localhost:8000/api/v1/external/fudan/connect',
    headers={'Authorization': f'Bearer {tok}'},
    json={'student_id':'25803050346','password':'Oyzl0817'})
print(f'Connect: {r.json()["success"]}')

# Sync
r = requests.post('http://localhost:8000/api/v1/external/fudan/sync',
    headers={'Authorization': f'Bearer {tok}'})
data = r.json()
print(f'Sync: success={data["success"]}, created={data["data"]["events_created"]}')

# Verify
r = requests.get('http://localhost:8000/api/v1/events/', params={'limit':200},
    headers={'Authorization': f'Bearer {tok}'})
events = r.json()
fudan = [e for e in events if e.get('source') == 'fudan']
print(f'Fudan events in DB: {len(fudan)}')

if fudan:
    from collections import Counter
    months = Counter()
    for e in fudan:
        if e.get('start_time'):
            months.update([e['start_time'][:7]])
    for k,v in sorted(months.items()):
        print(f'  {k}: {v}')
    for e in fudan[:5]:
        desc = (e.get('description') or '')[:60]
        start = e.get('start_time','')[:10] if e.get('start_time') else 'N/A'
        print(f'  {e["title"][:25]:25s} | {start:12s} | {desc}')
else:
    print(f'All events: {len(events)}')
    sources = set(e.get('source') for e in events)
    print(f'Sources: {sources}')