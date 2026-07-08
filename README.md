# Time Manager

> **开源的个人时间管理助手** — 将未来一切事务汇集一处，用 AI 辅助规划与复盘。

## 项目定位

- 核心实体：**日程、待办、长期目标**，专注时间管理，不加多余功能
- 用户完全掌控数据与 AI 密钥，外部系统密码不上传服务器
- 当前阶段：基础功能 + AI 文本提取 ✅，持续优化用户体验中

## 当前功能状态

| 功能 | 状态 | 说明 |
|------|------|------|
| 用户注册/登录 | ✅ 已完成 | JWT 认证 |
| 日程管理 | ✅ 已完成 | 创建/查看/编辑/删除，支持起止时间 |
| 待办管理 | ✅ 已完成 | 创建/查看/编辑/删除，支持优先级、截止时间 |
| 长期目标 | ✅ 已完成 | 创建/查看/编辑/删除，支持进度追踪 |
| 日历标识 | ✅ 已完成 | 节日、生日等特殊日期标记 |
| AI 文本提取 | ✅ 已验证 | 自然语言 → 结构化日程/待办，支持 DeepSeek |
| AI 时间建议 | ⚠️ 后端完成 | 根据空闲时间推荐安排时间 |
| AI 早安消息 | ⚠️ 后端完成 | 每日问候 + 日程概览 |
| 多端同步 | 📅 计划中 | WebSocket 实时推送 |
| 外部数据抓取 | 📅 计划中 | 复旦教务、飞书、微信 |
| 月/年报告 | 📅 计划中 | 统计完成率、时间分布 |
| 本地提醒 | 📅 计划中 | 手机端闹钟/通知 |

## AI 配置

使用 LiteLLM 作为 AI 网关，支持任意 OpenAI 兼容接口。

**DeepSeek 配置示例：**
| 字段 | 值 |
|------|-----|
| API Key | `sk-你的密钥` |
| API 地址 | `https://api.deepseek.com` |
| 模型名称 | `deepseek-chat` |

API Key 使用 Fernet AES 加密存储，不会明文暴露。

## 技术架构

| 层 | 技术 | 说明 |
|----|------|------|
| 前端 | Flutter + Riverpod | Android/iOS/Windows/macOS/Web |
| 后端 | Python FastAPI + SQLAlchemy 异步 | RESTful API，Alembic 迁移 |
| 数据库 | PostgreSQL | 结构化数据存储 |
| 缓存/队列 | Redis | 热点缓存、ARQ 任务队列 |
| AI 网关 | LiteLLM | 兼容任意模型，key 加密存储 |
| 实时推送 | WebSocket | FastAPI 原生支持（计划中） |
| 部署 | Docker Compose | 本地开发/单机生产 |

## 数据库表

| 表 | 说明 |
|----|------|
| `users` | 用户基础信息 |
| `events` | 日程，关联用户，支持 rrule、分类、外部来源 |
| `event_preparation_periods` | 日程的明确准备时间段 |
| `tasks` | 待办，含 deadline、优先级、状态 |
| `task_preparation_periods` | 待办的明确准备时间段 |
| `goals` | 长期目标及进度 |
| `ai_configs` | 用户 AI 配置（provider、端点、加密 key） |
| `ai_templates` | 系统预设提示词模板 |
| `notifications` | 已发送的早安消息等记录 |
| `special_dates` | 节日、生日等日期标记 |

## 快速开始

```bash
# 启动后端
cd backend
docker compose up -d

# 构建前端
cd frontend
D:/Flutter/bin/flutter build web

# 部署前端
cd frontend/build/web
python -m http.server 8080
```

访问 http://localhost:8080 使用，http://localhost:8000/docs 查看 API 文档。

## 安全

- 密码：bcrypt 哈希
- AI Key：服务端 Fernet AES 加密，密钥存环境变量
- 外部系统密码：永不上传，仅客户端使用
- API 通信强制 HTTPS，WebSocket 需 token 验证

## 许可证

AGPLv3 — 详见 [LICENSE](./LICENSE)