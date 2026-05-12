## CHANGELOG - 2026-05-05 01:19 - Service 解耦收口与 Graph/Lark 链路对齐

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

## CHANGELOG - 2026-05-05 15:14 - FRBuildingGraph 并发收口与提交质检文档补强

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

## CHANGELOG - 2026-05-07 19:06 - 文档体系补全与 Harness 约束沉淀

### 撰写时间

- 2026-05-07 19:06

### Base Commit

- 0e1926cdce2b9fff9caf373706f5d9773dccf3c5

### 背景与改动目标

- 这次改动的主体是文档收口，不是代码逻辑变更。目标是把项目现状、Harness 方法论和后续规划写成可复用的文档资产，减少协作时的信息断层。
- 本次记录按用户确认口径，忽略 `.env.example` 删除，仅聚焦文档相关改动。

### 改动概览

- `docs/HARNESS.md`：从单行标题扩展为完整落地方案，补齐 skill 定位、生产流程、消费方式、闭环示例与边界说明。
- `docs/BOTTLENECK.md`：在“共享数据库问题”之外，新增“单一飞书 Bot 问题”背景与长期方案，明确多 Bot 配置方向。
- `docs/BRIEF_INTRO.md`：新增项目简要介绍文档，覆盖 Why/What/How、核心链路、数据对象、CLI 与飞书集成、Harness 角色等全局信息。
- `docs/TODOs.md`：将“同一时间只允许一个 FRBuildingGraph 运行，限制并发”标记为已完成，状态与当前实现对齐。
- `.trae/rules/language-style.md`：新增表达风格规则，约束文档与回复语言，减少模板化表达。

### 关键链路解析（含上下游）

- 上游依赖：现有实现与既有 skill（`commit-quality-reviewer`、`commit-update-writer`、`doc-generator`、`doc-optimizer`）是文档内容的事实来源，文档更新需要与这些能力契约保持一致。
- 当前改动：通过 `HARNESS` 主文档 + `BRIEF_INTRO` 总览 + `BOTTLENECK` 议题沉淀 + `TODOs` 状态同步 + `language-style` 规则约束，形成“背景、方法、执行、约束、路线图”一体化文档链路。
- 下游影响：后续协作在“项目介绍、任务对齐、文档写作、收尾沉淀”场景下可直接复用这些资产，减少口头传递和重复解释成本。

### 改动结果与业务影响

- 当前收益主要在工程协作层：项目介绍、瓶颈分析、Harness 方法和待办状态都获得了统一的书面基线。
- 新成员和跨会话协作者可以更快理解系统结构与工作方式，降低“只看代码难以把握全貌”的成本。
- 文档规则被显式化后，后续更新记录与说明文档在表达风格上更一致，可读性更稳定。

### 风险与待办

- 已知风险：文档体量快速增长后，若缺少周期性校对，容易与代码实现再次漂移。
- 未验证项：`docs/BRIEF_INTRO.md` 中的流程和参数说明尚未做系统化一致性检查（仅基于当前认知整理）。
- 后续动作：在后续迭代建立“文档一致性复查”节奏，重点核对 Graph 行为、CLI 命令和 skill 清单是否保持同步。

### 建议 Commit Message（git-cz）

- `docs(harness): enrich project docs and align writing rules`

## CHANGELOG - 2026-05-08 18:51 - 会话校验扩展为当前用户信息并补齐飞书自动续登链路

### 撰写时间

- 2026-05-08 18:51

### Base Commit

- 498d8172ffa9bd45a471fdee89c0eca5a9031a7b

### Compare Scope

- working_tree_only

### 背景与改动目标

- 这次改动的起点是登录态校验语义不足。原实现 `getUserIdFromLocalSession()` 只返回 `user_id`，调用方如果还需要 token，需要重复读取本地会话，链路上存在重复与分散。
- 同时，飞书消息处理链路在 token 过期时没有自动恢复能力。用户在飞书里发消息时，若本地会话失效，服务侧会直接进入失败分支，交互连续性不稳定。
- 因此这次目标有两点：一是把本地会话读取能力从“只拿 user_id”扩展成“返回当前用户信息”；二是在 Lark 集成入口补上基于 `open_id` 的自动登录与会话落盘，降低 token 过期带来的中断。

### 改动概览

- `src/cli/utils.py`：将 `getUserIdFromLocalSession` 重命名为 `getCurrentUserFromLocalSession`，并把返回值改为包含 `user_id` 与 `access_token` 的 dict，同时更新返回类型注解。
- `src/cli/commands/auth.py`、`src/cli/commands/fr.py`、`src/cli/commands/lark_service.py`：统一切换到新接口，通过 `.get("user_id")` 读取身份信息，保持命令行为一致。
- `src/services/user.py`：新增 `userLoginByOpenId(open_id)`，用于飞书链路在已绑定账号场景下补发 access token。
- `src/channels/lark/integration/index.py`：新增 `loginIfNeeded(open_id)`，在 `messageHandler()` 前置执行。流程是先校验本地会话，失效时走 `userLoginByOpenId`，成功后 `saveLocalSession`。
- `docs/BOTTLENECK.md` 与 `src/main.py`：分别做文档小标题表述收口与函数签名类型补充（`-> None`），不改变主功能行为。

### 关键链路解析（含上下游）

- 上游依赖：`getCurrentUserFromLocalSession()` 依赖 `loadLocalSession()` 与 `getUserIdByAccessToken()` 做本地 token 校验；`userLoginByOpenId()` 依赖 `User.lark_open_id` 查询与 `createAccessToken()` 发 token。
- 当前改动：CLI 侧从“取单一 user_id”迁移到“取当前用户上下文”；Lark 侧在消息入口新增“先校验，后补登”的恢复逻辑，并将成功 token 写回本地 `session.json`。
- 下游影响：`whoami`、`fr`、`lark-service start` 这些命令仍沿用原有 user_id 语义，但现在可以复用同一份会话上下文；飞书消息主链路在会话过期时具备自动续登能力，减少因 token 失效导致的对话中断。

### 改动结果与业务影响

- 当前看，主要收益是“登录态能力聚合”和“消息入口稳定性”提升。调用方不再各自拼接会话信息，Lark 服务也不需要完全依赖人工重新登录才能继续处理消息。
- 这次还补了异常兜底：`loginIfNeeded()` 在自动登录或写本地会话异常时会记录日志并返回错误卡片，不会把异常直接抛到上层中断整条消息处理函数。
- 边界上仍然存在一类语义问题：`open_id` 未绑定账号时，当前反馈文案仍是“请稍后重试”，可读性不如“请先绑定账号”直观。

### 风险与待办

- 已知风险：`loginIfNeeded()` 里把“未绑定账号”和“系统异常”都收敛成同一提示文案，排障信息粒度不够。
- 已知风险：Lark 自动登录会覆盖本地 `session.json`，单机多账号轮流触发消息时会出现“最后一次登录覆盖前一次会话”的行为，需要后续按账号隔离会话文件。
- 未验证项：当前未看到新增自动化测试覆盖“token 过期自动续登成功”“open_id 未绑定失败文案”“会话写盘失败兜底”三条关键分支。
- 后续动作：补最小回归测试，并细分 `userLoginByOpenId` 的失败码与用户提示，降低误导性反馈。

### 建议 Commit Message（git-cz）

- `feat(auth): add lark open_id relogin and unify current session access`

## CHANGELOG - 2026-05-10 00:34 - Python 最低版本统一提升至 3.12 并同步发布链路

### 撰写时间

- 2026-05-10 00:34

### Base Commit

- 751bd2da74d98a7681e6c4b28ce5fd523583fc0e

### Compare Scope

- working_tree_only

### 背景与改动目标

- 这次改动的核心目标很直接：把项目里“Python 最低版本”从 `3.11` 统一提升到 `3.12`，避免文档、运行时校验、打包元数据和 CI 配置出现口径不一致。
- 一开始我们只看到包元数据里的 `requires-python`，但如果只改这一处，CLI 的 `doctor` 提示和 README 仍会继续引导用户使用 `3.11`，最终会造成“规范已变更、入口提示未同步”的体验割裂。因此这轮改动按链路做了同步收口。

### 改动概览

- 包与锁文件：`pyproject.toml`、`uv.lock` 的 `requires-python` 均从 `>=3.11` 调整为 `>=3.12`。
- 运行时校验：`src/cli/commands/index.py` 的 `min_py` 从 `(3, 11)` 提升到 `(3, 12)`，并同步更新失败提示文案。
- 文档口径：`README.md` 中“环境准备”和 `doctor` 检查项的版本描述同步改为 `3.12`；`docs/HEARTCOMPASS.md` 的 `langgraph.json` 示例 `python_version` 改为 `"3.12"`。
- 发布链路：`.github/workflows/publish.yml` 的 `actions/setup-python` 从 `3.11` 调整为 `3.12`，保证打包与发布作业不再基于旧版本。
- 资产补充：`.trae/skills/commit-update-writer/SKILL.md` 触发词补充了 `changelog`，让“生成本次 changelog”可以被更稳定地路由到该 skill。

### 关键链路解析（含上下游）

- 上游依赖：安装与解析入口依赖 `pyproject.toml`/`uv.lock` 的 `requires-python` 约束；开发与发布入口依赖 GitHub Actions 的 Python 解释器版本。
- 当前改动：在元数据、CLI 校验、用户文档、CI 四个层面同时把最低版本切到 `3.12`，并保持提示文案与实际校验逻辑一致。
- 下游影响：本地安装、`immortality doctor`、以及发布流水线现在都以 `3.12` 为基准；仍使用 `3.11` 的环境会更早在安装或健康检查阶段暴露不满足约束，而不是在运行时隐式失败。

### 改动结果与业务影响

- 当前收益是“版本约束单一事实源”更清晰：用户看到的文档、CLI 报错、构建元数据和 CI 行为已经对齐到同一最低版本。
- 对维护侧的好处是减少排障分歧。后续遇到环境问题时，团队不再需要先确认“到底以 README、doctor 还是 CI 为准”，因为三者口径一致。
- 代价是兼容边界收窄：仍在 `Python 3.11` 的开发机/执行环境需要升级到 `3.12` 才能继续走标准流程。

### 风险与待办

- 已知风险：本次是配置与文案对齐，没有覆盖完整运行回归；若某些依赖在 `3.12` 下存在边缘兼容问题，需要在真实安装链路中进一步验证。
- 未验证项：未执行完整的“新环境从零安装 + `uv sync` + `immortality doctor` + 发布作业”端到端校验。
- 后续动作：建议在 CI 中新增一条最小健康检查（安装并运行 `immortality doctor` 关键分支），把版本升级后的行为验证前置到流水线。

### 建议 Commit Message（git-cz）

- `build(python): raise minimum supported version to 3.12`

## CHANGELOG - 2026-05-11 09:22 - Docker 模式 PostgreSQL 就绪检查收敛并统一 checkpoints 库名

### 撰写时间

- 2026-05-11 09:22

### Base Commit

- 82f7d2ad627e2d4e82351a779359146bffe70978

### Compare Scope

- working_tree_only

### 背景与改动目标

- 这次改动的起点是 `immortality setup` 在 Docker 模式下存在误判：前置检查显示 PostgreSQL 已就绪，但后续执行 `psql` 仍可能因为默认 Unix socket 不存在而失败。
- 目标是让“就绪检查”和“实际数据库操作”使用同一连接语义，减少“看起来 ready、实际失败”的体验割裂，并同步文档与模板里的 checkpoint 数据库命名。

### 改动概览

- `src/cli/commands/index.py`：将 checkpoint 数据库初始化函数重命名为 `_setupCheckpointsDBIfNeeded`，并把数据库名统一为 `immortality_checkpoints`。
- `src/cli/commands/index.py`：两处 `docker exec ... psql` 增加 `-h 127.0.0.1`，强制走 TCP，不再依赖容器内默认 socket。
- `src/cli/commands/index.py`：Docker 启动后就绪判断从主机 `socket.create_connection` 改为容器内 `pg_isready` 探活，语义与后续执行链路保持一致。
- `src/cli/assets/init-db.sh`、`src/cli/assets/.env.example`、`README.md`：数据库名从 `immortality_checkpoint` 同步为 `immortality_checkpoints`，确保脚本、配置模板和说明口径一致。

### 关键链路解析（含上下游）

- 上游依赖：`docker compose up` 负责拉起 `immortality-postgres`；资源模板由 `src/cli/assets/init-db.sh` 与 `src/cli/assets/.env.example` 提供。
- 当前改动：`dockerDBSteup()` 先以 `pg_isready` 判断容器内 PostgreSQL 可用，再进入 `_setupCheckpointsDBIfNeeded()` 执行数据库存在性检查和创建。
- 下游影响：`setupCLI()` 继续写入 `.env`，但 `CHECKPOINT_DATABASE_URI` 默认指向 `immortality_checkpoints`；文档和自动初始化脚本不再出现单复数混用。

### 改动结果与业务影响

- 当前收益是失败模式更可预测：如果数据库未真正就绪，会在 `pg_isready` 阶段尽早失败；如果进入 `psql`，连接方式与探活方式一致。
- 对用户侧来说，这次优化能显著降低“容器已启动但 `psql` 报 socket 文件不存在”的概率，排障路径也更清晰。
- 这轮改动同时完成了配置与文档的口径收口，后续新环境初始化时不易因数据库命名不一致产生偏差。

### 风险与待办

- 已知风险：本次未包含“旧库名 `immortality_checkpoint` 自动迁移到 `immortality_checkpoints`”逻辑，历史环境是否保留旧数据可见性取决于用户现有库状态。
- 未验证项：尚未补充自动化测试覆盖 `pg_isready` 超时分支与 checkpoints 数据库创建分支。
- 后续动作：建议增加最小回归验证，覆盖 Docker 首次初始化、重复执行 setup、以及容器未就绪错误提示文案。

### 建议 Commit Message（git-cz）

- `fix(cli): align docker postgres readiness and checkpoints db setup`

## CHANGELOG - 2026-05-11 11:14 - Graph 用户名展示统一为 username(nickname)

### 撰写时间

- 2026-05-11 11:14

### Base Commit

- 2cd2d5c18e4210bcd98d74e44c538ed1acd8f8d0

### Compare Scope

- working_tree_only

### 背景与改动目标

- 这次改动的出发点是“对话上下文里的用户称呼不够稳定”。之前 `ConversationGraph` 与 `FRBuildingGraph` 都直接把 `username` 写入 `user_name`，当昵称和账号名存在差异时，提示词和报告上下文会丢失一部分身份信息。
- 目标是让两个 Graph 在构建 `user_name` 时保持同一规则，并让下游提示词消费到更完整的用户标识；同时顺手清理一处无实际作用的调试注释，减少链路噪音。

### 改动概览

- `src/agents/graphs/ConversationGraph/nodes.py`：`nodeLoadFRAndPersona` 新增 `username`/`nickname` 变量，`user_name` 统一改为 `username(nickname)`（两者相同则保留单值）。
- `src/agents/graphs/FRBuildingGraph/nodes.py`：`nodeLoadFR` 按同样规则构建 `user_name`，保持两个 Graph 的状态语义一致。
- `src/channels/lark/integration/menu.py`：删除 `buildPersonaLark` 内一行注释掉的调试输出（`# print(res)`），不改变流程行为。

### 关键链路解析（含上下游）

- 上游依赖：两处改动都依赖 `getUserById(user_id)` 返回的 `user` 字典字段（`username`、`nickname`）；规则变化发生在 Graph 的加载节点，而不是提示词模板本身。
- 当前改动：在 `nodeLoadFRAndPersona` 与 `nodeLoadFR` 入口统一把 `user_name` 做格式化，之后继续透传到 Graph state，不改变原有执行路径与错误分支。
- 下游影响：`ConversationGraph.nodeCallLLM` 仍通过 `state["user_name"]` 注入 `CONVERSATION_SYSTEM_PROMPT`；`FRBuildingGraph` 内多处报告和约束提示也消费该字段，因此下游会看到更明确的人名标识。`menu.py` 的注释清理只影响可读性，不影响飞书任务执行。

### 改动结果与业务影响

- 当前收益主要是“称呼一致性”提升：两个 Graph 对 `user_name` 的构造口径对齐，避免一处显示账号名、另一处显示昵称的语义偏差。
- 在昵称与账号名不同的场景下，提示词中的指代信息更完整，理论上有助于减少模型把“我/说话人”映射错对象的概率。
- 这轮变更没有引入新的服务调用或状态字段，整体属于低侵入改动。

### 风险与待办

- 未验证项：本次未看到围绕“昵称缺失/昵称等于账号名/昵称不同于账号名”的自动化回归，建议补最小单测覆盖格式化分支。

### 建议 Commit Message（git-cz）

- `fix(graph): unify user_name format with username and nickname`

## CHANGELOG - 2026-05-12 17:25 - 导入 DeepWiki 知识库以增强项目上下文

### 撰写时间

- 2026-05-12 17:25

### Base Commit

- 36079dd

### Compare Scope

- working_tree_only

### 背景与改动目标

这次改动的起点是为了提升 AI Agent（当前工作区的智能助手）对整个 Immortality 项目的全局理解能力。之前我们在交互时，由于缺乏系统的领域知识和架构说明，AI 可能需要反复通过搜索代码库来推断背景，甚至出现理解偏差。
因此这次我们将沉淀的 DeepWiki 知识库（包含架构设计、工作流机制、开发规范等）以 Markdown 和 ZIP 格式导入到 `.trae/deepwiki/` 目录。目标是让 AI 能够直接读取并索引这些高质量的结构化文档，从而在后续的编码和问答中提供更准确、更符合项目约定的建议。

### 改动概览

- 新增 `.trae/deepwiki.zip`：打包后的全量知识库归档。
- 新增 `.trae/deepwiki/` 目录及其下的多个 Markdown 文档，涵盖以下核心板块：
    - **核心架构与模型**：`核心概念与架构.md`、`数据模型与存储.md`
    - **工作流与图状态**：`代理图设计与工作流.md`、`ConversationGraph 对话工作流.md`、`FRBuildingGraph 人格构建工作流.md`、`图状态管理与持久化.md`
    - **集成与工具**：`飞书集成与交互.md`、`CLI 工具参考.md`
    - **开发指南与规范**：`快速开始.md`、`开发与贡献指南.md`、`人格构建与提示词工程.md` 等。

### 关键链路解析（含上下游）

- 上游依赖：无代码层面的直接依赖。这些文档是团队对现有代码实现和架构设计的抽象与总结。
- 当前改动：将这些文档实体化到 `.trae` 工作区目录下。这些文件未与业务代码混用，保持了文档资产与业务逻辑的隔离。
- 下游影响：主要影响 AI 助手的上下文检索（RAG）。当开发者要求生成代码或解释逻辑时，AI 能够优先命中 `.trae/deepwiki` 中的权威约定，避免自行脑补不符合规范的实现。

### 改动结果与业务影响

- **收益**：AI 助手的项目认知被拉齐，后续的 Agent 对话、代码生成和架构重构将具备更稳定的“系统记忆”。比如在修改图状态管理时，可以直接参考 `图状态管理与持久化.md` 的既有规范。
- **代价**：代码仓库体积略有增加，且引入了需要维护的文档副本。

### 风险与待办

- 当前看起来最大的风险是**知识库与代码实现的同步问题**。随着代码迭代，如果 `.trae/deepwiki` 没有被及时更新，AI 可能会基于过时的文档给出错误建议。
- 换句话说，当前解决的是“从无到有”的上下文注入，但还没有建立“自动保鲜”机制。
- 建议补充验证 / 后续动作：考虑编写一个 CI/CD 脚本或 Git Hook，在关键代码变更时提醒更新对应的 Wiki 文档；或者通过另外的自动化流程定期同步远端 Wiki 到本地。

### 建议 Commit Message（git-cz）

- `docs(knowledge): create deepwiki`
