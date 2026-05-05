## UPDATE - 2026-05-05 01:19 - Service 解耦收口与 Graph/Lark 链路对齐

### 撰写时间

- 2026-05-05 01:19

### Base Commit

- 922eb20468224b03c719a4bce1f193d3e4b8b91b

### 背景与改动目标

- 这轮改动的主线不是新增功能，而是把“非 service 解耦数据库操作”继续收口，目标是让 Graph、Lark 集成与 CLI 的数据访问统一走 service，减少 `with session() as db` 在非 service 层的散落。
- 同时我们在做 Harness 化沉淀：补齐 skill 能力（文档生成、文档优化、Graph 文档重写、commit 质检与更新记录写作）和对应文档资产，降低后续重复工作成本。

### 改动概览

- Graph 节点侧：`ConversationGraph` 与 `FRBuildingGraph` 的加载节点从 ORM 实体访问改为 service 返回 dict 访问，去掉对 `checkFigureAndRelationOwnership`/`session` 的直接依赖。
- Service 层：`user` 新增 `getUserIdByOpenId`；`figure_and_relation` 新增 `ifFRBelongsToUser`，并扩充 `getAllFigureAndRelations` 返回字段，补齐上游调用改造所需数据。
- Lark 集成侧：`index.py`、`menu.py` 从 `integration/utils.py` 中移除 DB 查询逻辑，统一改走 `src/services/user.py` 与 `src/services/figure_and_relation.py`。
- CLI 侧：`fr list` 输出前统一 `figure_role` 的字符串格式（`stringifyValue(...).upper()`），`doctor` 将 `session` import 下沉到检查分支，减少模块加载时耦合。
- 文档与工程资产：重写/更新 `ConversationGraph`、`FRBuildingGraph` README 以及 `docs/BOTTLENECK.md`、`docs/REFACTOR.md`、`docs/TODOs.md`，并新增多份 `.trae/skills/*` 能力说明。

### 关键链路解析（含上下游）

- 上游依赖：
- `src/services/user.py` 的 `getUserById`、新加 `getUserIdByOpenId`，以及 `src/services/figure_and_relation.py` 的 `getFigureAndRelation`/`getAllFigureAndRelations`/新加 `ifFRBelongsToUser` 成为统一数据入口。
- `buildFigurePersonaMarkdown` 的入参从 ORM 实例改为 dict，这直接要求上游调用方在 Graph 节点里不再传 ORM 对象。

- 当前改动：
- `ConversationGraph.nodeLoadFRAndPersona` 与 `FRBuildingGraph.nodeLoadFR` 先拿 `user` 再拿 `fr`，失败即抛错，成功后把 `figure_role`、`figure_name`、`words_figure2user` 等字段从 dict 读取并回写 state/log。
- `integration/utils.py` 删除 `getUserIdByOpenId` 与 `frBelongsToUser` 两个带 DB 访问的方法；`index.py`、`menu.py` 对应替换为 service 返回结构（`res.get(...)`）。
- `buildFigurePersonaMarkdown` 内部统一用 `fr.get(...)` 取字段，并在 `figure_name` 为空时降级标题为“人物画像”，避免空标题。

- 下游影响：
- Lark 消息处理链路（批量发送、菜单切换、消息入口鉴权）现在依赖 service 响应结构，减少 channel 层绕过 service 的概率，便于后续切到 dispatcher/远程 service。
- Graph 输出仍保持原状态字段形状（`figure_and_relation`、`user_name`、`logs` 等），因此下游节点消费面基本不变；但因为加载逻辑从 ORM 切到 dict，后续新增字段要同步 service 返回 include 列表。
- 文档消费侧（README、架构文档）与当前实现更对齐，能直接作为后续改造和 review 的事实基线。

### 改动结果与业务影响

- 当前看，核心收益是“链路一致性”提升：Graph / Lark / CLI 的身份与 FR 查询入口向 service 收敛，减少重复实现和跨层 DB 访问。
- 这也给后续能力（共享数据库模式、dispatcher 分流、权限治理）打了地基，因为调用方已经逐步从“拿 ORM 实体直接操作”迁移到“消费 service 返回协议”。
- 代价是返回值语义更依赖约定（大量 `.get(...)`），如果 service 返回字段不完整，调用侧会静默拿到 `None`，需要更多契约验证与回归测试兜底。

### 风险与待办

- 已知风险：`buildFigurePersonaMarkdown` 入参类型切换后，若仍有旧调用传 ORM 对象，会在运行时出现字段读取偏差；当前 diff 中已覆盖主要调用点，但仍建议做一次全局检索回归。
- 已知风险：Lark 集成链路改为 `dict` 协议后，错误码与空值分支主要靠调用侧判断，建议补一层统一错误处理工具，避免各处 `res.get(...)` 分散。
- 未验证项：本次没有看到针对 Graph/Lark/CLI 的自动化回归新增，建议至少补三类验证：`open_id -> user_id` 查找失败分支、`fr` 归属校验分支、Graph 节点加载失败分支。
- 后续动作：继续把剩余“非 service 层 DB 访问”做清点；并基于新加的 skill 资产在每次提交前固定执行“diff 质检 + 更新记录追加”。

### 建议 Commit Message（git-cz）

- `refactor(service): align graph and lark flows with service-only data access`

## UPDATE - 2026-05-05 15:14 - FRBuildingGraph 并发收口与提交质检文档补强

### 撰写时间

- 2026-05-05 15:14

### Base Commit

- ae067db5a89f989ed37cbda1d9fa1e04da057868

### 背景与改动目标

- 这次改动的起点有两条线，但本质上都在处理“约束要不要落成显式规则”。一条在线上链路：`FRBuildingGraph` 作为进程内单例被复用时，如果同时有多个画像完善任务进入，运行语义其实是不稳定的。另一条在 Harness 侧：我们已经开始依赖 `commit-quality-reviewer` 和 `commit-update-writer` 做提交流程约束，因此这些 skill 的触发边界和写作规则也需要写得更清楚。
- 一开始的目标不是扩展功能，而是把原本隐含的使用约束收紧成代码和文档里的显式行为。换句话说，这轮改动更像一次“收口”，而不是新增能力。

### 改动概览

- Graph 侧：`src/agents/graphs/FRBuildingGraph/graph.py` 把 `getFRBuildingGraph()` 从直接返回全局 graph，改成异步上下文管理器；内部新增 `asyncio.Semaphore(1)`，把“同一时刻只允许一个画像完善任务执行”变成显式约束。
- Lark 集成侧：`src/channels/lark/integration/menu.py` 的 `buildPersonaLark()` 同步切到 `async with getFRBuildingGraph()`；当 graph 处于运行中时，菜单命令不再静默失败，而是给用户回一张“请稍后再试”的黄色提示卡片。
- 测试/脚本侧：`tests/graphs/FRBuildingGraph.py` 的调用方式同步更新，避免继续以旧接口直接拿 graph。
- Harness 文档侧：`.trae/skills/commit-quality-reviewer/SKILL.md` 补充了“审查本次改动 / 检查代码变更 / review 代码 / 代码质检”等触发描述；`.trae/skills/commit-update-writer/reference/language-style.md` 删掉了重复的“追加记录建议骨架”，把重点重新收敛到文风和表达约束。

### 关键链路解析（含上下游）

- 上游依赖：`buildPersonaLark()` 并不是在当前线程里直接 `await` graph，而是通过 `_submitBackgroundCoroutine()` 把协程扔到 `src/channels/lark/integration/index.py` 里那条全局后台事件循环执行。因此这次并发控制的落点不是 HTTP 层或消息队列层，而是 `FRBuildingGraph` 入口本身。
- 当前改动：`getFRBuildingGraph()` 现在负责两件事。第一件事是用 `Semaphore(1)` 拒绝并发进入；第二件事是用 `async with` 保证异常路径也能释放占用。对应地，`buildPersonaLark()` 不再先拿 graph 再调用，而是在上下文里执行 `graph.ainvoke(init_state)`，并在 busy 分支回显更明确的用户提示。
- 下游影响：对人物画像完善主链路来说，输入 state、graph 节点拓扑和返回结果都没有变化，真正变化的是“什么时候允许执行”。也就是说，下游的报告发送、成功卡片、失败卡片逻辑基本保持原样；但从现在开始，同一进程内第二个并发画像任务会在入口被拒绝，而不是和第一个任务同时跑。
- 文档链路侧的影响更偏流程治理。`commit-quality-reviewer` 的触发面写清楚后，后续让 agent 执行“审查本次改动”这类自然语言请求时，路由更稳定；`commit-update-writer` 的风格参考去掉模板重复段落后，更新记录的唯一模板来源重新回到 skill 主文档，避免两份模板漂移。

### 改动结果与业务影响

- 当前看，最直接的收益是 `FRBuildingGraph` 的单实例使用语义更明确了。以前这件事更多依赖调用方自觉，现在变成 graph 入口自己兜底。对于 Lark 菜单命令来说，这能减少同一时刻重复触发画像完善时的状态错乱风险。
- 另一个收益是用户反馈更可解释。之前如果后台任务冲突，调用方很难知道为什么失败；现在至少会明确告诉用户“当前存在运行中任务，请等待完成后再试”。
- Harness 侧的收益则更偏长期。skill 触发词和文风规则补强后，提交流程里的自动质检、更新记录沉淀更容易走到一致路径，减少“能做但触发不到”或“同类文档写法反复漂移”的问题。

### 风险与待办

- 已知风险：这次把并发限制落在 graph 入口，主链路行为是清晰了，但没有配套自动化测试去验证“第二个请求被拒绝”“异常退出后信号量会释放”这两个边界。它不一定马上影响当前功能，但后续重构时缺少回归保护。
- 未验证项：当前没有看到基于真实 Lark 后台 loop 的并发回归，也没有看到针对 busy 提示卡片的自动化检查。现阶段只能认为语义上合理、实现上可读，但验证深度还不够。
- 后续动作：先把 busy 分支改成专用异常，再补一组最小异步测试，直接围绕 `getFRBuildingGraph()` 的占用与释放语义做校验；这样这轮“并发收口”才算真正闭环。

### 建议 Commit Message（git-cz）

- `feat(graph): guard FR building graph against concurrent runs`
