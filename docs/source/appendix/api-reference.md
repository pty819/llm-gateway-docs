API 参考手册
=============

代理端点
--------

### POST /v1/chat/completions

OpenAI Chat Completions 协议代理。

**认证**: ``Authorization: Bearer gw-...`` 或 ``X-Api-Key: gw-...``

**请求体**: 与 OpenAI API 完全一致。

.. code-block:: json

    {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": false
    }

**响应**: 与 OpenAI API 完全一致。

### POST /v1/responses

OpenAI Responses API 协议代理。

### POST /v1/messages

Anthropic Messages API 协议代理。

### GET /v1/models

列出当前 Key 可访问的模型。

**响应**:

.. code-block:: json

    {
        "object": "list",
        "data": [
            {"id": "gpt-4o", "object": "model", "owned_by": "llm-gateway"}
        ]
    }

认证端点
--------

### POST /auth/register

自助注册。

**请求体**:

.. code-block:: json

    {
        "username": "a12345678",
        "password": "your-password",
        "full_name": "张三"
    }

**响应**:

.. code-block:: json

    {
        "session_token": "sess-...",
        "subject": {...},
        "gateway_key": "gw-..."
    }

### POST /auth/login

登录。

### POST /auth/logout

登出。

### GET /auth/me

当前用户档案。

### GET /auth/usage/summary

当前用户用量统计。

**查询参数**: ``start_date``, ``end_date``, ``model``, ``group_by``

### PATCH /auth/password

修改密码。

### POST /auth/keys

签发个人 Gateway Key。

管理端点
--------

所有管理端点前缀 ``/admin``，需要 Admin 认证。

### Subjects

- ``POST /admin/subjects`` -- 创建
- ``GET /admin/subjects?q=<search>`` -- 列表（支持搜索）
- ``PATCH /admin/subjects/{id}`` -- 更新
- ``PATCH /admin/subjects/{id}/password`` -- 重置密码
- ``PATCH /admin/subjects/{id}/state`` -- 切换状态
- ``DELETE /admin/subjects/{id}`` -- 删除（级联清理）

### Projects

- ``POST /admin/projects`` -- 创建
- ``GET /admin/projects`` -- 列表
- ``PATCH /admin/projects/{id}`` -- 更新

### Gateway Keys

- ``POST /admin/gateway-keys`` -- 签发（返回明文，仅一次）
- ``GET /admin/gateway-keys`` -- 列表
- ``PATCH /admin/gateway-keys/{id}/state`` -- 切换状态

### Model Aliases

- ``POST /admin/model-aliases`` -- 创建（自动授权 admin 团队）
- ``GET /admin/model-aliases`` -- 列表
- ``PATCH /admin/model-aliases/{id}`` -- 更新（含 IP CIDR）
- ``DELETE /admin/model-aliases/{id}?cascade_upstreams=true`` -- 删除

### Teams

- ``POST /admin/teams`` -- 创建
- ``GET /admin/teams`` -- 列表
- ``PATCH /admin/teams/{id}`` -- 更新

### Upstream Targets

- ``POST /admin/upstreams`` -- 创建
- ``GET /admin/upstreams`` -- 列表
- ``GET /admin/upstreams/{id}/health`` -- 健康检查
- ``PATCH /admin/upstreams/{id}`` -- 更新
- ``DELETE /admin/upstreams/{id}`` -- 删除

### Rate Policies

- ``POST /admin/rate-policies`` -- 创建
- ``GET /admin/rate-policies`` -- 列表
- ``PATCH /admin/rate-policies/{id}`` -- 更新

### Analytics

- ``GET /admin/usage/summary?group_by=model&start=...&end=...`` -- 用量汇总
- ``GET /admin/usage/ranking?limit=10`` -- 用量排名
- ``GET /admin/audit-events`` -- 审计事件

健康端点
--------

- ``GET /health/live`` -- 存活探针
- ``GET /health/ready`` -- 就绪探针
