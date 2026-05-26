部署指南
========

系统要求
--------

- Python 3.14+
- PostgreSQL 15+
- Redis 7+
- Node.js 22+（前端构建）

环境变量
--------

生产环境至少需要配置以下环境变量：

.. code-block:: bash

    export LLM_GATEWAY_DATABASE_URL="postgresql+asyncpg://user:pass@db-host:5432/llm_gateway"
    export LLM_GATEWAY_REDIS_URL="redis://redis-host:6379/0"
    export LLM_GATEWAY_ADMIN_TOKEN="your-secure-admin-token"
    export LLM_GATEWAY_BOOTSTRAP_ADMIN_PASSWORD="your-secure-admin-password"

数据库初始化
-----------

.. code-block:: bash

    # 创建数据库
    createdb llm_gateway

    # 运行迁移
    python scripts/init_db.py

    # （可选）填充开发数据
    python scripts/seed_dev.py

启动服务
--------

### 后端

.. code-block:: bash

    python main.py

后端在 ``127.0.0.1:18080`` 启动。

### 前端

.. code-block:: bash

    cd frontend
    npm install
    npm run dev -- --host 0.0.0.0

开发模式下，Vite 代理所有 API 请求到后端。

### 生产构建

.. code-block:: bash

    cd frontend
    npm run build

构建产物在 ``frontend/build/`` 目录。

反向代理
--------

生产环境建议在 Gateway 前面放 Nginx 或 Caddy：

.. code-block:: nginx

    server {
        listen 443 ssl;
        server_name llm-gateway.example.com;

        location / {
            proxy_pass http://127.0.0.1:18080;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_buffering off;  # 流式响应必须关闭 buffering
        }
    }

如果使用反向代理，需要启用：

.. code-block:: bash

    export LLM_GATEWAY_TRUST_PROXY_HEADERS=true

客户端接入
----------

### OpenAI SDK

.. code-block:: python

    from openai import OpenAI

    client = OpenAI(
        api_key="gw-your-gateway-key",
        base_url="https://llm-gateway.example.com/v1"
    )

### Anthropic SDK

.. code-block:: python

    import anthropic

    client = anthropic.Anthropic(
        api_key="gw-your-gateway-key",
        base_url="https://llm-gateway.example.com"
    )

### Codex

.. code-block:: bash

    export OPENAI_API_KEY="gw-your-gateway-key"
    export OPENAI_BASE_URL="https://llm-gateway.example.com/v1"

### Claude Code

.. code-block:: bash

    export ANTHROPIC_API_KEY="gw-your-gateway-key"
    export ANTHROPIC_BASE_URL="https://llm-gateway.example.com"
