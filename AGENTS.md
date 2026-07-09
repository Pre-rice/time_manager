# Time Manager — AI 代理指令手册

> 本文档面向 AI 开发助手。每次新对话的第一步必须是 `read_file` 读取本文档和 `README.md`。

## 元原则

1. **文档持续迭代** — 用户指出问题（特别是反复指出）或自己总结出经验（特别是反复犯错）后，必须更新本文档，持续迭代。目标是让 AGENT 能够自我进化，避免再次犯错，且一切皆可修改（包括元原则），改变是为了进化
2. **严格遵守流程** — 先详细分析，给出切实可行的细化方案，再进行执行。完成任务后必须先进行后端测试，确保功能无误。最后必须启动 HTTP 服务器（`python -m http.server 8080`）并告知用户，让用户检查前端。且完成任务后要详细告知用户此次更新的细节
3. **准备开始新对话前必须更新文档** — 每次用户要求开启新对话前，必须同步本文档和 README.md 的信息到最新状态，在开发进度及技术细节模块中讲清楚此次添加内容的技术细节，并详细说明接下来要执行任务，确保新对话读取后能继续稳步推进
4. **遇到问题要说** — 遇到一切难以解决的问题要告知用户，不能自行跳过
5. **交流必须用中文** — 对话、思考过程，以及面向客户的文字，必须使用中文
6. **持续同步 Git** — 完成阶段性工作后立即提交

## 项目架构

### 技术栈

| 层 | 技术 | 版本/说明 |
|----|------|----------|
| 前端 | Flutter + Riverpod | Web 为主，多平台支持 |
| 后端 | Python FastAPI + SQLAlchemy | 异步，Alembic 迁移 |
| 数据库 | PostgreSQL (Docker) | 端口 5432 |
| 缓存 | Redis (Docker) | 端口 6379 |
| AI 网关 | LiteLLM | 支持 OpenAI 兼容接口 |
| 容器 | Docker Compose | 本地开发 |

### 项目结构

```
time_manager/
├── README.md              # 给用户看的说明
├── AGENTS.md               # 给 AI 看的指令手册
├── backend/
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/           # 数据库迁移
│   └── app/
│       ├── main.py        # FastAPI 入口
│       ├── core/
│       │   ├── config.py  # 配置（数据库URL、密钥等）
│       │   ├── security.py# 密码哈希、JWT
│       │   ├── crypto.py  # Fernet AES 加密
│       │   └── database.py# 异步引擎 + session
│       ├── models/        # SQLAlchemy 表模型
│       ├── schemas/       # Pydantic 请求/响应
│       ├── services/      # 业务逻辑
│       │   ├── fudan_service.py  # 复旦教务抓取
│       │   ├── fudan_parser.py   # 复旦数据解析
│       │   └── ai_service.py     # AI 功能
│       └── api/
│           ├── deps.py    # JWT 依赖注入
│           └── v1/        # API 路由
│               ├── auth.py
│               ├── events.py
│               ├── tasks.py
│               ├── goals.py
│               ├── ai.py
│               └── external.py   # 外部数据导入
└── frontend/
    └── lib/
        ├── main.dart      # 入口（设置中文本地化）
        ├── app.dart       # GoRouter 路由定义
        ├── theme.dart     # Material 3 主题
        ├── models/        # 数据模型
        ├── providers/     # Riverpod 状态
        ├── services/
        │   └── api_service.dart  # Dio HTTP 客户端
        └── pages/         # 页面
```

### 数据库表（共 10 张）

| 表名 | 说明 | 关键字段 |
|------|------|---------|
| `users` | 用户 | id, username, email, hashed_password |
| `events` | 日程 | title, start_time, end_time, rrule, source, event_type |
| `event_preparation_periods` | 日程准备时段 | event_id, start_time, end_time |
| `tasks` | 待办 | title, deadline, priority(1-3), status |
| `task_preparation_periods` | 待办准备时段 | task_id, start_time, end_time |
| `goals` | 长期目标 | title, target_value, current_value, unit |
| `ai_configs` | AI 配置 | provider, api_base, encrypted_key |
| `ai_templates` | 提示词模板 | type, template_text |
| `notifications` | 已发送通知 | type, title, content |
| `special_dates` | 特殊日期 | date, name, type |
| `fudan_credential` | 复旦凭证 | user_id, student_id, encrypted_password, cookies (加密) |

### API 路由（前缀 `/api/v1`）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/auth/register` | POST | 注册 |
| `/auth/login` | POST | 登录，返回 JWT |
| `/events/` | GET/POST | 列表/创建 |
| `/events/{id}` | PUT/DELETE | 编辑/删除 |
| `/tasks/` | GET/POST | 待办列表/创建 |
| `/tasks/{id}` | PUT/DELETE | 编辑/删除 |
| `/goals/` | GET/POST | 目标列表/创建 |
| `/goals/{id}` | PUT/DELETE | 编辑/删除 |
| `/goals/{id}/progress` | PATCH | 更新进度 |
| `/special-dates/` | GET/POST | 特殊日期 |
| `/ai/config/` | GET/PUT | AI 配置管理 |
| `/ai/extract` | POST | 文本提取 |
| `/ai/suggest-time` | POST | 时间建议 |
| `/ai/morning-message` | GET | 早安消息 |
| `/external/fudan/connect` | POST | 连接复旦教务 |
| `/external/fudan/sync` | POST | 同步数据 |
| `/external/fudan/status` | GET | 连接状态 |
| `/external/fudan/disconnect` | DELETE | 断开连接 |

## 开发环境

### Windows 注意事项

- **conda 虚拟环境**：`time_manager`，路径 `C:\Users\Administrator\.conda\envs\time_manager`
- **conda run 编码坑**：`conda run` 输出 stdout 时用 GBK 编码，含 Unicode 字符会报 `UnicodeEncodeError`
  - 解决：设置 `PYTHONIOENCODING=utf-8` 或用 `python -X utf8`
  - 或输出到文件再 `read_file`
- **Flutter**：`D:\Flutter\bin\flutter.bat`
- **Docker Desktop**：安装于 C 盘（空间不足时可迁移到 D 盘）

### 启动步骤

```bash
# 1. 启动数据库
cd e:\编程\time_manager\backend
docker compose up -d

# 2. 启动后端（自动建表）
conda run --cwd backend -n time_manager python -m uvicorn app.main:app --reload --port 8000

# 3. 构建前端
cd e:\编程\time_manager\frontend
D:\Flutter\bin\flutter.bat build web

# 4. 部署前端
python -m http.server 8080 -d e:\编程\time_manager\frontend\build\web
```

### curl 测试（验证后端）

```bash
# 注册
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@test.com","password":"123456"}'

# 登录
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123"}'
```

## 复旦教务数据集成（Phase 5）

### 认证流程（CAS + RSA）

```
authserver/login (获取 lck + entityId)
  → getJsPublicKey (获取 RSA 公钥)
  → queryAuthMethods (查询认证方式)
  → authExecute (RSA 加密密码登录，获 loginToken)
  → authnEngine (提交 loginToken，获 ticket)
  → sso/login (用 ticket 跳转回教务系统)
  → 访问 course-table 页面完成 SSO
```

### 数据源

| 数据 | 方式 | URL |
|------|------|-----|
| **课程列表+考试** | JSON API | `GET /student/for-std/course-table/getLesson?semesterId={}&studentId={}` |
| **考试安排（含期中）** | HTML 解析 | `GET /student/for-std/exam-arrange/` |
| **课表排课（每周时间）** | JSON API | `GET /student/for-std/course-table/semester/{sem_id}/print-data` |

### 开发调试凭据

> ⚠️ 敏感信息存储在 `.env.local` 文件中
>（该文件已被 `.gitignore` 排除，不会提交到 Git 仓库）
>
> AI 代理在需要执行测试时，请先 `read_file .env.local` 获取凭据。

### 已知问题

1. ~~**排课数据未导入** — `draw-table-data` API 返回了 HTML~~ ✅ 已修复：参考 DanXi 源码改为使用 `print-data` API（2026-07-09）
2. **`_get_client()` 缺少 `verify=False`** — 已修复（2026-07-09）
3. **`semester_start` 硬编码** — 已修复，改用 `compute_semester_start()` 根据学期名称自动计算（2026-07-09）
4. **Windows GBK 编码** — cmd 终端输出 Unicode 时报错，调试困难
5. **Cookie 会过期** — SSO 每次 sync 时需要自动跟随 ticket 重连
6. **Docker 容器内 Python stdout 缓冲** — `docker exec` 运行 Python 时输出被缓冲吞掉，调试困难。解决：写入文件再用 `cat` 读取
7. **`last_sync_at` 时区** — 后端存 UTC，前端直接显示 UTC 而非北京时间（需修复）
8. **前端编辑弹窗无 RRULE 支持** — 编辑弹窗没展示重复规则（需修复）

## 前端 Flutter 注意事项

- **中文本地化**：`main.dart` 需设置 `Intl.defaultLocale = 'zh_CN'`，`app.dart` 需加 `localizationsDelegates` 和 `supportedLocales`
- **`table_calendar` 3.x**：用 `StartingDayOfWeek` 枚举和 `startingDayOfWeek` 参数
- **Dio 异常**：必须用 `e is DioException` + `e.response?.statusCode` 判断，422 的 detail 是数组，409 的 detail 是字符串
- **`List<dynamic>` 转换**：手动用 for 循环 + `Map<String, dynamic>.from(e)`
- **`const` 常量**：不能用 `()` 调用，如 `_HomeData.empty` 不是 `_HomeData.empty()`
- **AI 提取弹窗复用**：`showEventEditDialog`/`showTaskEditDialog` 是顶层函数
- **错误提示**：必须从后端提取具体信息，不能笼统

## 开发进度及技术细节

### Phase 1 ✅ 骨架搭建
- FastAPI 项目结构，10 张表，JWT 认证，Docker Compose
- Flutter 项目，GoRouter 路由，登录/注册，API 封装，Riverpod

### Phase 2 ✅ 核心实体
- 后端日程/待办/目标 CRUD（含准备时段）
- 前端列表展示，对接真实 API

### Phase 3 ⚠️ AI（部分完成）
- 后端：AI 配置 CRUD、文本提取、时间建议、早安消息、LiteLLM
- 前端：AI 助手、AI 配置、早安消息卡片
- **待完成**：时间建议前端集成、早安消息自动推送

### Phase 4 ✅ UX 优化
- 日期/时间选择器、编辑弹窗、删除确认、月视图、周起始日设置、首页概览

### Phase 5 ⚠️ 复旦教务（部分完成）
- [x] fudan_credential 表（加密存储）
- [x] CAS 6 步认证 + RSA 加密
- [x] SSO ticket 自动跟随
- [x] JSON API 抓取课程+考试
- [x] 考试 HTML 解析（期中+期末）
- [x] API 路由（connect/sync/status/disconnect）
- [x] 增量 upsert 导入
- [x] sync 导入 37 条考试日程 ✅
- [x] `_get_client()` 修复 SSL 验证 ✅
- [x] 学期开始日期硬编码修复 ✅
- [x] **课表排课数据导入** — 使用 `print-data` API 替换失败的 `draw-table-data` API ✅
- [x] 修正节次时间表（14 节标准教务处时间）
- [x] weekday 映射修正（1=周一，直接透传）
- [x] 学期开始日期解析（从 JS 提取 startDate 并周日→周一）
- [x] 修复 upsert 去重（title+weekday 唯一匹配）
- [ ] `last_sync_at` 前端显示 UTC+8 时区修复
- [ ] 前端 RRULE 展示和编辑
- [ ] eLearning 作业抓取

### 关键技术障碍（2026-07-09 记录）

**`draw-table-data` API 返回 HTML 而非 JSON** ✅ 已修复：
- 日志显示 `Draw API non-200: body=<!DOCTYPE html>...`，说明该 API 端点已废弃或需要不同认证
- 参考 [DanXi](https://github.com/DanXi-Dev/DanXi)（复旦官方开源 Flutter App）的源码找到了正确 API
  - DanXi 使用 `print-data` API（`/student/for-std/course-table/semester/{sem_id}/print-data`）
  - 返回结构包含 `studentTableVms[].activities[]`，每个 activity 有 courseName、weekday、startUnit、endUnit、weekIndexes（数组）、room、teachers 等字段
  - 使用 GET 请求，无需 POST body
- 修复后 sync 成功导入 37 个日程（含完整的课程排课 + 考试）

### Phase 6 🔜 实时与提醒
### Phase 7 🔜 界面美化
### Phase 8 🔜 报告与发布