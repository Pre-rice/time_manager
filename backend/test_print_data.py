"""Standalone test for print-data API"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

from app.core.database import async_session_factory
from app.models.fudan_credential import FudanCredential
from sqlalchemy import select
from app.services.fudan_service import _get_client, _ensure_sso_session, COURSE_TABLE_URL, PRINT_DATA_URL
from app.services.fudan_parser import parse_print_data_schedules


async def test():
    async with async_session_factory() as db:
        result = await db.execute(
            select(FudanCredential).where(FudanCredential.is_active == True).limit(1)
        )
        cred = result.scalar_one_or_none()
        if not cred:
            print("NO_CREDENTIAL")
            return

        client = await _get_client(cred)
        if not client:
            print("NO_CLIENT - decrypt failed")
            return

        # Step 1: SSO
        ok = await _ensure_sso_session(client, COURSE_TABLE_URL)
        print(f"SSO_OK: {ok}")

        # Step 2: Get semester id
        import re
        resp1 = await client.get(COURSE_TABLE_URL, follow_redirects=True)
        print(f"PAGE: {resp1.status_code} LEN={len(resp1.text)}")

        sem_options = re.findall(r'<option\s+value="(\d+)"[^>]*>([^<]+)</option>', resp1.text)
        sid_match = re.search(r"studentIds\s*=\s*\[(\d+)\]", resp1.text)
        
        sem_id = sem_options[0][0] if sem_options else "527"
        student_id = sid_match.group(1) if sid_match else ""
        print(f"SEM={sem_id} SID={student_id}")

        # Step 3: Get lessons to build lesson_map
        lesson_map = {}
        if sem_id and student_id:
            jresp = await client.get(f"{COURSE_TABLE_URL}/getLesson", params={"semesterId": sem_id, "studentId": student_id})
            if jresp.status_code == 200:
                data = jresp.json()
                raw_lessons = data.get("lessons", [])
                teacher_map = data.get("teacherMap", {})
                for l in raw_lessons:
                    lid = str(l.get("id", ""))
                    course = l.get("course", {})
                    lesson_map[lid] = {
                        "title": course.get("nameZh", ""),
                        "code": l.get("code", ""),
                        "teacher": teacher_map.get(lid, ""),
                    }
                print(f"LESSONS: {len(raw_lessons)}, map entries: {len(lesson_map)}")

        # Step 4: Test print-data API
        print_data_url = PRINT_DATA_URL.replace("{sem_id}", str(sem_id))
        print(f"\nURL: {print_data_url}")
        print_resp = await client.get(print_data_url, follow_redirects=True)
        print(f"PRINT: {print_resp.status_code} LEN={len(print_resp.text)}")

        if print_resp.status_code == 200 and len(print_resp.text) > 20:
            print_data = print_resp.json()
            print(f"Keys: {list(print_data.keys()) if isinstance(print_data, dict) else 'N/A'}")

            vms = print_data.get("studentTableVms", [])
            print(f"VM count: {len(vms)}")
            for i, vm in enumerate(vms[:1]):
                acts = vm.get("activities", [])
                print(f"  VM[{i}] id={vm.get('id')}, acts={len(acts)}")
                for j, act in enumerate(acts[:3]):
                    print(f"    Act[{j}]: '{act.get('courseName')}' wd={act.get('weekday')} "
                          f"u={act.get('startUnit')}-{act.get('endUnit')} "
                          f"weeks={act.get('weekIndexes')[:3]}... "
                          f"room={act.get('room')} teacher={act.get('teachers')}")

            schedules = parse_print_data_schedules(print_data, lesson_map)
            print(f"\nPARSED: {len(schedules)} schedules")
            for s in schedules[:5]:
                print(f"  {s['title']} | 周{s['weekday']} | 第{s['start_unit']}-{s['end_unit']}节 | 周次={s['weeks']} | {s['location']}")
        else:
            print(f"FAILED: {print_resp.text[:500]}")

        await client.aclose()


asyncio.run(test())