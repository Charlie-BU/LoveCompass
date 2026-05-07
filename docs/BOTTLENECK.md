# 共享数据库问题

## 背景与目标

当前系统里，用户通过 `pip install`（或 `uv tool install`）安装 CLI 后，仍需要完成一系列前置配置（数据库创建、模型配置、飞书机器人配置等），最终才能通过 CLI 在本地/服务器启动飞书 WebSocket 服务，再通过飞书机器人与系统交互。

这个链路的心智成本非常高。  
我的目标是大量简化前期配置逻辑，让用户快速上手，从而提高整体投入意愿。

## 我尝试的切入点：共享数据库

我先从数据库入手：希望让用户的 CLI 直接连接我个人维护的 PostgreSQL 共享库，这样用户就不需要自己建库。

但一个核心安全前提是：我不能直接暴露数据库 `URI`（尤其是密码）。  
否则用户一旦拿到 URI，就可以在我的数据库上进行任意 CRUD 等高危操作。

## 已做的架构重构（当时方案）

我的思路是：`service` 层本身就是直接操作数据库的方法集合，可以再封装一层路由，通过 Web 框架暴露 HTTP 接口并上线，供用户调用。

基于这个方向，我做了如下重构：

1. 新增 `ServiceDispatcher` 模块。
    - 通过 `SERVICE_API_MAP` 将 `service` 方法与 HTTP 路由、请求方式、是否鉴权做映射。
    - 实现 `dispatchServiceCall`：根据是否启用共享数据库模式（环境变量 `USE_SHARED_DATABASE=True`），分发到本地 service（原逻辑）或远程 API。

2. 全面替换调用入口。
    - 把工程内所有消费 `service` 方法的地方，统一改为调用 `dispatchServiceCall`。
    - 覆盖范围包括 CLI、飞书服务集成、Graph。

3. 清理数据库耦合点。
    - 在改造过程中发现大量直接数据库耦合，例如 `with session() as db:`。
    - 对这些点统一处理为两类：
        - 若现有 service 可复用：直接改为 `dispatchServiceCall`。
        - 若现有 service 不可复用：下沉到新 service，同时补充路由并更新 `SERVICE_API_MAP`。
    - 最终目标是：**所有数据库操作必须在 service 层完成，其他位置不允许与数据库直接耦合。**

## 关键问题进展

在这轮重构里，我遇到过两个关键问题：其中第一个已通过补救方案解决，第二个仍然是最终 bottleneck。

### 1) 登录态有效期与 Graph 稳定性冲突（已解决）

用户在 CLI 登录后，本地会保存登录态 `token`。而在安全前提下，大部分 API（包括 Graph 工作流中涉及数据库操作的 service，在 `USE_SHARED_DATABASE` 场景下即 API 调用）都需要鉴权。

问题在于：调用 API 意味着必须持续保持有效登录态；而本地 token 有有效期，过期后要重新登录。Graph 运行在飞书机器人中，一旦登录态过期，就会导致 Graph 执行失败。

我最终采用了如下补救方案，并已解决这个问题：

- 在监听到用户消息后，先通过 user service 判断 token 是否过期。
- 若过期则自动触发重新登录，并把新 token 写回本地 session。
- 由于该场景不可能让用户手输账号密码，我在 user service 新增了一个“仅凭飞书 `open_id` 登录”的方法。

但需要注意的是，它绝不能作为通用 API 暴露给外部，只允许在飞书机器人自动续登这个特定场景内部触发。

### 2) `ConversationGraph` 的 checkpointer 无法通过 API 抽象（未解决）

`ConversationGraph` 的短期记忆 `checkpoint` 仍存储在 PostgreSQL。  
但这里不是我通过 service 主动建连数据库，而是借助 `langgraph` 的能力，通过数据库 `URI` 直接创建 `checkpointer` 实例。

这导致一个根本限制：

- 在 `USE_SHARED_DATABASE` 场景下，这部分无法通过 `dispatchServiceCall` 分流到远程 API。
- API 也不可能返回一个可用的 `checkpointer` 实例给本地进程。

换句话说：要正确创建 `checkpointer`，数据库 URI 必须在本地可得。  
这就是最后一个 bottleneck，也是当前方案最终被卡死的原因。

## 当前结论

我已经 `revert` 了上述全部改动。  
接下来准备采用其他路径，不再依赖“通过远程 API 调用数据库相关 service”的方案。

## 单一飞书 Bot 问题

### 问题背景

目前用户通过 `pip` 或 `uv` 安装 `immortality` 后，会在本地 HOME 目录创建 `.immortality`，其中包含 `.env` 等用户配置。  
现有实现基于单组环境变量（`LARK_APP_ID`、`LARK_APP_SECRET`、`LARK_CARD_TEMPLATE_ID`），因此 `immortality lark-service start` 每次只能启动一个 Bot 的 websocket 服务。  
当用户拥有多个飞书 Bot 且希望按需切换启动时，当前机制无法满足。

### 长期方案

将单 Bot 环境变量改为“列表化配置”，例如 `bots.yaml` / `bots.json` 或 `.immortality/bots/*.env`。  
CLI 明确支持按需选择：

- `immortality lark-service start --bot <name>`
- `immortality lark-service start --all`
