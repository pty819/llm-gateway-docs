数据模型
========

枚举类型
--------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - 枚举
     - 值
   * - SubjectType
     - ``USER``, ``SERVICE``
   * - ResourceState
     - ``ACTIVE``, ``DISABLED``
   * - IPPolicyMode
     - ``ALL_PASS``, ``ALLOWLIST``
   * - RequestOutcome
     - ``SUCCESS``, ``AUTH_FAILURE``, ``POLICY_DENIAL``, ``RATE_LIMITED``, ``ADAPTER_FAILURE``, ``UPSTREAM_FAILURE``, ``CLIENT_CANCELLED``
   * - EndpointFamily
     - ``OPENAI_CHAT``, ``OPENAI_RESPONSES``, ``ANTHROPIC_MESSAGES``
   * - UsageSource
     - ``LITELLM``, ``MISSING``
   * - RouterPolicy
     - ``CONSISTENT_HASH``, ``CACHE_AWARE``

模型基类
--------

所有模型继承自 ``TimestampMixin``，提供 ``created_at`` 和 ``updated_at`` 自动时间戳。
所有模型使用 UUID 主键。

核心模型关系图
--------------

```{mermaid}
graph LR
    subgraph 认证
        S[Subject] --> GK[GatewayKey]
        S --> US[UserSession]
    end

    subgraph 授权
        S --> PM[ProjectMembership]
        S --> TM[TeamMembership]
        TM --> T[Team]
        T --> MTG[ModelTeamGrant]
        MTG --> MA[ModelAlias]
        S --> ME[ModelEntitlement]
        ME --> MA
    end

    subgraph 路由
        MA --> UT[UpstreamTarget]
        MA --> RCC[RouterCommandConfig]
    end

    subgraph 限流
        RP[RatePolicy] -.-> GK
        RP -.-> S
        RP -.-> P[Project]
    end

    subgraph 审计
        S --> RF[RequestFact]
        S --> AE[AuditEvent]
    end
```

字段详解
--------

### ModelAlias

.. list-table::
   :header-rows: 1

   * - 字段
     - 类型
     - 说明
   * - alias
     - str (unique)
     - 虚拟模型名，如 ``gpt-4o``
   * - upstream_model_name
     - str
     - 上游实际模型名，如 ``openai/gpt-4o``
   * - litellm_model
     - str
     - LiteLLM 识别的模型标识
   * - supports_streaming
     - bool
     - 是否支持流式输出
   * - supports_tools
     - bool
     - 是否支持 Function Calling
   * - supports_reasoning
     - bool
     - 是否支持推理模式
   * - ip_policy_mode
     - IPPolicyMode
     - IP 策略模式
   * - ip_allowlist_cidrs
     - JSONB
     - CIDR 白名单列表

### UpstreamTarget

.. list-table::
   :header-rows: 1

   * - 字段
     - 类型
     - 说明
   * - model_alias_id
     - FK
     - 关联的模型别名
   * - base_url
     - str
     - 上游端点 URL
   * - api_key_ref
     - str (nullable)
     - 密钥引用（外部管理）
   * - api_key_value
     - str (nullable)
     - 密钥值（直接存储）
   * - health_path
     - str
     - 健康检查路径
   * - extra_headers
     - JSONB
     - 额外 HTTP Header

### RequestFact

.. list-table::
   :header-rows: 1

   * - 字段
     - 类型
     - 说明
   * - request_id
     - str
     - 唯一请求标识
   * - started_at / ended_at
     - timestamp
     - 请求时间范围
   * - endpoint_family
     - EndpointFamily
     - 协议类型
   * - subject_id
     - FK
     - 认证主体
   * - project_id
     - FK
     - 归属项目
   * - model_alias
     - str
     - 请求的模型别名
   * - upstream_target_id
     - FK
     - 实际上游
   * - streaming
     - bool
     - 是否流式
   * - outcome
     - RequestOutcome
     - 请求结果
   * - prompt/completion/total_tokens
     - int
     - Token 用量
   * - error_class / error_detail
     - str
     - 错误信息
