API 层
======

API 层由四个路由模块组成，通过 FastAPI 依赖注入共享公共服务。

路由注册
--------

.. code-block:: python

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/auth")
    app.include_router(admin.router, prefix="/admin")
    app.include_router(proxy.router, prefix="/v1")

健康检查（health.py）
--------------------

.. list-table::
   :header-rows: 1

   * - 方法
     - 路径
     - 认证
     - 说明
   * - GET
     - /health/live
     - 无
     - 存活探针，始终返回 ok
   * - GET
     - /health/ready
     - 无
     - 就绪探针，检查 PostgreSQL + Redis
   * - GET
     - /admin/diagnostics
     - Admin
     - 诊断信息（版本、环境）

自助认证（auth.py）
-------------------

.. list-table::
   :header-rows: 1

   * - 方法
     - 路径
     - 说明
   * - POST
     - /auth/register
     - 自助注册（工号 + 密码）
   * - POST
     - /auth/login
     - 登录，返回 session token
   * - POST
     - /auth/logout
     - 登出，撤销 session token
   * - GET
     - /auth/me
     - 当前用户档案
   * - GET
     - /auth/usage/summary
     - 当前用户用量统计
   * - PATCH
     - /auth/password
     - 修改密码
   * - PATCH
     - /auth/profile
     - 修改显示名
   * - POST
     - /auth/keys
     - 签发个人 Gateway Key

注册流程创建以下资源：

1. Subject（用户主体）
2. Project（个人项目）
3. TeamMembership（自动加入 guest 团队）
4. GatewayKey（个人 API Key）
5. UserSession（登录会话）

管理 API（admin.py）
-------------------

管理 API 提供所有资源的完整 CRUD 操作，全部受 Admin 认证保护。

### 资源端点

.. list-table::
   :header-rows: 1

   * - 资源
     - 操作
     - 特殊能力
   * - Subject
     - CRUD + 搜索 + 密码重置 + 状态切换
     - 删除时级联清理关联资源
   * - Project
     - CRUD
     - 成员管理
   * - ProjectMembership
     - 创建 + 查询
     - --
   * - GatewayKey
     - 创建 + 查询 + 状态切换
     - 创建时返回明文（仅一次）
   * - ModelAlias
     - CRUD
     - 创建时自动授权 admin 团队
   * - ModelEntitlement
     - 创建 + 查询 + 状态切换
     - --
   * - Team
     - CRUD
     - --
   * - TeamMembership
     - 创建 + 查询 + 状态切换
     - --
   * - ModelTeamGrant
     - 创建 + 查询 + 状态切换
     - --
   * - UpstreamTarget
     - CRUD + 健康检查
     - 删除 ModelAlias 支持 cascade
   * - RouterCommandConfig
     - CRUD
     - 返回渲染好的 CLI 命令
   * - RatePolicy
     - CRUD
     - --

### 分析端点

.. list-table::
   :header-rows: 1

   * - 方法
     - 路径
     - 说明
   * - GET
     - /admin/usage/summary
     - 按模型/用户/项目聚合用量
   * - GET
     - /admin/usage/ranking
     - 按 Token 消耗排名
   * - GET
     - /admin/audit-events
     - 最近 200 条审计事件

代理 API（proxy.py）
-------------------

代理 API 是核心 LLM 代理，支持三种协议：

.. list-table::
   :header-rows: 1

   * - 方法
     - 路径
     - 协议
     - 流式
   * - POST
     - /v1/chat/completions
     - OpenAI Chat Completions
     - 支持
   * - POST
     - /v1/responses
     - OpenAI Responses API
     - 支持
   * - POST
     - /v1/messages
     - Anthropic Messages
     - 支持
   * - GET
     - /v1/models
     - 模型列表
     - --

所有代理端点共享相同的请求处理流程：

1. 解析请求体，提取 ``model`` 和 ``stream``
2. 认证 Gateway Key
3. 解析限流策略
4. 解析路由（模型别名 + 上游）
5. 执行限流检查
6. 调用 LiteLLM 适配器
7. 记录请求事实

依赖注入（deps.py）
-------------------

FastAPI 依赖注入提供以下服务：

- ``session_dep`` -- 异步数据库会话
- ``settings_dep`` -- 应用配置
- ``redis_dep`` -- Redis 客户端
- ``client_ip_dep`` -- 客户端 IP（支持代理 Header）
- ``bearer_token`` -- Bearer Token 提取
- ``auth_dep`` -- Gateway Key 完整认证
- ``admin_dep`` -- Admin 认证（Token 或 Session）
- ``user_session_dep`` -- Session Token 认证
