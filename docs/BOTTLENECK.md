现在遇到了一个比较棘手的情况：

这个系统设计中，用户通过 pip install (或 uv tool install) 安装 CLI 后，需要通过一系列配置，包括数据库创建、模型配置、飞书机器人配置等，最终才能通过 CLI 在本地/服务器启动飞书 WebSocket 服务，进而通过飞书机器人与系统交互。

但很显然这个心智成本非常高，我需要大量简化前期配置逻辑，才能让用户快速上手，从而让更多用户投入。

我先从数据库入手：我准备用我个人的 PostgreSQL 数据库作为共享数据库让用户的 CLI 连接，从而无需用户自己创建数据库。但我不可能直接把我数据库的 URI，特别是密码直接暴露给用户。否则用户拿到 URI 后可以随意在我的数据库进行 CRUD 等高危操作。

于是我的一个思路是，service 层的 service 是直接操作数据库的方法，我将这些方法封装一层路由，通过 Web 框架暴露 HTTP 接口，部署上线给用户调用。于是在封装及部署完成后，我基于原有架构进行了如下重构：

- 完成了一个 ServiceDispatcher 模块，在里面通过一个 SERVICE_API_MAP 将 service 方法和 HTTP 路由、请求方式及是否鉴权关联；完成了一个 dispatchServiceCall 方法，根据用户当前是否是共享数据库模式（环境变量中 USE_SHARED_DATABASE 是否为 True），分发请求到本地服务（原先逻辑）或调用远程 API。
- 将全工程中消费 service 方法的地方，都替换为调用 dispatchServiceCall 方法。包括 CLI、飞书服务集成以及 Graph。
- 另外，在这些地方我发现很多原先直接耦合数据库操作的情况，即直接通过 `with session() as db:` 进行数据库操作。我将这些操作进行两种可能的处理：如果现有 service 可以复用，直接通过 dispatchServiceCall 调用；否则直接下沉到新 service 中，同步封装新的路由，同步在 SERVICE_API_MAP 更新。做到：全部的数据库操作必须在 service 层完成，其他位置不允许与数据库有任何耦合。

但即便如此，仍然遇到了一些难以 / 无法解决的问题：

1. 用户在 CLI 的登录态 token 是经用户在 CLI 登录后保存在本地，为安全起见大部分的 API 都需要鉴权，包括 Graph 工作流过程中涉及的数据库操作的 service（USE_SHARED_DATABASE 场景下即调用 API）。但调用 API 就意味这要始终维持登录态，而本地保存的 token 具有有效期，过期后需要重新登录。而 Graph 运行是在飞书机器人中，登录态过期就会导致 Graph 运行失败。我使用了如下解决方案：
在监听到用户发出消息后，首先利用 user service 中的方法判定 token 是否过期，若过期直接触发重新登录，将新的 token 保存到本地 session 中。但显然这个流程不可能让用户输入用户名和密码，所以在 user service 层添加了一个新方法，仅通过飞书 open_id 即可进行登录。但这个方法绝不可通过 API 直接暴露到外部，只允许在这种场景下飞书机器人自动触发登录。

2. ConversationGraph 中的短期记忆 checkpoint 依然存储在 PostgreSQL 数据库中，而这里的连接方式并不是通过 service 在我这边主动进行数据库连接，而是直接借助 langgraph 的能力通过 URI 直接得到 checkpointer 实例。这就意味着，不可能通过 dispatchServiceCall 将 USE_SHARED_DATABASE 的情况下分流到 call API 完成。API 也不可能给我返回一个 checkpointer 实例。换句话说，数据库 URI 必须在本地拿到才能正确创建 checkpointer。这是最后一个 bottleneck，却把我紧紧卡住。

现在我 revert 了全部的改动，准备采取其他方式，不依赖请求远程 API 调用数据库相关操作的服务了。
你是否有其他方案可以解决这个问题？请先理解上下文，阅读这个 issue 涉及到的全部代码后再回答。