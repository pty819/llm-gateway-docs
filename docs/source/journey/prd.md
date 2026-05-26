产品需求文档
============

产品愿景
--------

LLM Gateway 是企业内部 LLM 服务的统一入口。它为开发者和运营者提供：

- **对开发者**：一把 Key 走天下，无感知地使用多种 LLM 后端
- **对运营者**：完整的管控面，管理谁在什么时候用什么模型花了多少 Token

用户画像
--------

### 运营者（Operator）

- 职责：管理模型配置、用户权限、用量监控
- 需求：可视化控制台、批量操作、审计追溯
- 技术水平：不一定熟悉 CLI，偏好 Web 界面

### 开发者（Developer）

- 职责：在应用或工具中接入 LLM 服务
- 需求：简单的接入方式（API Key + OpenAI 兼容端点）、稳定的代理
- 技术水平：熟练使用 OpenAI SDK / Anthropic SDK / Codex

### 终端用户（End User）

- 职责：通过自助注册获取 LLM 访问权限
- 需求：自助注册/登录、查看自己的用量、管理自己的 Key
- 技术水平：一般

核心能力
--------

### Phase 1: 基础网关

- 透明代理（OpenAI / Anthropic / Responses 三协议）
- Gateway Key 认证
- 模型别名 + 上游路由
- IP CIDR 策略
- 请求级限流（RPM + 并发）
- 完整请求事实记录
- 管理控制台（CRUD + 诊断）

### Phase 2: 自助服务 + 团队权限

- 自助注册（工号验证）
- Session Token 登录
- 团队 + 团队模型授权
- 管理员密码管理
- 操作审计事件
- 非管理员受限视图

### Phase 3: 运营增强（规划中）

- 用量报表导出
- 成本分摊估算
- 告警和通知
- 上游自动故障转移

非目标
------

- 不做模型训练/微调
- 不做 Prompt 修改/注入
- 不做多租户 SaaS 隔离
- 不做计费结算
- 不做 Webhook/回调

阶段假设
--------

我们假设项目分两个阶段交付：

1. **Blueprint Phase** -- 先建立核心网关能力（认证、代理、限流、审计、管理面）
2. **Self-Service Phase** -- 再添加用户自助服务和团队 RBAC

这个顺序的原因是：Phase 1 的管理面通过 admin Token 操作，适合小团队快速启动。
Phase 2 引入自助注册后，需要团队模型授权来管理扩大的用户群。

```{mermaid}
graph LR
    subgraph Phase 1
        A1[Gateway Key Auth]
        A2[Transparent Proxy]
        A3[Model Routing]
        A4[Rate Limiting]
        A5[Request Facts]
        A6[Admin Console]
    end

    subgraph Phase 2
        B1[Self-Service Register]
        B2[Team RBAC]
        B3[Session Auth]
        B4[Audit Events]
        B5[User Dashboard]
    end

    Phase 1 --> Phase 2
```
