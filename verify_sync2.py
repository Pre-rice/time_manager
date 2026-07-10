import urllib.request, json
from collections import Counter

tok = open('token.txt').read().strip()

# Connect
req = urllib.request.Request('http://localhost:8000/api/v1/external/fudan/connect',
    data=json.dumps({'student_id':'25803050346','password':'Oyzl0817'}).encode(),
    headers={'Content-Type':'application/json','Authorization':f'Bearer {tok}'}, method='POST')
print('connect:', json.loads(urllib.request.urlopen(req).read())['success'])

# Sync
req = urllib.request.Request('http://localhost:8000/api/v1/external/fudan/sync',
    data=b'', headers={'Authorization':f'Bearer {tok}'}, method='POST')
d = json.loads(urllib.request.urlopen(req).read())
print(f'sync: success={d["success"]}, created={d["data"]["events_created"]}, errors={len(d["data"]["errors"])}')

# Events
req = urllib.request.Request('http://localhost:8000/api/v1/events/?limit=500',
    headers={'Authorization':f'Bearer {tok}'})
data = json.loads(urllib.request.urlopen(req).read())
fd = [e for e in data if e.get('source')=='fudan']
print(f'fudan events: {len(fd)}')

m = Counter()
for e in fd:
    if e.get('start_time'): m.update([e['start_time'][:7]])
for k,v in sorted(m.items()): print(f'  {k}: {v}')
for e in fd[:35]:
    s = e.get('start_time','N/A')[:16] if e.get('start_time') else 'N/A'
    et = e['event_type']; rr = (e.get('rrule') or '')[:20]
    desc = (e.get('description') or '')[:50]
    print(f'  {e["title"][:25]:25s} | {s:16s} | {et:5s} | {rr:20s} | {desc}')