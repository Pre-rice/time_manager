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

## 工作流程规范

每次完成任务后必须按以下顺序自行验证：

### 1. 后端测试（curl 测试 API）
```bash
# 注册测试
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@test.com","password":"123456"}'

# 登录测试
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

## 前端部署与查看

```bash
cd e:\编程\time_manager\frontend
D:/Flutter/bin/flutter build web
cd e:\编程\time_manager\frontend\build\web
python -m http.server 8080
```

> 不要用 `flutter run -d edge`，终端关闭时浏览器也会关闭。

### 访问地址
- 前端：http://localhost:8080
- API 文档：http://localhost:8000/docs

## 启动后端服务

```bash
cd e:\编程\time_manager\backend
docker compose up -d
```

## 常见问题

### 错误提示原则
面向用户的错误提示必须：
1. 用**中文**
2. **说清楚具体原因**（如"邮箱格式不正确"，而不是"注册失败"）
3. 不暴露技术细节（如 DioException、状态码等）

### 后端 422 错误处理
Pydantic 验证失败返回 422，格式为：
```json
{"detail":[{"type":"value_error","loc":["body","email"],"msg":"value is not a valid email address...","input":"...","ctx":{...}}]}
```
- 这是**数组**，不是对象，`data['detail']` 拿到的是列表
- 需要从列表中的每个元素提取 `msg` 字段展示给用户
- 常见的验证失败：邮箱格式不对、字段缺失、字段类型错误等

## 已踩过的坑

- `flutter run -d edge` 会在终端退出时关闭浏览器 → 应改用 `python -m http.server 8080`
- Dio 的 401/409/422 异常处理：**必须用 `e is DioException` 检查类型，用 `e.response?.statusCode` 获取状态码**。不要用 `msg.contains('409')` 字符串匹配
- 后端返回的中文错误信息（如"用户名或邮箱已存在"）可以通过 `e.response?.data['detail']` 提取
- 后端 422 错误的 detail 是**数组**，不是字符串，提取时要区分
- 注册页面前端虽然验证了邮箱格式，但后端也会验证，前端必须能展示后端返回的具体验证错误
- Python FastAPI 的 EmailStr 需要安装 `email-validator` 包
- 所有面向用户的错误提示必须**精准描述原因**，不能笼统说"失败"