服务层
======

服务层封装了所有业务逻辑，被 API 层通过依赖注入调用。

```{mermaid}
graph TB
    API[API Layer] --> S1[security.py]
    API --> S2[policy.py]
    API --> S3[rate_limit.py]
    API --> S4[litellm_client.py]
    API --> S5[facts.py]
    API --> S6[router_command.py]

    S1 --> DB[(PostgreSQL)]
    S2 --> DB
    S3 --> RD[(Redis)]
    S4 --> UP[Upstream LLM]
    S5 --> DB
```

security.py -- 认证与身份
-------------------------

### 密钥生成

| 函数 | 输出 | 用途 |
|------|------|------|
| ``generate_gateway_key()`` | ``gw-<token_urlsafe(32)>`` | API 认证密钥 |
| ``generate_session_token()`` | ``sess-<token_urlsafe(32)>`` | 浏览器会话令牌 |

### 密码管理

| 函数 | 算法 | 说明 |
|------|------|------|
| ``hash_password(password)`` | PBKDF2-SHA256, 210k iter | 生成 ``pbkdf2_sha256$iter$salt$digest`` 格式 |
| ``verify_password(password, hash)`` | 常量时间比较 | 验证密码是否匹配 |

### 认证函数

``authenticate_gateway_key(session, raw_key)``
: 通过前缀查找 Key，SHA-256 哈希验证，检查 Subject/Project 状态，
  返回 ``AuthContext(key, subject, project)``。

``authenticate_user_session(session, raw_token)``
: Session Token 认证，返回 ``UserSessionContext(session, subject)``。

### 用户创建

``create_registered_user(session, settings, username, password, full_name)``
: 完整的自助注册流程：创建 Subject + Project + Guest Team Membership + GatewayKey。

``ensure_builtin_identity(session, settings)``
: 启动时自动执行，确保 guest/admin 团队和管理员用户存在。

policy.py -- 授权引擎
---------------------

### 核心流程

``resolve_route_context(session, model_name, auth, client_ip)``
: 主授权管道，按顺序执行：

1. 查找活跃的 ModelAlias
2. 检查授权（直接或团队）
3. 检查 IP 策略
4. 查找活跃的 UpstreamTarget

### 授权检查

``subject_can_use_model(session, subject_id, model_alias_id, project_id, key_id)``
: 双路径检查：

- 路径 1：ModelEntitlement（直接授权）
- 路径 2：ModelTeamGrant（团队授权）
- 结果：任一路径通过即可（OR 逻辑）

### 模型列表

``list_accessible_model_aliases(session, key_id, subject_id, project_id)``
: 返回用户可访问的所有 ModelAlias 的并集。

rate_limit.py -- 限流服务
-------------------------

### 策略解析

``resolve_effective_rate_policy(session, key_id, subject_id, project_id, settings)``
: 从三个层级（key/subject/project）收集所有活跃策略，取最小值。

### RPM 检查

``check_request_rate(redis, policy, scope, scope_id)``
: Redis INCR + 60 秒 TTL 滑动窗口。

### 并发控制

``acquire_concurrency_slot(redis, key_id, limit)``
: 独立获取并发槽位，INCR 并检查，超限则 DECR 并抛出 ``RateLimitExceeded``。
返回 ``counter_key`` 用于后续释放。

``release_concurrency_slot(redis, counter_key)``
: 独立释放并发槽位，DECR。用于流式请求在 generator 的 ``finally`` 中释放。

``concurrency_slot(redis, key_id, limit)``
: 异步上下文管理器，组合 acquire + release，适用于非流式请求。900 秒安全 TTL。

litellm_client.py -- LLM 适配层
-------------------------------

统一封装三种协议的 LiteLLM 调用：

| 函数 | 协议 | LiteLLM 方法 |
|------|------|-------------|
| ``completion_once()`` | OpenAI Chat | ``litellm.acompletion`` |
| ``completion_stream()`` | OpenAI Chat (stream) | ``litellm.acompletion(stream=True)`` |
| ``responses_once()`` | OpenAI Responses | ``litellm.aresponses`` |
| ``responses_stream()`` | OpenAI Responses (stream) | ``litellm.aresponses(stream=True)`` |
| ``anthropic_messages_once()`` | Anthropic Messages | ``litellm.anthropic_messages`` |
| ``anthropic_messages_stream()`` | Anthropic Messages (stream) | ``litellm.anthropic_messages(stream=True)`` |

所有流式函数返回 ``(event_string, usage_dict)`` 元组的异步生成器。

``check_upstream_health(base_url, health_path, headers)``
: 通过 httpx 检查上游健康状态。

facts.py -- 用量记录
--------------------

``record_request_fact(session, **kwargs)``
: 创建不可变的 RequestFact 记录，包含请求的所有关键元数据。

``record_audit_event(session, **kwargs)``
: 创建审计事件记录。

辅助函数：
- ``extract_usage_dict(usage)`` -- 标准化 LiteLLM usage 对象
- ``prompt_tokens_from_usage(usage)`` -- 提取 prompt tokens
- ``completion_tokens_from_usage(usage)`` -- 提取 completion tokens

router_command.py -- 命令生成
-----------------------------

``render_router_command(config)``
: 将 RouterCommandConfig 渲染为可执行的 ``vllm-router`` CLI 命令字符串，
  包含正确的 flag 格式化和 shell 引用。
