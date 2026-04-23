# ConversationGraph 性能与短期记忆设计

- 本文档记录 `ConversationGraph` 当前版本的性能特征、已落地优化、短期记忆 trim 设计，以及后续建议。
- 当前版本已经不再是“短期记忆无上限增长”的第一版实现，而是包含：
    - `去重后的上下文注入`
    - `带 conversation_summary 的短期记忆 trim`
    - `按 round_uuid 整轮裁剪`
    - `nodeRecallFeedsFromDB` 与 `nodeBuildAndTrimMessage` 的并行执行
- 从真实样本看，当前系统的主瓶颈仍然是 `输入上下文过重`，尤其是较长的 system prompt、人物画像和 recall 补充；短期记忆 trim 的作用是把“最近对话”的成本控制在一个稳定区间，而不是单独解决全部性能问题。

## 历史问题

- 第一版最突出的问题是：
    - `提示词重复严重`
    - `短期记忆无上限增长`
    - `关键路径偏长`
    - `日志和远程 prompt 获取带来额外开销`
- 这些问题中，最伤长期稳定性的部分是 `messages` 会随着轮数持续增长，直接进入下一轮主模型上下文。
- 当前版本已经对其中最重要的两项做了修复：
    - `去除重复注入`
    - `短期记忆 trim + 滚动摘要`

## 这轮样例的判断

- 这轮输入最贵的不是最后那句 `垃圾`，而是模型在处理它之前被塞进去的那一大坨背景：
    - 基础系统 prompt
    - 人物画像
    - recall 补充信息
    - conversation summary
    - 最近几轮短期记忆
- 对“拟人闲聊”任务来说，模型真正高价值的上下文通常只有三类：
    - 稳定 persona
    - 与当前输入最相关的少量记忆
    - 最近几轮对话语气与节奏
- 因此短期记忆 trim 的目标不是“尽可能多保留历史”，而是把最近几轮对话压在一个足够用、但不过载的预算内。

## 性能分解

- `图调度成本`：低。图只有 4 个节点，本身不是问题，见 [graph.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/graph.py)。
- `数据库/召回成本`：中到高。尤其是 recall 的结果体积大时，后续拼 prompt 的成本更高。
- `网络成本`：中。每轮 `getPrompt()` 都是一次额外远程请求。
- `LLM 推理成本`：高，而且是主瓶颈。不是因为输出难，而是因为输入太长。
- `长期可扩展性`：相比第一版已明显改善，但在 recall 体积、prompt 拉取和日志方面仍有优化空间。

## 已落地优化

- `去除重复注入`：`figure_persona` 不再和 recall 的职责重叠过多，见 [nodes.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py) 与 [figure_and_relation.py](file:///Users/bytedance/Desktop/work/Immortality/src/services/figure_and_relation.py)。
- `短期记忆 trim`：更早消息会被总结到 `conversation_summary`，最近原始消息受字符预算和消息数兜底共同控制，见 [nodes.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py)。
- `并行化非依赖节点`：`nodeRecallFeedsFromDB` 与 `nodeBuildAndTrimMessage` 并行执行，见 [graph.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/graph.py)。
- `按轮次写入短期记忆`：`HumanMessage` 和 `AIMessage` 都带上 `additional_kwargs.round_uuid`，为整轮 trim 提供分组依据，见 [nodes.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py)。

## 综合评分

- `单轮性能`: 7/10
- `多轮稳定性`: 7/10
- `成本效率`: 5/10
- `可优化空间`: 仍然较大

## 一句话判断

- 当前版本已经从“多轮必然膨胀”的实现，演进成“短期记忆受控、效果和成本更均衡”的实现；但对短回复闲聊任务来说，`system prompt / persona / recall` 仍然偏重，后续优化重点仍然是压缩固定注入成本。

# 性能优化

本节记录当前版本已经落地的优化项、设计取舍、剩余问题与下一步建议。以下描述以当前代码为准，而不是最初的方案草稿。

## 当前结果

- 当前 `ConversationGraph` 已从“串行、重复注入、短期记忆无上限增长”的版本，演进为“部分并行、去重注入、带滚动摘要的短期记忆”版本。
- 已落地的核心优化有 3 类：
    - `去除重复注入`
    - `短期记忆裁剪`
    - `并行化非依赖节点`
- 这三类优化都遵循了 `最小改动原则`：不重构整体图，不改 LLM 输出协议，只在 `state.py`、`nodes.py`、`graph.py` 附近做局部调整。

## 1. 去除重复注入

### 问题

- 原实现中，`figure_persona` 已经包含 `core_personality`、`core_interaction_style`、`core_procedural_info`、`core_memory` 等摘要。
- 同时 `nodeCallLLM()` 又会把 DB 召回的 personality / interaction / procedural / memory 四类信息再次完整拼进 system messages。
- 这会导致同一类信息在 `人物画像` 和 `召回上下文` 中重复出现，增加 token、拉长推理时延，也会稀释真正重要的本轮信号。

### 当前实现

- 人物画像构建阶段会显式排除掉以下字段，见 [nodeLoadFRAndPersona](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L177-L222)：
    - `words_figure2user`
    - `words_user2figure`
    - `core_procedural_info`
    - `core_memory`
- 对应的画像构造函数已支持 `exclude_fields`，见 [buildFigurePersonaMarkdown](file:///Users/bytedance/Desktop/work/Immortality/src/services/figure_and_relation.py#L521-L571)。
- DB 召回阶段已经停掉 `PERSONALITY` 和 `INTERACTION_STYLE` 两类召回，只保留：
    - `PROCEDURAL_INFO`
    - `MEMORY`
      见 [nodeRecallFeedsFromDB](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L225-L357)。
- `nodeCallLLM()` 当前仅注入：
    - 基础 system prompt
    - 精简后的 `figure_persona`
    - `memory + procedural` 的 recall 补充
    - 可选的 `conversation_summary`
    - 最近的短期记忆消息
      见 [nodeCallLLM](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L412-L596)。

### 设计取舍

- 这里采用的是“`persona` 负责稳定画像，`recall` 负责本轮补充”的职责切分，而不是做复杂的语义去重。
- 这是一个偏保守但工程上更稳的方案：
    - 优点是实现简单、风险低、容易回滚。
    - 代价是 recall 仍然可能存在少量内部冗余，但相比原始版本，重复注入已经显著下降。

### 当前收益

- system prompt 区域的冗余明显减少。
- 人物画像和 recall 的职责边界更清晰。
- 生成模型在处理短闲聊时，不再需要每轮都消费同一批“画像摘要 + 原始例子”的双份上下文。

## 2. 短期记忆裁剪

### 问题

- 原实现会把历史 `HumanMessage` / `AIMessage` 持续累积在 `messages` 中。
- 多轮对话后，短期记忆会线性增长，并直接进入下一轮主模型上下文，成为最主要的长期退化来源之一。

### 当前实现

- `ConversationGraphState` 新增了 `conversation_summary`，用于承载“更早对话的滚动摘要”，见 [state.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/state.py#L35-L56)。
- `nodeBuildAndTrimMessage()` 会在把本轮 `HumanMessage` 加入 `messages` 后执行 trim，见 [nodeBuildAndTrimMessage](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L367-L409)。
- trim 逻辑在 `_buildTrimmedShortTermMemory()` 中，见 [nodes.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L82-L152)：
    - 若总字符数和消息条数都未超阈值，则不裁剪。
    - 若超阈值，则从最早的轮次开始裁掉。
    - 被裁掉的消息与旧摘要一起交给 `DOUBAO_2_0_MINI` 做滚动总结。
    - 生成新的 `conversation_summary`。
    - 通过 `RemoveMessage` 把旧消息从 `MessagesState` 中真正删除。
- `nodeCallLLM()` 会在主模型调用前，把 `conversation_summary` 作为一条额外的 `SystemMessage` 注入，见 [nodes.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L475-L481)。

### 为什么按 `round_uuid` 整轮裁剪

- 当前实现给每轮的 `HumanMessage` 和 `AIMessage` 都写入相同的 `additional_kwargs.round_uuid`。
- trim 时会读取最早消息的 `round_uuid`，并一次性删除同一轮次的全部消息，避免把同一轮的 `HumanMessage` 和 `AIMessage` 分开摘要。
- 如果遇到历史消息没有 `round_uuid`，会退化为单条 trim，避免把多个旧轮次错误合并。
- 如果发现最早轮次和最新轮次是同一个 `round_uuid`，则停止 trim，避免把当前轮输入一并删掉。

### 为什么不用“把 summary 伪装成一条普通聊天消息”

- 当前实现没有把 summary 塞回 `messages` 列表头部，而是单独放到 `conversation_summary` 字段。
- 这样做的原因是：
    - 摘要是元信息，不是用户或角色真实说过的一句话。
    - 单独存储可以避免“summary of summary” 和“把摘要误当历史原话”的语义污染。
    - 调试和日志分析时，也更容易区分“原始短期记忆”和“滚动摘要”。

### 为什么 `messages` 返回的是 patch 而不是整表

- `ConversationGraphState` 继承的是 `MessagesState`，其 `messages` 更新语义是“增量合并”，不是“整表覆盖”，见 [state.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/state.py#L35-L37)。
- 所以 `nodeBuildAndTrimMessage()` 返回的是：
    - 一组 `RemoveMessage`
    - 本轮新加入的 `HumanMessage`
- 未被删除、且本来就存在于 state 中的旧消息，不需要重复返回，见 [nodes.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L399-L407)。

### 当前参数

- 短期记忆 trim 当前使用以下阈值：
    - `SHORT_TERM_MEMORY_MAX_CHARS=1600`
    - `SHORT_TERM_MEMORY_TARGET_CHARS=1000`
    - `SHORT_TERM_MEMORY_MAX_MESSAGES=30`
      见 [.env](file:///Users/bytedance/Desktop/work/Immortality/.env#L96-L98)。
- 这组参数的含义是：
    - `MAX_CHARS` 是主触发条件，绝大多数场景下由消息字符数决定是否 trim。
    - `TARGET_CHARS` 是 trim 完成后的目标预算，用于提供 `MAX -> TARGET` 的回落区间，避免在阈值边缘频繁 summarize。
    - `MAX_MESSAGES` 只做兜底硬上限，用于拦截“消息很多但每条都很短”的异常碎片化对话。

### 为什么消息数只做兜底

- 真实对话里，当前系统最容易连续触发 trim 的原因，通常不是上下文真的过长，而是旧版本 `MAX_MESSAGES` 阈值过低。
- 如果消息数和字符数同权触发，而消息数阈值又贴得很近，就会出现：
    - 这一轮 trim 到阈值边缘
    - 下一轮一追加新消息又立刻越界
    - 连续多轮 summarize
- 因此当前策略改为：
    - `字符数主导 trim`
    - `消息数只做兜底`
- 这更符合闲聊场景的真实负载，也能显著减少无意义的频繁摘要。

### 这组参数为什么是 `1600 / 1000 / 30`

- 基于真实样本观察，一次传给 LLM 的上下文里，最大的 token 消耗来自：
    - system prompt
    - 人物画像
    - recall 补充
    - conversation summary
- 相比之下，最近几轮短期记忆真正需要保留的，通常只是一小段“当前语气、话题与互动节奏”。
- 因此短期记忆不宜继续占用过多预算，否则会和固定注入内容争抢上下文注意力。
- `1600 / 1000` 这一组值的目标是：
    - 保留足够多的最近轮次，保证语气连续性
    - 避免让短期记忆重新膨胀成主要上下文成本
    - 通过约 `62.5%` 的回落比例减少连续触发 trim 的概率
- `30` 作为消息数硬上限，则主要用来处理极端短句、高频往返但字符数不高的场景。

### 当前收益

- 多轮对话不会再无上限积累原始消息。
- 更早历史被压缩为结构化摘要，保留连续性但显著降低体积。
- trim 单位从“单条消息”提升为“同一轮次”，摘要语义更完整。
- 当前轮输入始终保留，避免由于裁剪丢失用户最新消息。

### 当前代价

- 一旦触发 trim，本轮会额外产生一次 `mini` 模型调用。
- 因此这项优化是“用偶发的 summary 成本，换取长期上下文体积受控”。
- 对长会话来说，这笔交易通常是值得的；对极短会话，trim 通常不会触发。

## 3. 图执行并行化

### 原问题

- 原图执行顺序是：
    - `Load FR -> Recall -> Build Message -> Call LLM`
- 其中 `Recall` 和“构建本轮消息”之间并没有真实依赖，但之前被串行放在主链路上。

### 当前实现

- 当前图结构改为：
    - `nodeLoadFRAndPersona`
    - 并行执行 `nodeRecallFeedsFromDB` 和 `nodeBuildAndTrimMessage`
    - 最后汇合到 `nodeCallLLM`
- 见 [graph.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/graph.py#L24-L45)。

### 收益

- “本轮消息构建 / trim”和“DB recall” 可以并行准备，缩短关键路径。
- 虽然这不是最大的性能收益来源，但实现简单，且没有明显副作用。

## 4. 其他顺手优化

- 当前写回短期记忆的 AI 消息，不再保留主模型的原始 JSON 输出，而是只保存角色本轮实际要发送的文本内容，见 [nodes.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py)。
- 这会减少：
    - 短期记忆中的无用格式噪声
    - checkpoint 持久化体积
    - 下一轮再次送入主模型时的字符数

## 5. 当前版本的整体评价

- 相比第一版，当前版本已经解决了两个最值钱的问题：
    - `重复注入`
    - `短期记忆无上限增长`
- 当前版本更接近适合上线试跑的工程形态：
    - 结构仍然简单
    - 风险可控
    - 性能随轮次恶化的问题已被显著缓解
- 但它仍不是最终最优版本，主要原因是：
    - `getPrompt()` 仍然每轮远程拉取 prompt
    - `messages_to_send` 仍然整包打印日志
    - `memory/procedural` recall 默认 `top_k=10/10`，对闲聊场景仍然偏保守
    - 触发 trim 时需要额外一次 mini 模型调用

## 6. 后续建议

- `优先级高`：给 `getPrompt()` 做进程内缓存，降低每轮远程 I/O。
- `优先级高`：删除或缩减整包 `messages_to_send` 日志，只保留条数、字符数、是否触发 trim 等统计信息。
- `优先级中`：继续观察 `SHORT_TERM_MEMORY_MAX_CHARS / TARGET_CHARS=1600/1000` 是否适合真实线上分布，必要时再根据平均轮次长度微调。
- `优先级中`：视线上效果继续下调 `TOP_K_MEMORY_FEEDS_FOR_CONVERSATION` 和 `TOP_K_PROCEDURAL_FEEDS_FOR_CONVERSATION`。
- `优先级低`：如果后续需要更强的连续性，再考虑把 `conversation_summary` 的生成 prompt 做成更细化的模板，或者区分“关系事实摘要”和“短期话题摘要”两层结构。

# FAQs

1. 每轮 message 中（指HumanMessage 和 AIMessage）除了 content 外，还有如下内容：
   additional_kwargs={}, response_metadata={}, id='ff407a75-7706-4b29-920b-fce587dc50da'
   这些内容的存在会占用token吗？会影响模型输入体积吗？

**结论**

- 在你这个项目当前的实现里，`additional_kwargs`、`response_metadata`、`id` **不会进入模型输入 token**。
- 真正发给 Ark/模型的，只有 `role` 和 `content`，见 [adapter.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/adapter.py#L233-L240)。
- 所以从“模型看到的上下文体积”角度，这些字段 **不计入 token**。

**依据**

- `nodeCallLLM()` 调用的是 `arkAinvoke(messages=messages_to_send)`，见 [nodes.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L326-L333)。
- `arkAinvoke()` 在真正请求前，会把 LangChain message 转成 Ark/OpenAI chat message，见 [llm.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/llm.py#L92-L97)。
- 转换函数 `langchain2OpenAIChatMessages()` 明确只取：
    - `role`
    - `content`
      见 [adapter.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/adapter.py#L233-L240)

也就是说，像下面这些：

```python
additional_kwargs={}
response_metadata={}
id="xxx"
```

是 `LangChain/BaseMessage` 对象在 Python 侧的元数据，不是最终发给模型的 prompt 内容。

**但有两个“会影响体积”的例外**

- `日志体积`：你现在有一行
  [nodes.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L324-L324)
  会直接打印 `messages_to_send`。这里打印出来的对象字符串里，通常会带上 `additional_kwargs`、`response_metadata`、`id`。这 **不影响模型 token**，但会增加日志 I/O 和日志存储。
- `checkpoint / 内存存储体积`：你把 `AIMessage` 原对象放回了 `messages`，见 [nodes.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L388-L414)。这些元数据会跟着消息对象一起被短期记忆/checkpointer 保存，所以会影响：
    - Python 内存占用
    - checkpoint 持久化体积
    - 序列化/反序列化成本
      但仍然 **不直接增加模型输入 token**。

**对你当前优化的实际含义**

- 你做短期记忆 trim 时，最该关注的还是 `message.content` 的长度。
- `id`、`response_metadata` 不是 token 问题，但如果你追求极致性能，也可以考虑在写回短期记忆前，把 AIMessage 压成更轻的形式，只保留必要字段。
- 不过这一步不属于第一阶段必须做的事，优先级低于：
    - 裁剪 `messages` 数量
    - 控制 `content` 总长度
    - 删除大段重复 system context

**一句话**

- 对模型 token：`不会占`
- 对程序内存/日志/checkpoint：`会有一点影响`
