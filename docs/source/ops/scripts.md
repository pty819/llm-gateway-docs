运维脚本
========

脚本工具箱
----------

项目提供以下运维脚本：

init_db.py -- 数据库初始化
--------------------------

初始化数据库 schema：

1. 检查是否已有 schema 存在
2. 如果已有，执行 ``alembic stamp head``（标记当前版本）
3. 如果没有，执行 ``alembic upgrade head``（创建全部表）

.. code-block:: bash

    python scripts/init_db.py

seed_dev.py -- 开发数据填充
---------------------------

创建开发环境所需的测试数据（幂等操作）：

- Subject: ``dev-user``
- Project: ``dev-project``
- ModelAlias: ``dev-model``
- UpstreamTarget: ``dev-upstream``
- GatewayKey: ``dev-key``

.. code-block:: bash

    python scripts/seed_dev.py

check_connectivity.py -- 连通性检查
-----------------------------------

验证 PostgreSQL 和 Redis 的网络连通性：

- TCP 连接测试（3 次重试）
- asyncpg 连接测试
- redis-py PING 测试

.. code-block:: bash

    python scripts/check_connectivity.py

smoke_controller.py -- 端到端冒烟测试
-------------------------------------

通过 Gateway 发送真实的 Chat Completion 请求：

1. 创建临时 Gateway Key
2. 发送 ``POST /v1/chat/completions``
3. 验证响应内容和用量记录
4. 清理临时 Key

.. code-block:: bash

    python scripts/smoke_controller.py

smoke_upstream.py -- 上游连通性测试
-----------------------------------

直连上游验证 LLM 服务是否可用：

1. 使用 LiteLLM 直连配置的上游
2. 发送测试 Chat Completion
3. 报告连通状态

.. code-block:: bash

    python scripts/smoke_upstream.py
