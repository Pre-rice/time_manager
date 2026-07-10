"""复旦教务数据解析器（纯规则匹配，无 AI）"""

import re
from datetime import datetime, timedelta

from bs4 import BeautifulSoup, Tag


def parse_course_table(html: str) -> list[dict]:
    """
    解析复旦课表页面 HTML，提取课程信息。
    
    典型课表表格结构：
    | 课程名称 | 教师 | 周次 | 星期 | 节次 | 地点 |
    
    返回列表，每个元素包含课程详情。
    """
    soup = BeautifulSoup(html, 'html.parser')
    courses = []
    
    # 查找课表表格 - 通常是最主要的 <table>
    table = soup.find('table', class_=re.compile(r'course|kb|grid|table', re.I))
    if not table:
        table = soup.find('table')
    if not table:
        return _fallback_table_parse(html, 'course')
    
    rows = table.find_all('tr')
    if not rows:
        return _fallback_table_parse(html, 'course')
    
    # 尝试识别表头
    headers = []
    header_row = rows[0]
    header_cells = header_row.find_all(['th', 'td'])
    for cell in header_cells:
        headers.append(cell.get_text(strip=True).lower())
    
    # 如果没有识别到表头，使用默认格式
    if not any(h in ' '.join(headers) for h in ['课程', '名称', '教师', '星期', '时间']):
        return _fallback_table_parse(html, 'course')
    
    for row in rows[1:]:
        cells = row.find_all('td')
        if len(cells) < 3:
            continue
        
        course = {}
        for i, cell in enumerate(cells):
            if i < len(headers):
                key = headers[i]
                text = cell.get_text(strip=True)
                if '课程' in key or '名称' in key:
                    course['title'] = text
                elif '教师' in key:
                    course['teacher'] = text
                elif '周' in key:
                    course['weeks'] = text
                elif '星期' in key or '星' in key:
                    course['weekday'] = text
                elif '节' in key or '时间' in key:
                    course['period'] = text
                elif '地点' in key or '教室' in key:
                    course['location'] = text
        
        if course.get('title'):
            courses.append(course)
    
    return courses


def parse_exam_table(html: str) -> list[dict]:
    """
    解析复旦考试安排页面 HTML，提取考试信息。
    
    典型考试表格结构：
    | 课程名称 | 考试日期 | 考试时间 | 地点 | 座位号 |
    """
    soup = BeautifulSoup(html, 'html.parser')
    exams = []
    
    table = soup.find('table', class_=re.compile(r'exam|grid|table', re.I))
    if not table:
        table = soup.find('table')
    if not table:
        return _fallback_table_parse(html, 'exam')
    
    rows = table.find_all('tr')
    if not rows:
        return _fallback_table_parse(html, 'exam')
    
    headers = []
    for cell in rows[0].find_all(['th', 'td']):
        headers.append(cell.get_text(strip=True).lower())
    
    if not any(h in ' '.join(headers) for h in ['课程', '考试', '日期', '时间']):
        return _fallback_table_parse(html, 'exam')
    
    for row in rows[1:]:
        cells = row.find_all('td')
        if len(cells) < 3:
            continue
        
        exam = {}
        for i, cell in enumerate(cells):
            if i < len(headers):
                key = headers[i]
                text = cell.get_text(strip=True)
                if '课程' in key or '名称' in key:
                    exam['title'] = text
                elif '日期' in key:
                    exam['date'] = text
                elif '时间' in key:
                    exam['time_range'] = text
                elif '地点' in key or '教室' in key:
                    exam['location'] = text
                elif '座位' in key:
                    exam['seat'] = text
        
        if exam.get('title'):
            exams.append(exam)
    
    return exams


def parse_elearning_tasks(html: str) -> list[dict]:
    """
    解析 eLearning 页面 HTML，提取作业/任务信息。
    
    典型 elearning 页面包含任务卡片或表格。
    """
    soup = BeautifulSoup(html, 'html.parser')
    tasks = []
    
    # 尝试多种可能的选择器
    task_elements = []
    
    # 尝试找到任务列表容器
    containers = soup.find_all(['div', 'ul'], class_=re.compile(
        r'task|assignment|homework|todo|job|work', re.I
    ))
    for container in containers:
        items = container.find_all(['li', 'div'], recursive=False)
        task_elements.extend(items)
    
    # 如果没找到，尝试直接找所有 <li> 或卡片元素
    if not task_elements:
        cards = soup.find_all(['div', 'li'], class_=re.compile(
            r'item|card|entry|row|block', re.I
        ))
        task_elements = cards
    
    for elem in task_elements:
        text = elem.get_text(strip=True)
        if len(text) < 5:
            continue
        
        task = {
            'title': text[:100],  # 截断过长的文本
            'raw_text': text,
        }
        
        # 尝试提取截止日期
        date_patterns = [
            r'截止[日期]?[：:]\s*(\d{4}[-/.]?\d{1,2}[-/.]?\d{1,2})',
            r'ddl[：:]\s*(\d{4}[-/.]?\d{1,2}[-/.]?\d{1,2})',
            r'deadline[：:]\s*(\d{4}[-/.]?\d{1,2}[-/.]?\d{1,2})',
            r'(\d{4}[-/.]?\d{1,2}[-/.]?\d{1,2})\s*(?:截止|前|之前)',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                task['deadline'] = match.group(1).replace('/', '-').replace('.', '-')
                break
        
        # 尝试提取课程名称（通常以 "【xxx】" 或 "[xxx]" 开头）
        course_match = re.search(r'[\[【](.+?)[\]】]', text)
        if course_match:
            task['course'] = course_match.group(1)
        
        tasks.append(task)
    
    return tasks


def _fallback_table_parse(html: str, data_type: str = 'course') -> list[dict]:
    """
    备用解析：当标准表格解析失败时，尝试从所有 <table> 中提取数据。
    这是最后的兜底方案。
    """
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            text = ' '.join(c.get_text(strip=True) for c in cells)
            if len(text) < 10:
                continue
            
            item = {'raw': text, 'cells': [c.get_text(strip=True) for c in cells]}
            
            if data_type == 'course':
                if any(kw in text for kw in ['课程', '星期', '节次', '教室']):
                    item['type'] = 'course'
                    item['title'] = cells[0].get_text(strip=True) if cells else text
            elif data_type == 'exam':
                if any(kw in text for kw in ['考试', '日期', '考场']):
                    item['type'] = 'exam'
                    item['title'] = cells[0].get_text(strip=True) if cells else text
            
            if text not in [r.get('raw', '') for r in results]:
                results.append(item)
    
    return results


def parse_fudan_data(html: str, data_type: str) -> list[dict]:
    """
    统一入口：根据 data_type 选择对应的解析器。
    
    Args:
        html: 页面原始 HTML
        data_type: 'course' | 'exam' | 'elearning'
    
    Returns:
        解析后的结构化数据列表
    """
    if data_type == 'course':
        return parse_course_table(html)
    elif data_type == 'exam':
        return parse_exam_table(html)
    elif data_type == 'elearning':
        return parse_elearning_tasks(html)
    return []


def parse_schedule_from_draw_data(draw_data: dict, lesson_map: dict) -> list[dict]:
    """
    解析 draw-table-data API 返回的课表排课数据。
    （已废弃，保留兼容）
    """
    schedules = []
    lesson_plans = draw_data.get("lessonPlanList", [])
    if not lesson_plans:
        result = draw_data.get("result", [])
        if result:
            schedules = _parse_result_format(result, lesson_map)
            if schedules:
                return schedules
        for key in ("lessons", "gridList", "data", "items"):
            items = draw_data.get(key, [])
            if items:
                schedules = _parse_result_format(items, lesson_map)
                if schedules:
                    return schedules
        if isinstance(draw_data, list):
            schedules = _parse_result_format(draw_data, lesson_map)
            if schedules:
                return schedules
        return schedules
    
    for plan in lesson_plans:
        title = plan.get("courseName", "") or lesson_map.get(str(plan.get("lessonId", "")), {}).get("title", "")
        teacher = plan.get("teacherName", "") or plan.get("teacher", "") or lesson_map.get(str(plan.get("lessonId", "")), {}).get("teacher", "")
        code = plan.get("courseCode", "") or lesson_map.get(str(plan.get("lessonId", "")), {}).get("code", "")
        
        schedule_list = plan.get("scheduleList", []) or plan.get("schedules", []) or plan.get("scheduleItems", [])
        for entry in schedule_list:
            weekday = entry.get("weekDay") or entry.get("weekday")
            start_unit = entry.get("startUnit") or entry.get("startTime") or entry.get("start")
            end_unit = entry.get("endUnit") or entry.get("endTime") or entry.get("end")
            weeks_str = entry.get("weekPeriod") or entry.get("weeks") or entry.get("weekDescription") or ""
            location = entry.get("classRoomName") or entry.get("classroom") or entry.get("location") or ""
            
            if weekday is None:
                continue
            
            schedules.append({
                "title": title,
                "code": code,
                "teacher": teacher,
                "weekday": int(weekday),
                "weeks": weeks_str,
                "start_unit": int(start_unit) if start_unit is not None else None,
                "end_unit": int(end_unit) if end_unit is not None else None,
                "location": location,
            })
    
    return schedules


def _parse_result_format(items: list, lesson_map: dict) -> list[dict]:
    """解析 result / lessons 格式的排课数据"""
    schedules = []
    
    for item in items:
        title = item.get("courseName", "") or item.get("title", "") or item.get("name", "")
        teacher = item.get("teacherName", "") or item.get("teacher", "") or item.get("teacherName", "")
        code = item.get("courseCode", "") or item.get("code", "")
        
        lesson_id = item.get("lessonId") or item.get("id")
        if not title and lesson_id:
            lesson_info = lesson_map.get(str(lesson_id), {})
            title = lesson_info.get("title", "")
            if not teacher:
                teacher = lesson_info.get("teacher", "")
            if not code:
                code = lesson_info.get("code", "")
        
        if not title:
            continue
        
        schedule_entries = (
            item.get("scheduleList", [])
            or item.get("schedules", [])
            or item.get("scheduleItems", [])
            or item.get("gridList", [])
        )
        
        if not schedule_entries:
            weekday = item.get("weekDay") or item.get("weekday") or item.get("week")
            start_unit = item.get("startUnit") or item.get("startTime") or item.get("startUnit") or item.get("start")
            end_unit = item.get("endUnit") or item.get("endTime") or item.get("end")
            weeks_str = item.get("weekPeriod") or item.get("weeks") or item.get("weekDescription") or ""
            location = item.get("classRoomName") or item.get("classroom") or item.get("location") or ""
            
            if weekday is not None:
                schedules.append({
                    "title": title,
                    "code": code,
                    "teacher": teacher,
                    "weekday": int(weekday),
                    "weeks": weeks_str,
                    "start_unit": int(start_unit) if start_unit is not None else None,
                    "end_unit": int(end_unit) if end_unit is not None else None,
                    "location": location,
                })
        else:
            for entry in schedule_entries:
                weekday = entry.get("weekDay") or entry.get("weekday") or entry.get("week")
                start_unit = entry.get("startUnit") or entry.get("startTime") or entry.get("start")
                end_unit = entry.get("endUnit") or entry.get("endTime") or entry.get("end")
                weeks_str = entry.get("weekPeriod") or entry.get("weeks") or entry.get("weekDescription") or ""
                location = entry.get("classRoomName") or entry.get("classroom") or entry.get("location") or ""
                
                if weekday is None:
                    continue
                
                schedules.append({
                    "title": title,
                    "code": code,
                    "teacher": teacher,
                    "weekday": int(weekday),
                    "weeks": weeks_str,
                    "start_unit": int(start_unit) if start_unit is not None else None,
                    "end_unit": int(end_unit) if end_unit is not None else None,
                    "location": location,
                })
    
    return schedules


def parse_print_data_schedules(print_data: dict, lesson_map: dict) -> list[dict]:
    """
    解析 print-data API 返回的课表排课数据。
    按 (lessonId, weekday, startUnit, endUnit) 分组，
    合并周次、地点、教师信息。
    
    weekday 映射规则：
    复旦教务系统 weekday: 1=周一, 2=周二, ..., 7=周日
    → 直接使用
    
    Args:
        print_data: print-data API 返回的 JSON dict
        lesson_map: { lesson_id: { title, code, teacher, ... } }
    
    Returns:
        排课条目列表
        { title, code, teacher, weekday, weeks_str, start_unit, end_unit, location }
    """
    import logging
    logger = logging.getLogger(__name__)
    
    student_tables = print_data.get("studentTableVms", [])
    if not student_tables:
        logger.warning("No studentTableVms in print-data response")
        return []
    
    # key: (lesson_id, weekday, start_unit, end_unit) → merged entry
    group_map = {}
    
    for table in student_tables:
        activities = table.get("activities", [])
        for activity in activities:
            course_name = activity.get("courseName", "")
            lesson_id = str(activity.get("lessonId", ""))
            
            lesson_info = lesson_map.get(lesson_id, {})
            title = course_name or lesson_info.get("title", "")
            if not title:
                continue
            
            teacher_list = activity.get("teachers", [])
            code = activity.get("lessonCode", "") or lesson_info.get("code", "")
            
            weekday = activity.get("weekday")
            start_unit = activity.get("startUnit")
            end_unit = activity.get("endUnit")
            week_indexes = activity.get("weekIndexes", [])
            
            if weekday is None or start_unit is None:
                continue
            
            weekday = int(weekday)
            start_unit = int(start_unit)
            end_unit = int(end_unit)
            
            # 构建完整地点：campus + building + room
            campus = activity.get("campus", "") or ""
            building = activity.get("building", "") or ""
            room = activity.get("room", "") or ""
            location_parts = []
            if campus:
                location_parts.append(campus)
            if building:
                # 去除 campus 前缀（如 "H邯郸校区" 已在 campus 中）
                bname = building
                if campus:
                    bname = building.replace(campus, "").strip()
                if bname:
                    location_parts.append(bname)
            if room:
                location_parts.append(room)
            location = " ".join(location_parts)
            
            # 按 key 分组
            key = (lesson_id, weekday, start_unit, end_unit)
            
            if key in group_map:
                existing = group_map[key]
                # 合并周次
                existing["_weeks_set"].update(week_indexes)
                # 合并教师
                for t in teacher_list:
                    existing["_teachers_set"].add(t)
                # 合并地点（去重）
                if location:
                    existing["_locations_set"].add(location)
            else:
                teachers_set = set(teacher_list)
                locations_set = set()
                if location:
                    locations_set.add(location)
                group_map[key] = {
                    "title": title,
                    "code": code,
                    "weekday": weekday,
                    "start_unit": start_unit,
                    "end_unit": end_unit,
                    "_weeks_set": set(week_indexes),
                    "_teachers_set": teachers_set,
                    "_locations_set": locations_set,
                }
    
    # 将分组结果转换为 schedules
    schedules = []
    for entry in group_map.values():
        week_indexes = sorted(entry["_weeks_set"])
        if not week_indexes:
            continue
        
        # 构建 weeks_str
        if len(week_indexes) > 1 and all(
            week_indexes[i] + 1 == week_indexes[i + 1] for i in range(len(week_indexes) - 1)
        ):
            weeks_str = f"{week_indexes[0]}-{week_indexes[-1]}"
        else:
            weeks_str = ",".join(str(w) for w in week_indexes)
        
        # 教师合并
        teacher = "、".join(sorted(entry["_teachers_set"])) if entry["_teachers_set"] else ""
        
        # 地点合并
        location = "、".join(sorted(entry["_locations_set"])) if entry["_locations_set"] else ""
        
        schedules.append({
            "title": entry["title"],
            "code": entry["code"],
            "teacher": teacher,
            "weekday": entry["weekday"],
            "weeks": weeks_str,
            "start_unit": entry["start_unit"],
            "end_unit": entry["end_unit"],
            "location": location,
        })
    
    logger.info(f"Parsed {len(schedules)} schedule entries (merged from {len(group_map)} groups)")
    return schedules


def compute_semester_start(semester_id: int, semester_name: str = "") -> str | None:
    """
    计算学期开始日期。
    复旦的学期通常：
    - 秋季学期（9月~1月）：9月1日左右
    - 春季学期（2月~6月）：2月24日左右
    通过 semester_id 可以推算大致年份。
    
    更精确的方式是从学期名称中提取。
    
    Args:
        semester_id: 学期ID (如 527)
        semester_name: 学期名称 (如 "2026-2027学年1学期")
    
    Returns:
        "YYYY-MM-DD" 格式的学期开始日期，或 None
    """
    # 优先从学期名称提取
    if semester_name:
        # "2026-2027学年1学期" -> 秋季, "2025-2026学年2学期" -> 春季
        year_match = re.search(r'(\d{4})', semester_name)
        if year_match:
            base_year = int(year_match.group(1))
            if '1学期' in semester_name or '秋' in semester_name:
                return f"{base_year}-09-01"
            elif '2学期' in semester_name or '春' in semester_name:
                return f"{base_year}-02-24"
    
    # 通过 semester_id 推算 (粗略)
    # 复旦从 ~500 开始对应 2020 年
    if semester_id:
        # 每学期 ID 大约递增 10，可以从已知对应关系推算
        known = {518: "2025-09-01", 527: "2026-09-01"}  # 示例映射
        if semester_id in known:
            return known[semester_id]
        # 粗略估算：每增加1约对应1个月
        if semester_id >= 518:
            year_offset = (semester_id - 518) / 10
            return f"{2025 + int(year_offset)}-09-01"
    
    return None


def build_rrule(weekday: int, weeks: list[int], semester_start: str, start_time_str: str) -> tuple[str, str, str]:
    """
    根据排课信息生成 RRULE 和具体的起止时间。
    
    策略：
    - 如果周次是连续的 (如 1-16)，使用 RRULE (FREQ=WEEKLY;COUNT=16)
    - 如果周次不连续，为每个周次分别创建日程
    
    Args:
        weekday: 星期几 (1=周一, 7=周日)
        weeks: 周次列表
        semester_start: 学期开始日期 "YYYY-MM-DD"
        start_time_str: 上课开始时间 "HH:MM"
        end_time_str: 下课结束时间 "HH:MM"
    
    Returns:
        (rrule_str, first_start_datetime_str, first_end_datetime_str)
        如果 weeks 不连续，rrule_str 为空字符串
    """
    from datetime import datetime, timedelta
    
    if not weeks:
        return ("", "", "")
    
    # 判断是否连续
    is_consecutive = len(weeks) > 1 and all(
        weeks[i] + 1 == weeks[i + 1] for i in range(len(weeks) - 1)
    )
    
    # 计算第一次上课的日期
    start_date = datetime.strptime(semester_start, "%Y-%m-%d")
    # 学期第1周的周一 = semester_start
    # 计算第1周中 weekday 对应的日期
    days_offset = weekday - 1  # 周一=0偏移
    first_week_date = start_date + timedelta(days=days_offset)
    
    if not weeks:
        return ("", "", "")
    
    # 第一周的上课日期
    first_week = weeks[0]
    first_date = first_week_date + timedelta(weeks=first_week - 1)
    
    first_start = f"{first_date.strftime('%Y-%m-%d')} {start_time_str}"
    
    if is_consecutive and len(weeks) > 1:
        rrule = f"FREQ=WEEKLY;COUNT={len(weeks)};BYDAY={_weekday_to_rrule(weekday)}"
        return (rrule, first_start, "")
    elif len(weeks) == 1:
        return ("", first_start, "")
    else:
        # 不连续 - 需要分别处理
        return ("", first_start, "")


def _weekday_to_rrule(weekday: int) -> str:
    """将 1-7 转换为 RRULE 的 BYDAY 值 (MO,TU,WE,TH,FR,SA,SU)"""
    mapping = {1: "MO", 2: "TU", 3: "WE", 4: "TH", 5: "FR", 6: "SA", 7: "SU"}
    return mapping.get(weekday, "MO")


def parse_weekday(weekday_str: str) -> int:
    """将中文星期转换为数字 (1=周一, 7=周日)"""
    mapping = {
        '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '日': 7, '天': 7,
        'mon': 1, 'tue': 2, 'wed': 3, 'thu': 4, 'fri': 5, 'sat': 6, 'sun': 7,
    }
    s = weekday_str.strip().lower()
    for k, v in mapping.items():
        if k in s:
            return v
    return 0


def parse_weeks(weeks_str: str) -> list[int]:
    """解析周次字符串，如 '1-16' -> [1,2,...,16], '1,3,5' -> [1,3,5]"""
    weeks = []
    s = weeks_str.strip()
    
    # 尝试匹配 "1-16" 格式
    range_match = re.findall(r'(\d+)\s*[-–]\s*(\d+)', s)
    for start, end in range_match:
        weeks.extend(range(int(start), int(end) + 1))
    
    # 尝试匹配 "1,3,5" 格式
    single_match = re.findall(r'(?<!\d)(\d+)(?!\s*[-–])', s)
    for w in single_match:
        w_int = int(w)
        if w_int not in weeks:
            weeks.append(w_int)
    
    return sorted(weeks)


def get_weekday_name(weekday: int) -> str:
    """数字星期 to 中文"""
    names = {1: '周一', 2: '周二', 3: '周三', 4: '周四', 5: '周五', 6: '周六', 7: '周日'}
    return names.get(weekday, '')


def period_to_time(period_str: str) -> tuple[str, str]:
    """
    将节次转换为起止时间。
    复旦标准教务处节次时间表：
    第1节	08:00-08:45
    第2节	08:55-09:40
    第3节	09:55-10:40
    第4节	10:50-11:35
    第5节	11:45-12:30
    第6节	13:30-14:15
    第7节	14:25-15:10
    第8节	15:20-16:05
    第9节	16:15-17:00
    第10节	17:10-17:55
    第11节	18:30-19:15
    第12节	19:25-20:10
    第13节	20:20-21:05
    第14节	21:15-22:00
    """
    period_map = {
        '1': ('08:00', '08:45'), '2': ('08:55', '09:40'),
        '3': ('09:55', '10:40'), '4': ('10:50', '11:35'),
        '5': ('11:45', '12:30'), '6': ('13:30', '14:15'),
        '7': ('14:25', '15:10'), '8': ('15:20', '16:05'),
        '9': ('16:15', '17:00'), '10': ('17:10', '17:55'),
        '11': ('18:30', '19:15'), '12': ('19:25', '20:10'),
        '13': ('20:20', '21:05'), '14': ('21:15', '22:00'),
    }
    
    # 提取数字
    nums = re.findall(r'\d+', period_str)
    if not nums:
        return ('08:00', '09:30')  # 默认
    
    first = nums[0]
    last = nums[-1] if len(nums) > 1 else first
    
    start = period_map.get(first, ('08:00',))[0]
    end = period_map.get(last, (None, '09:30'))[1]
    
    return (start, end)


def _extract_semesters_json(html: str) -> list | None:
    """
    暴力提取页面中 semesters 的 JSON 数据。
    页面中的格式是: var semesters = JSON.parse('[...大型转义JSON...]');
    由于 JS 转义层级复杂，正则难以正确提取，这里用字符串搜索+逐步清理的方式。
    """
    import json, logging
    logger = logging.getLogger(__name__)
    
    # 定位 JSON.parse(' 和 ');
    marker = "JSON.parse('"
    idx = html.find(marker)
    if idx < 0:
        return None
    
    content_start = idx + len(marker)
    
    # 找结束位置：从 content_start 往后找 '); 
    end_markers = ["');\n", "');", "'); ", "');\r"]
    end_idx = -1
    for em in end_markers:
        ei = html.find(em, content_start)
        if ei >= 0:
            end_idx = ei
            break
    
    if end_idx < 0:
        return None
    
    raw = html[content_start:end_idx]
    logger.info(f"Extracted raw semesters string: {len(raw)} chars, preview: {raw[:100]}")
    
    # 暴力转义清理：JS 序列化 JSON 到 Python 字符串再经 HTML 的转义层级
    # 先替换 4 层转义，再 2 层，等等
    attempts = []
    
    # 尝试 1: 直接解析（如果本来就没转义）
    attempts.append(raw)
    
    # 尝试 2: 去掉 \\" → "，去掉 \\n → ''，去掉 \\t → ''
    cleaned = raw.replace('\\\\"', '"').replace('\\"', '"')
    cleaned = cleaned.replace('\\\\n', '').replace('\\n', '').replace('\\\\t', '').replace('\\t', '')
    attempts.append(cleaned)
    
    # 尝试 3: 去掉所有反斜杠（除 \/ 外，但 JSON 中不常见）
    import re as _re
    cleaned2 = _re.sub(r'\\(.)', r'\1', raw)
    attempts.append(cleaned2)
    
    # 尝试 4: 逐步清理 - 先去掉 \\" 变成 \"，再从 \" 变成 "
    cleaned3 = raw
    for _ in range(3):
        cleaned3 = cleaned3.replace('\\\\"', '\\"')
    cleaned3 = cleaned3.replace('\\"', '"')
    cleaned3 = _re.sub(r'\\([^"])', '', cleaned3)  # 去掉其他转义
    attempts.append(cleaned3)
    
    for i, attempt in enumerate(attempts):
        if not attempt or len(attempt) < 10:
            continue
        try:
            data = json.loads(attempt)
            if isinstance(data, list) and len(data) > 0:
                logger.info(f"Semesters extracted via attempt {i+1}: {len(data)} entries")
                return data
        except (json.JSONDecodeError, ValueError) as e:
            if i == len(attempts) - 1:
                logger.warning(f"Last attempt failed: {e}")
            continue
    
    return None


def parse_all_semester_dates(page_html: str) -> dict[int, str]:
    """
    解析课表页面 HTML 中 var semesters = JSON.parse(...) 的所有学期日期。
    
    返回: { semester_id: "YYYY-MM-DD(周一)" }
    注意：原始数据中 startDate 是周日，需转换为周一。
    
    如果彻底解析不到任何学期日期，返回空 dict。
    绝不做静默估算。
    """
    import logging
    logger = logging.getLogger(__name__)
    import json
    
    all_sems = []
    
    # 方法1: 直接在 HTML 中找 var semesters = JSON.parse(...)
    # 有些页面中 semesters 数据在 script 标签内，需要先提取 script 内容
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', page_html, re.DOTALL | re.IGNORECASE)
    for script in scripts:
        if 'semesters' in script:
            # 在这个 script 中查找 JSON.parse
            # 注意：JS 转义后的字符串可能是 \" 或 \\"，需要用两步清理
            # 正则匹配时用 .+? 可能匹配过头，改用更精确的匹配方式
            # 先找 JSON.parse 的位置，然后找结束的 ');
            start_idx = script.find("JSON.parse('")
            if start_idx < 0:
                start_idx = script.find("JSON.parse( '")
            if start_idx >= 0:
                # JSON 内容从 start_idx + len("JSON.parse('") 开始
                content_start = script.index("'", start_idx) + 1
                # 结束标记是 '); 或者 ');
                # 从 content_start 之后找第一个 '); 不包含在转义字符串中的
                # 简单做法：找 '); 的位置
                end_markers = ["');", "') ;", "'); //", "');\n"]
                end_idx = -1
                for marker in end_markers:
                    ei = script.find(marker, content_start)
                    if ei >= 0:
                        end_idx = ei
                        break
                if end_idx < 0:
                    # 再尝试正则
                    for pattern in [
                        r"JSON\.parse\(\s*'(.+?)'\s*\)\s*;",
                    ]:
                        match = re.search(pattern, script, re.DOTALL)
                        if match:
                            raw = match.group(1)
                            try:
                                # 处理转义
                                cleaned = raw.replace('\\\\"', '\\"').replace('\\"', '"').replace("\\'", "'")
                                cleaned = cleaned.strip()
                                data = json.loads(cleaned)
                                if isinstance(data, list) and len(data) > 0:
                                    all_sems = data
                                    logger.info(f"parse_all_semester_dates: found {len(all_sems)} semesters via script regex")
                                    break
                            except Exception:
                                continue
                    if all_sems:
                        break
                else:
                    raw = script[content_start:end_idx]
                    try:
                        # 处理转义：JS 序列化的 JSON 字符串中
                        # \\" → \" → "
                        cleaned = raw.replace('\\\\"', '\\"').replace('\\"', '"').replace("\\'", "'")
                        cleaned = cleaned.replace('\\\\n', '').replace('\\\\t', '')
                        cleaned = cleaned.strip()
                        data = json.loads(cleaned)
                        if isinstance(data, list):
                            all_sems = data
                            logger.info(f"parse_all_semester_dates: found {len(all_sems)} semesters via script index")
                            break
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning(f"Script extraction failed: {e}, raw len={len(raw)}, preview={raw[:200]}")
                        # 如果包含多余字符，尝试逐层清理
                        # 有时页面中有多个 '); 匹配，我们取短的
                        for end_pos in range(end_idx-1, content_start, -1):
                            if script[end_pos:end_pos+2] == "')":
                                try:
                                    raw2 = script[content_start:end_pos]
                                    cleaned2 = raw2.replace('\\\\"', '\\"').replace('\\"', '"').replace("\\'", "'")
                                    cleaned2 = cleaned2.strip()
                                    data = json.loads(cleaned2)
                                    if isinstance(data, list):
                                        all_sems = data
                                        logger.info(f"parse_all_semester_dates: found {len(all_sems)} semesters via backtrack")
                                        break
                                except Exception:
                                    continue
                    if all_sems:
                        break
    
    # 方法2: 整个页面直接查找 JSON.parse
    if not all_sems:
        for pattern in [
            r'JSON\.parse\(\s*\'(.+?)\'\)\s*',
        ]:
            match = re.search(pattern, page_html, re.DOTALL)
            if match:
                raw = match.group(1)
                try:
                    cleaned = raw.replace('\\\\"', '\\"').replace('\\"', '"').replace("\\'", "'").replace('\\n', '').replace('\\t', '')
                    cleaned = cleaned.strip()
                    data = json.loads(cleaned)
                    if isinstance(data, list):
                        all_sems = data
                        logger.info(f"parse_all_semester_dates: found {len(all_sems)} semesters via whole-page JSON.parse")
                        break
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Whole-page JSON.parse failed: {e}")
                    continue
    
    # 方法3: 直接匹配 JSON.parse 中的转义字符串（逐个字符拼凑）
    if not all_sems:
        # 找 semesters = JSON.parse(' 和 '); 之间的内容
        start_marker = "JSON.parse('"
        end_marker = "');"
        start_idx = page_html.find(start_marker)
        if start_idx >= 0:
            start_idx += len(start_marker)
            end_idx = page_html.find(end_marker, start_idx)
            if end_idx >= 0:
                raw = page_html[start_idx:end_idx]
                try:
                    cleaned = raw.replace('\\\\"', '\\"').replace('\\"', '"').replace("\\'", "'").replace('\\n', '').replace('\\t', '')
                    cleaned = cleaned.strip()
                    data = json.loads(cleaned)
                    if isinstance(data, list):
                        all_sems = data
                        logger.info(f"parse_all_semester_dates: found {len(all_sems)} semesters via direct extraction")
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Direct JSON extraction failed: {e}")
    
    # 方法4: 从 HTML 中逐个提取 startDate 和 id
    if not all_sems:
        start_dates = re.findall(r'"startDate"\s*:\s*"(\d{4}-\d{2}-\d{2})"', page_html)
        ids = re.findall(r'"id"\s*:\s*(\d+)', page_html)
        if start_dates and ids and len(start_dates) == len(ids):
            all_sems = []
            for i, sem_id in enumerate(ids):
                all_sems.append({"id": int(sem_id), "startDate": start_dates[i]})
            logger.info(f"parse_all_semester_dates: found {len(all_sems)} semesters via regex")
    
    if not all_sems:
        logger.error("parse_all_semester_dates: FAILED to parse ANY semester dates from page! Page sample: " + page_html[:500])
        return {}
    
    # 转换为 dict，startDate 周日→周一
    result = {}
    from datetime import datetime, timedelta
    for sem in all_sems:
        sem_id = sem.get("id")
        start_date_str = sem.get("startDate", "")
        if sem_id and start_date_str:
            try:
                dt = datetime.strptime(start_date_str, "%Y-%m-%d")
                dt += timedelta(days=1)  # 周日 → 周一
                result[int(sem_id)] = dt.strftime("%Y-%m-%d")
            except ValueError as e:
                logger.error(f"parse_all_semester_dates: bad date '{start_date_str}' for sem {sem_id}: {e}")
                # 不插入错误日期
    
    logger.info(f"parse_all_semester_dates: result = {result}")
    return result


def unit_to_time(unit: int) -> tuple[str, str]:
    """将节次数字转换为起止时间字符串"""
    period_map = {
        1: ('08:00', '08:45'), 2: ('08:55', '09:40'),
        3: ('09:55', '10:40'), 4: ('10:50', '11:35'),
        5: ('11:45', '12:30'), 6: ('13:30', '14:15'),
        7: ('14:25', '15:10'), 8: ('15:20', '16:05'),
        9: ('16:15', '17:00'), 10: ('17:10', '17:55'),
        11: ('18:30', '19:15'), 12: ('19:25', '20:10'),
        13: ('20:20', '21:05'), 14: ('21:15', '22:00'),
    }
    return period_map.get(unit, ('08:00', '09:30'))
