"""Debug fudan page parsing"""
import httpx
import json
import re
import sys
sys.path.insert(0, '/app')

tok = httpx.post('http://localhost:8000/api/v1/auth/login', json={'username':'222','password':'222222'}).json()['access_token']
r = httpx.get('https://fdjwgl.fudan.edu.cn/student/for-std/course-table', 
    headers={'Authorization': f'Bearer {tok}'}, follow_redirects=True, verify=False)

with open('/tmp/out.log', 'w') as f:
    f.write(f'PAGE_SIZE: {len(r.text)}\n')
    f.write(f'HAS_semesters: {"semesters" in r.text}\n')
    
    from app.services.fudan_parser import parse_all_semester_dates
    result = parse_all_semester_dates(r.text)
    f.write(f'parse result: {result}\n')
    
    # Find JSON.parse
    idx = r.text.find('JSON.parse')
    if idx >= 0:
        start = max(0, idx-30)
        end = min(len(r.text), idx+800)
        f.write(f'JSON.parse at {idx}, ctx: {r.text[start:end]}\n')
    else:
        f.write('JSON.parse NOT FOUND in page\n')
        # Try semesters
        idx2 = r.text.find('semesters')
        if idx2 >= 0:
            f.write(f'semesters at {idx2}, ctx: {r.text[max(0,idx2-30):idx2+800]}\n')
    
    # Check for select options
    options = re.findall(r'<option\s+value="(\d+)"[^>]*>([^<]+)</option>', r.text)
    f.write(f'select options: {options}\n')
    
    # Check studentIds
    sid = re.search(r'studentIds\s*=\s*\[(\d+)\]', r.text)
    if sid:
        f.write(f'studentId: {sid.group(1)}\n')