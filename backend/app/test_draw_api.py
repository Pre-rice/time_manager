"""测试 draw-table-data API 返回结构 — 使用 fudan_service 内部的函数"""
import json
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

from app.core.database import async_session_factory
from app.models.fudan_credential import FudanCredential
from sqlalchemy import select
from app.services.fudan_service import _get_client, _ensure_sso_session

COURSE_TABLE_URL = "https://fdjwgl.fudan.edu.cn/student/for-std/course-table"


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

        # 做 SSO 重连
        ok = await _ensure_sso_session(client, COURSE_TABLE_URL)
        print(f"SSO_OK: {ok}")

        # 访问课表页面
        import httpx, re
        resp1 = await client.get(COURSE_TABLE_URL, follow_redirects=True)
        print(f"PAGE: {resp1.status_code} LEN={len(resp1.text)}")

        # 提取参数
        sem_options = re.findall(
            r'<option\s+value="(\d+)"[^>]*>([^<]+)</option>', resp1.text
        )
        sid_match = re.search(r"studentIds\s*=\s*\[(\d+)\]", resp1.text)
        pid_match = re.search(r"personId\s*=\s*(\d+)", resp1.text)

        semester_id = sem_options[0][0] if sem_options else "527"
        student_id = sid_match.group(1) if sid_match else "485841"
        person_id = pid_match.group(1) if pid_match else "552824"
        print(f"SEM={semester_id} SID={student_id} PID={person_id}")

        # getLesson
        resp2 = await client.get(
            f"{COURSE_TABLE_URL}/getLesson",
            params={"semesterId": semester_id, "studentId": student_id},
        )
        d2 = resp2.json()
        lessons = d2.get("lessons", [])
        print(f"LESSONS: {len(lessons)}")
        for l in lessons:
            c = l.get("course", {})
            lid = l.get("id", "")
            print(f"  [{lid}] {c.get('nameZh','')}")

        # draw-table-data
        try:
            resp3 = await client.post(
                "https://fdjwgl.fudan.edu.cn/ws/schedule-table/draw-table-data",
                json={
                    "semesterId": int(semester_id),
                    "studentIds": [int(student_id)],
                    "bizTypeId": 2,
                    "type": "student",
                    "personId": int(person_id),
                },
                timeout=30.0,
            )
            print(f"\nDRAW: {resp3.status_code} LEN={len(resp3.text)}")
            print(f"DRAW_RAW: {resp3.text[:2000]}")
        except Exception as e:
            print(f"DRAW_ERROR: {e}")

        await client.aclose()


asyncio.run(test())