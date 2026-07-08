# Time Manager 开发指南

## 环境要求

- **Python 3.12+**（建议使用 conda 虚拟环境）
- **Flutter SDK**（建议最新稳定版）
- **Docker Desktop**（用于运行 PostgreSQL 和 Redis）

## 快速开始

### 1. 启动数据库服务

```bash
cd backend
docker compose up -d
```

这会启动 PostgreSQL（端口 5432）和 Redis（端口 6379）。

### 2. 安装后端依赖

```bash
conda activate time_manager
cd backend
pip install -r requirements.txt
```

### 3. 启动后端（自动建表）

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

应用启动时会自动调用 `Base.metadata.create_all` 创建所有表。

API 文档：http://localhost:8000/docs

### 4. 安装前端依赖

```bash
cd frontend
flutter pub get
```

### 5. 启动前端

```bash
cd frontend
flutter run -d edge    # Edge 浏览器
flutter run -d windows # Windows 桌面（需开启开发者模式）
```

## 项目结构

```
time_manager/
├── README.md              # 项目说明
├── DEVELOPMENT.md         # 本文件 - 开发指南
├── backend/               # Python FastAPI 后端
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/           # 数据库迁移
│   └── app/
│       ├── main.py        # FastAPI 入口
│       ├── core/          # 配置、安全、数据库
│       │   ├── config.py
│       │   ├── security.py
│       │   └── database.py
│       ├── models/        # SQLAlchemy 数据表模型
│       ├── schemas/       # Pydantic 请求/响应模型
│       ├── services/      # 业务逻辑
│       └── api/
│           ├── deps.py    # 依赖注入（JWT）
│           └── v1/        # API v1 路由
└── frontend/              # Flutter 前端
    └── lib/
        ├── main.dart
        ├── app.dart       # GoRouter 路由
        ├── theme.dart     # Material 3 主题
        ├── models/        # 数据模型（待建）
        ├── providers/     # Riverpod 状态管理
        ├── services/      # HTTP 客户端
        └── pages/         # 页面
```

## API 概览

所有 API 均以 `/api/v1` 为前缀。

| 模块 | 端点 | 状态 |
|------|------|------|
| 认证 | `POST /auth/register` | ✅ 已完成 |
| 认证 | `POST /auth/login` | ✅ 已完成 |
| 日程 | `GET/POST/PUT/DELETE /events` | ✅ 已完成 |
| 待办 | `GET/POST/PUT/DELETE /tasks` | ✅ 已完成 |
| 目标 | `GET/POST/PUT/DELETE /goals` | ✅ 已完成 |
| 日历标识 | `GET/POST/DELETE /special-dates` | ✅ 已完成 |
| AI 配置 | `GET/PUT/PATCH/DELETE /ai/config/` | ✅ 已完成 |
| AI 文本提取 | `POST /ai/extract` | ✅ 已验证 |
| AI 时间建议 | `POST /ai/suggest-time` | ✅ 已完成 |
| AI 早安消息 | `GET /ai/morning-message` | ✅ 已完成 |

## 开发进度

### Phase 1 ✅ 骨架搭建
- [x] FastAPI 项目结构 + SQLAlchemy 异步引擎
- [x] 10 张数据表模型（users, events, tasks, goals...）
- [x] JWT 认证 + bcrypt 密码哈希
- [x] `/api/v1/auth/register` + `/api/v1/auth/login`
- [x] Docker Compose（PostgreSQL + Redis + API）
- [x] Alembic 迁移配置
- [x] Flutter 项目创建（多平台）
- [x] GoRouter 路由 + 10 个页面骨架
- [x] 登录/注册页面（表单验证）
- [x] 首页侧边栏导航
- [x] API 服务封装（Dio + 自动 Token 注入）
- [x] Riverpod 认证状态管理

### Phase 2 ✅ 核心实体
- [x] 后端：日程 CRUD 接口（含准备时段）
- [x] 后端：待办 CRUD 接口（含准备时段）
- [x] 后端：目标 CRUD 接口（含进度更新）
- [x] 后端：日历标识 CRUD 接口
- [x] 前端：日程列表（对接真实 API）
- [x] 前端：待办列表（对接真实 API）
- [x] 前端：目标进度管理（对接真实 API）

### Phase 3 ⚠️ AI 集成（部分完成）
- [x] 后端：AI 配置 CRUD（加密存储 API Key）
- [x] 后端：文本提取 API（自然语言 → 结构化日程/待办）
- [x] 后端：时间建议 API（根据空闲时间推荐安排）
- [x] 后端：早安消息 API（生成每日问候）
- [x] 后端：LiteLLM 集成（支持 DeepSeek 等模型）
- [x] 前端：AI 助手页面（文本输入 → 提取 → 添加）
- [x] 前端：AI 配置页面（API Key/模型/地址配置）
- [x] 前端：首页早安消息卡片（手动触发生成）
- [x] **AI 文本提取已验证通过** ✅
- [ ] 时间建议前端集成
- [ ] 早安消息自动定时推送

### Phase 4 🔜 MVP 用户体验优化（当前阶段）
- [ ] 时间选择器（替换手动输入时间戳，默认当前时间）
- [ ] 编辑功能（点击列表项弹窗编辑）
- [ ] 删除确认（弹窗确认）
- [ ] 日程月视图（table_calendar 集成）
- [ ] 首页今日梳理（AI 生成概览）
- [ ] 首页概览（今日日程 + 待办统计）

### Phase 5 🔜 外部数据
### Phase 6 🔜 实时与提醒
### Phase 7 🔜 界面美化
### Phase 8 🔜 报告与发布

## 常见问题

### Q: Docker 拉取镜像太慢？
配置镜像加速器：创建 `~/.docker/daemon.json`
```json
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://dockerproxy.com"
  ]
}
```
然后重启 Docker Desktop。

### Q: Windows 桌面运行报错"需要 symlink 支持"？
开启**开发者模式**：
1. 设置 → 更新和安全 → 开发者选项
2. 开启"开发人员模式"
3. 或在命令行运行：`start ms-settings:developers`

### Q: Flutter Web SDK 下载失败？
Flutter 会从国内镜像源下载，如遇网络问题可以配置代理或重试。