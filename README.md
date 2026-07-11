# 智能客服系统

严格分层 / LangGraph 多 Agent / 双记忆 / 提示词版本管理 / 反馈自优化 / 运维观测。

## 一、项目分层结构

```
chat_customer/
├── config/                  配置层（settings + seed 提示词）
├── app/
│   ├── llm/                 LLM 推理层（client/embedding/熔断/重试/格式修复）
│   ├── tools/               工具层（订单/用户/RAG/安全）
│   ├── storage/             数据库存储层（SQLite + Qdrant）
│   ├── memory/              记忆层（短期会话 + 长期 RAG + 用户习惯）
│   ├── prompts/             提示词版本管理（CRUD/启用切换/对比）
│   ├── feedback/            反馈与自优化（差评分析/自动优化/示例库）
│   ├── agents/              Agent 调度层（LangGraph 主图 + 6 个子 Agent + 协同）
│   ├── security/            安全鉴权（JWT/API Key/限流/敏感词）
│   ├── api/                 API 接口层（12 个路由组）
│   ├── services/            业务编排层
│   └── logger/              日志运维层
├── frontend/                前端页面（React + Vite + TS + AntD）
│   └── src/
│       ├── api/             Axios 实例 + 按业务模块的 API 函数
│       ├── components/      通用组件（PlaceholderPage 等占位页组件）
│       ├── pages/
│       │   ├── business/    业务中心首页（快速入口卡片）
│       │   ├── chat/        对话工作台
│       │   ├── dashboard/   数据看板
│       │   ├── knowledge/   RAG 知识库管理
│       │   ├── prompts/     提示词版本管理
│       │   ├── feedback/    反馈历史
│       │   ├── ops/         运维观测
│       │   ├── recycle/     回收站
│       │   ├── profile/     个人资料
│       │   ├── system/      通用设置
│       │   ├── team/        团队设置下的二级页（占位）
│       │   │   ├── config-list/      配置列表
│       │   │   ├── wechat/           微信客服
│       │   │   ├── agent-manage/     客服管理
│       │   │   ├── visitor-manage/   访客管理
│       │   │   ├── service-stats/    服务统计
│       │   │   └── douyin/           抖音接入
│       │   └── mall/        商城设置下的二级页
│       │       ├── merchant/         商家设置
│       │       └── order-manage/     订单管理
│       └── stores/          Zustand 状态管理（auth 等）
├── scripts/                 运维脚本（init_db / init_qdrant / seed_*）
└── tests/                   测试
```

### 前端侧栏分组（一级菜单 / 二级菜单）

| 一级菜单 | 二级菜单 | 备注 |
|---|---|---|
| **业务中心** | 对话工作台 / 数据看板 / 提示词版本 / 反馈历史 / 运维观测 / 回收站 | 日常运营相关 |
| **团队设置** | 机器人设置 / 大模型设置 / RAG 知识库 / 配置列表 / 微信客服 / 客服管理 / 访客管理 / 服务统计 / 抖音接入 | 9 个二级；前 3 个接现有功能，6 个占位页 |
| **商城设置** | 商家设置 / 订单管理 | 2 个占位页 |
| **个人设置** | 个人资料 | 1 个表单页 |
| **系统设置** | 通用设置 | 1 个占位页 |

侧栏使用 antd `Menu.mode="inline"` + `defaultOpenKeys`，按 URL 路径自动展开当前一级分组。

分层依赖：`api → services → agents → tools + memory + llm + storage`，`logger` 横切，`config` 单向只读。

## 二、SQLite 完整建表

见 [app/storage/sqlite/migrations/001_init.sql](app/storage/sqlite/migrations/001_init.sql)。

包含表：users / api_keys / customers / orders / sessions / messages / prompt_versions / feedback / feedback_analysis / examples / user_preferences / knowledge_meta / run_logs / tool_call_logs / api_call_logs / token_usage / page_operation_logs / deleted_records / stats_daily。

所有删除走软删 + `deleted_records` 快照表，支持一键回溯。

## 三、.env 配置

复制 `.env.example` 为 `.env`，填入：

```env
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
LLM_API_KEY=你的key
LLM_MODEL=glm-4-plus
EMBEDDING_BASE_URL=https://open.bigmodel.cn/api/paas/v4
EMBEDDING_API_KEY=你的key
EMBEDDING_MODEL=embedding-3
QDRANT_URL=http://localhost:6333
JWT_SECRET=随机长字符串
```

支持任意 OpenAI 兼容协议模型（GLM / Qwen / DeepSeek / Moonshot / 豆包 / OpenAI），改 `.env` 即可切换，无需改代码。

## 四、启动步骤

### 1. 后端

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库（自动建表 + 创建管理员 admin/admin123）
python scripts/init_db.py

# 初始化 Qdrant 集合（需先启动 Qdrant）
python scripts/init_qdrant.py

# 导入种子提示词
python scripts/seed_prompts.py

# 导入演示数据
python scripts/seed_data.py

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Qdrant（Docker）

```bash
docker-compose up -d qdrant
# 或单独：docker run -p 6333:6333 qdrant/qdrant
```

### 3. 前端

```bash
cd frontend
npm install
npm run dev
```

### 4. 一键 Docker

```bash
docker-compose up -d
```

## 五、访问地址

| 服务 | 地址 |
|---|---|
| 前端 Web | http://localhost:5173 |
| 后端 API 文档（Swagger） | http://localhost:8000/docs |
| 后端健康检查 | http://localhost:8000/health |
| Qdrant 控制台 | http://localhost:6333/dashboard |

## 六、API 调用示例

### 6.1 登录获取 token

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

返回：
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer",
    "username": "admin",
    "role": "admin",
    "user_id": 1
  }
}
```

### 6.2 发起对话（JWT 鉴权）

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"message":"我的订单 ORD20260702002 怎么还没发货","session_id":null}'
```

返回：
```json
{
  "success": true,
  "data": {
    "session_id": "sess_abc123",
    "answer": "您的订单 ORD20260702002 当前状态为待发货...",
    "intent": "order",
    "agent": "order",
    "tool_calls_count": 1,
    "latency_ms": 2350,
    "token_input": 520,
    "token_output": 180,
    "message_id": 42
  }
}
```

### 6.3 对外开放接口（API Key 鉴权 + 限流）

```bash
curl -X POST http://localhost:8000/api/chat/external \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"message":"退货流程是什么"}'
```

### 6.4 提交反馈（差评自动分析 + 优化提示词）

```bash
curl -X POST http://localhost:8000/api/feedback \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"message_id":42,"session_id":"sess_abc123","rating":"bad","comment":"回答没说清楚时效"}'
```

返回会包含 `analysis`（原因分析）和 `optimize`（自动生成的优化版本 id）。

### 6.5 提示词版本对比

```bash
curl -X POST http://localhost:8000/api/prompts/compare \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"version_a_id":1,"version_b_id":2,"test_question":"退货多久到账"}'
```

返回两个版本各自的回答，便于对比效果。

### 6.6 上传知识库文档

```bash
curl -X POST http://localhost:8000/api/knowledge/upload \
  -H "Authorization: Bearer eyJ..." \
  -F "file=@产品手册.md" \
  -F "title=产品手册"
```

### 6.7 运维观测

```bash
curl http://localhost:8000/api/ops/tool-stats?days=7 \
  -H "Authorization: Bearer eyJ..."
```

## 七、核心特性清单

- [x] 严格分层：工具/LLM/存储/API/前端/日志完全隔离，标准化参数交互
- [x] .env 配置驱动：LLM 地址/密钥/模型名全部配置化，无硬编码
- [x] 熔断 + 重试 + 超时：`MAX_TOOL_ROUNDS` / `TASK_TIMEOUT_SEC` / 熔断器
- [x] 输出格式自修复：JSON 坏掉自动修复，排版混乱自动整理
- [x] LangGraph 多 Agent：主调度 + 售前/售后/订单/RAG/安全 5 子 Agent + 兜底
- [x] 子任务协同：复杂请求自动拆「采集→整理→复盘」三阶段
- [x] 双记忆：短期会话 + 长期 RAG
- [x] 提示词版本管理：永久保存所有版本 / 一键切换 / 版本对比
- [x] 反馈自优化：差评自动分析原因 + 自动生成优化提示词 + 优质/差评示例库
- [x] SQLite 统一持久化 + 软删回收站一键回溯 + 表级写锁防并发
- [x] 页面状态保留：弹窗/侧边面板关闭后输入与生成内容不清空
- [x] 历史会话关键词检索
- [x] 安全：JWT 账号鉴权 + API Key + 限流 + 调用日志 + 敏感词过滤
- [x] 运维观测面板：任务耗时 / 工具成功率 / Token 消耗 / 高频错误
- [x] 全链路 trace_id + run_logs 落库

## 八、后续扩展

- Agent 提示词：当前 `config/prompts/*.md` 为占位，可直接编辑或通过「提示词版本」页面在线编辑保存
- 业务字段：users / orders 等表用通用最小集，可在 `models.py` + repo 扩展
- 流式输出：当前 `chat_stream` 简化实现，可改造为 graph 内部真正流式
