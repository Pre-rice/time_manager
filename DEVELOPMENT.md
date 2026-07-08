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
pip install -r backend/requirements.txt
```

### 3. 运行数据库迁移

```bash
cd backend
alembic revision --autogenerate -m "init"
alembic upgrade head
```

或直接让 FastAPI 自动创建表（`main.py` 中已有 `lifespan` 逻辑，启动时会调用 `Base.metadata.create_all`）。

### 4. 启动后端

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

API 文档自动生成于：http://localhost:8000/docs

### 5. 安装前端依赖

```bash
cd frontend
flutter pub get
```

### 6. 启动前端

```bash
cd frontend
flutter run
```

## 项目结构

```
time_manager/
├── README.md
├── DEVELOPMENT.md        # 本文件
├── backend/              # Python FastAPI 后端
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/          # 数据库迁移
│   └── app/
│       ├── main.py       # 应用入口
│       ├── core/         # 配置、安全、数据库
│       ├── models/       # SQLAlchemy 模型（10张表）
│       ├── schemas/      # Pydantic 模型
│       ├── services/     # 业务逻辑
│       └── api/
│           ├── deps.py   # 依赖注入
│           └── v1/       # API v1 路由
└── frontend/             # Flutter 前端
    └── lib/
        ├── main.dart
        ├── app.dart       # 路由配置
        ├── theme.dart     # 主题
        ├── models/        # 数据模型
        ├── providers/     # Riverpod 状态管理
        ├── services/      # HTTP 客户端
        └── pages/         # 页面
```

## 目前实现的功能

### 后端（Phase 1 骨架）
- [x] FastAPI 项目结构
- [x] SQLAlchemy 异步引擎配置
- [x] 10 张数据表模型（users, events, tasks, goals 等）
- [x] JWT 认证 + bcrypt 密码哈希
- [x] `/api/v1/auth/register` - 注册
- [x] `/api/v1/auth/login` - 登录
- [x] Docker Compose（PostgreSQL + Redis + API）
- [x] Alembic 迁移配置

### 前端（Phase 1 骨架）
- [x] Flutter 项目创建（多平台）
- [x] GoRouter 路由配置
- [x] Material 3 主题
- [x] 10 个占位页面
- [x] 登录/注册页面（表单验证）
- [x] 首页侧边栏导航
- [x] API 服务封装（Dio + 自动 Token 注入）
- [x] Riverpod 认证状态管理

## 下一步（Phase 2：核心实体开发）

1. 后端：日程/待办/目标 CRUD 接口
2. 后端：准备时段管理
3. 后端：日历标识接口
4. 前端：日程列表（日/周/月视图）
5. 前端：待办列表（多视图模式）
6. 前端：目标进度管理