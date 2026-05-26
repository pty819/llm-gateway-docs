数据库设计
==========

ER 图
-----

```{mermaid}
erDiagram
    Subject ||--o{ Project : owns
    Subject ||--o{ ProjectMembership : in
    Subject ||--o{ GatewayKey : has
    Subject ||--o{ TeamMembership : in
    Subject ||--o{ UserSession : has
    Subject ||--o{ RequestFact : records
    Subject ||--o{ AuditEvent : triggers

    Project ||--o{ ProjectMembership : contains
    Project ||--o{ GatewayKey : scopes
    Project ||--o{ RequestFact : records

    ModelAlias ||--o{ UpstreamTarget : routes_to
    ModelAlias ||--o{ ModelEntitlement : granted_via
    ModelAlias ||--o{ ModelTeamGrant : granted_via
    ModelAlias ||--o{ RouterCommandConfig : configured_by
    ModelAlias ||--o{ RequestFact : requested_as

    Team ||--o{ TeamMembership : has
    Team ||--o{ ModelTeamGrant : granted

    UpstreamTarget ||--o{ RequestFact : served_by

    Subject {
        uuid id PK
        string name
        string type USER_or_SERVICE
        string state ACTIVE_or_DISABLED
        string login_username UK
        string password_hash
        boolean is_admin
        timestamp created_at
        timestamp updated_at
    }

    Project {
        uuid id PK
        string name UK
        string state
        uuid owner_subject_id FK
        timestamp created_at
        timestamp updated_at
    }

    ModelAlias {
        uuid id PK
        string alias UK
        string upstream_model_name
        string litellm_model
        boolean supports_streaming
        boolean supports_tools
        boolean supports_reasoning
        string ip_policy_mode ALL_PASS_or_ALLOWLIST
        jsonb ip_allowlist_cidrs
        timestamp created_at
        timestamp updated_at
    }

    GatewayKey {
        uuid id PK
        uuid subject_id FK
        uuid project_id FK
        string name
        string key_prefix indexed
        string key_hash
        string state
        timestamp expires_at
        timestamp created_at
        timestamp updated_at
    }

    Team {
        uuid id PK
        string name UK
        string state
        boolean is_builtin
        timestamp created_at
        timestamp updated_at
    }

    UpstreamTarget {
        uuid id PK
        uuid model_alias_id FK
        string name
        string base_url
        string api_key_ref
        string api_key_value
        string health_path
        jsonb extra_headers
        timestamp created_at
        timestamp updated_at
    }

    RequestFact {
        uuid id PK
        string request_id
        timestamp started_at
        timestamp ended_at
        string endpoint_family
        uuid subject_id FK
        uuid project_id FK
        string model_alias
        uuid upstream_target_id FK
        boolean streaming
        string outcome
        string usage_source
        integer prompt_tokens
        integer completion_tokens
        integer total_tokens
        string error_class
        string error_detail
    }
```

表说明
------

### Subject（主体）

用户或服务账户。每个 Subject 有唯一的 ``login_username``（用户）或系统分配的名称（服务账户）。
``is_admin`` 标识管理员，管理员可以访问所有管理 API。

### Project（项目）

用量归属单元。每个用户注册时自动创建个人项目。
项目可以关联多个成员（ProjectMembership），用于多人协作场景的用量归属。

### ModelAlias（模型别名）

虚拟模型名到实际模型名的映射。例如 ``gpt-4o`` -> ``openai/gpt-4o``。
通过别名机制，可以在不修改客户端代码的情况下切换上游模型。

支持三个能力标记：
- ``supports_streaming`` -- 是否支持流式输出
- ``supports_tools`` -- 是否支持 Function Calling
- ``supports_reasoning`` -- 是否支持推理模式

IP 策略有两种模式：
- ``ALL_PASS`` -- 不限制来源 IP
- ``ALLOWLIST`` -- 仅允许 ``ip_allowlist_cidrs`` 中的 CIDR 网段

### GatewayKey（网关密钥）

API 认证凭据。格式 ``gw-<random>``，仅创建时返回明文。
数据库存储 ``key_prefix``（前 8 字符，用于查询）和 ``key_hash``（SHA-256，用于验证）。

### Team / TeamMembership（团队）

RBAC 的核心。内置两个团队：
- ``guest`` -- 所有注册用户自动加入，用于基础模型授权
- ``admin`` -- 管理员团队，创建新模型时自动授权

### ModelTeamGrant（团队模型授权）

团队级别的模型访问授权。管理员创建一个 Grant 后，
该团队的所有成员自动获得模型访问权限。

### UpstreamTarget（上游目标）

实际的上游推理端点。一个 ModelAlias 可以有多个 UpstreamTarget（预留多上游支持）。
``api_key_ref`` 和 ``api_key_value`` 分别支持引用式和直接式密钥存储。

### RouterCommandConfig（路由器命令配置）

vLLM Router 的配置。存储 ``worker_urls``、``policy``（一致性哈希或缓存感知）、
端口和额外参数。通过 ``render_router_command()`` 渲染为可执行的 CLI 命令。

### RatePolicy（限流策略）

三层限流配置：

| Scope | 作用域 | 示例 |
|-------|--------|------|
| key | 单个 Gateway Key | 某个 Key 限制 60 RPM |
| subject | 单个用户/服务账户 | 某用户限制 120 RPM |
| project | 单个项目 | 某项目限制 500 RPM |

生效规则：取所有匹配策略中的**最小值**（最严格 wins）。

### RequestFact（请求事实）

不可变的请求级分析数据。记录每个请求的完整生命周期，
包括认证、授权、路由、用量等所有关键信息。

### AuditEvent（审计事件）

管理员操作的审计追踪。记录谁（actor）在什么时间对什么资源做了什么操作，结果如何。

迁移策略
--------

使用 Alembic 进行数据库迁移，支持异步执行：

- **0001_initial_schema** -- 创建初始表结构（核心网关）
- **0002_auth_teams** -- 添加自助认证和团队 RBAC 相关表

迁移脚本支持 ``offline`` 模式（生成 SQL 文件）和 ``online`` 模式（直接执行）。
