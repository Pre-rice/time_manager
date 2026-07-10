"""Verify sync results"""
import sys, json, urllib.request
from collections import Counter

tok = open('token.txt').read().strip()

# Query events
req = urllib.request.Request('http://localhost:8000/api/v1/events/?limit=500',
    headers={'Authorization': f'Bearer {tok}'})
data = json.loads(urllib.request.urlopen(req).read().decode())

fd = [e for e in data if e.get('source') == 'fudan']
m = Counter()
for e in fd:
    if e.get('start_time'):
        m.update([e['start_time'][:7]])

print(f'Total fudan events: {len(fd)}')
print(f'Months: {dict(sorted(m.items()))}')
for e in fd[:40]:
    s = e.get('start_time', 'N/A')[:16] if e.get('start_time') else 'N/A'
    et = e['event_type']
    rr = (e.get('rrule') or '')[:20]
    desc = (e.get('description') or '')[:50]
    print(f'  {e["title"][:25]:25s} | {s:16s} | {et:5s} | {rr:20s} | {desc}')