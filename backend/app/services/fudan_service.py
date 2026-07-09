import base64
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import parse_qs, urlparse, urlencode

import httpx
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import encrypt_api_key, decrypt_api_key
from app.models.fudan_credential import FudanCredential
from app.models.event import Event
from app.models.task import Task
from app.services.fudan_parser import (
    parse_fudan_data,
    parse_weekday,
    parse_weeks,
    period_to_time,
    parse_schedule_from_draw_data,
    parse_print_data_schedules,
    compute_semester_start,
    build_rrule,
    unit_to_time,
    get_weekday_name,
)

logger = logging.getLogger(__name__)

ID_HOST = "id.fudan.edu.cn"
COURSE_TABLE_URL = "https://fdjwgl.fudan.edu.cn/student/for-std/course-table"
EXAM_ARRANGE_URL = "https://fdjwgl.fudan.edu.cn/student/for-std/exam-arrange/"
ELEARNING_URL = "https://elearning.fudan.edu.cn/dash"
PRINT_DATA_URL = "https://fdjwgl.fudan.edu.cn/student/for-std/course-table/semester/{sem_id}/print-data"


def _rsa_encrypt(password: str, public_key_b64: str) -> str:
    """使用 RSA PKCS1 加密密码，参考 DanXi 的 neo_login_tool.dart"""
    pem = f"-----BEGIN PUBLIC KEY-----\n{public_key_b64}\n-----END PUBLIC KEY-----"
    key = RSA.import_key(pem)
    cipher = PKCS1_v1_5.new(key)
    encrypted = cipher.encrypt(password.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


async def get_credential(db: AsyncSession, user_id: uuid.UUID) -> FudanCredential | None:
    """获取用户的复旦凭证"""
    result = await db.execute(
        select(FudanCredential).where(
            FudanCredential.user_id == user_id,
            FudanCredential.is_active == True,
        ).limit(1)
    )
    return result.scalar_one_or_none()


async def _get_public_key(client: httpx.AsyncClient) -> str | None:
    """获取 RSA 公钥"""
    resp = await client.get(f"https://{ID_HOST}/idp/authn/getJsPublicKey")
    data = resp.json()
    logger.info(f"getJsPublicKey response: {data.get('code')}, has data: {bool(data.get('data'))}")
    return data.get("data")


async def _get_lck_and_entity_id(client: httpx.AsyncClient, target_url: str):
    """
    通过访问目标服务获取 lck 和 entityId。
    DanXi 的做法是直接访问 id.fudan.edu.cn/authserver/login。
    """
    # 直接访问 id.fudan.edu.cn/authserver/login
    login_url = f"https://{ID_HOST}/authserver/login?service={target_url}"
    logger.info(f"Accessing login URL: {login_url}")
    
    resp = await client.get(login_url, follow_redirects=True)
    logger.info(f"Login page status: {resp.status_code}, final URL: {resp.url}")
    
    # 从最终 URL 中提取 lck 和 entityId
    final_url = str(resp.url)
    if "#/index" in final_url:
        fragment = final_url.split("#/index")[1] if "#/index" in final_url else ""
    elif "#" in final_url:
        fragment = final_url.split("#")[1]
    else:
        fragment = ""
    
    if fragment:
        params = parse_qs(fragment)
        lck = params.get("lck", [None])[0]
        entity_id = params.get("entityId", [None])[0]
        logger.info(f"Extracted from fragment - lck: {lck}, entityId: {entity_id}")
        return lck, entity_id
    
    # 尝试从页面内容中提取
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(resp.text, "html.parser")
    for script in soup.find_all("script"):
        if script.string and "lck" in script.string:
            logger.info(f"Found lck in script: {script.string[:200]}")
    
    logger.warning(f"Could not find lck/entityId in URL: {final_url}")
    logger.info(f"Response preview: {resp.text[:500]}")
    return None, None


async def _fudan_authenticate_old(
    client: httpx.AsyncClient, student_id: str, password: str, target_url: str
) -> bool:
    """旧版认证方式 - 通过重定向链"""
    lck = None
    entity_id = None
    
    resp = await client.get(target_url, follow_redirects=False)
    logger.info(f"Initial target response: {resp.status_code} {resp.url}")
    
    for i in range(6):
        if resp.status_code not in (301, 302, 303, 307, 308):
            if resp.status_code == 200:
                pass
            break
        
        redirect_url = resp.headers.get("location", "")
        if not redirect_url:
            break
        
        logger.info(f"Redirect {i}: {resp.status_code} -> {redirect_url[:100]}")
        
        if ID_HOST in redirect_url:
            # 尝试从 URL 中解析
            parsed = urlparse(redirect_url)
            if "#/index" in redirect_url:
                fragment_params = parse_qs(parsed.fragment)
                lck = fragment_params.get("lck", [None])[0]
                entity_id = fragment_params.get("entityId", [None])[0]
                if lck and entity_id:
                    break
        
        resp = await client.get(redirect_url, follow_redirects=False)
    
    if not lck or not entity_id:
        logger.warning(f"Could not get lck/entityId. lck={lck}, entityId={entity_id}")
        return False
    
    logger.info(f"Got lck={lck}, entityId={entity_id}")
    return True


async def _fudan_authenticate(
    client: httpx.AsyncClient, student_id: str, password: str, target_url: str
) -> bool:
    """
    认证流程：
    1. 在 id.fudan.edu.cn 上发起 CAS 登录，拿到 lck 和 entityId
    2. 获取 RSA 公钥
    3. 查询认证方式
    4. RSA 加密密码提交登录
    5. 拿到 loginToken 提交获取 ticket
    6. 用 ticket 重定向回目标
    """
    # Step 1: 通过 authserver/login 获取 lck 和 entityId
    login_url = f"https://{ID_HOST}/authserver/login?service={target_url}"
    logger.info(f"Step 1: GET {login_url}")
    
    resp = await client.get(login_url, follow_redirects=True)
    logger.info(f"Response: {resp.status_code}, final URL: {resp.url}")
    
    if resp.status_code != 200:
        logger.warning(f"Unexpected status: {resp.status_code}")
        return False
    
    # 从 URL fragment 中提取 lck 和 entityId
    final_url = str(resp.url)
    fragment = final_url.split("#")[1] if "#" in final_url else ""
    lck = None
    entity_id = None
    
    if fragment:
        # 实际格式: /index?lck=xxx&entityId=yyy
        # 需要先按 ? 拆分，得到查询参数部分
        if "?" in fragment:
            query_part = fragment.split("?", 1)[1]
        else:
            query_part = fragment
        params = parse_qs(query_part)
        lck = params.get("lck", [None])[0]
        entity_id = params.get("entityId", [None])[0] if lck else params.get("entityId", [None])[0]
    
    if not lck or not entity_id:
        # 尝试从页面内容中找
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # 找 meta refresh 或 script
        for elem in soup.find_all(["script", "meta"]):
            text = str(elem)
            if "lck" in text.lower():
                import re
                lck_match = re.search(r'lck[=:"]+([^"&\s]+)', text)
                entity_match = re.search(r'entityId[=:"]+([^"&\s]+)', text)
                if lck_match:
                    lck = lck_match.group(1)
                if entity_match:
                    entity_id = entity_match.group(1)
                if lck and entity_id:
                    break
    
    if not lck or not entity_id:
        logger.error(f"Failed to get lck/entityId. URL: {final_url}, fragment: {fragment}")
        logger.error(f"Page sample: {resp.text[:1000]}")
        return False
    
    logger.info(f"Got lck={lck[:20]}..., entityId={entity_id[:20]}...")
    
    # Step 2: 获取 RSA 公钥
    logger.info("Step 2: getJsPublicKey")
    pub_key = await _get_public_key(client)
    if not pub_key:
        logger.error("Failed to get public key")
        return False
    logger.info(f"Got public key: {pub_key[:30]}...")
    
    # Step 3: 查询认证方式
    logger.info("Step 3: queryAuthMethods")
    resp = await client.post(
        f"https://{ID_HOST}/idp/authn/queryAuthMethods",
        json={"lck": lck, "entityId": entity_id},
    )
    auth_data = resp.json()
    logger.info(f"Auth methods response: {auth_data.get('code')}, second: {auth_data.get('second')}")
    
    if auth_data.get("second") == True:
        logger.warning("Two-factor auth required, not supported")
        return False
    
    methods = auth_data.get("data", [])
    chain_code = None
    for method in methods:
        if method.get("moduleCode") == "userAndPwd":
            chain_code = method.get("authChainCode")
            logger.info(f"Found userAndPwd auth method, chainCode: {chain_code}")
            break
    
    if not chain_code:
        logger.error(f"No userAndPwd auth method found. Methods: {methods}")
        return False
    
    # Step 4: RSA 加密密码并登录
    logger.info("Step 4: authExecute")
    encrypted_password = _rsa_encrypt(password, pub_key)
    
    resp = await client.post(
        f"https://{ID_HOST}/idp/authn/authExecute",
        json={
            "authModuleCode": "userAndPwd",
            "authChainCode": chain_code,
            "entityId": entity_id,
            "requestType": "chain_type",
            "lck": lck,
            "authPara": {
                "loginName": student_id,
                "password": encrypted_password,
                "verifyCode": "",
            },
        },
    )
    
    login_result = resp.json()
    logger.info(f"authExecute response: code={login_result.get('code')}, message={login_result.get('message')}")
    
    message = login_result.get("message", "")
    if "验证码" in message:
        logger.warning("Captcha required")
        return False
    if login_result.get("code") != 200:
        logger.warning(f"Login failed: code={login_result.get('code')}, message={message}")
        return False
    
    login_token = login_result.get("loginToken")
    if not login_token:
        logger.error("No loginToken in response")
        return False
    logger.info(f"Got loginToken: {login_token[:20]}...")
    
    # Step 5: 提交 loginToken
    logger.info("Step 5: authnEngine")
    resp = await client.post(
        f"https://{ID_HOST}/idp/authCenter/authnEngine",
        data={"loginToken": login_token},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    logger.info(f"authnEngine status: {resp.status_code}, length: {len(resp.text)}")
    
    # Step 6: 从页面中提取 ticket
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(resp.text, "html.parser")
    
    logon_form = soup.find(id="logon")
    ticket_input = soup.find(id="ticket")
    
    if not logon_form or not ticket_input:
        # 尝试其他方式
        logger.warning("Could not find logon form or ticket input")
        logger.info(f"Page sample: {resp.text[:500]}")
        return False
    
    submit_action = logon_form.get("action", "")
    ticket_value = ticket_input.get("value", "")
    logger.info(f"Form action: {submit_action[:100]}, ticket: {ticket_value[:20]}...")
    
    if not submit_action or not ticket_value:
        return False
    
    if "?" in submit_action:
        ticket_url = f"{submit_action}&ticket={ticket_value}"
    else:
        ticket_url = f"{submit_action}?ticket={ticket_value}"
    
    logger.info(f"Step 6: GET ticket URL: {ticket_url[:100]}")
    await client.get(ticket_url, follow_redirects=True)
    logger.info("Authentication completed successfully")
    
    return True


async def connect_fudan(
    db: AsyncSession, user_id: uuid.UUID, student_id: str, password: str
) -> dict:
    """
    连接复旦教务系统：
    1. 用学号密码通过 id.fudan.edu.cn CAS 认证
    2. 访问课表页面触发 SSO 跳转，获取 fdjwgl 域的 cookie
    3. 保存 Cookie 和加密密码
    """
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        try:
            login_ok = await _fudan_authenticate(
                client, student_id, password, COURSE_TABLE_URL
            )
            if not login_ok:
                return {"success": False, "message": "登录失败，请检查学号或密码"}
        except Exception as e:
            logger.exception("Connection error")
            return {"success": False, "message": f"连接复旦服务器失败: {str(e)}"}

        # 认证通过后，再访问课表页面完成 SSO 跳转
        # 这样 fdjwgl.fudan.edu.cn 才会设置会话 cookie
        try:
            logger.info("Completing SSO redirect by accessing course table page...")
            sso_resp = await client.get(COURSE_TABLE_URL, follow_redirects=True)
            logger.info(f"SSO redirect completed: {sso_resp.status_code} -> {sso_resp.url}")
            logger.info(f"After SSO: domain cookies = {[c.domain for c in client.cookies.jar]}")
        except Exception as e:
            logger.warning(f"SSO redirect failed but may still work: {e}")

        # 提取 Cookie
        cookies_dict = {}
        for cookie in client.cookies.jar:
            domain = cookie.domain or ""
            path = cookie.path or "/"
            if domain not in cookies_dict:
                cookies_dict[domain] = {}
            if path not in cookies_dict[domain]:
                cookies_dict[domain][path] = {}
            cookies_dict[domain][path][cookie.name] = cookie.value
        
        cookie_str = json.dumps(cookies_dict) if cookies_dict else ""
        logger.info(f"Saved cookies for domains: {list(cookies_dict.keys())}")

    encrypted_pwd = encrypt_api_key(password)
    encrypted_cookies = encrypt_api_key(cookie_str) if cookie_str else None

    existing = await get_credential(db, user_id)
    if existing:
        existing.student_id = student_id
        existing.encrypted_password = encrypted_pwd
        existing.cookies = encrypted_cookies
        existing.is_active = True
    else:
        credential = FudanCredential(
            user_id=user_id,
            student_id=student_id,
            encrypted_password=encrypted_pwd,
            cookies=encrypted_cookies,
            is_active=True,
        )
        db.add(credential)

    await db.flush()
    return {"success": True, "message": "复旦教务系统连接成功"}


async def _get_client(credential: FudanCredential) -> httpx.AsyncClient | None:
    """用保存的 Cookie 创建 httpx 客户端"""
    if not credential.cookies:
        return None

    try:
        cookie_str = decrypt_api_key(credential.cookies)
        cookies = json.loads(cookie_str)
    except Exception:
        return None

    client = httpx.AsyncClient(timeout=30.0, verify=False, follow_redirects=True)

    for domain, paths in cookies.items():
        for path, cookie_dict in paths.items():
            for name, value in cookie_dict.items():
                client.cookies.set(name, value, domain=domain, path=path)

    return client


async def _ensure_sso_session(client: httpx.AsyncClient, target_url: str) -> bool:
    """确保当前 session 能正常访问教务页面（自动完成 SSO ticket 跳转）"""
    try:
        resp = await client.get(target_url, follow_redirects=True)
        # 如果被重定向到 logon 页面，说明需要 SSO ticket 跳转
        if "logon" in resp.text[:300].lower() or 'authenticate' in str(resp.url).lower():
            import re
            ticket_match = re.search(r'ticket=([^"&\s]+)', resp.text)
            if ticket_match:
                ticket = ticket_match.group(1)
                # 提取 refer URL
                refer_match = re.search(r'refer=([^&\s]+)', resp.text)
                refer = refer_match.group(1) if refer_match else target_url
                sso_url = f"https://fdjwgl.fudan.edu.cn/student/sso/login?refer={refer}&ticket={ticket}"
                logger.info(f"Following SSO ticket: {sso_url[:80]}...")
                await client.get(sso_url, follow_redirects=True)
                return True
            return False
        return True
    except Exception as e:
        logger.warning(f"SSO check failed: {e}")
        return False


async def _fetch_lessons(client: httpx.AsyncClient) -> list[dict]:
    """通过 JSON API 获取课程列表和考试信息"""
    import re
    
    # 先访问课表页面获取 semesterId 和 studentId
    resp = await client.get(COURSE_TABLE_URL, follow_redirects=True)
    
    # 从 select option 中提取学期ID
    sem_options = re.findall(r'<option\s+value="(\d+)"[^>]*>([^<]+)</option>', resp.text)
    sid_match = re.search(r'studentIds\s*=\s*\[(\d+)\]', resp.text)
    
    semester_id = None
    for val, name in sem_options:
        if '暑' not in name:
            semester_id = int(val)
            break
    if not semester_id and sem_options:
        semester_id = int(sem_options[0][0])
    
    student_id = sid_match.group(1) if sid_match else ""
    if not semester_id or not student_id:
        logger.error(f"Cannot find semester={semester_id} or studentId={student_id}")
        return []
    
    # 调用 getLesson API 获取课程
    lesson_url = f"{COURSE_TABLE_URL}/getLesson"
    resp = await client.get(lesson_url, params={"semesterId": semester_id, "studentId": student_id})
    if resp.status_code != 200:
        logger.warning(f"getLesson API returned {resp.status_code}")
        return []
    
    data = resp.json()
    lessons = data.get("lessons", [])
    teacher_map = data.get("teacherMap", {})
    
    result = []
    for lesson in lessons:
        course = lesson.get("course", {})
        lesson_id = str(lesson.get("id", ""))
        result.append({
            "title": course.get("nameZh", ""),
            "code": lesson.get("code", ""),
            "credits": course.get("credits", 0),
            "teacher": teacher_map.get(lesson_id, ""),
            "exam_start": lesson.get("examStartDate", ""),
            "exam_end": lesson.get("examEndDate", ""),
            "exam_mode": lesson.get("examMode", {}).get("nameZh", ""),
            "remark": lesson.get("remark", ""),
        })
    
    logger.info(f"Fetched {len(result)} lessons from JSON API")
    return result


async def _fetch_exams(client: httpx.AsyncClient) -> list[dict]:
    """从考试页面 HTML 解析考试安排"""
    from bs4 import BeautifulSoup
    
    resp = await client.get(EXAM_ARRANGE_URL, follow_redirects=True)
    if "logon" in resp.text[:300].lower():
        import re
        t = re.search(r'ticket=([^"&\s]+)', resp.text)
        if t:
            await client.get(
                f"https://fdjwgl.fudan.edu.cn/student/sso/login?refer=https://fdjwgl.fudan.edu.cn/student/for-std/exam-arrange/&ticket={t.group(1)}",
                follow_redirects=True,
            )
            resp = await client.get(EXAM_ARRANGE_URL, follow_redirects=True)
    
    soup = BeautifulSoup(resp.text, "html.parser")
    exams = []
    
    # 查找考试行
    exam_rows = soup.find_all("tr", class_=lambda c: c and "exam-row" in c)
    if not exam_rows:
        # 备用查找
        exam_rows = soup.select("tr[data-finished]")
    
    for row in exam_rows:
        try:
            title_cell = row.find("td", attrs={"data-label": "课程信息"})
            time_cell = row.find("td", attrs={"data-label": "考试信息"})
            venue_cell = row.find("td", attrs={"data-label": "场地信息"})
            
            if not title_cell:
                continue
            
            # 提取课程名称
            title_span = title_cell.find("span", style=lambda s: s and "font-weight: bold" in s and "14px" in s)
            if not title_span:
                title_span = title_cell.find_all("span")
                title = title_span[0].get_text(strip=True) if title_span else ""
            else:
                title = title_span.get_text(strip=True)
            
            # 提取考试时间
            time_text = ""
            if time_cell:
                time_div = time_cell.find("div", class_="time")
                if time_div:
                    time_text = time_div.get_text(strip=True)
                else:
                    time_text = time_cell.get_text(strip=True)
            
            # 提取场地
            location = ""
            if venue_cell:
                venue_spans = venue_cell.find_all("span")
                location_parts = []
                for s in venue_spans:
                    if s.get("id") and "seat" in (s.get("id", "")):
                        continue
                    txt = s.get_text(strip=True)
                    if txt and txt != "--":
                        location_parts.append(txt)
                location = " ".join(location_parts)
            
            if title:
                exams.append({
                    "title": title.strip(),
                    "time_text": time_text,
                    "location": location,
                })
        except Exception as e:
            logger.warning(f"Failed to parse exam row: {e}")
            continue
    
    logger.info(f"Parsed {len(exams)} exams from HTML")
    return exams


async def _fetch_course_schedules(client: httpx.AsyncClient) -> list[dict]:
    """获取课表排课信息（每周几、节次、地点）"""
    import re
    import json
    
    resp = await client.get(COURSE_TABLE_URL, follow_redirects=True)
    
    # 提取 semester 和 student info
    sem_match = re.search(r'semesters\s*=\s*JSON\.parse\(\s*\'(.+?)\'\)', resp.text, re.DOTALL)
    sid_match = re.search(r'studentIds\s*=\s*\[(\d+)\]', resp.text)
    pid_match = re.search(r'personId\s*=\s*(\d+)', resp.text)
    
    if sem_match:
        escaped = sem_match.group(1).replace('\\"', '"')
        all_sems = json.loads(escaped)
        semester_id = None
        for s in all_sems:
            if '暑' not in s.get('name', ''):
                semester_id = s['id']
                break
        if not semester_id:
            semester_id = all_sems[0]['id']
    else:
        semester_id = 527
    student_id = sid_match.group(1) if sid_match else ""
    person_id = pid_match.group(1) if pid_match else ""
    
    # 通过 getLesson API 获取课程列表
    lesson_url = f"{COURSE_TABLE_URL}/getLesson"
    resp = await client.get(lesson_url, params={"semesterId": semester_id, "studentId": student_id})
    if resp.status_code != 200:
        return []
    
    data = resp.json()
    lessons = data.get("lessons", [])
    teacher_map = data.get("teacherMap", {})
    
    # 从课表页面 JS 中的 all-courses or schedule-table 数据提取排课信息
    # 打印页面获取 schedule-table JS
    print_page = await client.get(f"{COURSE_TABLE_URL}/print", params={"semesterId": semester_id})
    # 试试 print 页面是否有排课表格
    print_text = print_page.text if print_page.status_code == 200 else ""
    
    schedules = []
    
    # 从 print-data API 获取课表时间安排
    try:
        draw_url = "https://fdjwgl.fudan.edu.cn/ws/schedule-table/draw-table-data"
        body = {
            "semesterId": semester_id,
            "studentIds": [int(student_id)] if student_id else [485841],
            "bizTypeId": 2,
            "type": "student",
            "personId": int(person_id) if person_id else 552824,
        }
        draw_resp = await client.post(draw_url, json=body)
        if draw_resp.status_code == 200 and len(draw_resp.text) > 20:
            draw_data = draw_resp.json()
            # 记录返回结构
            logger.info(f"Draw API returned type: {type(draw_data).__name__}")
            logger.info(f"Draw API keys: {list(draw_data.keys()) if isinstance(draw_data, dict) else 'N/A'}")
    except Exception as e:
        logger.warning(f"Draw-table-data API failed: {e}")
    
    # 从课表页面 JS 中提取排课信息的脚本
    # 将 lessons 信息与 teacher 结合返回
    for lesson in lessons:
        lesson_id = str(lesson.get("id", ""))
        course = lesson.get("course", {})
        schedules.append({
            "title": course.get("nameZh", ""),
            "code": lesson.get("code", ""),
            "teacher": teacher_map.get(lesson_id, ""),
            "credits": course.get("credits", 0),
            "lesson_id": lesson_id,
        })
    
    return schedules


def _parse_semester_start_date(page_html: str) -> str | None:
    """
    从课表页面的 JS 中解析学期 startDate。
    页面中 JS 格式: var semesters = JSON.parse('[{...}]');
    
    Returns:
        "YYYY-MM-DD" 格式的周一日期，或 None
    """
    import re, json, ast
    
    # 查找所有 startDate 和 id 出现的位置，直接匹配日期
    # 页面中的格式通常是: ...startDate:"2026-09-06"...
    # 无论是否转义，日期格式 YYYY-MM-DD 是唯一的
    date_pattern = r'(?:startDate)[=:]\s*["\']?(\d{4}-\d{2}-\d{2})["\']?'
    id_pattern = r'(?:id)[=:]\s*["\']?(\d+)["\']?'
    
    # 提取所有可能的学期数据
    dates = re.findall(r'"startDate"\s*:\s*"(\d{4}-\d{2}-\d{2})"', page_html)
    ids = re.findall(r'"id"\s*:\s*(\d+)', page_html)
    
    # 如果常规格式没找到，尝试转义格式 \\"startDate\\":\\"2026-09-06\\"
    if not dates:
        dates = re.findall(r'\\"startDate\\"\s*:\s*\\"(\d{4}-\d{2}-\d{2})\\"', page_html)
        ids = re.findall(r'\\"id\\"\s*:\s*(\d+)', page_html)
    
    # 如果还没找到，尝试更宽松的匹配
    if not dates:
        dates = re.findall(r'startDate["\':]+\s*["\']*(\d{4}-\d{2}-\d{2})', page_html)
        ids = re.findall(r'"id"\s*[=:]\s*["\']*(\d+)', page_html)
        if not ids:
            ids = re.findall(r'\\"id\\"\s*[=:]\s*["\']*(\d+)', page_html)
    
    if not dates:
        return None
    
    # 选择非暑期学期
    sem_options = re.findall(r'<option\s+value="(\d+)"[^>]*>([^<]+)</option>', page_html)
    selected_id = None
    for val, name in sem_options:
        if '暑' not in name:
            selected_id = val
            break
    if not selected_id and sem_options:
        selected_id = sem_options[0][0]
    
    # 匹配 startDate 到选中学期
    start_date_str = None
    if selected_id and len(dates) == len(ids):
        for i, sid in enumerate(ids):
            if sid == selected_id and i < len(dates):
                start_date_str = dates[i]
                break
    
    if not start_date_str and dates:
        # 保守起见，取最早的日期（秋季学期通常早于春季）
        start_date_str = dates[0] if dates else None
    
    if start_date_str:
        from datetime import datetime, timedelta
        try:
            dt = datetime.strptime(start_date_str, "%Y-%m-%d")
            dt += timedelta(days=1)  # 周日 → 周一
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return start_date_str
    return None


async def _do_sso_and_fetch(client: httpx.AsyncClient) -> tuple[list, list, list, list, str]:
    """
    执行 SSO 重连并获取所有数据
    返回: (lessons, html_exams, lesson_exams, schedules, semester_start_date)
    schedules 包含真正的排课数据: {title, weekday, weeks, start_unit, end_unit, location, teacher, code}
    """
    import re, json
    
    # Step 1: 先做 SSO 重连
    sso_ok = await _ensure_sso_session(client, COURSE_TABLE_URL)
    logger.info(f"SSO result: {sso_ok}")
    
    # Step 2: 访问课表页面一次，提取 semesterId、studentId、personId 和学期名称
    try:
        resp = await client.get(COURSE_TABLE_URL, follow_redirects=True)
        logger.info(f"Course page response: {resp.status_code}, size={len(resp.text)}, url={resp.url}")
    except Exception as e:
        logger.warning(f"Failed to load course page: {type(e).__name__}: {e}")
        # 如果课表页面都无法访问，直接返回空结果
        return [], [], [], [], ""
    logger.info(f"Course page size: {len(resp.text)}, logon={'logon' in resp.text[:300].lower()}")
    
    # 从页面 JS 中解析学期开始日期（精确到具体日期）
    semester_start_date = _parse_semester_start_date(resp.text)
    logger.info(f"Semester start date from page: {semester_start_date}")
    
    # 从 select option 中提取学期ID（格式 <option value="527">2026-2027学年1学期</option>）
    sem_options = re.findall(r'<option\s+value="(\d+)"[^>]*>([^<]+)</option>', resp.text)
    sid_match = re.search(r'studentIds\s*=\s*\[(\d+)\]', resp.text)
    pid_match = re.search(r'personId\s*=\s*(\d+)', resp.text)
    
    semester_id = None
    semester_name = ""
    student_id = ""
    person_id = ""
    
    # 选第一个非暑期的学期
    if sem_options:
        for val, name in sem_options:
            if '暑' not in name:
                semester_id = int(val)
                semester_name = name
                break
        if not semester_id and sem_options:
            semester_id = int(sem_options[0][0])
            semester_name = sem_options[0][1]
        logger.info(f"Found semester: id={semester_id}, name={semester_name}")
    
    if sid_match:
        student_id = sid_match.group(1)
        logger.info(f"Found studentId: {student_id}")
    if pid_match:
        person_id = pid_match.group(1)
        logger.info(f"Found personId: {person_id}")
    
    # Step 3: 调用 JSON API 获取课程列表和考试信息
    lessons = []
    lesson_exams = []
    raw_lessons = []
    teacher_map = {}
    
    if semester_id and student_id:
        lesson_url = f"{COURSE_TABLE_URL}/getLesson"
        jresp = await client.get(lesson_url, params={"semesterId": semester_id, "studentId": student_id})
        logger.info(f"getLesson API: {jresp.status_code}, size={len(jresp.text)}")
        
        if jresp.status_code == 200:
            data = jresp.json()
            raw_lessons = data.get("lessons", [])
            teacher_map = data.get("teacherMap", {})
            
            for l in raw_lessons:
                course = l.get("course", {})
                lid = str(l.get("id", ""))
                lessons.append({
                    "title": course.get("nameZh", ""),
                    "code": l.get("code", ""),
                    "teacher": teacher_map.get(lid, ""),
                })
                # 提取考试信息
                es = l.get("examStartDate", "")
                ee = l.get("examEndDate", "")
                if es and ee:
                    lesson_exams.append({
                        "title": course.get("nameZh", ""),
                        "start": es,
                        "end": ee,
                        "exam_mode": l.get("examMode", {}).get("nameZh", ""),
                    })
            
            logger.info(f"Fetched {len(lessons)} lessons, {len(lesson_exams)} exams from JSON API")
    
    # Step 4: 获取考试 HTML
    html_exams = await _fetch_exams(client)
    
    # Step 5: 通过 print-data API 获取真正的排课数据
    schedules = []
    if semester_id and student_id:
        # 构建 lesson_map
        lesson_map = {}
        for l in raw_lessons:
            lid = str(l.get("id", ""))
            course = l.get("course", {})
            lesson_map[lid] = {
                "title": course.get("nameZh", ""),
                "code": l.get("code", ""),
                "teacher": teacher_map.get(lid, ""),
            }
        
        try:
            print_data_url = PRINT_DATA_URL.replace("{sem_id}", str(semester_id))
            logger.info(f"Calling print-data API: {print_data_url}")
            print_resp = await client.get(print_data_url, follow_redirects=True)
            
            if print_resp.status_code == 200 and len(print_resp.text) > 20:
                print_data = print_resp.json()
                schedules = parse_print_data_schedules(print_data, lesson_map)
                logger.info(f"Parsed {len(schedules)} schedule entries from print-data API")
                # 注入 semester_name 和 semester_start_date
                for s in schedules:
                    s["semester_name"] = semester_name
                    if semester_start_date:
                        s["semester_start_date"] = semester_start_date
            else:
                logger.warning(f"Print-data API returned {print_resp.status_code}")
        except Exception as e:
            logger.warning(f"Print-data API failed: {type(e).__name__}: {e}")
    
    # 如果 print-data API 没拿到数据，fallback 到旧方式
    if not schedules:
        schedules = lessons
        logger.info(f"Falling back to simple lesson list ({len(schedules)} items)")
    
    return lessons, html_exams, lesson_exams, schedules, semester_start_date or ""


async def sync_fudan_data(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """同步复旦教务数据（使用 JSON API + HTML 混合方式）"""
    credential = await get_credential(db, user_id)
    if not credential:
        return {'success': False, 'message': '未连接复旦教务，请先在设置中配置'}

    client = await _get_client(credential)
    if not client:
        return {'success': False, 'message': '登录凭证已过期，请重新连接'}

    result = {
        'events_created': 0,
        'events_updated': 0,
        'tasks_created': 0,
        'tasks_updated': 0,
        'errors': [],
    }

    try:
        # 执行 SSO 重连并获取数据
        lessons, html_exams, lesson_exams, schedules, semester_start_date = await _do_sso_and_fetch(client)
        
        # 更新 cookies (可能 SSO 重连产生了新 cookie)
        try:
            new_cookies = {}
            for cookie in client.cookies.jar:
                domain = cookie.domain or ""
                path = cookie.path or "/"
                if domain not in new_cookies:
                    new_cookies[domain] = {}
                if path not in new_cookies[domain]:
                    new_cookies[domain][path] = {}
                new_cookies[domain][path][cookie.name] = cookie.value
            if new_cookies:
                credential.cookies = encrypt_api_key(json.dumps(new_cookies))
                logger.info(f"Updated cookies for domains: {list(new_cookies.keys())}")
        except Exception as e:
            logger.warning(f"Failed to update cookies: {e}")

        logger.info(f"Got lessons={len(lessons)}, html_exams={len(html_exams)}, lesson_exams={len(lesson_exams)}, schedules={len(schedules)}")

        # 导入课程信息 → 日程
        for schedule in schedules:
            try:
                await _upsert_course_event(db, user_id, schedule)
                result['events_created'] += 1
            except Exception as e:
                result['errors'].append(f"课程导入失败: {schedule.get('title', '未知')} - {str(e)}")

        # 导入考试信息（从 getLesson API 中提取）
        for exam in lesson_exams:
            try:
                record = {
                    "title": exam["title"],
                    "date": exam["start"][:10],
                    "time_range": f"{exam['start'][11:16]}-{exam['end'][11:16]}",
                    "location": exam.get("exam_mode", ""),
                }
                await _upsert_exam_event(db, user_id, record)
                result['events_created'] += 1
            except Exception as e:
                result['errors'].append(f"考试导入失败: {exam.get('title', '未知')} - {str(e)}")

        # 导入 HTML 解析的考试
        import re as _re_import
        for exam in html_exams:
            try:
                record = {"title": exam["title"], "time_text": exam.get("time_text", ""), "location": exam.get("location", "")}
                date_match = _re_import.search(r'(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})', exam.get("time_text", ""))
                time_match = _re_import.search(r'(\d{2}:\d{2})~(\d{2}:\d{2})', exam.get("time_text", ""))
                if date_match:
                    date_str = date_match.group(1).replace("/", "-").replace(".", "-")
                    if time_match:
                        record["date"] = date_str
                        record["time_range"] = f"{time_match.group(1)}-{time_match.group(2)}"
                    else:
                        record["date"] = date_str
                    await _upsert_exam_event(db, user_id, record)
                    result['events_created'] += 1
            except Exception as e:
                result['errors'].append(f"考试导入失败: {exam.get('title', '未知')} - {str(e)}")

    finally:
        await client.aclose()

    credential.last_sync_at = datetime.now(timezone.utc)
    logger.info(f"Sync completed: {result['events_created']} events, {result['tasks_created']} tasks")
    await db.commit()

    return {
        'success': True,
        'data': result,
        'message': f"同步完成：导入 {result['events_created']} 个日程，{result['tasks_created']} 个待办",
    }


async def _upsert_course_event(db: AsyncSession, user_id: uuid.UUID, course: dict):
    """
    课程 → 日程
    
    使用 title + weekday + start_unit 做唯一匹配，
    因为同一课程可能有多个时间槽（如数据结构：周一11-13节 + 周二1-2节）。
    
    支持两种格式：
    1. 从 print-data API 获取的格式: {title, weekday(int), weeks(str), start_unit, end_unit, location, teacher, code, semester_start_date}
    2. 旧格式 (HTML 解析): {title, weekday(str), weeks(str), period(str), location, teacher}
    """
    title = course.get('title', '')
    if not title:
        return

    # 检测是哪种格式
    weekday_raw = course.get('weekday')
    start_unit = course.get('start_unit')
    end_unit = course.get('end_unit')
    weeks_str = course.get('weeks', '')
    location = course.get('location', '')
    teacher = course.get('teacher', '')
    
    if isinstance(weekday_raw, int) and start_unit is not None:
        # 新格式：来自 print-data API
        weekday = weekday_raw  # 已经是数字，1=周一
        weeks = parse_weeks(weeks_str)
        # start=第一节课的开始时间, end=最后一节课的结束时间
        start_time_str, _ = unit_to_time(start_unit)
        _, end_time_str = unit_to_time(end_unit)
    else:
        # 旧格式：来自 HTML 解析 / fallback
        weekday = parse_weekday(course.get('weekday', ''))
        weeks = parse_weeks(weeks_str)
        period_str = course.get('period', '')
        start_time_str, end_time_str = period_to_time(period_str)

    # 构建描述
    description_parts = []
    if teacher:
        description_parts.append(f"教师：{teacher}")
    if weeks:
        description_parts.append(f"第 {weeks[0]}-{weeks[-1]} 周")
    if location:
        description_parts.append(f"地点：{location}")
    if weekday:
        description_parts.append(f"每周{get_weekday_name(weekday)}")
    
    # 使用 title + weekday + start_unit 作为唯一标识
    existing_query = await db.execute(
        select(Event).where(
            Event.user_id == user_id,
            Event.source == 'fudan',
            Event.event_type == 'class',
            Event.title == title,
            # 通过 description 包含周几信息来匹配
        ).limit(10)
    )
    existing_events = existing_query.scalars().all()
    
    # 找到完全匹配（同一天 + 同节次）
    existing = None
    for ev in existing_events:
        if ev.start_time:
            ev_weekday = ev.start_time.isoweekday()  # 1=周一
            if ev_weekday == weekday:
                existing = ev
                break

    if weekday and weeks:
        # 有排课信息 - 创建带时间的事件
        try:
            # 优先使用从页面解析的学期开始日期
            semester_start_date = course.get('semester_start_date', '')
            if not semester_start_date:
                semester_name = course.get('semester_name', '')
                computed = compute_semester_start(None, semester_name)
                semester_start_date = computed if computed else "2026-09-01"
            
            first_week = weeks[0]
            
            # 计算起始日期
            from datetime import datetime as dt, timedelta as td
            start_date = dt.strptime(semester_start_date, "%Y-%m-%d")
            # 学期第1周的周一 = semester_start_date
            # 注意：复旦课表从周一开始，semester_start_date 就是第1周周一的日期
            days_off = weekday - 1  # 周一=0
            first_week_base = start_date + td(days=days_off)
            first_date = first_week_base + td(weeks=first_week - 1)
            
            # 解析时间
            start_h, start_m = map(int, start_time_str.split(':'))
            end_h, end_m = map(int, end_time_str.split(':'))
            
            first_start = first_date.replace(hour=start_h, minute=start_m)
            first_end = first_date.replace(hour=end_h, minute=end_m)
            
            # 判断周次是否连续
            is_consecutive = len(weeks) > 1 and all(
                weeks[i] + 1 == weeks[i + 1] for i in range(len(weeks) - 1)
            )
            
            rrule = None
            if is_consecutive and len(weeks) > 1:
                # 使用 RRULE 生成重复事件
                rrule = f"FREQ=WEEKLY;COUNT={len(weeks)};BYDAY={_weekday_to_rrule(weekday)}"
            
            if not existing:
                event = Event(
                    user_id=user_id,
                    title=title,
                    description=' | '.join(description_parts) if description_parts else None,
                    event_type='class',
                    start_time=first_start,
                    end_time=first_end,
                    rrule=rrule,
                    source='fudan',
                    is_all_day=False,
                )
                db.add(event)
                logger.info(f"Created class event: {title} weekday={weekday} start={first_start} rrule={rrule}")
            else:
                existing.description = ' | '.join(description_parts) if description_parts else None
                existing.start_time = first_start
                existing.end_time = first_end
                existing.rrule = rrule
                logger.info(f"Updated class event: {title} weekday={weekday} start={first_start} rrule={rrule}")
        except Exception as e:
            logger.warning(f"Failed to create time-based event for {title} (weekday={weekday}): {e}")
            # fallback: 创建无时间事件
            if not existing:
                event = Event(
                    user_id=user_id,
                    title=title,
                    description=' | '.join(description_parts) if description_parts else None,
                    event_type='class',
                    source='fudan',
                    is_all_day=False,
                )
                db.add(event)
            else:
                existing.description = ' | '.join(description_parts) if description_parts else None
    else:
        # 没有排课信息 - 仅创建基本信息事件
        if not existing:
            event = Event(
                user_id=user_id,
                title=title,
                description=' | '.join(description_parts) if description_parts else None,
                event_type='class',
                source='fudan',
                is_all_day=False,
            )
            db.add(event)
        else:
            existing.description = ' | '.join(description_parts) if description_parts else None


def _weekday_to_rrule(weekday: int) -> str:
    """将 1-7 转换为 RRULE BYDAY"""
    mapping = {1: "MO", 2: "TU", 3: "WE", 4: "TH", 5: "FR", 6: "SA", 7: "SU"}
    return mapping.get(weekday, "MO")


async def _upsert_exam_event(db: AsyncSession, user_id: uuid.UUID, exam: dict):
    """考试 → 日程"""
    title = exam.get('title', '')
    if not title:
        return

    date_str = exam.get('date', '')
    time_range = exam.get('time_range', '')
    location = exam.get('location', '')

    start_time = None
    end_time = None

    if date_str:
        date_clean = date_str.strip().replace('/', '-').replace('.', '-')
        try:
            from datetime import datetime as dt
            if time_range:
                times = time_range.split('-')
                if len(times) == 2:
                    start_time = dt.strptime(f"{date_clean} {times[0].strip()}", "%Y-%m-%d %H:%M")
                    end_time = dt.strptime(f"{date_clean} {times[1].strip()}", "%Y-%m-%d %H:%M")
                else:
                    start_time = dt.strptime(f"{date_clean} 08:00", "%Y-%m-%d %H:%M")
                    end_time = dt.strptime(f"{date_clean} 10:00", "%Y-%m-%d %H:%M")
            else:
                start_time = dt.strptime(f"{date_clean} 08:00", "%Y-%m-%d %H:%M")
                end_time = dt.strptime(f"{date_clean} 10:00", "%Y-%m-%d %H:%M")
        except ValueError:
            pass

    description_parts = []
    if exam.get('seat'):
        description_parts.append(f"座位号：{exam['seat']}")
    if location:
        description_parts.append(f"地点：{location}")
    if exam.get('teacher'):
        description_parts.append(f"教师：{exam['teacher']}")

    existing_query = await db.execute(
        select(Event).where(
            Event.user_id == user_id,
            Event.source == 'fudan',
            Event.title == title,
            Event.event_type == 'exam',
        ).limit(1)
    )
    existing = existing_query.scalar_one_or_none()

    if existing:
        existing.description = ' | '.join(description_parts) if description_parts else None
        if start_time:
            existing.start_time = start_time
            existing.end_time = end_time
    else:
        event = Event(
            user_id=user_id,
            title=title,
            description=' | '.join(description_parts) if description_parts else None,
            event_type='exam',
            start_time=start_time,
            end_time=end_time,
            source='fudan',
            is_all_day=False,
        )
        db.add(event)


async def _upsert_task(db: AsyncSession, user_id: uuid.UUID, task_data: dict):
    """eLearning 作业 → 待办"""
    title = task_data.get('title', '')
    if not title or len(title) < 3:
        return

    deadline_str = task_data.get('deadline')
    deadline = None
    if deadline_str:
        try:
            from datetime import datetime as dt
            deadline = dt.strptime(deadline_str, "%Y-%m-%d")
        except ValueError:
            pass

    course_name = task_data.get('course', '')
    description = f"[{course_name}] {task_data.get('raw_text', '')}" if course_name else task_data.get('raw_text', '')

    existing_query = await db.execute(
        select(Task).where(
            Task.user_id == user_id,
            Task.source == 'fudan',
            Task.title == title[:200],
        ).limit(1)
    )
    existing = existing_query.scalar_one_or_none()

    if existing:
        existing.description = description
        if deadline:
            existing.deadline = deadline
    else:
        task = Task(
            user_id=user_id,
            title=title[:200],
            description=description[:1000] if description else None,
            deadline=deadline,
            priority=1,
            status='todo',
            source='fudan',
        )
        db.add(task)


async def disconnect_fudan(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """断开复旦连接"""
    credential = await get_credential(db, user_id)
    if credential:
        credential.is_active = False
        credential.cookies = None
        await db.flush()
        return True
    return False