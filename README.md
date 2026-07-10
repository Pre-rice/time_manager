# Time Manager

> **开源的个人时间管理助手** — 将未来一切事务汇集一处，用 AI 辅助规划与复盘。

## 功能

| 功能 | 状态 |
|------|------|
| 日程管理 | ✅ |
| 待办管理 | ✅（重要标记替代优先级） |
| 长期目标追踪 | ✅ |
| 日历月视图 | ✅ |
| AI 文本提取（自然语言→日程/待办） | ✅ |
| AI 早安消息 | ✅ |
| 复旦教务数据导入 | ✅（课程+考试） |
| 准备日程（日程关联机制） | ✅（2026-07-10 新架构） |
| 时间建议 | ⚠️ 后端完成 |
| 多端同步 | 📅 计划中 |
| 本地提醒 | 📅 计划中 |

## 技术栈

- **前端**：Flutter + Riverpod（Web/桌面/移动）
- **后端**：Python FastAPI + SQLAlchemy 异步
- **数据库**：PostgreSQL + Redis（Docker）
- **AI 网关**：LiteLLM（支持 DeepSeek 等）

## 快速开始

**方式一：双击 `deploy.bat` 一键部署（推荐）**
```bash
# 项目根目录双击 deploy.bat
# 自动完成5步：启动Docker → 数据库迁移 → 重启API → 构建前端 → 启动HTTP
```

**方式二：手动分步部署**
```bash
# 1. 启动数据库
cd backend && docker compose up -d

# 2. 启动后端（自动建表）
conda run --cwd backend -n time_manager python -m uvicorn app.main:app --reload --port 8000

# 3. 构建前端
cd frontend && flutter build web

# 4. 部署前端
python -m http.server 8080 -d frontend/build/web
```

- 前端：http://localhost:8080
- API 文档：http://localhost:8000/docs

## 数据库结构（9 张表）

| 表名 | 说明 |
|------|------|
| `users` | 用户 |
| `events` | 日程（含准备日程、重复规则、来源标记） |
| `tasks` | 待办（含重要标记、状态） |
| `goals` | 长期目标 |
| `ai_configs` | AI 配置 |
| `ai_templates` | 提示词模板 |
| `notifications` | 已发送通知 |
| `special_dates` | 特殊日期 |
| `fudan_credential` | 复旦教务凭证 |

## AI 配置（以 DeepSeek 为例）

| 字段 | 值 |
|------|-----|
| API Key | `sk-你的密钥` |
| API 地址 | `https://api.deepseek.com` |
| 模型名称 | `deepseek-chat` |

API Key 使用 Fernet AES 加密存储。

## 复旦教务导入

在设置页配置学号和密码，可自动同步：
- 课程列表（含排课时间、RRULE）
- 考试安排（期中+期末）
- 作业等 elearning 任务（待实现）

> 学号和密码使用 Fernet AES 加密存储在后端数据库，仅用于向复旦 CAS 认证，不会上传到任何第三方服务。

## 安全

- 用户密码：bcrypt 哈希
- AI Key：服务端 Fernet AES 加密存储
- 复旦密码：通过 HTTPS 传输到服务器，使用 Fernet AES 加密存储在数据库，仅用于向复旦 CAS 系统认证，不分享给任何第三方
- API 通信需 JWT token
- 数据库往来凭证定时刷新

## 许可证

AGPLv3