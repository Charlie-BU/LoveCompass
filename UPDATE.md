# UPDATE 说明（对比基线 commit）

## 1. 基线与范围

- **对比基线 commit**：`b0f1e27bfb356ef1f0bbb62c5889025b588f68b5`
- **当前变更规模**：`29 files changed, 1115 insertions(+), 380 deletions(-)`
- **核心主题**：
  - 引入“共享数据库模式（`USE_SHARED_DATABASE`）”
  - 新增服务分发层 `dispatchServiceCall`，统一本地直连 / 远程 HTTP 调用
  - FR（Figure & Relation）相关逻辑进一步下沉到 service，并补齐 router / dispatcher 映射
  - Lark 集成链路逐步去除 integration 层直连 DB，改为 service + dispatch
  - 修复 Robyn `query_params.get` 默认值缺失导致的运行时错误
  - Graph 节点里 `figure_and_relation` 从 ORM 对象向字典形态收敛，消除类型不一致

---

## 2. 变更动机（为什么做）

### 2.1 统一调用路径，支持两种运行模式

- 目标是让同一份业务代码在两种场景下都可运行：
  - **本地模式**：直接调用 Python service
  - **共享数据库模式**：将 service 调用转发到服务端 HTTP API
- 这要求把“业务调用入口”统一收口到 dispatcher，而不是在各层随意直连 DB 或直接调 service。

### 2.2 降低 integration/graph 层直接依赖 DB 的耦合

- `lark integration`、`ConversationGraph`、`FRBuildingGraph` 中原先存在不少直接数据库依赖或对象形态耦合。
- 本轮改造通过新增/复用 service，逐步把这部分能力下沉，调用层只感知标准化 `dict` 返回结构。

### 2.3 修复已暴露的运行时错误

- `request.query_params.get("x")` 在 Robyn 环境下需要显式 default 参数，否则报：
  - `QueryParams.get() missing 1 required positional argument: 'default'`
- `figure_and_relation` 在部分节点中已变为 `dict`，但仍按 ORM 属性访问，存在 `AttributeError` 风险；本轮已针对关键路径修复。

---

## 3. 架构级改动

## 3.1 新增服务分发层 `src/service_dispatcher.py`

### 做了什么

- 新增 `SERVICE_API_MAP`，集中维护 service 名称与 HTTP 路由映射（method/path/auth_required）。
- 新增 `dispatchServiceCall(service, args)`：
  - `USE_SHARED_DATABASE=False`：本地直接 `service(**args)`；
  - `USE_SHARED_DATABASE=True`：按 `SERVICE_API_MAP` 调远端 HTTP。
- 支持同步/异步 service 统一执行（`_runAwaitableSync`）。
- 使用 `HTTP_BASE_URL`（替换旧 `BASE_URL`）作为远端服务基地址。

### 原因

- 统一调用协议，避免各处自行判断“本地调用还是走 HTTP”。
- 让 CLI / Graph / Integration / Service 调用路径一致，减少模式切换下的行为分叉。

### 影响

- service 需要在 `SERVICE_API_MAP` 中有映射才能在共享模式下调用。
- `auth_required=True` 的映射依赖本地 session 的 `access_token`。

---

## 4. 业务域改动（按模块）

## 4.1 FR 领域（service + router + dispatcher）

### 文件

- `src/services/figure_and_relation.py`
- `src/server/subrouters/fr.py`
- `src/service_dispatcher.py`
- `src/channels/lark/integration/menu.py`
- `src/channels/lark/integration/utils.py`
- `src/utils/index.py`

### 做了什么

- 新增 FR service：
  - `frBelongsToUser(user_id, fr_id)`
  - `getFRAccessContextByOpenId(open_id, fr_id)`
- 新增 FR 路由：
  - `GET /fr/frBelongsToUser`
  - `GET /fr/getFRAccessContextByOpenId`
- 在 `SERVICE_API_MAP` 中补齐映射：
  - `frBelongsToUser`（auth）
  - `getFRAccessContextByOpenId`（no auth）
- `menu.py` 关键路径去 DB 直连，改为 dispatch：
  - `_getCommonInfo` -> `getFRAccessContextByOpenId`
  - `listAvailableFRsLark` -> `getUserIdByOpenId + getAllFigureAndRelations`
- `utils.py` 中 `frBelongsToUser` 改为 dispatch service 调用。
- `utils/index.py` 中归属校验拆分：
  - `checkFigureAndRelationOwnershipInDB(db, ...)`（保留 ORM 返回，服务内部用）
  - `checkFigureAndRelationOwnership(user_id, fr_id)`（dispatch + dict 返回，调用侧用）

### 原因

- 将 integration 层“业务判断 + DB 访问”下沉到 service，统一边界和返回结构。
- 保留 DB 内部方法以兼容事务/ORM 场景，避免一次性全局迁移引发回归。

### 注意

- `getAllFigureAndRelations` 的排序由 `updated_at.desc()` 调整为 `id.asc()`（这是显式行为变化）。
- `buildFigurePersonaMarkdown` 签名改为 `dict` 输入后，调用方应避免传 ORM 对象。

---

## 4.2 Graph 领域（ConversationGraph / FRBuildingGraph）

### 文件

- `src/agents/graphs/ConversationGraph/nodes.py`
- `src/agents/graphs/FRBuildingGraph/nodes.py`
- `src/services/figure_and_relation.py`（`buildFigurePersonaMarkdown`）

### 做了什么

- 大量 service 调用改为 `dispatchServiceCall(...)`。
- `nodeLoadFRAndPersona` / `nodeLoadFR` 修复 `figure_and_relation` 类型使用：
  - 从 ORM 属性访问改为 dict 访问；
  - 需要 `user_name` 时通过 `getUserById` 补全；
  - `figure_role` 做 `parseEnum` 校验。
- `buildFigurePersonaMarkdown` 改为接收 `dict[str, Any]`，内部使用 `fr.get(...)`。
- `getFRAllContext` 内调用 `buildFigurePersonaMarkdown(fr=fr.toJson())`。
- `FRBuildingGraph` 中以下调用显式改为 dispatch：
  - `getFROverallUpdateLogsThisRound`
  - `updateFigureAndRelation`
  - `addFineGrainedFeed`
  - `addFineGrainedFeedConflict`
  - `addOriginalSource`
  - `recallFineGrainedFeeds`
  - `updateFineGrainedFeed`

### 原因

- 共享数据库模式下，图节点不能绕过 dispatcher；否则本地/远程行为不一致。
- 统一 `figure_and_relation` 形态（dict）是避免 runtime 属性错误的关键。

### 注意

- `getFROverallUpdateLogsThisRound` 已做兼容解析（本地 list / 远端 dict.items）。

---

## 4.3 Lark integration 登录与分发

### 文件

- `src/channels/lark/integration/index.py`
- `src/services/user.py`
- `src/server/subrouters/user.py`
- `src/service_dispatcher.py`

### 做了什么

- 新增用户服务：
  - `getUserIdByOpenId(open_id)`
  - `userLoginByOpenId(open_id)`
- 新增用户路由：
  - `GET /user/getUserIdByOpenId`
- dispatcher 映射新增 `getUserIdByOpenId`（`auth_required=False`）。
- `index.py` 中引入 `loginIfNeeded(open_id)`：
  - token 有效则复用；
  - token 失效则 `userLoginByOpenId` 并写入本地 session；
  - 登录失败返回 `False`，上游 `messageHandler` 会提前 `return`。
- `_sendBatchMessages` 和 `messageHandler` 中 user 获取改为 dispatch `getUserIdByOpenId`。

### 原因

- 确保需要鉴权的 dispatch 在 token 失效时可自动续期。
- 去除 integration 层对 user 表的直接 DB 查询。

### 注意

- 当前设计假设“本地单用户会话文件”，不覆盖多用户并发隔离。

---

## 4.4 Router 层 `query_params.get` 修复

### 文件

- `src/server/subrouters/fr.py`
- `src/server/subrouters/feed.py`
- `src/server/subrouters/knowledge.py`
- `src/server/subrouters/user.py`（注释代码一并修正）

### 做了什么

- 全量补齐 `request.query_params.get("key", None)` 默认值。

### 原因

- 修复 Robyn `QueryParams.get` 调用签名要求，避免运行时报缺参错误。

---

## 4.5 CLI 领域（统一走 dispatcher + 共享模式适配）

### 文件

- `src/cli/utils.py`
- `src/cli/commands/auth.py`
- `src/cli/commands/fr.py`
- `src/cli/commands/index.py`
- `src/cli/commands/lark_service.py`

### 做了什么

- `getUserIdFromLocalSession()` 升级为 `getCurrentUserFromLocalSession()`，返回：
  - `{"user_id": ..., "access_token": ...}`
- auth/fr 命令中的 service 调用改为 `dispatchServiceCall(...)`。
- `doctor` / `setup` 引入共享数据库模式逻辑：
  - 新增必填环境变量 `USE_SHARED_DATABASE`
  - `USE_SHARED_DATABASE=True` 时跳过本地 DB 连通性检查
  - setup 新增 `easy` 模式（共享数据库），并在该模式下不初始化本地 DB

### 原因

- CLI 作为主要调用入口，也必须遵循统一 dispatch 策略。
- 共享数据库模式下不应强依赖本地 PostgreSQL 初始化和连接。

---

## 4.6 通用与配置项

### 文件

- `.env.example`
- `src/cli/assets/.env.example`
- `src/utils/request.py`
- `src/agents/prompt.py`
- `src/agents/llm.py`
- `README.md`
- `.gitignore`
- `pyproject.toml`
- `uv.lock`
- `src/agents/graphs/checkpointer.py`

### 做了什么

- `.env` 模板：
  - 新增 `USE_SHARED_DATABASE=False`
  - `BASE_URL` 更名为 `HTTP_BASE_URL`
- 请求工具：
  - `fetch` 重命名为 `afetch`（明确异步语义）
  - prompt 拉取改为 `afetch`
- LLM 参数处把 `base_url` 改为 `HTTP_BASE_URL`（需确认 SDK 参数名是否与库约定一致）
- README 微调 pip 安装文案。
- `.gitignore` 去掉 `.trae` 忽略规则（允许纳入仓库）。
- 版本号变更：
  - `pyproject.toml`：`1.5.3 -> 1.2.2`
  - `uv.lock` 同步为 `1.2.2`
- `checkpointer.py` 添加注释 `# todo：没法连接远程`。

### 原因

- 与共享数据库模式、统一 HTTP 分发配置保持一致。
- 明确异步请求接口命名，减少误用。

---

## 5. 逐文件清单（简版）

1. `.env.example`：新增共享模式开关，`BASE_URL` 改名 `HTTP_BASE_URL`  
2. `.gitignore`：移除 `.trae` 忽略  
3. `README.md`：安装文案微调  
4. `pyproject.toml`：版本回退到 `1.2.2`  
5. `src/agents/graphs/ConversationGraph/nodes.py`：dispatch 改造、`figure_and_relation` dict 化修复  
6. `src/agents/graphs/FRBuildingGraph/nodes.py`：dispatch 改造、`figure_and_relation` dict 化修复  
7. `src/agents/graphs/checkpointer.py`：注释补充  
8. `src/agents/llm.py`：LLM base URL 参数名调整  
9. `src/agents/prompt.py`：`fetch -> afetch`  
10. `src/channels/lark/integration/index.py`：登录续期 + dispatch 改造  
11. `src/channels/lark/integration/menu.py`：去 DB 直连，改 dispatch  
12. `src/channels/lark/integration/utils.py`：`frBelongsToUser` 改 dispatch  
13. `src/cli/assets/.env.example`：同根 `.env.example` 调整  
14. `src/cli/commands/auth.py`：统一 dispatch + session 接口升级  
15. `src/cli/commands/fr.py`：统一 dispatch + session 接口升级  
16. `src/cli/commands/index.py`：doctor/setup 适配共享数据库模式  
17. `src/cli/commands/lark_service.py`：session 校验接口升级  
18. `src/cli/utils.py`：`getCurrentUserFromLocalSession` 新接口  
19. `src/server/subrouters/feed.py`：query_params 全量补 default  
20. `src/server/subrouters/fr.py`：新增 FR 路由 + query_params default 修复  
21. `src/server/subrouters/knowledge.py`：query_params default 修复  
22. `src/server/subrouters/user.py`：新增 `getUserIdByOpenId` 路由  
23. `src/service_dispatcher.py`：新增统一分发层与映射表  
24. `src/services/figure_and_relation.py`：新增 FR service，persona 输入改 dict，归属校验接口重构  
25. `src/services/fine_grained_feed.py`：统一使用 `*InDB` 归属校验  
26. `src/services/user.py`：新增 open_id 相关 service  
27. `src/utils/index.py`：归属校验拆分为 DB 内部版 + dispatch 版  
28. `src/utils/request.py`：`afetch` 命名与注释  
29. `uv.lock`：版本同步到 `1.2.2`

---

## 6. 结果与当前状态

- 架构上已形成“**service -> dispatcher -> local/remote**”统一模型，核心链路可在共享数据库模式运行。
- FR 与 Lark integration 相关逻辑完成了主要下沉与路由/分发表联动。
- 已修复关键运行时问题（`query_params.get` 默认值、`figure_and_relation` 类型误用）。
- 当前分支包含较大范围结构性改造，建议合入前继续做以下回归：
  - Lark message 主链路（登录续期、切换 FR、发消息、批处理）
  - FRBuildingGraph / ConversationGraph 全流程
  - CLI `doctor/setup/auth/fr` 在两种模式下各跑一遍
  - 版本号变更（`1.5.3 -> 1.2.2`）是否符合发布预期

---

## 7. 补充说明

- 本文档记录的是“**当前工作区代码** 相对 `b0f1e27...` 的实际差异”，未包含未追踪文件（如 `.trae/`）内容本身。
- 若需要，我可以再出一份“仅本轮对话触达文件”的精简版 UPDATE（剔除历史累计改动）。
