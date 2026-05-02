# ConversationGraph

这个 graph 用于在单轮对话中，基于当前 `FigureAndRelation`、细粒度召回信息与短期记忆，生成角色本轮回复；并通过滚动摘要与消息裁剪，控制多轮会话的上下文体积与稳定性。

## 工作流设计

1. 首节点输入 `request` 作为初始 invoke，其中包含：
    - `user_id`
    - `fr_id`
    - `messages_received`（本轮收到的消息数组）
2. `nodeLoadFRAndPersona` 首先执行，完成以下动作：
    - 生成本轮 `round_uuid`（`uuid4`）
    - 调用 `checkFigureAndRelationOwnership` 校验并加载当前 `figure_and_relation`
    - 调用 `buildFigurePersonaMarkdown` 构建人物画像 `figure_persona`
    - `exclude_fields` 显式排除：
        - `words_figure2user`
        - `words_user2figure`
        - `core_procedural_info`
        - `core_memory`
    - 从 `figure_and_relation.words_figure2user` 生成 `words_to_user`
    - 记录节点日志（`logs`）
3. 图在这一层进入并行分支（两条分支无直接依赖）：
    - `nodeRecallFeedsFromDB`
    - `nodeBuildAndTrimMessage`
4. `nodeRecallFeedsFromDB` 处理召回：
    - 将 `messages_received` 拼接为 `query`
    - 若 `query` 为空：跳过召回，写入 warning 和 skip 日志
    - 若 `query` 非空：调用 `recallFineGrainedFeeds`
    - 当前 scope 只保留两类高语境依赖信息：
        - `PROCEDURAL_INFO`（`TOP_K_PROCEDURAL_FEEDS_FOR_CONVERSATION`，默认 `10`）
        - `MEMORY`（`TOP_K_MEMORY_FEEDS_FOR_CONVERSATION`，默认 `10`）
    - `PERSONALITY` 与 `INTERACTION_STYLE` 召回已停用（避免与 persona 重复注入）
    - 将召回结果格式化为 markdown 写回：
        - `recalled_procedural_infos_from_db`
        - `recalled_memories_from_db`
    - 记录节点日志（成功 / 失败）
5. `nodeBuildAndTrimMessage` 处理本轮消息与短期记忆裁剪：
    - 读取当前 `messages` 与 `conversation_summary`
    - 将本轮 `messages_received` 合并为一个 `HumanMessage`，并写入 `additional_kwargs.round_uuid`
    - 调用 `_buildTrimmedShortTermMemory()` 执行裁剪与滚动摘要
    - 返回 `messages` patch（不是整表覆盖）：
        - 一组 `RemoveMessage`（删除被 trim 的历史消息）
        - 本轮新增 `HumanMessage`
    - 记录 trim 统计日志
6. 两条并行分支汇合到 `nodeCallLLM`，构建最终模型输入 `messages_to_send`：
    - 系统提示词 `CONVERSATION_SYSTEM_PROMPT`（动态注入 `words_to_user`、`current_timestamp`、`user_name`）
    - `figure_persona`
    - 高语境召回补充（`memory + procedural`）
    - 若存在，附加 `conversation_summary`（更早对话摘要）
    - 追加当前 `messages`（短期记忆 + 本轮输入）
7. `nodeCallLLM` 调用 `arkAinvoke(model="LITE_MODEL")` 生成回复：
    - 参数：`temperature=0.3`、`reasoning_effort="low"`
    - `reasoning_content_in_ai_message=False`（不把 reasoning 写入 AIMessage，减小消息体积）
    - 通过 `ainvokeJsonWithRetry(max_retries=2)` 解析 JSON 输出
    - 兼容 `messages_to_send` 返回类型（`None / str / list`）
8. 写回输出与短期记忆：
    - `llm_output.messages_to_send` 写回角色本轮回复数组
    - `llm_output.reasoning_content` 写回推理内容
    - 若本轮有回复，追加 `AIMessage(content="\n".join(messages_to_send))` 到 `messages`，并写入同一 `round_uuid`
    - 记录节点日志并返回结果
9. 图结构与编译方式：
    - 基础结构：`START -> nodeLoadFRAndPersona -> (nodeRecallFeedsFromDB || nodeBuildAndTrimMessage) -> nodeCallLLM -> END`
    - 运行时默认使用 `buildConversationGraphWithMemory()`，通过异步 checkpointer 编译
    - `getConversationGraph()` 使用单例 + `asyncio.Lock`，避免重复构建

【过程中实时记录日志】

## 短期记忆与 Trim 策略实现

### 核心目标

- 短期记忆不再无上限增长。
- 更早历史转为滚动摘要 `conversation_summary`，最近轮次保留原始消息。
- 裁剪单位优先按 `round_uuid` 整轮删除，避免拆开同一轮的人类输入与角色回复。

### 状态字段与更新语义

- `ConversationGraphState` 继承 `MessagesState`，`messages` 是增量合并语义。
- 新增字段 `conversation_summary` 承载更早历史摘要。
- 由于是增量更新语义，trim 节点返回的是 patch：
    - `RemoveMessage(id=...)` 删除旧消息
    - 本轮新 `HumanMessage`
- 未被删除且已存在于 state 的消息无需重复返回。

### 触发条件与参数

trim 使用三个环境变量参数：

- `SHORT_TERM_MEMORY_MAX_CHARS`（默认 `1600`）
- `SHORT_TERM_MEMORY_TARGET_CHARS`（默认 `1000`）
- `SHORT_TERM_MEMORY_MAX_MESSAGES`（默认 `30`）

触发逻辑：

- 当 `总字符数 <= MAX_CHARS` 且 `消息条数 <= MAX_MESSAGES` 时，不触发 trim。
- 否则进入裁剪循环，从最早消息开始删除，直到：
    - `kept_chars <= TARGET_CHARS`
    - 且消息条数不超过 `MAX_MESSAGES`（条数作为兜底约束）
- 无论如何，至少保留 1 条最新消息，避免丢失当前轮输入。

### 整轮裁剪逻辑（按 round_uuid）

在 `_buildTrimmedShortTermMemory()` 中，裁剪细节如下：

1. 读取最早消息与最新消息的 `additional_kwargs.round_uuid`。
2. 若二者相同，说明只剩当前轮，停止 trim，避免误删本轮。
3. 若最早消息无 `round_uuid`，退化为单条删除（兼容历史消息）。
4. 若最早消息有 `round_uuid`，连续删除该轮次的整批消息（Human/AI 一起删）。
5. 将被删消息累计到 `messages_to_summarize`，并实时扣减 `kept_chars`。

### 滚动摘要生成

被删除消息不会直接丢弃，而是与旧摘要一起进入 `_summarizeTrimmedMessages()`：

- 使用 `prepareLLM("MINI_MODEL")`，参数：
    - `temperature=0`
    - `reasoning_effort="minimal"`
- system prompt 来源：`SUMMARY_MESSAGES_FOR_TRIM`
- user prompt 包含两块：
    - 旧摘要（`old_summary`，为空时写“无”）
    - 本次新纳入摘要的历史消息（文本化后按 `[MessageType] + content` 拼接）
- 返回新摘要 `new_summary`，写回 `conversation_summary`

### 主模型消费 summary 的方式

- `conversation_summary` 不会伪装成普通聊天消息塞回 `messages`。
- 其在 `nodeCallLLM` 中以单独 `SystemMessage` 注入：
    - `"以下是更早对话的摘要：\n{conversation_summary}"`
- 这保证了“摘要是元信息”的边界，避免把摘要混同为真实原话。

### 写回链路与体积控制

- 本轮 `HumanMessage` 与 `AIMessage` 都带 `round_uuid`，为后续整轮 trim 提供分组基础。
- AI 回写时仅保留最终对外发送文本，不把 `reasoning_content` 写入 `AIMessage`。
- 该策略可减少 `messages` 持久化体积与下轮上下文噪声。

### 当前策略的工程取舍

- 优点：
    - 多轮会话体积可控，避免线性膨胀
    - 裁剪按轮次进行，摘要语义更完整
    - 与现有图结构兼容，改动集中在 `state.py` / `nodes.py` / `graph.py`
- 成本：
    - 触发 trim 时增加一次 `MINI_MODEL` 调用
    - `nodeCallLLM` 仍每轮调用 `getPrompt` 拉取系统 prompt
    - `messages_to_send` 当前仍有整包日志输出，存在额外 I/O 开销

## FAQs

1. 每轮 message 中（指HumanMessage 和 AIMessage）除了 content 外，还有如下内容：
   additional_kwargs={}, response_metadata={}, id='ff407a75-7706-4b29-920b-fce587dc50da'
   这些内容的存在会占用token吗？会影响模型输入体积吗？

**结论**

在当前的实现里，`additional_kwargs`、`response_metadata`、`id` **不会进入模型输入 token**。真正发给 Ark/模型的，只有 `role` 和 `content`。
