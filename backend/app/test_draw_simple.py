"""测试 draw-table-data API"""
import asyncio, httpx, re, json

from app.core.database import async_session_factory
from app.models.fudan_credential import FudanCredential
from sqlalchemy import select
from app.core.crypto import decrypt_api_key


async def test():
    async with async_session_factory() as db:
        cred = (await db.execute(
            select(FudanCredential).where(FudanCredential.is_active == True).limit(1)
        )).scalar_one_or_none()
        if not cred:
            print("NO_CREDENTIAL")
            return

        cookie_str = decrypt_api_key(cred.cookies)
        cookies = json.loads(cookie_str)
        jar = httpx.Cookies()
        for d, paths in cookies.items():
            for p, cdict in paths.items():
                for n, v in cdict.items():
                    jar.set(n, v, domain=d, path=p)

        client = httpx.AsyncClient(cookies=jar, timeout=30.0, follow_redirects=True, verify=False)
        r = await client.get("https://fdjwgl.fudan.edu.cn/student/for-std/course-table")
        sems = re.findall(r'<option value="(\d+)"[^>]*>([^<]+)</option>', r.text)
        sid = re.search(r'studentIds\s*=\s*\[(\d+)\]', r.text)
        pid = re.search(r'personId\s*=\s*(\d+)', r.text)
        sem_id = sems[0][0] if sems else "527"
        stu_id = sid.group(1) if sid else ""
        per_id = pid.group(1) if pid else ""
        print(f"PAGE: {r.status_code} sem={sem_id} sid={stu_id} pid={per_id}")

        r3 = await client.post(
            "https://fdjwgl.fudan.edu.cn/ws/schedule-table/draw-table-data",
            json={
                "semesterId": int(sem_id),
                "studentIds": [int(stu_id)],
                "bizTypeId": 2,
                "type": "student",
                "personId": int(per_id),
            },
        )
        print(f"DRAW: {r3.status_code} len={len(r3.text)}")
        if r3.status_code == 200 and len(r3.text) > 20:
            print(r3.text[:2000])
        else:
            print(r3.text[:500])
        await client.aclose()


asyncio.run(test())