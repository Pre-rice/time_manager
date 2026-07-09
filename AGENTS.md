# Time Manager — AI 代理指令手册

> 本文档面向 AI 开发助手。每次新对话的第一步必须是 `read_file` 读取本文档和 `README.md`。

## 元原则

1. **先记录，再改正** — 用户指出问题后，先更新文档（AGENTS.md 或 README.md），再去改代码
2. **自己跑完所有流程再找用户** — 后端测试 → 构建 → 启动服务器让用户查看，全部通过后才报告
3. **新对话先读本文档 + README.md** — 每次开启新对话时，第一条消息必须 read_file 这两个文件
4. **部署是最后一步** — attempt_completion 之前必须启动 HTTP 服务器（`python -m http.server 8080`）并告知用户可访问
5. **部署端口 8080** — 如有进程占用先 `taskkill /F /IM python.exe`
6. **遇到问题要说** — 连不上、构建失败等要告知用户
7. **文档持续迭代** — 每次新经验都要更新到本文档
8. **思考过程用中文**
9. **错误提示必须精准** — 不能笼统说"注册失败"，要指出具体原因
10. **持续同步 Git** — 完成阶段性工作后立即提交

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
│       │   ├── fudan_parser.py   # 复旦数据解析（已弃用）
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
| **课表排课（每周时间）** | 待实现 | 需要从 `all-courses` 或 `draw-table-data` API 获取 |

### 开发调试凭据

> ⚠️ 敏感信息存储在 `.env.local` 文件中
>（该文件已被 `.gitignore` 排除，不会提交到 Git 仓库）
>
> AI 代理在需要执行测试时，请先 `read_file .env.local` 获取凭据。

### 已知问题

1. **排课数据未导入** — 课表每周上课时间、节次、地点仍需要从 `all-courses` API 或 `draw-table-data` API 获取
2. **Windows GBK 编码** — cmd 终端输出 Unicode 时报错，调试困难
3. **Cookie 会过期** — SSO 每次 sync 时需要自动跟随 ticket 重连

## 前端 Flutter 注意事项

- **中文本地化**：`main.dart` 需设置 `Intl.defaultLocale = 'zh_CN'`，`app.dart` 需加 `localizationsDelegates` 和 `supportedLocales`
- **`table_calendar` 3.x**：用 `StartingDayOfWeek` 枚举和 `startingDayOfWeek` 参数
- **Dio 异常**：必须用 `e is DioException` + `e.response?.statusCode` 判断，422 的 detail 是数组，409 的 detail 是字符串
- **`List<dynamic>` 转换**：手动用 for 循环 + `Map<String, dynamic>.from(e)`
- **`const` 常量**：不能用 `()` 调用，如 `_HomeData.empty` 不是 `_HomeData.empty()`
- **AI 提取弹窗复用**：`showEventEditDialog`/`showTaskEditDialog` 是顶层函数
- **错误提示**：必须从后端提取具体信息，不能笼统

## 开发进度

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
- [x] 前端设置页配置
- [x] sync 导入 37 条日程 ✅
- [ ] 课表排课数据导入（每周上课时间地点）
- [ ] eLearning 作业抓取

### Phase 6 🔜 实时与提醒
### Phase 7 🔜 界面美化
### Phase 8 🔜 报告与发布