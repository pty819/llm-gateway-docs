缘起：为什么需要 LLM Gateway
==============================

背景
----

2025 年，大语言模型（LLM）在企业的应用从实验阶段进入了生产化阶段。
团队内部的开发者开始广泛使用 Codex、Claude Code、OpenAI SDK 等工具连接各类推理后端。
但很快，一系列问题浮现：

1. **接入混乱** -- 每个开发者直接持有多把上游 API Key，轮换和回收成本极高。
2. **没有权限管控** -- 谁能访问哪个模型？谁用了多少 Token？没有统一的管理面。
3. **计费黑盒** -- 上游按 Token 收费，但团队内部无法精确分摊成本到项目和个人。
4. **多协议并存** -- OpenAI Chat Completions、Anthropic Messages、OpenAI Responses API 格式各异，客户端适配困难。
5. **缺乏可观测性** -- 请求失败时无法追溯原因，无法区分是认证失败、策略拒绝、限流还是上游故障。

我们需要一个**企业级 LLM API 网关**，在客户端和推理后端之间充当统一入口，
提供认证、授权、限流、路由、用量审计等能力。

核心设计目标
------------

从最初的需求讨论中，我们确立了以下设计原则：

- **协议透明** -- 对下游客户端而言，网关是完全透明的代理。OpenAI SDK、Anthropic SDK 无需任何修改即可接入。
- **全链路可审计** -- 每一个请求，无论成功还是失败，都必须留痕。认证失败、策略拒绝、限流、上游错误，全部记录。
- **零信任安全模型** -- API Key 不存储明文，上游密钥不返回给客户端，所有操作都有审计事件。
- **渐进式权限** -- 从简单的 Key 认证到团队 RBAC，权限模型可以随组织规模增长而演进。
- **运营友好** -- 提供完整的管理控制台，运营人员无需接触 CLI 即可完成日常操作。

不是什么
--------

明确项目边界同样重要。以下功能**不在**本项目范围内：

- **模型训练/微调** -- Gateway 不涉及模型本身的训练或优化。
- **Prompt 工程** -- Gateway 不修改请求/响应内容，只做透传。
- **多模态处理** -- Gateway 处理文本 LLM 请求，不涉及图像、音频等模态。
- **计费结算** -- Gateway 记录用量，但不做金额计算和账单生成。
- **多租户 SaaS** -- 单实例部署，不做租户隔离。

```{mermaid}
graph LR
    Client[Clients] --> Gateway[LLM Gateway]
    Gateway --> vLLM[vLLM Cluster]
    Gateway --> OpenAI[OpenAI API]
    Gateway --> Anthropic[Anthropic API]
    Gateway --> Other[Any OpenAI-Compatible]

    subgraph Gateway
        Auth[Authentication]
        Policy[Authorization]
        Rate[Rate Limiting]
        Route[Routing]
        Audit[Audit & Facts]
    end
```

设计哲学
--------

本项目遵循以下设计哲学：

**做加法不做乘法**
: Gateway 在请求链路上做的是叠加（add）而非变换（multiply）。
  它添加认证、添加审计、添加限流，但不改变请求体的结构和语义。

**数据即证据**
: 每个请求产生的事实记录（RequestFact）是不可变的审计证据。
  用量统计、故障排查、合规审计全部基于同一份数据源。

**配置即代码的平衡**
: 数据库存储运行时配置（模型、上游、策略），Alembic 管理结构变更。
  开发环境通过 seed 脚本初始化，生产环境通过管理 API 配置。

**先让它工作，再让它正确**
: 从 MVP 开始 -- 先实现 Key 认证 + 透明代理，再逐步添加团队 RBAC、
  自助注册、用量分析等能力。每一层都是增量式的。
