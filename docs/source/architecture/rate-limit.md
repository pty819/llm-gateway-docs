限流设计
========

架构
----

限流系统基于 Redis 实现，提供两个维度：

1. **RPM（Requests Per Minute）** -- 滑动窗口计数器
2. **并发（Concurrency）** -- 槽位管理器

```{mermaid}
graph LR
    A[Incoming Request] --> B[resolve_effective_rate_policy]
    B --> C[check_request_rate]
    C --> D{RPM exceeded?}
    D -->|Yes| E[429 Rate Limit Exceeded]
    D -->|No| F{Concurrency exceeded?}
    F -->|Yes| E
    F -->|No| G[Process Request]
    G --> H[Release Concurrency Slot]
```

策略解析
--------

``resolve_effective_rate_policy()`` 从三个层级收集限流策略：

| 层级 | Key | 说明 |
|------|-----|------|
| Key 级 | gateway_key_id | 针对单个 API Key |
| Subject 级 | subject_id | 针对单个用户/服务账户 |
| Project 级 | project_id | 针对单个项目 |

最终生效值 = min(所有匹配策略的 RPM, 所有匹配策略的并发限制, 全局默认值)

```python
# 全局默认值
DEFAULT_RPM = 120
DEFAULT_CONCURRENCY = 8

# 示例：Key 级 60 RPM，Subject 级 200 RPM
# 生效 RPM = min(60, 200, 120) = 60
```

RPM 滑动窗口
------------

使用 Redis ``INCR`` + ``EXPIRE`` 实现固定窗口计数器：

```text
Key: ratelimit:{scope}:{scope_id}:rpm
Value: 当前窗口内的请求数
TTL: 60 秒
```

每次请求：

1. ``INCR key``
2. 如果值 == 1，设置 ``EXPIRE key 60``
3. 如果值 > RPM 限制，拒绝请求

并发槽位
--------

使用 Redis ``INCR`` / ``DECR`` 实现并发计数器：

```text
Key: ratelimit:{scope}:{scope_id}:concurrency
Value: 当前并发请求数
TTL: 900 秒（安全网，防止泄漏）
```

非流式请求：
1. 请求开始前 ``INCR``
2. 如果超限，``DECR`` 并拒绝
3. 请求完成后 ``DECR``

流式请求：
1. 请求开始前 ``INCR``
2. 在 async generator 中处理
3. Generator 结束后 ``DECR``

故障关闭
--------

当 Redis 不可用时，系统通过 ``rate_limit_fail_closed`` 配置决定行为：

- ``True``（默认）-- Redis 故障时拒绝所有请求（安全优先）
- ``False`` -- Redis 故障时放行所有请求（可用性优先）
