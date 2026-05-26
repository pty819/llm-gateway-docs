迭代历程：从 0 到 122 个目标
==============================

Ultragoal 工作流
----------------

本项目使用 Ultragoal 方法论进行目标管理。整个项目被分解为 122 个可验证的目标（Goal），
每个目标都有明确的验收条件和完成证据。

### 目标分解统计

| 阶段 | 目标数 | 耗时 |
|------|--------|------|
| 项目初始化 | 8 | ~15 min |
| 核心数据库模型 | 15 | ~20 min |
| API 层 - 管理 | 25 | ~25 min |
| API 层 - 代理 | 12 | ~15 min |
| 服务层 | 20 | ~20 min |
| 前端 - 管理控制台 | 22 | ~25 min |
| 自助服务 + 团队 | 15 | ~15 min |
| 测试 + 验证 | 5 | ~10 min |

### 关键里程碑

**M1: 数据库骨架完成**
: 所有 15 个 SQLModel 模型定义完毕，Alembic 迁移可以成功执行。

**M2: 管理面 API 完成**
: 所有 CRUD 端点可用，包括 Subject、Project、ModelAlias、Upstream、RatePolicy 等。

**M3: 透明代理工作**
: 通过 Gateway 可以成功代理 OpenAI Chat Completions 请求到上游，
  流式和非流式均正常。

**M4: 管理控制台完成**
: SvelteKit 前端可以完成所有管理操作，包括实时健康检查、用量查看。

**M5: 自助服务上线**
: 用户可以自助注册、登录、管理自己的 Key 和查看自己的用量。

**M6: 团队 RBAC 完成**
: 管理员可以创建团队、分配模型授权，团队成员自动获得模型访问权限。

开发节奏
--------

整个项目在一天内完成（2026-05-22 到 2026-05-26），
采用密集的迭代节奏：

1. **2026-05-22** -- 需求访谈、PRD 编写、架构设计
2. **2026-05-22 ~ 23** -- Phase 1 实现（核心网关）
3. **2026-05-24** -- Phase 2 规划、自助服务实现
4. **2026-05-25** -- 团队 RBAC、前端完善
5. **2026-05-26** -- 集成测试、代码审查、修复

```{mermaid}
gantt
    title LLM Gateway Development Timeline
    dateFormat YYYY-MM-DD
    section Design
    Interview and Spec     :done, des1, 2026-05-22, 1d
    Architecture Design  :done, des2, 2026-05-22, 1d
    section Phase 1
    Database Models      :done, p1a, 2026-05-22, 1d
    Admin API            :done, p1b, 2026-05-22, 2d
    Proxy Layer          :done, p1c, 2026-05-23, 1d
    Admin Console        :done, p1d, 2026-05-23, 1d
    section Phase 2
    Self-Service Auth    :done, p2a, 2026-05-24, 1d
    Team RBAC            :done, p2b, 2026-05-25, 1d
    Integration Tests    :done, p2c, 2026-05-25, 2d
```

经验教训
--------

### 什么做得好

- **先访谈再编码** -- 9 轮 Socratic 访谈把需求模糊度压缩到 10.2%，避免了大量返工。
- **增量式架构** -- Phase 1 的管理面为 Phase 2 的自助服务提供了基础。
- **测试驱动** -- 12 个集成测试覆盖了所有核心路径，给了我们重构的信心。
- **完整的事实记录** -- RequestFact 从第一天就存在，让调试和用量分析变得简单。

### 什么可以改进

- **前端单文件** -- 整个管理控制台写在一个 ``+page.svelte`` 里（143 个符号），
  后续应该拆分为独立组件。
- **错误消息** -- 部分错误消息是英文硬编码，国际化不完整。
- **前端测试** -- 只有 1 个 E2E 冒烟测试，单元测试覆盖率可以更高。
