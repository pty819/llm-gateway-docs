需求访谈：从模糊到清晰
========================

原始需求陈述
------------

项目启动时，需求只有一句话：

> 做一个企业内部的 LLM Gateway，让团队能统一管理 API 访问。

这句话背后有大量未明确的问题。在正式设计之前，我们通过深度访谈（Deep Interview）
方法论进行了 9 轮 Socratic 追问，将模糊需求精确化为可执行的规格。

访谈方法论
----------

我们使用了基于 Socratic 方法的结构化访谈流程：

1. **意图澄清** -- "你说的统一管理，具体管理什么？"
2. **边界划定** -- "什么不在管理范围内？"
3. **优先级排序** -- "如果只能做一个功能，先做什么？"
4. **约束发现** -- "有没有技术或合规上的硬约束？"
5. **假设检验** -- "如果 X 情况发生，你期望系统怎么响应？"

最终将模糊度（Ambiguity）从初始的高位压缩到了 10.2%。

关键决策记录
------------

通过访谈，我们做出了以下关键决策：

### 1. 认证模型

**问题**：API 认证怎么做？JWT？OAuth？API Key？

**决策**：采用 Gateway Key（前缀 + SHA-256 哈希）模式，类似 Stripe API Key。

**理由**：
- 客户端集成最简单 -- 只需在 HTTP Header 里放一个字符串
- 无需 OAuth 的重定向流程（纯 API 场景不需要浏览器交互）
- SHA-256 哈希 + 前缀索引兼顾安全和查询性能
- 格式 ``gw-<random>`` 易于识别和管理

### 2. 授权模型

**问题**：谁能用哪个模型？怎么表达这个关系？

**决策**：双层授权 -- 直接授权（ModelEntitlement）+ 团队授权（ModelTeamGrant）。

**理由**：
- 小团队用直接授权，简单直接
- 大团队用团队授权，批量管理
- 授权检查取并集（OR 逻辑），任一路径通过即可

### 3. 多协议支持

**问题**：支持哪些 API 协议？

**决策**：同时支持 OpenAI Chat Completions、OpenAI Responses API、Anthropic Messages 三种协议。

**理由**：
- OpenAI Chat Completions 是事实标准，几乎所有 SDK 和工具都支持
- OpenAI Responses API 是新标准，Codex 等工具开始迁移
- Anthropic Messages 是 Claude 系列模型的专有协议
- 通过 LiteLLM 做协议适配，Gateway 本身不需要理解协议细节

### 4. 数据存储

**问题**：用什么数据库？

**决策**：PostgreSQL + Redis。

**理由**：
- PostgreSQL 提供 ACID、JSONB（灵活字段）、丰富的索引类型
- Redis 用于限流（滑动窗口 + 并发槽位）
- 两者都是团队已有运维经验的组件

### 5. 前端技术

**问题**：管理控制台用什么技术栈？

**决策**：SvelteKit 5 单页应用。

**理由**：
- Svelte 5 的 runes 响应式模型适合数据密集的管理界面
- 编译时框架，运行时极小
- 团队有 Svelte 经验

### 6. 用量分析

**问题**：用量分析要做到什么程度？

**决策**：记录每个请求的完整事实（RequestFact），聚合分析通过查询实现。

**理由**：
- 不可变事实记录满足审计需求
- 聚合维度灵活（按模型、用户、项目、时间）
- 不需要预计算，PostgreSQL 的聚合能力足够

```{mermaid}
graph TD
    Q[模糊需求] --> I1[9轮 Socratic 访谈]
    I1 --> S[精确规格]
    S --> P[PRD]
    P --> M[Master Spec Group]
    M --> G1[Blueprint Spec]
    M --> G2[Self-Service Auth Spec]

    style Q fill:#f9f,stroke:#333
    style S fill:#9f9,stroke:#333
    style P fill:#99f,stroke:#333
```

从访谈到规格的转化
------------------

访谈结束后，我们产出了以下规格文档：

.. list-table::
   :header-rows: 1

   * - 文档
     - 用途
     - 核心内容
   * - Deep Interview Spec
     - 访谈记录和约束分析
     - 10.2% 模糊度、5 个决策边界、3 个硬约束
   * - PRD Blueprint
     - 产品需求文档
     - 用户画像、核心能力、非目标、阶段假设
   * - Master Spec Group
     - 总体协调文档
     - ADR（架构决策记录）、产出物矩阵、验收标准
   * - Test Spec
     - 测试规格
     - 验证矩阵、单元/集成测试清单、可观测性验证
