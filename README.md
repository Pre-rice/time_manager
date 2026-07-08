# Time Manager

> **开源的个人时间管理助手** — 将未来一切事务汇集一处，用 AI 辅助规划与复盘。

## 项目定位

- 核心实体：**日程、待办、长期目标**，专注时间管理，不加多余功能
- 用户完全掌控数据与 AI 密钥，外部系统密码不上传服务器
- AGPLv3 协议，人人可免费使用、修改、自部署

## 功能模块

1. **日程管理** — 含起止时间/全天，可设置周期。课程、考试是特殊日程。可推迟并记录反馈
2. **待办管理** — DDL、优先级、多种剩余时间视图
3. **长期目标** — 可记录进度，持续激励
4. **准备时长/时段** — 日程和待办可选填准备分钟数或指定准备时间段
5. **日历标识** — 节日、生日等特殊日期
6. **AI 自然语言提取** — 提交文本，返回结构化任务，确认添加
7. **AI 时间分配建议** — 根据事项和空闲时间生成准备时段建议
8. **AI 早安推送** — 每日定时生成人性化提醒与鼓励
9. **外部数据抓取** — 复旦教务/elearning、飞书群消息、微信通知监听（实验）
10. **多端同步** — 手机、桌面、Web 数据实时一致（WebSocket 推送）
11. **本地提醒** — 手机端闹钟/通知，桌面/Web 仅通知
12. **月/年报告** — 统计完成率、时间分布，含 AI 总结建议
13. **客户端自动更新** — 检测 GitHub Release 并引导升级

## 技术架构

| 层 | 技术 | 说明 |
|----|------|------|
| 前端 | Flutter + Riverpod | Android/iOS/Windows/macOS/Web |
| 后端 | Python FastAPI + SQLAlchemy 异步 | RESTful API，Alembic 迁移 |
| 数据库 | PostgreSQL | 结构化数据存储 |
| 缓存/队列 | Redis | 热点缓存、ARQ 任务队列 |
| AI 网关 | LiteLLM | 兼容任意模型，key 加密存储 |
| 实时推送 | WebSocket | FastAPI 原生支持 |
| 后台任务 | ARQ worker + cron | 定时早安消息、报告生成 |
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

## 外部集成

- **复旦系统**：客户端独立 Dart 包 `fudan_scraper`，密码仅内存使用，结果经 `/sync/upload` 同步
- **飞书**：服务端接收应用机器人事件，AI 提取后直接创建任务
- **微信**：Android 端 `NotificationListenerService` 实验模块，编译开关控制，强提示风险

## 安全

- 密码：bcrypt 哈希
- AI Key：服务端 Fernet AES 加密，密钥存环境变量
- 外部系统密码：永不上传，仅客户端使用
- API 通信强制 HTTPS，WebSocket 需 token 验证

## 许可证

AGPLv3 — 详见 [LICENSE](./LICENSE)