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
    复旦标准：第1节=08:00-08:45, 第2节=08:50-09:35, ...
    """
    period_map = {
        '1': ('08:00', '08:45'), '2': ('08:50', '09:35'),
        '3': ('09:50', '10:35'), '4': ('10:40', '11:25'),
        '5': ('11:30', '12:15'), '6': ('13:30', '14:15'),
        '7': ('14:20', '15:05'), '8': ('15:20', '16:05'),
        '9': ('16:10', '16:55'), '10': ('17:00', '17:45'),
        '11': ('18:30', '19:15'), '12': ('19:20', '20:05'),
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