前端架构
========

技术栈
------

.. list-table::
   :header-rows: 1

   * - 技术
     - 版本
     - 用途
   * - SvelteKit
     - 2.57
     - 全栈框架
   * - Svelte
     - 5.55
     - UI 组件（runes 模式）
   * - Vite
     - 8
     - 构建工具
   * - TypeScript
     - 6
     - 类型安全
   * - Lucide
     - latest
     - 图标库

架构图
------

```{mermaid}
graph TB
    subgraph SvelteKit App
        Layout["+layout.svelte"]
        Page["+page.svelte"]

        subgraph Components
            ST[StateBadge]
            JV[JsonViewer]
            CB[CommandBlock]
            SD[SecretOnceDialog]
            RT[ResourceTable]
        end

        subgraph API Client
            AC[AdminApiClient]
            TY[Type Definitions]
        end

        subgraph State
            AT[admin-token.ts]
        end

        subgraph Validators
            VL[validators/index.ts]
        end
    end

    Layout --> Page
    Page --> Components
    Page --> API Client
    Page --> State
    API Client --> TY
```

页面结构
--------

管理控制台是一个单页应用（``+page.svelte``），分为 5 个导航组：

### 1. 运维（Operations）

- **总览** -- 关键指标仪表盘（请求数、成功率、Token 用量）
- **诊断** -- 健康检查、上游健康状态、LiteLLM 版本

### 2. 配置（Configuration）

- **模型** -- ModelAlias CRUD + IP CIDR 编辑器
- **上游** -- UpstreamTarget CRUD + 健康检查按钮
- **路由命令** -- vLLM Router CLI 生成器

### 3. 访问（Access）

- **主体** -- Subject CRUD + 密码重置 + 搜索
- **项目** -- Project CRUD + 成员管理
- **密钥** -- GatewayKey 签发 + 状态切换
- **团队** -- Team CRUD + 成员管理 + 模型授权

### 4. 策略（Policy）

- **旧版授权** -- 直接 ModelEntitlement 管理
- **限流策略** -- RatePolicy CRUD（RPM + 并发限制）

### 5. 证据（Evidence）

- **用量** -- 按模型/用户/项目聚合的 Token 统计
- **排名** -- 按 Token 消耗排名的用户列表
- **审计** -- 操作审计日志 + JSON 详情查看器

### 非管理员视图

非管理员用户看到受限视图：

- 自己的用量统计
- 自己的 Gateway Key 列表
- 自己的团队成员资格
- 工具集成指南（Codex 配置、Claude Code 环境变量、端点 URL）

API 客户端
----------

``AdminApiClient`` 封装了所有与后端的通信：

.. code-block:: typescript

    class AdminApiClient {
        // 自动附加认证 Header
        // 支持 admin token 和 session token 两种模式
        get<T>(path: string): Promise<T>
        post<T>(path: string, body: unknown): Promise<T>
        patch<T>(path: string, body: unknown): Promise<T>
        delete<T>(path: string): Promise<T>
    }

错误处理支持两种格式：
- FastAPI 格式：``{detail: "message"}``
- Gateway 格式：``{error: {type, message}}``

组件
----

### StateBadge

资源状态徽章，自动着色：
- ACTIVE -> 绿色
- DISABLED -> 红色

### JsonViewer

JSON 美化展示，自动遮盖密钥字段。

### CommandBlock

代码块 + 复制按钮，用于展示 vLLM Router 命令。

### SecretOnceDialog

一次性密钥展示对话框。创建 Gateway Key 后弹出，
用户关闭后密钥永远不可再次查看。

### ResourceTable

通用表格组件，使用 Svelte 5 泛型实现类型安全的列定义和行渲染。

Session 管理
------------

浏览器会话通过 ``localStorage`` 持久化：

- 登录成功后保存 session token
- 支持 "记住我" 选项
- 登出时清除 token
- 页面刷新时自动恢复会话

开发代理
--------

Vite 开发服务器配置了以下代理规则：

.. code-block:: typescript

    server: {
        proxy: {
            '/admin': 'http://127.0.0.1:18080',
            '/auth':  'http://127.0.0.1:18080',
            '/health':'http://127.0.0.1:18080',
            '/v1':    'http://127.0.0.1:18080',
        }
    }

这使得前端开发时无需 CORS 配置，所有 API 请求自动代理到后端。
