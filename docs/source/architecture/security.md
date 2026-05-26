安全模型
========

安全架构
--------

```{mermaid}
graph TB
    subgraph Ingress_Security[Ingress Security]
        IP[Client IP]
        TLS[TLS Termination]
    end

    subgraph Auth_Layer[Authentication Layer]
        GK[Gateway Key Auth]
        ST[Session Token Auth]
        AT[Admin Token Auth]
    end

    subgraph Authz_Layer[Authorization Layer]
        ME[Model Entitlement]
        MTG[Model Team Grant]
        IPC[IP CIDR Policy]
    end

    subgraph Rate_Layer[Rate Limiting Layer]
        RPM[RPM Sliding Window]
        CC[Concurrency Slots]
    end

    subgraph Data_Security[Data Security]
        KH[Key Hashing SHA-256]
        SK[Secret Redaction]
        AE[Audit Events]
    end

    IP --> GK
    IP --> ST
    IP --> AT
    GK --> ME
    GK --> MTG
    GK --> IPC
    ME --> RPM
    MTG --> RPM
    IPC --> CC
```

密钥管理
--------

### Gateway Key 生命周期

1. **创建** -- ``generate_gateway_key()`` 生成 ``gw-<token_urlsafe(32)>``
2. **存储** -- 数据库保存 ``key_prefix``（前 8 字符）和 ``key_hash``（SHA-256）
3. **验证** -- 前缀查询 + HMAC 常量时间比较
4. **吊销** -- 设置 ``state = DISABLED``
5. **过期** -- ``expires_at`` 字段控制

### 密钥安全特性

- **不存储明文** -- Gateway Key 创建后仅显示一次，数据库只存哈希
- **前缀索引** -- 通过 ``key_prefix`` 快速定位，避免全表扫描
- **HMAC 比较** -- 使用 ``hmac.compare_digest()`` 防止时序攻击
- **SHA-256** -- 单向哈希，即使数据库泄露也无法反推 Key

### 上游密钥保护

上游 API Key 通过两种方式存储：
- ``api_key_ref`` -- 引用外部密钥管理系统
- ``api_key_value`` -- 直接存储（仅在管理 API 中脱敏返回）

所有管理 API 响应中的上游密钥自动替换为 ``***masked***``。

密码安全
--------

用户密码使用 PBKDF2-SHA256 哈希：

- 210,000 次迭代（OWASP 2023 推荐）
- 16 字节随机盐
- 存储格式：``pbkdf2_sha256$iterations$salt$digest``
- 验证使用常量时间比较

IP 策略
-------

ModelAlias 可以配置 IP 访问策略：

- ``ALL_PASS`` -- 不限制来源 IP（默认）
- ``ALLOWLIST`` -- 仅允许指定 CIDR 网段

CIDR 校验使用 Python ``ipaddress`` 模块，支持 IPv4 和 IPv6。
支持通过 ``X-Forwarded-For`` / ``X-Real-IP`` 获取真实客户端 IP
（需启用 ``trusted_proxy_headers`` 配置）。

审计追踪
--------

### 管理员操作审计

所有管理员操作产生 ``AuditEvent`` 记录：

```json
{
    "actor_subject_id": "uuid-of-admin",
    "action": "update",
    "resource_type": "model_alias",
    "resource_id": "uuid-of-model",
    "outcome": "success",
    "detail": {
        "field": "ip_allowlist_cidrs",
        "old_value": ["10.0.0.0/8"],
        "new_value": ["10.0.0.0/8", "172.16.0.0/12"]
    }
}
```

### 请求事实审计（全路径覆盖）

每一个代理请求，无论成功还是失败，都会产生一条 ``RequestFact`` 记录。
系统经过硬化，确保以下所有路径都留痕：

| 请求结果 | outcome 值 | 记录时机 |
|----------|-----------|---------|
| 认证失败 | ``AUTH_FAILURE`` | 认证阶段 |
| 策略拒绝 | ``POLICY_DENIAL`` | 授权阶段 |
| RPM 超限 | ``RATE_LIMITED`` | 限流阶段 |
| 并发超限 | ``RATE_LIMITED`` | 并发槽位获取阶段（路由前后均覆盖） |
| 适配失败 | ``ADAPTER_FAILURE`` | LiteLLM 调用失败 |
| 上游失败 | ``UPSTREAM_FAILURE`` | 上游返回错误 |
| 客户端取消 | ``CLIENT_CANCELLED`` | 流式请求被中断 |
| 成功 | ``SUCCESS`` | 请求完成 |

**关键硬化点**：并发超限曾在流式请求中被遗漏（因为检查在 generator 内部）。
现在并发检查提前到 ``StreamingResponse`` 创建之前，超限时能记录完整的
认证上下文、模型别名、上游目标信息。

### ModelEntitlement 验证

创建 ModelEntitlement 时强制校验：
- 必须且只能指定一个 scope（``subject_id``、``project_id`` 或 ``gateway_key_id``）
- 引用的实体必须存在（不存在返回 404）

### 前端安全

登出时清除所有敏感状态：
- Session token
- 明文密钥（``plaintextKey``）
- 复制状态（``copiedItem``）
- 错误信息（``pageError``）

自助注册安全
------------

自助注册流程的安全设计：

1. **工号验证** -- ``login_username`` 必须匹配 ``/^[a-z]\d{8}$/i``
2. **密码哈希** -- PBKDF2-SHA256 存储
3. **自动加入 guest 团队** -- 新用户只能访问 guest 团队被授权的模型
4. **创建个人项目** -- 用量独立归属
5. **实名门控** -- 登录后如果显示名仍为工号格式，强制要求修改实名
