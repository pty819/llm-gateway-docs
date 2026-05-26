测试体系
========

测试策略
--------

项目采用集成测试策略 -- 测试直接运行 FastAPI 应用，连接真实的 PostgreSQL 和 Redis，
不使用 mock。

```{mermaid}
graph LR
    A[httpx AsyncClient] --> B[FastAPI ASGI]
    B --> C[(PostgreSQL)]
    B --> D[(Redis)]
    B --> E[LiteLLM]

    style C fill:#336791,color:white
    style D fill:#dc382d,color:white
```

测试基础设施
------------

### conftest.py

.. list-table::
   :header-rows: 1

   * - Fixture
     - Scope
     - 说明
   * - ``init_db()``
     - session
     - 启动前运行 ``init_db()``
   * - ``client``
     - function
     - httpx AsyncClient（ASGI transport）
   * - ``external_ip_client``
     - function
     - 模拟外部 IP 的客户端
   * - ``gateway_fixture``
     - function
     - 创建完整的测试链（Subject + Project + Model + Upstream + Entitlement + Key）
   * - ``fetch_request_fact()``
     - function
     - 按 request_id 查询 RequestFact

集成测试清单
------------

### 认证与授权

.. list-table::
   :header-rows: 1

   * - 测试
     - 验证内容
   * - List models returns entitled aliases
     - Key 认证 + 模型列表过滤
   * - List models rejects invalid key
     - 无效 Key 返回 401
   * - Self-service register/login
     - 注册 + 登录 + guest 团队模型访问
   * - Registration rejects non-employee username
     - 工号格式校验
   * - Admin password reset + subject deletion
     - 密码重置 + 级联删除

### 团队 RBAC

.. list-table::
   :header-rows: 1

   * - 测试
     - 验证内容
   * - Admin session manages team union permissions
     - 团队成员获得模型访问权限
   * - Legacy user must complete real name
     - 实名门控

### 代理核心

.. list-table::
   :header-rows: 1

   * - 测试
     - 验证内容
   * - Real upstream OpenAI chat completion
     - 真实上游请求 + 用量记录
   * - OpenAI streaming completion
     - 流式请求 + success fact
   * - Anthropic messages conversion
     - 协议转换 + 用量记录
   * - Invalid key records auth failure fact
     - 失败请求的事实记录

### 安全与策略

.. list-table::
   :header-rows: 1

   * - 测试
     - 验证内容
   * - IP allowlist denies disallowed client
     - CIDR 策略拒绝
   * - Key-scoped rate policy blocks
     - 限流策略生效

### 管理 API

.. list-table::
   :header-rows: 1

   * - 测试
     - 验证内容
   * - Health + admin diagnostics
     - 健康检查 + 诊断信息
   * - Model alias delete requires cascade
     - 有上游时禁止删除
   * - Usage ranking with token fallback
     - 用量排名
   * - Self-service usage summary
     - 用户自己的用量
   * - Admin updates router/rate/upstream health
     - 管理操作完整性

运行测试
--------

.. code-block:: bash

    # 确保 PostgreSQL 和 Redis 运行
    python scripts/check_connectivity.py

    # 运行全部测试
    pytest tests/ -v

    # 运行单个测试
    pytest tests/test_backend_integration.py::test_chat_completion -v

前端测试
--------

### 单元测试

.. code-block:: bash

    cd frontend
    npm test  # Vitest

### E2E 测试

.. code-block:: bash

    cd frontend
    npx playwright test  # Playwright

### 冒烟测试

.. code-block:: bash

    python scripts/smoke_controller.py  # 端到端：创建 Key -> 请求 -> 验证响应
    python scripts/smoke_upstream.py    # 直连上游验证
