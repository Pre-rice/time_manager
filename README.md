# Time Manager

> **开源的个人时间管理助手** — 将未来一切事务汇集一处，用 AI 辅助规划与复盘。

## 功能

| 功能 | 状态 |
|------|------|
| 日程管理 | ✅ |
| 待办管理 | ✅ |
| 长期目标追踪 | ✅ |
| 日历月视图 | ✅ |
| AI 文本提取（自然语言→日程/待办） | ✅ |
| AI 早安消息 | ✅ |
| 复旦教务数据导入 | ✅（课程+考试） |
| 时间建议 | ⚠️ 后端完成 |
| 多端同步 | 📅 计划中 |
| 本地提醒 | 📅 计划中 |

## 技术栈

- **前端**：Flutter + Riverpod（Web/桌面/移动）
- **后端**：Python FastAPI + SQLAlchemy 异步
- **数据库**：PostgreSQL + Redis（Docker）
- **AI 网关**：LiteLLM（支持 DeepSeek 等）

## 快速开始

```bash
# 启动数据库
cd backend && docker compose up -d

# 启动后端（自动建表）
conda run --cwd backend -n time_manager \
  python -m uvicorn app.main:app --reload --port 8000

# 构建前端
cd frontend && flutter build web

# 部署前端
python -m http.server 8080 -d frontend/build/web
```

- 前端：http://localhost:8080
- API 文档：http://localhost:8000/docs

## AI 配置（以 DeepSeek 为例）

| 字段 | 值 |
|------|-----|
| API Key | `sk-你的密钥` |
| API 地址 | `https://api.deepseek.com` |
| 模型名称 | `deepseek-chat` |

API Key 使用 Fernet AES 加密存储。

## 复旦教务导入

在设置页配置学号和 UIS 密码，可自动同步：
- 当前学期课程列表
- 期末考试安排
- 期中考试安排

> 密码仅用于 CAS 认证，加密存储后不上传任何外部服务器。

## 安全

- 密码：bcrypt 哈希
- AI Key：服务端 AES 加密
- 复旦密码：加密存储，仅用于本地认证
- API 通信需 JWT token

## 许可证

AGPLv3