---
name: "commit-update-writer"
description: "基于当前工作区与上次 commit 的差异，分析上下游依赖并产出改动说明，追加写入 docs/UPDATES.md。用户要求“生成本次改动文档/更新记录”时触发。"
---

# Commit Update Writer

用于对“当前工作区 vs 上次 git commit”的改动做完整理解，并将结果以项目既有文风写入 `docs/UPDATES.md`。  
该 skill 的目标不是罗列 diff，而是解释**改动目的、业务逻辑、实现结果、上下游影响与风险**。

## 触发时机

- 用户要求“生成本次改动说明 / 更新日志 / 变更文档”
- 用户要求“基于 git diff 写 markdown 到 docs/UPDATES.md”
- 用户要求“分析改动及其依赖、被依赖影响并沉淀文档”

## 强制输入约定

- `base_commit` 固定为：`HEAD~1`
- 比较范围固定为：`HEAD~1..HEAD` + working tree 未提交变更

## 强制执行规则

1. 每次必须在文档中显式写出基线 commit id（`Base Commit`）。
2. 每次必须读取并遵循风格参考：  
   `.trae/skills/commit-update-writer/reference/language-style.md`
3. 输出文件固定为：`docs/UPDATES.md`（注意拼写）。
4. 只能**在文件末尾追加**，禁止修改/删除已有内容。
5. 若 `docs/UPDATES.md` 不存在，先创建，再追加首条记录。
6. 每次必须显式写出“当前内容撰写时间”，格式固定为 `YYYY-MM-DD HH:mm`（24 小时制）。
7. 每次输出末尾必须给出一条建议 `git commit message`，遵循 git-cz 规范（`type(scope): subject`），语义准确且长度适中（建议不超过 72 个字符）。

## 分析范围（强制）

不仅要读 diff 文件，还要覆盖以下上下文：

- 改动代码本身（变更 hunks）
- 改动部分直接依赖的上游（imports、被调用函数/类、配置来源）
- 依赖改动部分的下游（调用方、消费方、命令入口、graph 节点链路）
- 相关业务链路（CLI、channel、graph、service、database、prompt）

## 执行步骤

1. 锁定基线
    - 解析并记录 `HEAD~1` 对应 commit 的完整/短 SHA（作为 `Base Commit`）。
2. 收集变更
    - 获取文件级和 hunk 级 diff。
    - 标注新增、修改、删除、重命名。
3. 构建上下游依赖图
    - 对每个改动点定位：上游依赖、下游调用、运行入口。
    - 识别是否存在“改动点未同步其依赖方”的断链风险。
4. 还原业务逻辑
    - 改动前行为是什么。
    - 改动动机是什么（要解决什么问题）。
    - 改动后行为和结果是什么。
5. 评估影响与风险
    - 功能正确性、兼容性、稳定性、性能、可维护性。
    - 明确“已验证项 / 未验证项 / 建议补充验证”。
6. 按风格生成文档片段并追加
    - 生成一个“本次改动记录”区块。
    - 追加到 `docs/UPDATES.md` 末尾。
7. 生成建议 commit message
    - 根据本次改动主线，产出 1 条 git-cz 风格 message：`type(scope): subject`。
    - `subject` 需简洁，不写空泛词，不堆叠多主题。

## 追加写入模板（必须包含）

```markdown
## UPDATE - <YYYY-MM-DD HH:mm> - <一句话主题>

### 撰写时间

- <YYYY-MM-DD HH:mm>

### Base Commit

- <commit_id>

### 背景与改动目标

- <为什么改>

### 改动概览

- <改了哪些模块/文件，核心动作是什么>

### 关键链路解析（含上下游）

- 上游依赖：<依赖了什么，是否变更>
- 当前改动：<核心实现与逻辑>
- 下游影响：<谁依赖它，是否需要同步改>

### 改动结果与业务影响

- <结果、收益、边界、代价>

### 风险与待办

- <潜在风险>
- <建议补充验证 / 后续动作>

### 建议 Commit Message（git-cz）

- `<type>(<scope>): <subject>`
```

## 质量标准

- 文档必须能回答：
    - 改动是否合理
    - 是否可能引入新问题
    - 是否可能导致上下游依赖链路异常
- 不得只贴 diff，不得只列文件名。
- 结论必须有代码依据，不写无依据猜测。

## 禁止事项

- 禁止覆盖 `docs/UPDATES.md` 历史内容。
- 禁止写入 `docs/UPDATES.md`（除非用户明确改口）。
- 禁止省略 `Base Commit`（其值应来自 `HEAD~1`）。
- 禁止省略“撰写时间”（`YYYY-MM-DD HH:mm`）。
- 禁止输出不符合 git-cz 的 commit message，或过长、语义不清的 subject。
- 禁止忽略依赖与被依赖影响分析。
