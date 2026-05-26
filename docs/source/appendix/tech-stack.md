技术栈详解
==========

后端
----

### FastAPI

**选择理由**: 异步原生、自动 OpenAPI 文档、强大的依赖注入系统。

关键用法：
- ``asynccontextmanager`` 管理应用生命周期
- ``Depends()`` 依赖注入（数据库会话、认证、授权）
- ``StreamingResponse`` 流式代理
- Pydantic 模型自动校验请求/响应

### SQLModel

**选择理由**: Pydantic + SQLAlchemy 2.0 合一，类型安全，减少样板代码。

关键用法：
- 所有模型同时是 Pydantic 模型和 SQLAlchemy 模型
- UUID 主键 + TimestampMixin 基类
- JSONB 字段用于灵活结构（CIDR 列表、Header、参数）
- 异步 session（``asyncpg`` 驱动）

### SQLAlchemy 2.0 (Async)

**选择理由**: 异步 ORM，与 FastAPI 配合良好。

关键用法：
- ``select()`` 风格查询
- 异步 session（``AsyncSession``）
- PostgreSQL enum 类型映射

### LiteLLM

**选择理由**: 统一 OpenAI/Anthropic/其他 LLM 的调用接口。

关键用法：
- ``litellm.acompletion`` -- OpenAI Chat Completions
- ``litellm.aresponses`` -- OpenAI Responses API
- ``litellm.anthropic_messages`` -- Anthropic Messages
- 流式和非流式支持

### Alembic

**选择理由**: SQLAlchemy 生态标准迁移工具。

关键用法：
- 异步迁移执行
- PostgreSQL enum 类型管理
- offline 模式（生成 SQL 文件）

前端
----

### SvelteKit 5

**选择理由**: 编译时框架，运行时极小，Svelte 5 runes 提供优雅的响应式。

关键用法：
- Svelte 5 runes（``$state``, ``$derived``, ``$props``）
- 单页管理控制台
- Vite 开发代理

### TypeScript

**选择理由**: 类型安全，与后端 Pydantic 模型对齐。

关键用法：
- 34 个类型定义（``types.ts``）镜像所有后端模型
- 泛型 API 客户端（``AdminApiClient``）
- 类型安全的校验器

### Lucide Icons

**选择理由**: 轻量、一致的图标库。

基础设施
--------

### PostgreSQL

**角色**: 主数据存储。

关键用法：
- JSONB 灵活字段
- UUID 主键
- 自动时间戳
- 索引优化（key_prefix 唯一索引）

### Redis

**角色**: 限流和并发控制。

关键用法：
- INCR + TTL 滑动窗口计数器
- INCR/DECR 并发槽位管理
- 900 秒安全 TTL 防止泄漏

开发工具
--------

### uv

**角色**: Python 包管理和环境管理。

### Vitest

**角色**: 前端单元测试。

### Playwright

**角色**: 前端 E2E 测试。

### httpx

**角色**: 测试中的异步 HTTP 客户端（ASGI transport）。

依赖关系
--------

```{mermaid}
graph TB
    subgraph Runtime
        FastAPI --> SQLModel
        FastAPI --> Redis_py[redis-py]
        FastAPI --> LiteLLM
        SQLModel --> SQLAlchemy
        SQLAlchemy --> asyncpg
        LiteLLM --> httpx_up[httpx]
    end

    subgraph Dev
        pytest --> httpx_test[httpx]
        Vitest --> Svelte
        Playwright --> Svelte
        Alembic --> SQLAlchemy
    end

    subgraph Infra
        asyncpg --> PG[(PostgreSQL)]
        Redis_py --> RD[(Redis)]
        httpx_up --> Upstream[LLM Upstream]
    end
```
