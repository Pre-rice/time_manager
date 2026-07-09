# 开发注意事项

## 元原则（Meta Principles）

> 本文档必须持续迭代。遇到任何变更、踩坑经验、用户指出的问题，都必须先记录到文档中，再修复代码。

1. **先记录，再改正** — 用户指出问题后，先更新文档，再去改代码
2. **自己跑完所有流程再找用户** — 后端测试 → 部署，全部通过后才报告结果
3. **遇到问题要说** — 连不上、构建失败等要告知用户，不能跳过
4. **文档要持续迭代** — 每次发现问题、学到经验都要更新到对应文档中
5. **文档分工明确** — `NOTES.md` 记注意事项和经验教训，`DEVELOPMENT.md` 记项目开发指南和进度
6. **思考过程用中文** — 所有分析和推理都要用中文
7. **错误提示必须精准** — 不能笼统说"注册失败"，要告诉用户具体原因，如"邮箱格式不正确"
8. **学会从后端错误中提取具体信息** — 后端返回了详细的验证错误（422），前端要提取并展示给用户
9. **持续同步 Git** — 完成阶段性工作后立即提交，不要堆积变更

## 工作流程规范

每次完成任务后必须按以下顺序自行验证：

### 1. 后端测试（curl 测试 API）
```bash
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@test.com","password":"123456"}'

curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123"}'
```

### 2. 部署给用户查看
```bash
cd e:\编程\time_manager\frontend
D:/Flutter/bin/flutter build web
cd e:\编程\time_manager\frontend\build\web
python -m http.server 8080
```

## Docker 相关问题

### Docker Desktop C 盘空间不足
Docker 默认把镜像和容器存储在 `C:\Users\Administrator\AppData\Local\Docker`，会占用大量空间。

**迁移方法：**
1. 右键系统托盘 Docker 图标 → **Settings** → **Resources** → **Advanced**
2. 修改 **Disk image location** 为 `D:\docker-data`
3. 点击 **Apply & Restart**
4. 或者完全退出 Docker，把 `C:\Users\Administrator\AppData\Local\Docker` 整个移到 D 盘，创建 `mklink /J` 符号链接

**清理空间：**
```bash
docker system prune -af  # 删除所有未使用的镜像、容器、网络
```

### Docker 启动失败
- `failed to connect to the docker API` → Docker Desktop 崩溃，需重启
- `no configuration file provided` → 需要在 backend 目录下执行命令

### 常用 Docker 命令
```bash
# 在 backend 目录下
cd e:\编程\time_manager\backend
docker compose up -d           # 启动
docker compose up -d --build api  # 重建 API 并启动
docker ps                      # 查看运行状态
docker logs backend-api-1      # 查看 API 日志
```

## 常见问题

### 错误提示原则
面向用户的错误提示必须：
1. 用**中文**
2. **说清楚具体原因**（如"邮箱格式不正确"，而不是"注册失败"）
3. 不暴露技术细节（如 DioException、状态码等）

### 后端 422 错误处理
Pydantic 验证失败返回 422，格式为数组：
```json
{"detail":[{"type":"value_error","loc":["body","email"],"msg":"value is not a valid email address..."}]}
```
需要从列表中的每个元素提取 `msg` 字段展示给用户。

## 已踩过的坑

- `flutter run -d edge` 会在终端退出时关闭浏览器 → 应改用 `python -m http.server 8080`
- Dio 的 401/409/422 异常处理：**必须用 `e is DioException` + `e.response?.statusCode`**，不要 `msg.contains()`
- 后端 422 错误的 detail 是数组不是字符串
- 后端返回的中文错误信息（如"用户名或邮箱已存在"）可以通过 `e.response?.data['detail']` 提取
- 所有面向用户的错误提示必须精准描述原因
- Python FastAPI 的 EmailStr 需要安装 `email-validator` 包
- **Git 要持续提交** — 完成一个阶段就提交一次，不要堆积
- **Dart `const` 静态常量不能用 `()` 调用** — `static const empty` 定义后使用 `_HomeData.empty` 而不是 `_HomeData.empty()`
- **Dart `List<dynamic>` 类型处理** — `api.getEvents()` 返回 `List<dynamic>`，不能直接调用 `.where()` 或 `.cast<T>()`，需要手动用 `for` 循环遍历并 `Map<String, dynamic>.from(e)` 转换
- **Flutter `StatefulBuilder` 用于 AlertDialog 内部状态更新** — 在 `showDialog` 中想更新局部状态（如日期选择），需要用 `StatefulBuilder` 包裹 builder
- **错误提示要从后端提取具体信息** — 422 的 `detail` 是数组，409 的 `detail` 是字符串，要区分处理
- **AI 文本提取的日期偏移问题** — LLM 默认处理时可能用 UTC 时间或"今天"的语义取决于上下文，需要在前端校准日期
- **AI 提取结果需要可编辑** — 提取出的日程/待办需要在添加到系统前允许用户修改
- **多次提取结果要叠加** — 新提取的内容不能覆盖上次结果，要追加到已有列表
- **星期的起始日配置** — 需要全局设置"周一/周日作为每周第一天"，影响日历视图和日期选择器
- **删除 `taskkill /F /IM python.exe` 再重启服务器的正确做法** — 先单独执行 taskkill，确认杀死后再单独启动，不要链式执行
- **需要 `table_calendar` 包来实现月视图**
