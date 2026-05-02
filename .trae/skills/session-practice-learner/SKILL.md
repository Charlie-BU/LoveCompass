---
name: 'session-practice-learner'
description: 'session 收尾自动提炼经验并路由到 skill/rule/agent。触发条件：session 收尾、用户明确纠偏、稳定实践/重复错误/harness 资产缺口暴露。关键字：session 收尾、纠偏、经验落盘、知识沉淀、skill 更新、rule 更新、agent 更新、ESLint 规则新增。文件类型：.trae/skills/**、.trae/rules/**、.trae/agents/**、AGENTS.md、.eslintrc.*。使用场景：每次 session 结束前判断是否有长期可复用知识，落盘到最合适的资产或输出 No-op。'
---

# Session Practice Learner

在 session 即将结束时运行，完成"提炼 → 路由 → 落盘"全流程，无需分步调用。

## 触发时机

- Session 收尾，回顾本轮的改动与决策
- 用户明确说"以后都应该这样做"
- 同类错误在本轮多次出现，已值得总结
- 某个改动背后体现了稳定的新实践，而非局部修补

---

## Step 1 — 提炼学习点

从以下材料中归纳本轮的学习点：

- 用户的纠偏、补充要求、对最终方案的确认
- 最终落地文件和关键实现方式
- 本轮中间的失败尝试或返工记录
- 构建 / 测试 / review 结果

每条学习点输出：

```
### <标题>
- Type: Hard Rule | Reusable Practice | Role Gap | One-off Context
- Evidence: <支撑证据>
- Why It Matters: <对未来的价值>
- Scope: <适用范围>
- Confidence: high | medium | low
```

**质量门槛**：没有证据的结论不输出；只涉及一次性上下文的标为 `One-off Context`，不进入后续步骤。

---

## Step 2 — 路由落点

对每条 `Hard Rule` 或 `Reusable Practice`，按下表选落点：

| 落点     | 选它的条件                                                                                              |
| -------- | ------------------------------------------------------------------------------------------------------- |
| `rule`   | 本质是"必须/应该遵守的长期约束"；可用 MUST/SHOULD 表达；违反会带来稳定风险或返工                        |
| `skill`  | 本质是"怎么做一件事"的执行说明；有清晰触发条件和典型输入；更像 checklist、playbook、实施模板            |
| `agent`  | 需要长期存在的职责边界；有独立输入/输出/决策门槛；不是一句规则或一个 skill 能覆盖的职责                 |
| `eslint` | 规范描述的是**可被 AST 静态检测的代码结构问题**；有现成 ESLint 规则可配置，或结构固定到可以写自定义规则 |
| `no-op`  | 只适用于本轮上下文；只是个体偏好；没有稳定触发条件或验收标准                                            |

**已有资产的处理**：先检查现有 `.trae/skills/`、`.trae/rules/`、`.trae/agents/`、`.eslintrc.js`，如果已有资产能覆盖但表达不足，**优先更新现有资产**，而不是新增。只有确认现有资产已完整时才落到 `no-op`。

一条学习点可以同时拆成多个落点组合，例如 `rule + eslint`（文字约束 + 自动拦截）。

每条输出：

```
### <标题>
- Decision: rule | skill | agent | eslint | no-op | update:<existing-file>
- Why: <理由>
- Rejected Alternatives: <排除了哪些落点及原因>
- Target Files: <建议写入的文件路径>
```

---

## Step 3 — 落盘

根据 Step 2 的决策直接写文件，不需要用户逐条确认（置信度 `low` 的除外，先征询意见）。

### 写 rule

- 路径：`.trae/rules/<rule-name>.md`
- **文件不超过 80 行**：rule 只写约束本身，不写操作说明；操作说明另建 skill
- 只有需要影响所有 session 默认行为的约束才设 `alwaysApply: true`
- 正文用 MUST / SHOULD / SHOULD NOT 组织，每条约束一行，不写散文
- 不包含示例代码；如需举例，链接到对应 skill 或 docs

### 写 skill

- 路径：`.trae/skills/<skill-name>/SKILL.md`
- **文件不超过 200 行**：超出说明职责过宽，应拆分或抽 docs/
- frontmatter 必填字段：
  - `name`：kebab-case，与目录名一致
  - `description`：一句话，必须同时说明**做什么**和**何时调用**（作为 AI 路由依据）
- 正文必须包含以下章节（可合并，但不可缺）：
  - **触发时机**：明确列出哪些场景下应调用此 skill，避免模糊描述
  - **输入**：调用者需要提供什么上下文或材料
  - **步骤**：执行流程，有序编号
  - **输出 / 质量门槛**：产出物格式，或判断执行是否合格的标准
- 不在 SKILL.md 里堆砌大段示例代码；示例放 `docs/` 子目录并通过链接引用

### 写 agent

- 路径：`.trae/agents/<agent-name>.md`
- **文件不超过 150 行**：agent 定义职责边界，不是操作手册
- 必须包含以下章节：
  - **主体职责**（一句话 + 简短说明）：这个 agent 存在的唯一理由是什么
  - **触发时机**：在哪个阶段、由谁、在什么条件下调用
  - **输入**：需要哪些上下文、文件、结论
  - **流程**：核心决策步骤，3-7 步为宜
  - **输出格式**：产出物的结构或模板
  - **禁止事项**：明确列出不该做的事，防止职责蔓延
  - **边界说明**：与现有 agent / skill 的职责分界，避免重叠
- 只有职责稳定且反复出现时才新建 agent；一次性任务用 skill

### 落到 eslint

调用 `/coding-standards-lint` skill，输入本条学习点作为待检查的规范条目，由该 skill 判断：

- 若有现成 ESLint 规则：直接在 `.eslintrc.js` 的 `rules` 中补充或调整配置
- 若需要自定义规则：按 `.trae/skills/coding-standards-lint/docs/custom-rule-guide.md` 的"新增规则三步走"，在 `eslint-rules/` 中创建规则文件并注册

### 更新现有资产

直接 Edit 对应文件，在变更摘要里注明改了哪些部分及原因。

---

## 最终输出

```
## Session Learnings 落盘摘要

### 已写入
- [rule] .trae/rules/xxx.md — <一句话说明>
- [skill] .trae/skills/xxx/SKILL.md — <一句话说明>
- [agent] .trae/agents/xxx.md — <一句话说明>
- [eslint] .eslintrc.js rules / eslint-rules/xxx.js — <规则名及作用>
- [update] .trae/skills/yyy/SKILL.md — <改了什么>

### 跳过
- <标题> — One-off Context / 已被现有资产完整覆盖 / 置信度低待确认
```
