配置系统
========

配置管理
--------

所有配置通过 ``pydantic_settings.BaseSettings`` 管理，支持环境变量和 ``.env`` 文件。

### 配置项

.. list-table::
   :header-rows: 1
   :widths: 30 25 25 20

   * - 配置项
     - 默认值
     - 环境变量
     - 说明
   * - app_name
     - ``LLM Gateway``
     - --
     - 应用名称
   * - environment
     - ``local``
     - --
     - 运行环境
   * - database_url
     - ``postgresql+asyncpg://...``
     - ``LLM_GATEWAY_DATABASE_URL``
     - PostgreSQL 连接串
   * - redis_url
     - ``redis://localhost:6379/0``
     - ``LLM_GATEWAY_REDIS_URL``
     - Redis 连接串
   * - trusted_proxy_headers
     - ``False``
     - ``LLM_GATEWAY_TRUST_PROXY_HEADERS``
     - 是否信任代理 Header
   * - rate_limit_fail_closed
     - ``True``
     - ``LLM_GATEWAY_RATE_LIMIT_FAIL_CLOSED``
     - Redis 故障时是否拒绝请求
   * - default_request_limit_per_minute
     - ``120``
     - ``LLM_GATEWAY_DEFAULT_RPM``
     - 默认 RPM 限制
   * - default_concurrency_limit
     - ``8``
     - ``LLM_GATEWAY_DEFAULT_CONCURRENCY``
     - 默认并发限制
   * - request_fact_timeout_seconds
     - ``30``
     - ``LLM_GATEWAY_FACT_TIMEOUT_SECONDS``
     - 请求事实超时
   * - admin_token
     - ``dev-admin-token``
     - ``LLM_GATEWAY_ADMIN_TOKEN``
     - 管理员 Token
   * - bootstrap_admin_username
     - ``admin``
     - ``LLM_GATEWAY_BOOTSTRAP_ADMIN_USERNAME``
     - 初始管理员用户名
   * - bootstrap_admin_password
     - ``dev-admin-password``
     - ``LLM_GATEWAY_BOOTSTRAP_ADMIN_PASSWORD``
     - 初始管理员密码
   * - session_ttl_hours
     - ``168`` (7 days)
     - ``LLM_GATEWAY_SESSION_TTL_HOURS``
     - Session 有效期

### 优先级

配置值的优先级从高到低：

1. 环境变量
2. ``.env.local`` 文件
3. ``.env`` 文件
4. 默认值

### 缓存

``get_settings()`` 使用 ``@lru_cache`` 装饰器，确保全局单例。

应用启动
--------

.. code-block:: python

    def create_app() -> FastAPI:
        settings = get_settings()

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            async with AsyncSessionLocal() as session:
                await ensure_builtin_identity(session, settings)
            yield

        app = FastAPI(title=settings.app_name, lifespan=lifespan)
        app.include_router(health.router)
        app.include_router(auth.router, prefix="/auth")
        app.include_router(admin.router, prefix="/admin")
        app.include_router(proxy.router, prefix="/v1")
        return app

启动时的 ``lifespan`` 确保内置身份（guest/admin 团队、管理员用户）始终存在。
