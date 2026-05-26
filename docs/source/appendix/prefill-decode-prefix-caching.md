Prefill/Decode 与 Prefix Caching：下一步的性能战场
====================================================

这一章讨论 LLM 推理的性能优化，特别是我们 Gateway 背后的推理基础设施面临的挑战和下一步方向。

为什么需要关注推理性能
---------------------

LLM Gateway 的工作是代理请求，但请求的最终服务质量取决于后端推理引擎的性能。
当用户通过 Codex 或 Claude Code 发送请求时，他们感受到的延迟由两部分组成：

1. **Gateway 延迟** -- 认证、授权、限流（毫秒级，几乎可忽略）
2. **推理延迟** -- 模型处理请求并生成响应（秒级，是主要瓶颈）

优化推理延迟是提升用户体验的关键。

Prefill 和 Decode：两个根本不同的工作负载
----------------------------------------

### Prefill 阶段

当 LLM 收到一个请求时，它首先对整个输入序列（prompt + 历史消息）做一次**全并行**的前向传播。
每一个 token 同时计算 Query、Key、Value 张量，通过多头注意力机制处理。

这个阶段是**计算密集型**的 -- 大量矩阵-矩阵乘法（GEMM），受益于 GPU 的高 TFLOPS。

关键指标是 **TTFT（Time to First Token）**：

> T_prefill(N) 正比于 N × d²_model / TFLOPS

对于 10K token 的 prompt，prefill 可能需要 4-5 秒。

Prefill 的输出是第一个生成的 token 加上 **KV Cache** --
为每个输入 token 在每个注意力层存储的 Key 和 Value 张量，相当于模型的"短期记忆"。

### Decode 阶段

Prefill 之后，模型**逐个 token** 自回归地生成输出。
每一步：检索整个缓存的 KV 张量，为单个新 token 计算注意力，应用前馈和采样。

这个阶段是**内存带宽密集型**的 -- 高频、小批量、带宽受限的内存访问。

关键指标是 **ITL（Inter-Token Latency）**，即每生成一个 token 的延迟。

### 两者为什么不能混在一起

```{mermaid}
graph LR
    subgraph prefill["Prefill: Compute-Bound"]
        direction TB
        P1["Large GEMM operations"]
        P2["Full GPU tensor cores"]
        P3["Benefits from high TFLOPS"]
    end

    subgraph decode["Decode: Memory-Bound"]
        direction TB
        D1["Small sequential reads"]
        D2["GPU tensor cores idle"]
        D3["Benefits from high HBM bandwidth"]
    end

    prefill ---|Opposite requirements| decode
```

在同一个 GPU 上混合 prefill 和 decode 会导致：

1. **ITL 抖动** -- Decode 在 prefill 运行时被暂停，流式输出出现卡顿
2. **TTFT 增加** -- 如果 decode 批次正在运行，新请求等待 prefill 开始
3. **SLO 违规** -- 不可预测的调度使得同时满足 TTFT 和 ITL SLO 几乎不可能
4. **GPU 利用率低** -- 研究表明过载场景下 GPU 利用率可低至 0.2%

### PD 分离（Prefill-Decode Disaggregation）

PD 分离将 prefill 和 decode 物理隔离到独立扩展的资源池：

| 组件 | 角色 | 硬件偏好 |
|------|------|----------|
| Prefill Worker | Prompt 处理，KV Cache 构建 | 计算优化 GPU |
| KV Store | 存储和共享 KV Cache | 高带宽互连 |
| Decode Worker | 逐 token 生成 | 内存优化 GPU |

实测效果：7.4x RPS 提升，99 分位延迟 SLO 收紧 12-15 倍，硬件成本降低 40%。

但 PD 分离有一个前提：**需要开源的 KV Cache 传输实现**。
对于 Qwen 3.6 这类模型，目前没有成熟的开源 PD 分离方案。

Prefix Caching：不分离 PD 时的最佳妥协
--------------------------------------

### 什么是 KV Cache

KV Cache 存储了模型已经处理过的每个 token 的 Key 和 Value 张量。
对于一个大模型（如数百层的架构），100K token 的 prompt 产生约 500MB-1GB 的 KV Cache。

KV Cache 使得自回归生成不需要在每一步重新计算所有前序 token 的注意力。

### 什么是 Prefix Caching

Prefix Caching 将 KV Cache 的复用扩展到**跨请求**。
当多个请求共享相同的 token 序列前缀（如同一个系统提示），共享部分的 KV Cache 可以直接复用，
跳过昂贵的 prefill 计算。

### vLLM 的自动 Prefix Caching（APC）

vLLM 的 APC 基于 PagedAttention：

1. **分块** -- KV Cache 分成固定大小的块（默认 16 token）
2. **内容寻址哈希** -- 每个块用 SHA-256(parent_hash, token_ids) 标识
3. **父链验证** -- 父哈希创建链条，匹配块 N 意味着块 0 到 N-1 完全一致
4. **全局哈希表** -- 映射块哈希到物理 KV Cache 块
5. **最长前缀匹配** -- 新请求到来时，顺序遍历块哈希直到未命中

### 多轮对话中的效果

| Turn | 动作 | TTFT |
|------|------|------|
| Turn 1 | 全量 prefill（写入缓存） | ~4.3 秒 |
| Turn 2 | 缓存命中前缀，仅 prefill 新消息 | ~0.6 秒 |
| Turn 3 | 缓存命中前两轮前缀 | 更低 |

缓存命中率可达 90-96%，输入 token 成本降低约 10 倍。

### Prefix Caching 的局限

1. **精确匹配** -- 前缀中任何一个字节变化都会从该点向后失效整个哈希链
2. **分布式中失效** -- 标准 LB 将相关请求分散到不同 Pod，破坏缓存局部性
3. **内存压力** -- 高负载时块被 LRU 驱逐，来不及复用
4. **无中间段缓存** -- 只能从前向后匹配，不能独立缓存中间段落

vLLM Router 的局限：为什么需要 Prefix-Aware Router
--------------------------------------------------

### vLLM Router 现状

vLLM Router 是用 Rust 编写的高性能负载均衡器，支持四种策略：

| 策略 | 路由方式 | 缓存友好性 |
|------|----------|-----------|
| 一致性哈希 | 按 session_id 路由 | 中等 |
| Power of Two | 随机二选一 | 低 |
| Round Robin | 轮询 | 无 |
| Random | 随机 | 无 |

### 核心问题

一致性哈希按 session_id 路由，**不是按 prompt 内容路由**：

- 不同用户共享同一个系统提示 -> 路由到不同 worker -> 缓存无法复用
- 用户 session_id 变化 -> 丢失缓存亲和性
- Router 对每个 worker 上实际缓存了什么一无所知

```{mermaid}
graph TB
    subgraph problem["Problem: Session-based routing"]
        U1["User A: sys prompt X"] -->|session 1| W1["Worker 1"]
        U2["User B: sys prompt X"] -->|session 2| W2["Worker 2"]
        U3["User C: sys prompt X"] -->|session 3| W3["Worker 3"]
    end

    subgraph solution["Solution: Prefix-based routing"]
        U4["User A: prefix hash H1"] -->|H1| W4["Worker 1: cached H1"]
        U5["User B: prefix hash H1"] -->|H1| W4
        U6["User C: prefix hash H1"] -->|H1| W4
    end
```

### 已有的解决方案

| 项目 | 方法 | 效果 |
|------|------|------|
| llm-d Precise Scheduling | 实时 KVEvent 索引 + 缓存亲和评分 | 57x TTFT 提升 |
| Ray Serve | 分布式前缀树 + 亲和路由 | 可配置匹配阈值 |
| vLLM Production Stack | LMCache 集成 + 前缀感知路由 | 确认缓存命中 |

Claude Code 与 Prefix Caching
-----------------------------

### Claude Code 的缓存设计

Claude Code 实际上**高度优化了 prompt caching**：

1. **分层结构** -- 静态内容在前（系统提示、工具定义），项目上下文次之，动态内容最后
2. **动态内容放在 message 中** -- 时间戳、git status 等通过 system-reminder 注入，不改系统提示
3. **延迟工具加载** -- MCP 工具先注册为轻量 stub，按需加载完整 schema
4. **压缩保留前缀** -- 对话压缩时复用相同的系统提示和工具定义

### 为什么通过第三方网关缓存效果打折

Claude Code 的系统提示嵌入了**每台机器/每个目录独有的信息**：

- 工作目录路径
- Git 分支名和最近提交
- 平台、Shell、OS 版本
- 自动记忆路径

这不是恶意的反缓存策略，而是功能正确性的需要 --
不同目录的会话需要不同的上下文。但实际效果是：
不同机器/不同目录的会话会构建不同的前缀，无法通过第三方网关共享系统提示缓存。

对于使用 **Qwen 3.6 等自部署模型**的场景，这个问题不存在 --
我们自己控制完整的 prompt 结构，可以设计出最优的缓存策略。

下一步：构建 Prefix-Matching Router
------------------------------------

### 设计思路

我们计划构建一个基于前缀哈希的智能路由器，替代 vLLM Router 的一致性哈希：

1. **提取稳定前缀** -- 从每个请求中提取系统提示 + 对话前缀
2. **计算前缀哈希** -- 对稳定部分计算 SHA-256
3. **一致性哈希路由** -- 按前缀哈希（而非 session ID）映射到 worker
4. **负载感知降级** -- 当目标 worker 过载时，回退到次优选择

### 核心算法

```
对于每个请求:
    prefix_hash = SHA256(system_prompt + conversation_prefix)
    workers = consistent_hash_ring.lookup(prefix_hash)

    if workers[0].queue_length < THRESHOLD:
        route to workers[0]  // 缓存亲和性最优
    else if workers[1].queue_length < THRESHOLD:
        route to workers[1]  // 哈希环上的下一个副本
    else:
        route to least_loaded_worker  // 降级为负载均衡
```

### 更进一步的方案：KVEvent 驱动的精确调度

参考 llm-d 的设计：

1. 每个 vLLM Pod 发出 KVEvent 流（缓存块创建/驱逐事件）
2. 全局索引维护 block_hash -> pod 的映射
3. 路由器为每个请求计算每个 Pod 的"缓存亲和分数"
4. 结合负载感知评分做出路由决策

这个方案在 8 Pod、16 H100 的环境下实现了 **57x TTFT 提升**（0.542s vs 31s）。

### 对我们 Gateway 的意义

```{mermaid}
graph TB
    subgraph current["Current Architecture"]
        G1["LLM Gateway"] --> R1["vLLM Router"]
        R1 --> V1["vLLM Worker 1"]
        R1 --> V2["vLLM Worker 2"]
        R1 --> V3["vLLM Worker 3"]
    end

    subgraph future["Future: Prefix-Aware"]
        G2["LLM Gateway"] --> PR["Prefix Router"]
        PR -->|"hash H1"| P1["Worker 1: cached H1"]
        PR -->|"hash H2"| P2["Worker 2: cached H2"]
        PR -->|"hash H1"| P1
        PR -->|"hash H3"| P3["Worker 3"]
    end
```

LLM Gateway 作为请求的统一入口，天然是做 Prefix-Aware Routing 的最佳位置：

- 它能看到完整的请求体（包含 prompt 内容）
- 它能计算前缀哈希
- 它能跟踪路由历史
- 它能与 vLLM worker 的缓存状态同步

这是我们的下一个主要技术方向。
