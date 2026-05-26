安全模型
========

安全架构
--------

```{mermaid}
graph TB
    subgraph 入口安全
        IP[Client IP]
        TLS[TLS 终端]
    end

    subgraph 认证层
        GK[Gateway Key Auth]
        ST[Session Token Auth]
        AT[Admin Token Auth]
    end

    subgraph 授权层
        ME[Model Entitlement]
        MTG[Model Team Grant]
        IPC[IP CIDR Policy]
    end

    subgraph 限流层
        RPM[RPM Sliding Window]
        CC[Concurrency Slots]
    end

    subgraph 数据安全
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

所有管理员操作产生 ``AuditEvent`` 记录：

.. code-block:: json

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

自助注册安全
------------

自助注册流程的安全设计：

1. **工号验证** -- ``login_username`` 必须匹配 ``/^[a-z]\d{8}$/i``
2. **密码哈希** -- PBKDF2-SHA256 存储
3. **自动加入 guest 团队** -- 新用户只能访问 guest 团队被授权的模型
4. **创建个人项目** -- 用量独立归属
5. **实名门控** -- 登录后如果显示名仍为工号格式，强制要求修改实名
