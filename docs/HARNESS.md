# Digital Immortality Harness 落地方案

> 你一行代码都不该写，这是我们的目标

## 本项目的 Harness 定位

在本工程中，Harness 的核心对象是 `skills` 资产。每个 `skill` 都是一个可执行的工程能力单元，包含：

- 触发时机：什么请求会路由到这个 skill。
- 输入约定：运行前必须准备哪些上下文。
- 执行步骤：在仓库内如何完成任务。
- 质量门槛：输出达到什么标准才算完成。
- 禁止事项：哪些行为会导致结论失真或流程失控。

换句话说，Harness 把“经验”变成“可执行规程”，再把规程挂到实际研发链路里。

## 现有技术资产

当前仓库已落地的 skill 资产位于 `.trae/skills/`：

- `commit-quality-reviewer`
- `commit-update-writer`
- `doc-generator`
- `doc-optimizer`
- `graph-doc-writer`
- `session-practice-learner`

这些 skill 覆盖了研发流程中最关键的几个环节：改动质检、更新记录、文档生成与优化、Graph 文档对齐、会话经验沉淀。

## Skill 如何被生产

本项目 Harness 落地的重点是“skill 怎么从一次次真实协作里被生产出来”。

从真实高频任务反推资产。例如：

- 每次改动后都要做差异质检，于是沉淀 `commit-quality-reviewer`。
- 每次改动都需要可追溯文档，于是沉淀 `commit-update-writer`。
- 每个 Graph 完成都需要类似的说明文档，详细描述工作流，于是沉淀 `graph-doc-writer`。

结合本仓库前几轮实践，生产流程是：

1. 发现稳定需求：先从高频、易重复的研发动作中识别**可复用**的候选能力（如差异质检、更新记录、文档重写）。
2. 向 GeniusAI 详细描述 skill 需求、用于什么场景、何时触发、如何工作、如何验收等等，让 GeniusAI 完成初版 skill 落入 `.trae/skills` 中。
3. 审阅 skill 是否存在不符合预期的部分，继续与 GeniusAI 沟通调整，直到基本符合预期。
4. 进入实战消费：在不同场景下让 GeniusAI 触发 skill 进行消费，观测结果。
5. 用纠偏反向修模：指出偏差，直接回写 skill 规则，而不是只改当次结果。
6. 二次验证闭环：更新后立即在后续任务中复用，确认新规则可稳定生效。

## Agent 如何消费 Skill

在我（Charlie）的当前工程实践中，主要使用 `GeniusAI` Code Agent 消费 skills，偶尔会由 `Trae Builder` 参与。

### 1. 路由消费

agent 先判断用户意图是否命中已有 skill，再决定调用哪个能力单元。例如：

- 改动审查 -> `commit-quality-reviewer`
- 改动文档 -> `commit-update-writer`
- 文档成文 -> `doc-generator`（并衔接 `doc-optimizer`）
- Graph 文档 -> `graph-doc-writer`
- 收尾沉淀 -> `session-practice-learner`

### 2. 执行消费

agent 进入 skill 后，会按 `SKILL.md` 的执行步骤读取上下文、运行检查、产出结果。  
这里的关键不是“会不会写代码”，而是“是否严格遵循该 skill 的输入/输出契约”。

### 3. 纠偏消费

当用户对结果纠偏时，agent 需要把纠偏升级成资产更新：  
要么更新已有 skill，要么新增 skill/rule/agent，避免同类偏差重复出现。

## 一个完整的生产-消费闭环（示例）

一次典型改动会形成如下链路：

1. 代码改动完成。
2. 触发 `commit-quality-reviewer` 做差异质检。
3. 根据质检结果修复阻塞问题。
4. 触发 `commit-update-writer` 追加 `docs/UPDATES.md`。
5. 若涉及文档重写，再触发 `doc-generator` + `doc-optimizer`。
6. session 收尾触发 `session-practice-learner` 判断是否沉淀新资产。

这条链路的重点是：每次执行不仅产出当次结果，还会反哺 skill 资产本身，形成持续演化的 Harness。

## 当前边界与后续方向

当前 Harness 以 `.trae/skills` 为主，`rules/agents` 仍在逐步建设中。  
这并不影响现阶段使用，但后续会把高频稳定约束继续沉淀为 `rules`，把跨任务长期职责沉淀为 `agents`，进一步降低执行漂移。
