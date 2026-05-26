架构总览
========

系统架构
--------

LLM Gateway 采用经典的**分层架构**，分为四层：

```{mermaid}
graph TB
    subgraph clients["Clients"]
        C1["OpenAI SDK"]
        C2["Anthropic SDK"]
        C3["Codex and Claude Code"]
        C4["Browser Console"]
    end

    subgraph api_layer["API Layer"]
        A1["health"]
        A2["auth"]
        A3["admin"]
        A4["proxy"]
    end

    subgraph service_layer["Service Layer"]
        S1["security"]
        S2["policy"]
        S3["rate_limit"]
        S4["litellm_client"]
        S5["facts"]
    end

    subgraph data_layer["Data Layer"]
        D1[("PostgreSQL")]
        D2[("Redis")]
    end

    clients --> api_layer
    api_layer --> service_layer
    service_layer --> data_layer
    S4 --> U["Upstream LLM"]
```

目录结构
--------

```text
llm_gateway/
├── main.py                     # 入口：uvicorn 启动器
├── src/llm_gateway/
│   ├── main.py                 # FastAPI 应用工厂
│   ├── core/
│   │   └── config.py           # Pydantic Settings 配置
│   ├── api/
│   │   ├── health.py           # 健康检查端点
│   │   ├── auth.py             # 自助认证端点
│   │   ├── admin.py            # 管理 API（CRUD）
│   │   ├── proxy.py            # LLM 代理端点
│   │   └── deps.py             # FastAPI 依赖注入
│   ├── services/
│   │   ├── security.py         # 认证和身份服务
│   │   ├── policy.py           # 授权引擎
│   │   ├── rate_limit.py       # 限流服务
│   │   ├── litellm_client.py   # LiteLLM 适配层
│   │   ├── facts.py            # 用量记录
│   │   └── router_command.py   # vLLM Router 命令生成
│   └── db/
│       ├── models.py           # SQLModel 数据模型
│       └── session.py          # 数据库会话管理
├── alembic/                    # 数据库迁移
├── frontend/                   # SvelteKit 管理控制台
├── scripts/                    # 运维脚本
└── tests/                      # 集成测试
```

技术选型
--------

| 领域 | 技术 | 选择理由 |
|------|------|----------|
| 后端框架 | FastAPI | 异步原生、自动 OpenAPI 文档、依赖注入系统 |
| ORM | SQLModel (SQLAlchemy 2.0) | Pydantic 模型 + SQLAlchemy 模型合一，类型安全 |
| 数据库 | PostgreSQL | JSONB 支持灵活字段、成熟的索引和查询能力 |
| 缓存/限流 | Redis | 原子操作 INCR/DECR 适合限流、低延迟 |
| LLM 适配 | LiteLLM | 统一 OpenAI/Anthropic/其他协议的调用接口 |
| 迁移 | Alembic | SQLAlchemy 生态标准，支持异步 |
| 前端框架 | SvelteKit 5 | 编译时框架，运行时极小，runes 响应式 |
| 前端构建 | Vite 8 | 极快的 HMR，原生 TypeScript 支持 |
| 配置管理 | pydantic-settings | 类型安全的配置，支持 .env 文件 |

设计原则
--------

### 协议透明

Gateway 对下游客户端完全透明。OpenAI SDK、Anthropic SDK 直接将 API 端点指向 Gateway 即可，
无需修改请求格式。

### 全链路审计

每个请求产生一条 ``RequestFact`` 记录，包含：

- 请求 ID、开始/结束时间
- 端点类型（Chat/Responses/Messages）
- 认证主体、项目
- 模型别名、上游目标
- 是否流式
- 结果状态（成功/认证失败/策略拒绝/限流/适配失败/上游失败/客户端取消）
- Token 用量
- 错误信息

### 最小权限

- Gateway Key 只存储 SHA-256 哈希，不存明文
- 上游 API Key 在响应中自动脱敏
- 前端 JSON 查看器自动遮盖匹配 ``/key|token|secret|password/i`` 的字段

### 防御性编程

- 限流 Redis 不可用时，根据 ``rate_limit_fail_closed`` 配置决定是拒绝还是放行
- 上游请求失败时记录 ``ADAPTER_FAILURE`` 事实并返回 502
- 并发槽位有 900 秒安全 TTL，防止泄漏
