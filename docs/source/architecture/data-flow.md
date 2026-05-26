数据流
======

请求生命周期
------------

一个 LLM 代理请求的完整生命周期如下：

```{mermaid}
sequenceDiagram
    participant C as Client
    participant P as proxy_py
    participant Auth as security_py
    participant Pol as policy_py
    participant RL as rate_limit_py
    participant Lite as litellm_client_py
    participant Facts as facts_py
    participant U as Upstream

    C->>P: POST /v1/chat/completions
    Note over P: parse request body, extract model and stream

    P->>Auth: authenticate_gateway_key(key)
    alt Key invalid
        Auth-->>Facts: record AUTH_FAILURE
        Auth-->>P: 401 Unauthorized
        P-->>C: 401
    end

    P->>Pol: resolve_route_context(alias, subject, ip)
    alt No permission
        Pol-->>Facts: record POLICY_DENIAL
        Pol-->>P: 403 Forbidden
        P-->>C: 403
    end

    P->>RL: check_request_rate(policy)
    alt Rate exceeded
        RL-->>Facts: record RATE_LIMITED
        RL-->>P: 429 Too Many Requests
        P-->>C: 429
    end

    alt Non-streaming
        RL->>RL: acquire concurrency slot
        P->>Lite: completion_once(model, messages, ...)
        Lite->>U: HTTP POST
        U-->>Lite: Response + Usage
        Lite-->>P: LiteLLMCallResult
        RL->>RL: release concurrency slot
        P->>Facts: record SUCCESS fact
        P-->>C: 200 OK + JSON body
    else Streaming
        P->>Lite: completion_stream(model, messages, ...)
        Lite->>U: HTTP POST stream
        loop SSE events
            U-->>Lite: data chunk
            Lite-->>P: event, usage tuple
            P-->>C: SSE event
        end
        RL->>RL: release concurrency slot
        P->>Facts: record SUCCESS fact
        P-->>C: DONE
    end
```

认证流程
--------

### Gateway Key 认证

```{mermaid}
graph LR
    A[Raw Key gw-abc123...] --> B[Extract prefix gw-abc]
    B --> C[DB query key_prefix + ACTIVE]
    C --> D[SHA-256 hash]
    D --> E[HMAC constant-time compare]
    E --> F{Match?}
    F -->|Yes| G[Check Subject/Project state]
    F -->|No| H[Auth failure]
    G --> I{Both ACTIVE?}
    I -->|Yes| J[Return AuthContext]
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
    A[Request model=gpt-4o] --> B[Find ModelAlias]
    B --> C{Alias exists?}
    C -->|No| D[404 Model Not Found]
    C -->|Yes| E[Check ModelEntitlement]
    E --> F{Direct grant?}
    F -->|Yes| G[Check IP policy]
    F -->|No| H[Check ModelTeamGrant]
    H --> I{Team grant?}
    I -->|No| J[403 Forbidden]
    I -->|Yes| G
    G --> K{IP policy?}
    K -->|ALL_PASS| L[Find UpstreamTarget]
    K -->|ALLOWLIST| M{IP in allowlist?}
    M -->|No| J
    M -->|Yes| L
    L --> N{Upstream available?}
    N -->|Yes| O[Return RouteContext]
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
    B -->|Yes| C[Compare with settings.admin_token]
    C --> D{Match?}
    D -->|Yes| E[Allow]
    D -->|No| F[401]
    B -->|No| G{Bearer sess-...?}
    G -->|Yes| H[authenticate_user_session]
    H --> I{Valid Session?}
    I -->|Yes| J{subject.is_admin?}
    J -->|Yes| E
    J -->|No| K[403 Not Admin]
    I -->|No| F
    G -->|No| F
```
