# 第一版 ConversationGraph 性能分析

- 这条 `ConversationGraph` 的功能链路很短，但当前这一轮对话下的性能表现我会评为 `中等偏慢，且会随对话轮数明显恶化`。
- 真正的瓶颈不在图结构本身，而在 `每轮重复注入的大体积上下文`、`无裁剪的短期记忆`、以及 `额外远程 I/O`。
- 以你贴出的这一轮为例，输入已经是明显的 `万级 token` 量级候选，延迟和成本都会偏高，后续多轮对话会继续线性甚至接近超线性变差。

**主要问题**

- `提示词重复严重`：`figure_persona` 已经包含 `core_personality/core_interaction_style/core_procedural_info/core_memory`，但在 `nodeCallLLM` 里又把四类 recalled feeds 再完整拼进去一次，见 [nodes.py:L289-L304](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L289-L304) 和 [figure_and_relation.py:L521-L566](file:///Users/bytedance/Desktop/work/Immortality/src/services/figure_and_relation.py#L521-L566)。你给的样例里，“黄色网站”“基金回本”“PPT 很 AI”“调侃风格”等内容明显重复出现，属于最伤性能的一类冗余。
- `每轮都可能拉太多 recall`：四个维度默认都是 `top_k=20`，合计最多 80 条，见 [nodes.py:L123-L151](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L123-L151)。而 `_recalledFeeds2Markdown()` 基本是原样展开文本，见 [nodes.py:L23-L42](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L23-L42)。这会直接把召回结果膨胀成大段 system message。
- `短期记忆不做 trim/summarize`：代码里已经有 `todo`，但当前没有真正裁剪，见 [nodes.py:L232-L237](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L232-L237)。同时 `nodeCallLLM` 会把新的 `ai_message` 继续写回 `messages`，见 [nodes.py:L378-L404](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L378-L404)。这意味着轮数越多，历史越长，LLM 输入持续变大。
- `每轮远程取 prompt`：`getPrompt()` 每次都 `fetch` 远程 HTML，再解析 prompt，见 [prompt.py:L73-L80](file:///Users/bytedance/Desktop/work/Immortality/src/agents/prompt.py#L73-L80)。这是额外的网络 I/O，而且在高 QPS 或网络抖动时会直接放大尾延迟。
- `关键路径完全串行`：图是 `Load FR -> Recall -> Build Message -> Call LLM`，见 [graph.py:L24-L41](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/graph.py#L24-L41)。其中 FR 查询、recall、prompt fetch、LLM 调用都堆在同一条关键路径上，没有做前置并发。
- `日志本身也很重`：`logger.info(f"\nmessages_to_send:\n{messages_to_send}\n\n")` 会把整包 prompt 和历史消息直接打日志，见 [nodes.py:L314-L314](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L314-L314)。在你这种长上下文场景里，这会增加 CPU、I/O 和日志存储成本。

**这轮样例的具体评价**

- 这轮输入最贵的不是最后那句 `垃圾`，而是模型在处理它之前被塞进去的那一大坨背景：
    - 基础系统 prompt
    - 整个人物画像
    - 四类召回结果
    - 累积的历史 Human/AI message
- 从你贴出的实际内容看，`人物画像` 和 `召回记忆` 存在高重叠，信息增益很低，但 token 成本很高。
- 对“闲聊回复”这个任务来说，模型真正需要的上下文其实很少：最近几轮语气、对方人设摘要、1 到 3 条相关记忆，通常就够了。现在是典型的 `为一个很短的输出，支付了过大的输入成本`。
- 这类任务的输出只有一个 JSON，且通常 1 到 3 句短消息；所以当前系统的 `input/output token 比` 很不经济。

**性能分解**

- `图调度成本`：低。图只有 4 个节点，本身不是问题，见 [graph.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/graph.py)。
- `数据库/召回成本`：中到高。尤其是 recall 的结果体积大时，后续拼 prompt 的成本更高。
- `网络成本`：中。每轮 `getPrompt()` 都是一次额外远程请求。
- `LLM 推理成本`：高，而且是主瓶颈。不是因为输出难，而是因为输入太长。
- `长期可扩展性`：偏差。对话越长、FR 越丰富、feed 越多，延迟和成本都会继续上升。

**我会优先做的优化**

- `先砍重复`：`figure_persona` 只保留稳定摘要；四类 recall 改成“仅注入和当前 query 最相关的少量增量信息”。这是收益最大的优化点。
- `降低 top_k`：对闲聊场景，`personality/interactions` 可以保留少量，`procedural/memory` 更应该压低，先从 `3/3/2/2` 这种量级试。
- `做短期记忆裁剪`：保留最近 `N` 轮显式消息，再附一个 conversation summary；不要无上限累积 `messages`。
- `缓存系统 prompt`：`getPrompt()` 结果至少做进程内缓存，按 prompt key + variables 模板控制。
- `删大日志`：不要打印整包 `messages_to_send`，改成只打 token 估算、条数、字符数。
- `并发非依赖项`：FR 加载完成后，prompt fetch 和 recall 理论上可以并行准备，减少关键路径时长。

**综合评分**

- `单轮性能`: 6/10
- `多轮稳定性`: 4/10
- `成本效率`: 3/10
- `可优化空间`: 很大

**一句话判断**

- 现在这条图 `能跑、也能产出像样结果`，但对这种短回复闲聊任务来说，`上下文注入明显过重`，已经属于“效果可能不错，但性能和成本都不划算”的实现。

如果你愿意，我下一步可以直接基于这三个文件给你做一版 `性能优化方案 + diff 预览`，优先只动最值钱的两处：`recall 压缩` 和 `short-term memory trim`。

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
    - 若超阈值，则从最早的消息开始裁掉。
    - 被裁掉的消息与旧摘要一起交给 `DOUBAO_2_0_MINI` 做滚动总结。
    - 生成新的 `conversation_summary`。
    - 通过 `RemoveMessage` 把旧消息从 `MessagesState` 中真正删除。
- `nodeCallLLM()` 会在主模型调用前，把 `conversation_summary` 作为一条额外的 `SystemMessage` 注入，见 [nodes.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L475-L481)。

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
    - `SHORT_TERM_MEMORY_MAX_CHARS=4000`
    - `SHORT_TERM_MEMORY_MAX_MESSAGES=12`
    - `SHORT_TERM_MEMORY_TARGET_CHARS=2800`
      见 [.env](file:///Users/bytedance/Desktop/work/Immortality/.env#L96-L98)。
- 这组参数的含义是：
    - 超过 `MAX_CHARS` 或 `MAX_MESSAGES` 时才触发滚动摘要。
    - 一旦触发，尽量把剩余原始消息压回到 `TARGET_CHARS` 附近。
    - `MAX -> TARGET` 的回落区间用于避免在阈值边缘频繁反复 summarize。

### 当前收益

- 多轮对话不会再无上限积累原始消息。
- 更早历史被压缩为结构化摘要，保留连续性但显著降低体积。
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

- 当前写回短期记忆的 AI 消息，不再保留主模型的原始 JSON 输出，而是只保存角色本轮实际要发送的文本内容，见 [nodes.py](file:///Users/bytedance/Desktop/work/Immortality/src/agents/graphs/ConversationGraph/nodes.py#L551-L570)。
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
- `优先级中`：继续观察 `SHORT_TERM_MEMORY_MAX_CHARS / TARGET_CHARS` 是否偏宽松，必要时收紧到更偏性能优先的区间。
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
