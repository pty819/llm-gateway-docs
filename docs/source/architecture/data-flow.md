数据流
======

请求生命周期
------------

一个 LLM 代理请求的完整生命周期如下：

```{mermaid}
sequenceDiagram
    participant C as Client
    participant P as proxy.py
    participant Auth as security.py
    participant Pol as policy.py
    participant RL as rate_limit.py
    participant Lite as litellm_client.py
    participant Facts as facts.py
    participant U as Upstream

    C->>P: POST /v1/chat/completions
    Note over P: 解析请求体，提取 model 和 stream

    P->>Auth: authenticate_gateway_key(key)
    alt Key 无效
        Auth-->>Facts: record AUTH_FAILURE
        Auth-->>P: 401 Unauthorized
        P-->>C: 401
    end

    P->>Pol: resolve_route_context(alias, subject, ip)
    alt 无权限
        Pol-->>Facts: record POLICY_DENIAL
        Pol-->>P: 403 Forbidden
        P-->>C: 403
    end

    P->>RL: check_request_rate(policy)
    alt 超限
        RL-->>Facts: record RATE_LIMITED
        RL-->>P: 429 Too Many Requests
        P-->>C: 429
    end

    alt 非流式
        RL->>RL: acquire concurrency slot
        P->>Lite: completion_once(model, messages, ...)
        Lite->>U: HTTP POST
        U-->>Lite: Response + Usage
        Lite-->>P: LiteLLMCallResult
        RL->>RL: release concurrency slot
        P->>Facts: record SUCCESS fact
        P-->>C: 200 OK + JSON body
    else 流式
        P->>Lite: completion_stream(model, messages, ...)
        Lite->>U: HTTP POST (stream)
        loop SSE events
            U-->>Lite: data chunk
            Lite-->>P: (event, usage) tuple
            P-->>C: SSE event
        end
        RL->>RL: release concurrency slot
        P->>Facts: record SUCCESS fact
        P-->>C: [DONE]
    end
```

认证流程
--------

### Gateway Key 认证

```{mermaid}
graph LR
    A[Raw Key: gw-abc123...] --> B[提取前缀: gw-abc]
    B --> C[数据库查询: key_prefix + ACTIVE]
    C --> D[SHA-256 哈希]
    D --> E[HMAC 常量时间比较]
    E --> F{匹配?}
    F -->|Yes| G[检查 Subject/Project 状态]
    F -->|No| H[认证失败]
    G --> I{均为 ACTIVE?}
    I -->|Yes| J[返回 AuthContext]
    I -->|No| H
```

Gateway Key 的格式为 ``gw-<base64url(32 bytes)>``，总长度约 47 个字符。
数据库中存储 ``key_prefix``（前 8 个字符，用于索引）和 ``key_hash``（完整 key 的 SHA-256）。

### Session Token 认证

Session Token 格式为 ``sess-<base64url(32 bytes)>``，用于浏览器会话。
查询逻辑与 Gateway Key 相同（前缀索引 + 哈希验证）。
Session 有 TTL（默认 7 天）和手动撤销。

路由解析
--------

```{mermaid}
graph TD
    A[请求: model=gpt-4o] --> B[查找 ModelAlias]
    B --> C{alias 存在?}
    C -->|No| D[404 Model Not Found]
    C -->|Yes| E[检查 ModelEntitlement]
    E --> F{有直接授权?}
    F -->|Yes| G[检查 IP 策略]
    F -->|No| H[检查 ModelTeamGrant]
    H --> I{有团队授权?}
    I -->|No| J[403 Forbidden]
    I -->|Yes| G
    G --> K{IP 策略?}
    K -->|ALL_PASS| L[查找 UpstreamTarget]
    K -->|ALLOWLIST| M{IP 在白名单?}
    M -->|No| J
    M -->|Yes| L
    L --> N{上游可用?}
    N -->|Yes| O[返回 RouteContext]
    N -->|No| P[503 No Upstream]
```

管理 API 认证
-------------

管理 API 支持两种认证方式：

1. **Admin Token** -- 通过 ``X-Admin-Token`` Header 传入，适合 CI/CD 和脚本
2. **Session Token** -- 通过 ``X-Session-Token`` 或 ``Authorization: Bearer sess-...`` 传入，适合浏览器控制台

```{mermaid}
graph LR
    A[Admin Request] --> B{X-Admin-Token?}
    B -->|Yes| C[与 settings.admin_token 比较]
    C --> D{匹配?}
    D -->|Yes| E[Allow]
    D -->|No| F[401]
    B -->|No| G{Bearer sess-...?}
    G -->|Yes| H[authenticate_user_session]
    H --> I{有效 Session?}
    I -->|Yes| J{subject.is_admin?}
    J -->|Yes| E
    J -->|No| K[403 Not Admin]
    I -->|No| F
    G -->|No| F
```
