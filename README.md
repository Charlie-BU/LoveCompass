# HeartCompass 研发之路

### FIRST ENTRY - 2026.02.07

::: danger
**以下内容补充于 2026.03.20**
2 月 7 日的日记内容是本产品的最初定位，到研发后期已经大程度偏离最初定位。请移步以下红色高亮块 3 月 14 日补充内容进一步了解。
:::

Why I wanna build an app like this:
**写在前面**：我最近在观察研究 MBTI 是否真的能够准确地刻画一个人。首先拿我自己来说，几乎 ENTJ 的每个特征基本都能与我符合，而我观察的其他人也不约而同的符合着他们的 MBTI 类型所描述的特征。因此，通过 MBTI 进行人物分析可以算是一个 trigger。
【2 月 7 日的日记部分内容暂不可见】
::: danger
**以下内容补充于 2026.03.14**
一个多月过去了，MVP 主链路已经跑通。一个月来随着开发工作持续进行，我越来越觉得这个产品如果仅仅定位于上面所述的范围，实在太过大材小用。

- 一方面构建丰富的人物画像可以服务于和用户产生关系的全部群体 —— 家人、朋友，甚至是自己
- 一方面人际关系的分析并不是一个很突破性的，或者说 ROI 很高的事情；收集大量的人物画像仅仅用于此目的过于大材小用。因此决定本产品主要定位在**虚拟人**—— 通过大量关系及画像上下文构建虚拟形象和用户对话
  :::

```python
class RelationStage(enum.Enum):
    SELF = "self"
    FAMILY = "family"
    STRANGER = "stranger"
    FRIEND = "friend"
    AMBIGUOUS = "ambiguous"
    DATING = "dating"
    TENSION = "tension"
    BROKEN_UP = "broken_up"
    FAILED = "failed"

```

一些 ideas 如下：

- 收集用户 User 的个人信息，包括**MBTI**（非常重要）、性别、性格（option 选择）、过往经历，以及任何所需要的个人 features 字段，用以分析人物以及后续关系分析等所需要的个人信息。（尽可能全面）
- Modeling：以每个用户 User 为单位，对于一个用户 User，与一个关系构成一条主链路。主链路以不同阶段做区分，不同阶段尽可能共用数据结构，但在大模型侧需把不同阶段提升至顶层上下文进行辅助
- 收集对方的尽可能全面的个人信息作为 context，如**MBTI**（非常重要），性别、性格（option 选择）、过往经历，以及任何所需要的个人 features 字段，AI 需要针对这些信息进行研判，基于这些信息和分析研判后得到的信息得到初步的人物画像
- 在同一链路辅助过程中用户需持续提供新的 context，进行人物画像丰富
- Context 是最重要的 Model，需要非常谨慎设计建模
    - context 在一段主链路中属于一级概念，i.e 每个 context 直接与当前主链路产生外键关联
    - ai 侧需要把不同类型的 context 进行区分，如人物相关信息、聊天记录、以及通过一级信息分析得到的二级信息（扁平化存储），明确每种 context 以何种形式存储
    - 为每个 context 添加权重表示重要性
    - 及时进行 context 的整理，明确哪些 context 重要需要提高权重，哪些不重要需要降低、哪些属于旧信息脏数据需要删除。尽可能保证 context 准确，尽可能避免遗忘、腐烂
    - 每个 context 需要有添加时间，便于存在明显矛盾时进行旧数据删除
- 不同类型 context 的获取方式需要你来判断，如性别、MBTI 等可以通过用户手动输入；聊天记录如何获取（更方便用户使用）？截屏？录屏？权限问题？
- ai 侧技术选型使用 LangChain / LangGraph，暂定 python。请充分利用 LangChain / LangGraph 的相关功能，如 memory、agent skills、MCP tools 等。保证 context 全面而有效，尽可能避免腐烂
- 前端技术选型待定，若产出形式为 web app 则使用 react + vite，若为移动端 app 则用跨端框架 Lynx
- 后期可通过大量的 context 构建数字人，进行新的探索
  我有很多无法确定的问题：
- 产出形式是 web app 还是移动端 app 比较好？
- context 应包含什么？怎么存储？怎么获取？
- ……

### SECOND ENTRY - 2026.02.22

到现在为止，一周过去了，我基本上已经完成了系统架构的设计。我来陈述下已经完成的工作：

- Robyn 作为后端框架以 FaaS 服务的形式完成后端服务搭建，在本地 1314 端口跑通
- 使用 langchain_openai 连接火山方舟模型服务，使用 Doubao-Seed-1.6 搭建 agent，全局单例在系统中使用
- 完成数据模型架构设计，包含 User, Crush, RelationChain, ChainStageHistory, Event, ChatLog, InteractionSignal, DerivedInsight, ContextEmbedding, Knowledge。其中预期将 Crush, Event, ChatLog, InteractionSignal, DerivedInsight, ContextEmbedding, Knowledge 表内容组织为模型上下文/短期记忆/长期记忆传递给 agent 以供后续需求实现
- 通过火山方舟向量模型 Doubao-embedding-vision 配合 pgvector 搭建向量数据表和文本向量化和召回链路：支持将知识库条目 knowledge、对方个人画像、事件 event、聊天记录 chat_log 和派生的推断/洞察 insight 分别适配处理为适合向量化的文本，向量化后落入 ContextEmbedding 表以供后续召回
- 通过 llm 从用户的自然语言描述中提取出其中涉及的对方的个人画像（包含 MBTI、喜好、不喜欢、个人边界、个人特点以及其他信息）和事件 event，结构化输出后经解析分别落入 Crush 表和 Event 表。同时通过 4 中的向量化链路对二者进行文本处理、向量化并落入落入 ContextEmbedding 表以供后续召回
- 完成知识库条目添加同时向量化落库链路：通过 llm 将输入的自然语言表述的事实/观点拆分为一条或多条可写入向量数据表用于后续召回的知识条目，解析后同时落入 Knowledge 表和 ContextEmbedding 表
  经过本地测试，目前的三条主链路 —— 自然语言转画像/事件并向量化落库、自然语言新增知识库条目并向量化落库、embedding 召回均正常工作。我将其封装为三个 API 供外部调用：`/addKnowledge`, `/addContextByNaturalLanguage`, `/recallContextFromEmbedding`。其中 embedding 召回效果显著，准确性较高，且支持限定向量来源（FROM_KNOWLEDGE、FROM_CRUSH_PROFILE、FROM_EVENT、FROM_CHAT_LOG、FROM_DERIVED_INSIGHT）
  下一步我将着手实现系统的核心功能 —— 关系分析。但我预期的产出并不是仅仅做一个和用户对话的 chatbot，而是一系列可供用户调用的 API，分别实现不同的功能。首先，我希望首先实现这个功能：
- `/getIntelligentReply`：传入用户和对方聊天的部分最近上下文给出用户回复建议。需要大量参考数据库中上下文信息，包括对方的个人画像以及他/她的 MBTI 类型，知识库中召回此类型的特征，推断怎样回复更能提高对方的好感、关注度，更能推动聊天进一步发展
  我了解到这个过程可能需要 agent 的几个功能：短期记忆、长期记忆、tool call、skills… 但我暂时还不知道该如何入手。

### THIRD ENTRY - 2026.02.23

我阅读了 langchain 部分文档，我得到了一些理解：
首先，短期记忆就是指在同一 thread（相同 thread_id 才会加载同一份记忆）范围内用户与 LLM 先前的交互内容，包括 HumanMessage, AiMessage 和 ToolMessage 和一些相关信息。在 langchain 中可以通过 langgraph checkpoint 的方式保存每次回话的 messages 快照（或自定义的额外字段）在 AgentState 中，记录在内存 `InMemorySaver ()`（LangGraph 的 checkpoint 保存器）或数据库支持的 checkpointer 中。进入新的回话时 agent 就可以保持对先前交互的记忆。
但 LLM 的上下文窗口有限，对于长对话过多的记忆可能超出其上下文窗口，所以需要设计记忆遗忘或压缩策略。常见策略包括：

- trim messages（裁剪最早/近 N 条）
- delete messages（规则删除）
- summarize messages（总结压缩）
  另外，长期记忆通常有两种形态：一种是基于 langgraph 的内存存储 `store = InMemoryStore ()`（一个轻量 KV 容器）把需要长期记忆的信息结构化组织，通过 tool 来读取返回给 agent，InMemoryStore 在 creat_agent 时作为 store 参数传入，可在 tool 中作为 runtime 读取/更新。但通过 InMemoryStore 进行记忆存储一方面依赖于内存，一方面生命周期和 agent 绑定，不适合在生产环境使用。而在生产环境中可以将 tool 直连外部数据库，返回所需内容直接提供给 agent。另一种是向量检索型的长期记忆，即 RAG。通过【用户输入 → embedding → vector search → 取回相关记忆 → 拼接给 LLM】的链路实现记忆。
  对于生产环境，一种可能的技术选型：
- InMemorySaver → PostgreSaver
- InMemoryStore → PostgreSQL 数据库
  LLM 和 agent 本身没有记忆功能，无论哪种记忆，都是通过工程层面把需要记忆的信息组织/储存后作为 context 传给模型。
  回到本项目当前预期实现的功能 getIntelligentReply，我认为短期记忆在此处没有丝毫用处 —— 我并不是要做一个 chatbot 给用户使用，所以自然不涉及"历史对话"此类信息需要作为短期记忆。而长期记忆正是我所需要的。我已经建立了上面提及的非常详细的数据模型，其中 Crush, Event, ChatLog, InteractionSignal, DerivedInsight, ContextEmbedding, Knowledge 将被分别被作为不同的上下文部分结构化地传递给 agent。
  我目前有一种 maybe 可行的技术方案：
  对于 getIntelligentReply 功能，可以定制化设计针对实现它功能的 skills，并明确工作流编排，对于每个节点，都设计对应的 tool 来实现功能并返回。例如：
  ::: warning
  用户输入和对方聊天的部分最近上下文 → 通过当前用户获取当前 User 信息 → 根据 User 信息获取他当前处于的 RelationChain 以及关系链中的对方信息，结构化封装对方相关信息作为 context 的一部分 → 根据对方的 mbti 从 knowledge 中向量化检索相关条目，作为 context 的一部分 → 基于聊天的上下文从 ContextEmbedding 向量表中分别召回相关 event、chat_log、derived_insight 和 knowledge 条目，分别合理排序后结构化封装为 context 的一部分 → …(其他所需 context) → context 和当前功能的 prompt 一并传给 agent 等待回复
  :::

### FOURTH ENTRY - 2026.02.25

现在的 agent 架构是这样：

```python
@lru_cache
def getAgent():
    # 1. Prepare LLM
    llm: ChatOpenAI = prepareLLM()
    # 2. Prepare Tools
    # mcp_psms_list = get_mcp_psms_list()
    # tools: List[BaseTool] = await init_mcp_tools(mcp_psms_list)
    # 3. Init Agent
    agent_instance = create_agent(model=llm, tools=[], system_prompt=SYSTEM_PROMPT)

    return agent_instance

```

但显然 ReAct 形式的自主决策的 agent 不是很符合我们固定工作流的设计。我们需要在工作流的每个节点都可控制可回溯，拿到中间产物。所以我理解 langgraph 的 StateGraph 更适配当前需求，更可控。所以我期望重构 agent 架构，不，另开一个单独的 workflow，保留原有的 ReAct agent。

### FIFTH ENTRY - 2026.02.27

最近两天我完成了 StateGraph 的框架搭建，在这个工作流中，用户需要输入和对方的聊天上下文以供模型判断。基于我现有的架构（ChatLog 模型）需要用户把各平台（如微信、抖音）的聊天记录导出再通过系统能力落库。昨天我调研了各个微信聊天记录的导出方式，无一例外成本都非常高，直接让用户进行导出恐怕不大行。
我又尝试了让用户上传聊天记录的截图交给模型处理（还构思了一些 rules，如**截图必须至少包含一个时间**、**必须按时间顺序上传**、**不得多于 5 张**），让模型返回符合 ChatLog 规范的结构化的 json：

```python
## 从截图中提取聊天记录
async def extractChatFromScreenshots(screenshot_urls: List[str]) → str:
    if not isinstance(screenshot_urls, list) or len(screenshot_urls) == 0:
        return "Wrong screenshot format"
    if len(screenshot_urls) > 5:
        return "Screenshots should be no more than 5"
    cleaned_urls: List[str] = []
    for url in screenshot_urls:
        if not isinstance(url, str):
            return "Wrong screenshot url"
        url = url.strip()
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            return "Wrong screenshot url"
        cleaned_urls.append(url)

    today = datetime.now(timezone.utc).date().isoformat()
    prompt = await getPrompt(
        os.getenv("EXTRACT_CHAT_FROM_SCREENSHOTS_PROMPT"),
        {"today": today},
    )
    agent = await getAgent()
    return await askWithNoContext(
        react_agent=agent,
        prompt=prompt,
        images_urls=cleaned_urls,
    )

```

prompt：

```plaintext
你是聊天截图信息抽取助手。请根据用户提供的聊天截图，抽取结构化聊天记录。

要求：
1. 输出 JSON 数组，数组元素为 RawChat。
2. RawChat 字段：
   - speaker: "me" 或 "crush" 或 "third_party"
   - content: 纯文本内容
   - timestamp: ISO 8601 字符串，例如 "2025-02-26T13:20:00+08:00"
   - channel: 枚举值之一 ["offline","weixin","douyin","sms","email","phone","other"]
   - weight: 0-1 之间的浮点数，表示重要性
   - other_info: 字典数组，基于整段聊天内容总结出的补充信息，允许空数组
3. timestamp：
   - 若截图显示具体日期与时间，直接使用并保持时区信息
   - 若只显示时间（如 13:20），请结合今天日期推断日期，默认当天
   - 若未显示时间，请根据上下文合理推断一个时间，保证同一张图内对话时间单调递增
4. channel：
   - 根据截图 UI 风格、气泡样式、昵称/头像布局推断
   - 无法判断时用 "other"
5. other_info：
   - 必须结合全部聊天内容抽取，例如关系进展、地点、事件、情绪、偏好等
   - 每个元素是字典，键为英文，值为字符串或数字
6. 输出数组元素按timestamp排序
7. 仅输出 JSON，不要包含任何解释或 Markdown。

今天日期：{{today}}

```

验证结论：

- 速度极其慢：2 张截图处理要大概 2min
- 效果极其差：时间混乱、sender 错乱、聊天内容与原文不符、存在无效信息如表情包（猪猪侠【sticker: red pig】）
  之后我理解原有的表是原始聊天记录 ChatLog，但由于任何渠道的原始聊天记录不便于收集导出，在本系统中粒度过细的原始聊天记录对于构建人物画像也没有什么用处，我希望更换一种模式：把 ChatLog 表换为聊天话题 ChatTopic 表。用户传入聊天记录截图（要求单次上传必须属于同一 topic，把语义化分割的任务交给用户），模型理解并抽取 crush_profile 和 chat_topic 并落库。后续构建上下文时直接使用 chat_topic 而无需基于原始聊天记录做进一步分析。这样既减轻了模型压力，又可以更精确的向量化和召回。

### SIXTH ENTRY - 2026.03.04

最近几天一直埋头于开发工作，没顾得上写复盘。自上次数据模型重构后，到昨天为止，总算完成了 StateGraph 的全部链路。我把 `/getIntelligentReply` 改名为 `/conversationAnalysis`。通过一系列 node 完成了一条线性的 graph workflow。
::: warning
**用户输入**：聊天记录截图、补充上下文 additional_context
**经过节点**：nodeLoadEntity → nodeBuildCrushProfileContext → nodeBuildRecallQueries → nodeRecallKnowledge → nodeRecallNonKnowledge → nodeGetInteractionSignal → nodeOrganizeContext → nodeFetchPrompt → nodeCallLLM → nodeOutput
**输出**：下一步消息候选 message_candidates、风险提示 risks、下一步推进话题或行动建议 suggestions
:::

测试这个链路，用时 1min32s 才完成，这效率有点太低。我尝试接入了 PostgresSaver 的 checkpointer 来给 graph 支持短期记忆。
graph 编译：

```python
## 通过 PostgresSaver 保存 checkpoint 实现短期记忆
with PostgresSaver.from_conn_string(os.getenv("DATABASE_URI")) as checkpointer:
    _graph_instance = graph.compile(checkpointer=checkpointer)

```

graph 消费：

```python
short_term_memory_config = {"configurable": {"thread_id": str(relation_chain_id)}}
result = await graph.ainvoke(initial_state, config=short_term_memory_config)

```

我已经有了初步的下一步规划，但在开始之前有几个问题需要搞明白。于是我在 Trae 里如此发问：

> 针对这个架构，我还有很多地方不理解：
> 请尽可能详细帮我解答

GPT-5.2-Codex 如此回复：

> **核心结论**
>
> **1) 一个 graph 只服务 conversationAnalysis 吗？**不是"只能"，但"当前实现基本等同于只服务"。原因在于：
>
> 结论：目前的 graph 是**一个特化流程**。如果你想让它服务多种功能，需要将"共用能力"抽离，例如：
>
> 这些可以变成"子图"或"通用节点"，而不是被 conversationAnalysis 节点硬编码驱动。
>
> **2) 想基于已完成 conversationAnalysis 再追加 askNext 的设计思路**你希望：
>
> 推荐方案：**引入"流程阶段 + 可复用子图"**
> **方案 A：单图多分支**
>
> 优点：统一 graph、统一记忆；缺点：图逻辑复杂度上升。
> **方案 B：拆分子图 + 编排**
>
> 优点：更清晰，可测试性强；缺点：子图组合需要额外编排代码。
>
> **3) 短期记忆是否必要？如何裁剪？**你当前的 pipeline 实际上是"短期重用 + LLM 大上下文"，这类场景短期记忆是有价值的：
> **必要性**
>
> **裁剪策略**需要区分：
>
> 推荐策略：
>
> 重点：裁剪不是删字段，而是**保留"更稀疏、更稳定"的版本**，保证后续 askNext 仍能复用语义。
>
> **4) 模拟对话等新功能是否需要新 graph？**大概率需要一个新 graph 或者一个新分支，但**不代表不能复用**。
> 你可以复用的部分：
>
> 需要新写的部分：
>
> 一种可行做法：
>
> 这样你**不是复用现有 graph 的"输出格式"**，而是复用"上下文构建能力"。
>
> **建议的抽象方式（最少侵入）**
>
> 了解后我准备开始公共子图构建了。

### SEVENTH ENTRY - 2026.03.06

昨天感冒了，今天还没完全好。晕晕沉沉地对着现在已有的 ContextGraph 和 AnalysisGraph 不知所措。确实我一开始的需求 —— 通过聊天记录截图或自然语言叙述进行分析 —— 已经跑通了，但这个架构的成熟度实在不敢恭维...... 我承认这是我第一次用 langgraph 做开发，对于其 state 怎么设计、node 怎么分界这些标准都不清楚。于是我就栽到了下面的坑里：

- 我的 GraphState 里包含了太多没用的中间产物（如 Entities、CrushProfileContext、RecallQueries 等等），这在我希望用 checkpoint 做短期记忆的时候才意识到。这些中间产物不但没有丝毫作用，还极大地消耗了 token。
- 特别是 Entities 里面甚至把诸如 User、Crush 等 ORM 实例存到了 state 里，这让它们无法像普通 dict 一样被 msgpack 包装，也就没法作为 checkpoint 存储。
  一开始我决定在 graph 的最后一个 node 结束前把 state 中的中间产物清空，设为 None。但实际上 checkpoint 会存储每一步 node 完成的 state 快照。这样仅仅让最后一节点的 checkpoint 没有中间产物记录，也就是说中间产物还是会被 checkpoint 记录。
  之后我决定直接把中间产物从 state 剔除：

```python
class ContextGraphState(TypedDict):
    request: Request
    context_block: str

class AnalysisGraphState(TypedDict):
    request: Request
    context_block: str
    llm_output: LLMOutput

```

我发现我不懂怎么分 node 了。
我想既然每个 node 接受整个 state 为参数，返回 state patch。我寻思我先前很多节点做的操作在新的 state 中根本不会改变 state 本身，都是得到中间产物 --- 消费。那我似乎没必要分这么多节点了。于是我干脆只保留了一个节点，中间过程都用普通函数 step...() 代替：

#### ContextGraph

```python
async def node(state: ContextGraphState) -> ContextGraphState:
    request = state["request"]
    entities = await stepLoadEntity(request)
    crush_profile_context = await stepBuildCrushProfileContext(entities)

    recall_queries: RecallQueries = {
        "knowledge_query": None,
        "non_knowledge_query": None,
    }
    if request.get("narrative") and request.get("narrative") != "":
        recall_queries = await stepBuildRecallQueriesFromNarrative(
            request, entities, crush_profile_context
        )
    else:
        recall_queries = await stepBuildRecallQueriesFromScreenshots(
            request, entities, crush_profile_context
        )

    recalled_knowledges = await stepRecallKnowledge(request, recall_queries)
    recalled_non_knowledges = await stepRecallNonKnowledge(request, recall_queries)
    interaction_signals = await stepGetInteractionSignal(request)
    all_context = {
        "knowledge": recalled_knowledges,
        "event": recalled_non_knowledges["events"],
        "chat_topic": recalled_non_knowledges["chat_topics"],
        "derived_insight": recalled_non_knowledges["derived_insights"],
        "interaction_signal": interaction_signals,
    }

    context_block = await stepOrganizeContext(
        entities, crush_profile_context, all_context
    )
    return {
        "request": request,
        "context_block": context_block,
    }

```

#### AnalysisGraph

```python
async def node(state: AnalysisGraphState) -> AnalysisGraphOutput:
    request = state["request"]
    context_block = state["context_block"]
    history_state = state.get("history_state")
    if state["is_first_analysis"]:
        # 首轮分析，根据 narrative 或 screenshots 生成 prompt
        if request.get("narrative") and request.get("narrative") != "":
            final_prompt = await stepFetchPromptFromNarrative(request, context_block)
        else:
            final_prompt = await stepFetchPromptFromScreenshots(request, context_block)
    else:
        # 后续分析，根据 narrative 生成 prompt
        final_prompt = await stepFetchPrompt4ContinuousAnalysis(request)

    llm_output = await stepCallLLM(request, final_prompt, history_state)
    return {
        "llm_output": llm_output,
    }

```

这样一来两个 graph 依然能顺利跑通。我之所以这样做是为了引入短期记忆。我之所以要引入短期记忆是为了在分析后用户进一步输入后续 narrative（或后续聊天记录截图，搁置了），链路无需再次调用极其耗时的 ContextGraph，只借助存储的先前的 checkpoint 就保留上轮分析的全部信息（包括 request、context_block 和 llm_output），就可以直接调用 AnalysisContext 做进一步分析（自然要使用新的提示词，见上 `stepFetchPrompt4ContinuousAnalysis`）。
为此我设计如下（以 narrative 链路为例）：

```python
## 自然语言叙述分析
@app_router.post("/narrativeAnalysis", auth_required=True)
async def narrativeAnalysis(request: Request):
    data = request.json()
    # todo: 鉴权 + 删除 dev 豁免
    user_id = (
        userGetUserIdByAccessToken(request=request)
        if os.getenv("CURRENT_ENV") != "dev"
        else 1
    )
    relation_chain_id = data["relation_chain_id"]
    narrative = data["narrative"]
    # 调用图
    context_graph = await getContextGraph()
    analysis_graph = await getAnalysisGraph()
    initial_state = initContextGraphState(
        {
            "user_id": user_id,
            "relation_chain_id": int(relation_chain_id),
            "narrative": narrative,
        }
    )
    with session() as db:
        new_analysis = Analysis(
            relation_chain_id=int(relation_chain_id),
            type=AnalysisType.NARRATIVE,
            narrative=narrative,
            is_first_analysis=True,
        )
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)

    short_term_memory_config = {
        "configurable": {"thread_id": f"{relation_chain_id}_{new_analysis.id}"}
    }
    # ContextGraph 无需记忆
    context_state: ContextGraphState = await context_graph.ainvoke(initial_state)
    # AnalysisGraph 需要记忆
    result: AnalysisGraphOutput = await analysis_graph.ainvoke(
        AnalysisGraphInput(**context_state, is_first_analysis=True, history_state=None),
        config=short_term_memory_config,
    )
    # 两阶段 session，避免 ainvoke 耗时操作长时间占用数据库连接
    with session() as db:
        analysis = db.get(Analysis, new_analysis.id)
        if analysis is not None:
            analysis.message_candidates = result["llm_output"].get(
                "message_candidates", []
            )
            analysis.risks = result["llm_output"].get("risks", [])
            analysis.suggestions = result["llm_output"].get("suggestions", [])
            db.commit()

    return {
        "status": 200,
        "message": "Success",
        "result": result["llm_output"],
        "analysis_id": new_analysis.id,
    }


## 基于分析记录短期记忆连续分析（无需重新调用 ContextGraph）
@app_router.post("/continuousAnalysis", auth_required=True)
async def continuousAnalysis(request: Request):
    data = request.json()
    # todo: 鉴权 + 删除 dev 豁免
    user_id = (
        userGetUserIdByAccessToken(request=request)
        if os.getenv("CURRENT_ENV") != "dev"
        else 1
    )
    relation_chain_id = data["relation_chain_id"]
    base_analysis_id = data["analysis_id"]
    narrative = data["narrative"]

    # 调用图
    analysis_graph = await getAnalysisGraph()
    with session() as db:
        base_analysis = db.get(Analysis, int(base_analysis_id))
        if base_analysis is None or base_analysis.relation_chain_id != int(
            relation_chain_id
        ):
            return {
                "status": -1,
                "message": "analysis not found",
            }
        base_analysis_id_value = base_analysis.id
        new_analysis = Analysis(
            relation_chain_id=int(relation_chain_id),
            type=AnalysisType.NARRATIVE,
            narrative=narrative,
            is_first_analysis=False,
        )
        db.add(new_analysis)
        db.commit()
        db.refresh(new_analysis)
        new_analysis_id = new_analysis.id

    short_term_memory_config = {
        "configurable": {
            "thread_id": f"{relation_chain_id}_{base_analysis_id_value}"
        }
    }
    request_payload = {
        "user_id": user_id,
        "relation_chain_id": int(relation_chain_id),
        "conversation_screenshots": None,
        "additional_context": None,
        "narrative": narrative,
    }
    result: AnalysisGraphOutput = await analysis_graph.ainvoke(
        AnalysisGraphInput(
            request=request_payload,
            context_block="",
            is_first_analysis=False,
        ),
        config=short_term_memory_config,
    )
    with session() as db:
        analysis = db.get(Analysis, new_analysis_id)
        if analysis is not None:
            analysis.message_candidates = result["llm_output"].get(
                "message_candidates", []
            )
            analysis.risks = result["llm_output"].get("risks", [])
            analysis.suggestions = result["llm_output"].get("suggestions", [])
            db.commit()

    return result["llm_output"]

```

然而现实又一次重拳出击，第一轮 analysis 后跑 continuousAnalysis 却无法正确拿到第一轮 analysis 中存储的 checkpoint 记忆，ai 分析原因如下：

> 短期记忆只保存"图的 state"，不是 LLM 对话历史。AnalysisGraph 的 stepCallLLM 每次只构造一个新的 HumanMessage（没有历史消息拼接），所以即便 checkpoint 存了上次 state，也不会自动影响当前 LLM 输入。
> 另外，continuousAnalysis 会用 context_block="" 覆盖 checkpoint 中的 context_block。LangGraph 复用 checkpoint 时会把新的 input 合并进 state，input 里提供的字段会覆盖旧值。你这里给了空字符串，等价于把历史上下文清空了。
> 到现在为止，我决定不再盲目继续乱撞了，而需要重新评估我的需求是否合理。事实上 ai 已经给出了针对上述问题的解决方案：
> 给 AnalysisGraphState 添加 history_state，在执行 continuousAnalysis 时调用 checkpoint 接口手动把需要的 channel_values 加到 history_state 中，在 stepCallLLM 时添加 history_state 为 SystemMessage：
> continuousAnalysisstepCallLLM
> 但这样不行啊！如果每次把执行的全部 state 作为 history_state 包一层加到上下文，history_state 无限嵌套 token 会爆炸的；如果只把 state 中必要的三项（见上文：request、context_block 和 llm_output）加到 history_state，history_state 没有了嵌套结构，history_state 只能保留上一次执行的 state，两次前的 state 就被覆盖了。
> 我需要重新评估这个需求是否合理，另外使用短期记忆 checkpoint 来实现是否合理。
> 另外，我决定后续的主要人力投入到虚拟人的开发中，不再硬搞分析建议这一套了。有了人物画像，虚拟人的开发应该问题不大。
> ::: primary
> 后续 TODOs：

- 添加上下文的原始数据（截图、自然语言叙述）留存
- Crush 表补充字段自己和对方的说话习惯，另开字段存储典型的说话语气 ✅
- 重新评估 short-term memory ✅
  :::

### EIGHTH ENTRY - 2026.03.14

> MILEPOST
> 哎，这会是一篇意义重大的日记。自 3.6 以来居然落下那么多东西没有及时写下来。
> 事实上 6 号之后仅用了 3 天就把虚拟人 Virtual Figure 这个链路基本完成了。之后进入了很长时间的休止期 —— 这周工作内容比较多，确实没什么时间回头搞自己的。

![进度](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_33ca0c3b2b.png?x-oss-process=image/resize,w_800)

然鹅，这周也同样接受了太多关于 Agent 开发的知识，这些东西对我来讲可以说是颠覆性的。让我不得不从头思考这个工程的架构和实现。不出意外这些都会在这篇日记里面一一阐明。

#### Virtual Figure 链路

##### 数据表与 API 完善

- 为 Crush 表添加两个字段 `words_to_user` 和 `words_from_user`。前者表示对方对用户讲过的话，用于构建虚拟人模拟对方交流风格；后者反之，用于 analysis 时给用户回复建议
- RelationChain 表添加字段 `context_block`，存放 ContextGraph 构建的关系与画像上下文，在虚拟人对话时消费
- 添加新 API `/recalculateContextBlock` 在新增了新的 event、chat_topic 和 crush 画像内容时重新跑 ContextGraph 更新关系与画像上下文 context_block。使虚拟人拥有最新的上下文

##### Websocket

为了实现更真实的对话流，我不再采用 LLM 普遍的一问一答的形式，不再通过 SSE 向客户端推送消息。我建立了 Websocket 双向通信，遵守以下策略：
::: primary
用户发信息后，计时器倒计时 WAITING_SECONDS_FOR_VIRTUAL_FIGURE 秒（暂定 15s）。若倒计时未结束时用户继续发消息，计时器重置。直到计时器结束（一个完整的 WAITING_SECONDS_FOR_VIRTUAL_FIGURE 秒用户没有发消息），将本轮次用户发送的全部消息按顺序打包后一并交由 VirtualFigureGraph 处理。处理后 Agent 生成若干条回复消息。每条消息随机间隔 0.8～2.2s 向客户端推送。
:::

##### VirtualFigureGraph

**State 设计**：

```python
class Message(TypedDict):
    message: str
    relation_chain_id: int

class Request(TypedDict):
    user_id: int
    relation_chain_id: int
    messages_received: List[Message]

class Memory(TypedDict):
    messages: Annotated[
        List[BaseMessage], add_messages
    ]
    context_block: str
    recalled_facts_from_db: str
    recalled_facts_from_mem0: List[dict]

class LLMOutput(TypedDict):
    messages_to_send: List[str]
    thinking: str

class VirtualFigureGraphState(TypedDict):
    request: Request
    memory: Memory
    llm_output: LLMOutput

```

**工作流设计**：

```plaintext
获取本 relation_chain 中关系与画像上下文 context_block
↓
根据用户消息从数据库召回 events、chat_topics 和 derived_insights
↓
从 Mem0 召回（暂未实现）
↓
构造 context：将系统提示词、关系与画像上下文和召回的长期记忆分别作为三个 SystemMessage；将打包后的用户消息作为 HumanMessage
↓
call LLM
↓
解析回应并写入 memory

```

##### 短期记忆

每轮次 HumanMessage 和 AIMessage 放在 `state ["memory"]["messages"]` 中，不存放 SystemMessage，每次单独构建；VirtualFigureGraph compile 时使用 PostgresSaver 作为 checkpointer（详见上文）

##### 本周的新认知与本项目的思考

这周很偶然地接触到去年字节爆火的一个开源产品 DeerFlow，使用 LangStack 以 Multi-Agent 架构搭建的 Deep Research Agent。这个工程的建设很大程度上采用了 LangChain/LangGraph 的最佳实践，比如 state、node 的设计；以及很多 Agent 开发相关技术、架构，例如 Meta Prompt、Supervisor 架构、Handoffs 模式...... 都非常值得借鉴。回看 HeartCompass 中架构和链路的设计，果然有非常多的缺陷和优化点。因此我决定基于这些新的认知和 ChatGPT 一同完成 HeartCompass 的优化工作。
::: primary
后续 TODOs：

- 提示词使用 Meta Prompt 重构
- Virtual Figure 提示词添加当前时间戳
- 重构全量 agent 架构
- 与 ChatGPT 讨论实现 Virtual Figure 最佳工程实践，重构 VirtualFigureGraph
    - 引入 tool call
    - 不是每轮对话都需要召回长期记忆（包括 DB 召回和 Mem0 召回），智能判断是否需要召回
    - 召回封装成 tool
- Websocket 添加心跳机制和断线重连
- 引入火山 Mem0 长期记忆
- 添加关系与画像上下文的原始数据（截图、自然语言叙述）留存
- 探索新的关系与画像上下文补充方式，完成对应 API
- 引入 LangGraph Studio 调试：`uvx --refresh --from"langgraph-cli [inmem]"--with-editable . --python 3.13 langgraph dev --allow-blocking`
  :::

### NINTH ENTRY - 2026.03.16-18

> 大规模重构

#### graph 目录架构重构

agent/graph 目录中，以 graph 种类组织工程结构。

![graph 目录架构重构](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_27d6e6fa0a.png?x-oss-process=image/resize,w_500)

#### 向量召回策略重构

先前以 `distance` 作为唯一召回指标，没有考虑权重 `weight`、关键字、时间衰减。重构策略如下：

##### 召回流程

参数校验 → 源范围归一化 → 向量召回 → 业务过滤 → 打分排序

##### 候选逐条业务过滤与字段抽取

使用 `ContextEmbedding.embedding.cosine_distance (vector)` 计算距离
查询条件与顺序：

- `ContextEmbedding.type in selected_types`
- 按距离升序（越小越相似）
- 候选数限制：`limit (int (os.getenv("VECTOR_CANDIDATES")))`
  每条候选会根据 `embedding.type` 分支读取关联对象并抽取：-**公共输出字段**：
    - `data`：对应实体的 `toJson ()` 结果
    - `weight`：对应实体权重，默认 `1.0`
    - `created_at`：仅部分类型参与时间衰减
      **分支规则**：
- `FROM_KNOWLEDGE`：
    - 使用 `embedding.knowledge`
    - `weight = knowledge.weight`
    - 不做 relation_chain 过滤
- `FROM_CRUSH_PROFILE`：
    - 使用 `embedding.crush`
    - 若存在 `crush_id` 且 `embedding.crush.id != crush_id`，跳过
    - `weight = crush.weight`
    - 不参与时间衰减
- `FROM_EVENT`：
    - 使用 `embedding.event`
    - 若传入 `relation_chain_id` 且不等于 `event.relation_chain_id`，跳过
    - `weight = event.weight`
    - `created_at = event.created_at`
- `FROM_CHAT_TOPIC`：
    - 使用 `embedding.chat_topic`
    - 若传入 `relation_chain_id` 且不等于 `chat_topic.relation_chain_id`，跳过
    - `weight = chat_topic.weight`
    - `created_at = chat_topic.created_at`
- `FROM_DERIVED_INSIGHT`：
    - 使用 `embedding.derived_insight`
    - 若传入 `relation_chain_id` 且不等于 `derived_insight.relation_chain_id`，跳过
    - `weight = derived_insight.weight`
    - `created_at = derived_insight.created_at`
      若类型与关联对象不匹配，直接跳过该候选。

##### 召回评分

-**语义分**：`semantic_score = 1 - distance` -**时间衰减**：

- 若有 `created_at`：`time_decay = exp (-delta_days / HALF_LIFE_DAYS)`
- 若无 `created_at`：`time_decay = 1.0` -**融合分（未衰减）**：
- `raw_score = semantic_score * 0.8 + weight * 0.2` -**最终分**：
- `score = raw_score * time_decay`
  其中：`delta_days = (now_utc - created_at).days`。若 `created_at` 无时区信息，会按 UTC 处理。
  所有有效候选按 `score` 降序排序，取前 `top_k` 条作为返回 `items`。

#### ContextGraph 重构

##### Pipeline

> 原先：LoadEntity → BuildProfileContext → BuildRecallQueries → RecallKnowledge → RecallNonKnowledge → GetInteractionSignal → OrganizeContext
> **新架构**：
> 链路 1：relation_chain_id → relation_chain → crush + current_stage → 整理，得到：

```python
"basic_context": {
    "his_mbti": his_mbti,
    "his_profile": his_profile,
    "current_stage": current_stage.value if current_stage else None,
}

```

**若无聊天记录、无自然语言叙述输入，这些信息足够**
链路 2：召回 events、chat_topics 和 derived_insights
【思路一】relation_chain_id + 聊天记录/自然语言叙述 → LLM → tool call（向量召回封装为 tool） → 组织后的可直接作为上下文消费的 non_knowledge
【思路二】（保留原有逻辑）聊天记录/自然语言叙述 → build query + relation_chain_id → recall → 手动组织
链路 3：链路 1 后 → his_mbti → 关键字召回 knowledge
链路 4：relation_chain_id → interaction_signal
**图结构**：

```python
graph = StateGraph(
    state_schema=ContextGraphState,
    input_schema=ContextGraphInput,
    output_schema=ContextGraphOutput,
)
graph.add_node("nodeGenBasicContext", nodeGenBasicContext)
graph.add_node(
    "nodeBuildRecallQueryFromScreenshots", nodeBuildRecallQueryFromScreenshots
)
graph.add_node(
    "nodeBuildRecallQueriesFromNarrative", nodeBuildRecallQueriesFromNarrative
)
graph.add_node("nodeRecallFromDB", nodeRecallFromDB)
graph.add_node("nodeRecallBranchDone", nodeRecallBranchDone)
graph.add_node("nodeGetMBTIKnowledge", nodeGetMBTIKnowledge)
graph.add_node("nodeGetInteractionSignal", nodeGetInteractionSignal)
graph.add_node("nodeOrganizeContext", nodeOrganizeContext)

## 三链路并行
## BasicContext → MBTIKnowledge
graph.add_edge(START, "nodeGenBasicContext")
graph.add_edge("nodeGenBasicContext", "nodeGetMBTIKnowledge")

def routerByType(state: ContextGraphState) -> str:
    req_type = state["request"].get("type")
    match req_type:
        case "conversation":
            return "nodeBuildRecallQueryFromScreenshots"
        case "narrative":
            return "nodeBuildRecallQueriesFromNarrative"
        case "no_material":
            return "nodeRecallBranchDone"
        case _:
            return "nodeRecallBranchDone"

graph.add_conditional_edges(
    START,
    routerByType,
    [
        "nodeBuildRecallQueryFromScreenshots",
        "nodeBuildRecallQueriesFromNarrative",
        "nodeRecallBranchDone",
    ],
)
graph.add_edge("nodeBuildRecallQueryFromScreenshots", "nodeRecallFromDB")
graph.add_edge("nodeBuildRecallQueriesFromNarrative", "nodeRecallFromDB")
graph.add_edge("nodeRecallFromDB", "nodeRecallBranchDone")

graph.add_edge(START, "nodeGetInteractionSignal")

graph.add_edge(
    [
        "nodeGetMBTIKnowledge",
        "nodeRecallBranchDone",
        "nodeGetInteractionSignal",
    ],
    "nodeOrganizeContext",
)

graph.add_edge("nodeOrganizeContext", END)

```

![Graph 结构](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/Need%20to%20backup%20paper%20documents_d456f9052b.png?x-oss-process=image/resize,w_800)

在实际实现过程中，由于一些问题最终按照以下方式组织图结构：
**重要**：BasicContext 获取、Embedding 召回和 InteractionSignal 获取三条链路并行运行需要保证**在 nodeOrganizeContext 之前三链路均已结束**

#### LangSmith Studio 调试

- 安装依赖：`uv add"langgraph-cli [inmem]"`
- 工程根目录配置 `langgraph.json`：

```json
{
    "dockerfile_lines": [],
    "graphs": {
        "ContextGraph": "./src/agent/graph/ContextGraph/graph.py:ContextGraph"
    },
    "python_version": "3.13",
    "env": "./.env",
    "dependencies": ["."]
}
```

- `.env` 配置 `LANGSMITH_API_KEY`
- 运行 `langgraph dev`

效果：

![LangSmith Studio](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_506e568667.png)

#### AnalysisGraph 重构

##### AnalysisGraph State 设计

```python
class Request(TypedDict):
    user_id: int
    relation_chain_id: int
    type: Literal["conversation", "narrative"]
    conversation_screenshots: List[str] | None
    crush_name: str | None
    additional_context: str | None
    narrative: str | None

class LLMOutput(TypedDict):
    message_candidates: List[str]
    risks: List[str]
    suggestions: List[str]
    message: str | None

class AnalysisGraphState(MessagesState):
    request: Request
    context_block: str
    system_prompt: str
    llm_output: LLMOutput

```

##### AnalysisGraph 图结构

```python
graph = StateGraph(
    state_schema=AnalysisGraphState,
    input_schema=AnalysisGraphInput,
    output_schema=AnalysisGraphOutput,
)
graph.add_node(
    "nodeFetchSystemPromptFromNarrative", nodeFetchSystemPromptFromNarrative
)
graph.add_node(
    "nodeFetchSystemPromptFromScreenshots", nodeFetchSystemPromptFromScreenshots
)
graph.add_node("nodeCallLLM", nodeCallLLM)

def routerByType(state: AnalysisGraphState) -> str:
    req_type = state["request"].get("type")
    match req_type:
        case "conversation":
            return "nodeFetchSystemPromptFromScreenshots"
        case "narrative":
            return "nodeFetchSystemPromptFromNarrative"

graph.add_conditional_edges(
    START,
    routerByType,
    {
        "nodeFetchSystemPromptFromScreenshots": "nodeFetchSystemPromptFromScreenshots",
        "nodeFetchSystemPromptFromNarrative": "nodeFetchSystemPromptFromNarrative",
    },
)
graph.add_edge("nodeFetchSystemPromptFromScreenshots", "nodeCallLLM")
graph.add_edge("nodeFetchSystemPromptFromNarrative", "nodeCallLLM")
graph.add_edge("nodeCallLLM", END)

```

![可视化 AnalysisGraph](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_bba3b331c1.png?x-oss-process=image/resize,w_800)

##### Tool Call 引入

在AnalysisGraph中，Knowledge的获取不再采用之前每次调用都需要召回。我希望让模型判断当前语境是否是需要触发Knowledge召回的时机，如果是再按需召回。

这就需要用到 Tool Call了——通过提示词和Tool Description，让模型自行判断。

首先，我把获取Knowledge封装成 Tool，Description 为：

```plain
Get MBTI/personality knowledge for this relation_chain to enrich persona and relationship context.
```

需要说明的是，这个Tool接受的参数是当前的relation_chain_id，而Knowledge的来源是在ContextGraph计算时连同context_block一并计算落入RelationChain表中。

而在模型触发tool call时，模型不能稳定地给出当前的relation_chain_id作为tool call参数。所以这意味着，我们需要在tool call发生前，劫持模型的tool call参数，换成当前的relation_chain_id。

于是我设计了一个`ToolAndItsArgsHandler`，存放tool本身和处理其参数的回调函数`args_handler`。

另外我单独封装了`handleIfToolCall ()`方法，这样在graph node中一旦需要引入tool call就可以方便复用：

```python
class ToolAndItsArgsHandler:
    def __init__(self, tool: BaseTool, args_handler: Callable | None = None):
        self.tool = tool
        self.args_handler = args_handler  # 手动处理tool call参数的方法。接受两个参数：tool_call和messages。返回处理后的参数dict。

    def process_args(self, tool_call: dict, messages: list) -> dict:
        # llm 给出的tool call参数
        tool_args = tool_call.get("args") or {}
        if isinstance(tool_args, str):
            try:
                tool_args = json.loads(tool_args)
            except json.JSONDecodeError:
                tool_args = {}
        if not isinstance(tool_args, dict):
            tool_args = {}
        if self.args_handler:
            handled_args = self.args_handler(tool_call, messages)
            if isinstance(handled_args, dict):
                tool_args = handled_args
            else:
                logger.error(
                    f"Args handler {self.args_handler.__name__} return non-dict value {handled_args}"
                )
        return tool_args

async def handleIfToolCall(
    tools_and_args_handlers: List[ToolAndItsArgsHandler],
    messages: list,
    llm_with_tools: Runnable[LanguageModelInput, AIMessage],
    llm_response: AIMessage,
    max_tool_round: int = 3,
) -> tuple[AIMessage, list]:
    # 为降低时间复杂度，提前构建tool_name到ToolAndItsArgsHandler的映射
    tool_map = {ta.tool.name: ta for ta in tools_and_args_handlers}
    tool_round = 0

    while (
        getattr(llm_response, "tool_calls", None)
        and isinstance(llm_response.tool_calls, list)
        and len(llm_response.tool_calls) > 0
        and tool_round < max(0, max_tool_round)
    ):
        # 把新一轮的llm_response加入messages
        messages.append(llm_response)

        for tool_call in llm_response.tool_calls:
            tool_name = tool_call.get("name")
            tool_call_id = tool_call.get("id")
            if not tool_call_id:
                logger.error(f"Tool call id not found in {tool_call}")
                continue

            # find tool
            tool_and_args_handler = tool_map.get(tool_name)
            if tool_and_args_handler is None:
                logger.error(f"Tool {tool_name} not found")
                messages.append(
                    ToolMessage(
                        content=f"ERROR: tool {tool_name} not found\nThis message should be ignored.",
                        tool_call_id=tool_call_id,
                    )
                )
                continue

            # call tool
            tool = tool_and_args_handler.tool
            tool_args = tool_and_args_handler.process_args(tool_call, messages)

            tool_result = None
            try:
                tool_result = await tool.ainvoke(tool_args)
            except Exception as e:
                logger.error(f"Tool {tool_name} error: {e}")
                tool_result = f"ERROR: {e}\nThis message should be ignored."

            messages.append(
                ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_call_id,
                )
            )

        llm_response = await llm_with_tools.ainvoke(messages)
        tool_round += 1

    return llm_response, messages
```

下游AnalysisGraph node中，引入tool call如此：

```python
llm_with_tools = llm.bind_tools([useKnowledge])
response = await llm_with_tools.ainvoke(messages)
# 处理tool call
response = (
    await handleIfToolCall(
        tools_and_args_handlers=[
            ToolAndItsArgsHandler(
                tool=useKnowledge,
                args_handler=lambda _tool_call, _messages: {
                    "relation_chain_id": state["request"].get("relation_chain_id")
                },
            )
        ],
        messages=messages,
        llm_with_tools=llm_with_tools,
        llm_response=response,
        max_tool_round=3,
    )
)[0]
```

显然这套流程下来比LangChain ReAct Agent的tool call复杂的多。后者只需要在`create_agent`时注册工具直接invoke即可。在agent执行过程中会自动处理tool call。但LangGraph node工作流编排等优点就不用我赘述了，我们采取手动处理tool call的流程。

```python
agent = create_agent(
    llm=llm,
    tools=[useKnowledge],
)
agent.invoke(messages)
```

### TENTH ENTRY - 2026.03.24-28

#### VirtualFigureGraph 重构

##### VirtualFigureGraph State 设计

```python
class Message(TypedDict):
    message: str
    relation_chain_id: int

class Request(TypedDict):
    user_id: int
    relation_chain_id: int
    messages_received: List[Message]  # 本轮收到的消息

class LLMOutput(TypedDict):
    messages_to_send: List[str]  # 本轮要发送的消息
    reasoning_content: str  # 本轮推理内容

class VirtualFigureGraphState(
    MessagesState
):  # 继承自MessagesState，自动包含messages: Annotated[list[AnyMessage], add_messages]字段
    request: Request
    context_block: str  # 关系与画像上下文
    words_to_user: str  # 非常重要，所以单独放在state顶层
    recalled_facts_from_db: str  # 根据本轮消息召回的Knowledge、Event、ChatTopic、InteractionSignal、DerivedInsight
    recalled_facts_from_viking: List[dict]  # Viking 记忆库召回的记忆
    llm_output: LLMOutput
```

##### VirtualFigureGraph 图结构

```python
graph = StateGraph(
    state_schema=VirtualFigureGraphState,
    input_schema=VirtualFigureGraphInput,
    output_schema=VirtualFigureGraphOutput,
)
graph.add_node("nodeInitState", nodeInitState)
graph.add_node("nodeLoadPersona", nodeLoadPersona)
graph.add_node("nodeRecallFromDB", nodeRecallFromDB)
graph.add_node("nodeRecallFromViking", nodeRecallFromViking)
graph.add_node("nodeBuildMessage", nodeBuildMessage)
graph.add_node("nodeCallLLM", nodeCallLLM)

graph.add_edge(START, "nodeInitState")
# 四链路并行
graph.add_edge("nodeInitState", "nodeLoadPersona")
graph.add_edge("nodeInitState", "nodeRecallFromDB")
graph.add_edge("nodeInitState", "nodeRecallFromViking")
graph.add_edge("nodeInitState", "nodeBuildMessage")

# 汇聚
graph.add_edge(
    [
        "nodeLoadPersona",
        "nodeRecallFromDB",
        "nodeRecallFromViking",
        "nodeBuildMessage",
    ],
    "nodeCallLLM",
)
graph.add_edge("nodeCallLLM", END)
```

![可视化 VirtualFigureGraph](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_ef2b0b63b1.png?x-oss-process=image/resize,w_1000)

##### VirtualFigureGraph 上下文设计

在 VirtualFigureGraph 中，模型输入的上下文分为5个部分：

- 系统提示词，放在`SystemMessage`中
- 关系与画像上下文，从RelationChain中获取；若没有则执行ContextGraph重新计算并落库。放在`SystemMessage`中。
- 数据库召回的长期记忆，包括Event、ChatTopic、InteractionSignal。这些是用户明确添加的关于关系与画像的上下文信息，是可信的。放在`SystemMessage`中。
- Viking 记忆库召回的长期记忆。这些是基于用户和虚拟人交谈对话的内容，经过总结和抽取存在Viking远端的，是不可信的。放在`SystemMessage`中。
- 本轮收到的消息，放在`HumanMessage`中。

##### 推理内容reasoning_content的获取

到目前为止，我们调用**LLM**的方式全部是基于LangStack ChatOpenAI的API。直接`llm.ainvoke()`获取结构化的标准的LLM响应。

> OpenAI标准Chat API请求及响应参数可参考：[OpenAI Chat API 参数完整中文指南](https://cloud.tencent.com/developer/article/2565819)

::: warning
由于方舟的向量模型不支持，Embedding 模型并不是通过LangStack的API调用，而是使用方舟 SDK。这是模型调用的第二种方式。
:::

我们使用的LLM是doubao-seed-2-0-lite-260215和doubao-seed-2-0-mini-260215，都支持深度思考。在VirtualFigureGraph中，我们希望在最终模型返回时不仅拿到本轮要发送的消息，还能拿到思考推理内容reasoning_content。但我翻遍了`llm.ainvoke()` 的响应结构也没有找到这个字段。直到我看到了这样的内容......

![ChatOpenAI Integration](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_d72ac856d5.png)

而由于方舟模型在 LangStack 中并没有 provider-specific package 的支持，这就意味着通过 LangStack 调用方舟模型无法获取 reasoning_content。

看来我们又要转回方舟 SDK 了，方舟 SDK 自然支持直接获取 reasoning_content。参考[深度思考](https://www.volcengine.com/docs/82379/1449737)。

方舟有两种调用模型的API，一种是普遍而传统的Chat API，另一种是新的Responses API。二者的关系和差异可参考：[迁移至 Responses API](https://www.volcengine.com/docs/82379/1585128)。

项目基于LangStack工具链，我们在graph state中和模型交互的信息都是LangChain的标准信息结构`SystemMessage`, `HumanMessage`, `AIMessage`等。但既然在这个场景下我们需要切换到方舟 SDK进行invoke，自然我们需要把LangChain的信息结构转换为方舟的API的输入格式。于是我专门设计了一个转换方法，并支持了Chat API和Ark Responses API两种格式转换：

```python
# 【重要‼️】将 LangChain messages 转换为 Ark Responses API 格式
# 适配 Ark SDK
def langchain2OpenAIChatMessages(
    messages: List[BaseMessage], is_ark_responses_messages: bool = False
) -> List[Dict[str, Any]]:

    def _roleMap(message: BaseMessage) -> str:
        if isinstance(message, HumanMessage):
            return "user"
        elif isinstance(message, AIMessage):
            return "assistant"
        elif isinstance(message, SystemMessage):
            return "system"
        else:
            raise ValueError(f"Unsupported message type: {type(message)}")

    # 将不同格式统一为 Ark Responses API 格式
    def _normalizeBlock(
        block: Dict[str, Any], is_ark_responses_messages: bool
    ) -> Dict[str, Any]:
        block_type = block.get("type")
        # 文本统一
        if block_type in ("text", "input_text"):
            if is_ark_responses_messages:
                return {"type": "input_text", "text": block.get("text", "")}
            return {"type": "text", "text": block.get("text", "")}
        # 图片统一
        elif block_type in ("image_url", "input_image"):
            if is_ark_responses_messages:
                return {
                    "type": "input_image",
                    "image_url": block.get("image_url") or block.get("url"),
                }
            return {
                "type": "image_url",
                "image_url": block.get("image_url") or block.get("url", ""),
            }
        # 视频统一
        elif block_type in ("video_url", "input_video"):
            if is_ark_responses_messages:
                return {
                    "type": "input_video",
                    "video_url": block.get("video_url") or block.get("url"),
                }
            return {
                "type": "video_url",
                "video_url": block.get("video_url") or block.get("url", ""),
            }
        # 文档统一
        elif block_type in ("file_url", "input_file"):
            if is_ark_responses_messages:
                return {
                    "type": "input_file",
                    "file_url": block.get("file_url") or block.get("url"),
                }
            return {
                "type": "file_url",
                "file_url": block.get("file_url") or block.get("url", ""),
            }
        # 未知类型直接报错
        raise ValueError(f"Unsupported content block type: {block_type}")

    def _contentMap(
        content: Any, role: str, is_ark_responses_messages: bool
    ) -> List[Dict[str, Any]] | str:
        # system / assistant 为纯文本
        if role in ("system", "assistant"):
            return content

        # 字符串 → text block
        if isinstance(content, str):
            if is_ark_responses_messages:
                return [{"type": "input_text", "text": content}]
            return content

        # list → 多模态
        if isinstance(content, list):
            return [
                _normalizeBlock(item, is_ark_responses_messages) for item in content
            ]

        raise ValueError(f"Unsupported content type: {type(content)}")

    result = []

    for msg in messages:
        role = _roleMap(msg)
        result.append(
            {
                "role": role,
                "content": _contentMap(msg.content, role, is_ark_responses_messages),
            }
        )

    return result
```

随后，我又基于Ark Responses API专门封装了`arkAinvoke`方法，用来替换LangStack的`llm.ainvoke`：

```python
# 通过 Ark SDK ainvoke llm
# todo：暂不支持 ToolMessage
async def arkAinvoke(
    model: Literal["DOUBAO_2_0_LITE", "DOUBAO_2_0_MINI"],
    messages: List[BaseMessage],
    model_options: LLMOptions = {},
) -> ArkLLMResponse:
    model_name = os.getenv(model, "")
    assert model_name, f"required '{model}' for AI Agent!!!"

    # 全局单例
    _ark_client = arkClient()

    reasoning_effort = model_options.get("reasoning_effort", None)
    resp = await _ark_client.responses.create(
        model=model_name,
        input=langchain2OpenAIChatMessages(
            messages=messages, is_ark_responses_messages=True
        ),
        temperature=model_options.get("temperature", None),
        max_output_tokens=model_options.get("max_tokens", None),
        reasoning=(
            {
                "effort": reasoning_effort,
            }
            if reasoning_effort
            else None
        ),
        extra_body=model_options.get("extra_body", None),
    )

    output_chunks: List[str] = []
    reasoning_chunks: List[str] = []
    for item in getattr(resp, "output", None) or []:
        item_type = getattr(item, "type", None)
        if item_type == "message":
            for block in getattr(item, "content", None) or []:
                text = getattr(block, "text", None)
                if isinstance(text, str) and text:
                    output_chunks.append(text)
        elif item_type == "reasoning":
            for summary in getattr(item, "summary", None) or []:
                text = getattr(summary, "text", None)
                if isinstance(text, str) and text:
                    reasoning_chunks.append(text)

    output_text = "\n".join(output_chunks)
    reasoning_content = "\n".join(reasoning_chunks)

    return {
        "output": output_text,
        "reasoning_content": reasoning_content,
        "ai_message": AIMessage(
            content=output_text,
            id=str(getattr(resp, "id", "")) or None,
            response_metadata={
                "model": getattr(resp, "model", None),
                "status": getattr(resp, "status", None),
                "reasoning_content": reasoning_content or None,
            },
        ),
    }
```

下游VirtualFigureGraph的 node 进行消费就十分方便，reasoning_content也顺利获取。

```python
messages_to_send = [
    # 1. 系统提示词
    SystemMessage(
        content=(
            await getPrompt(
                os.getenv("VIRTUAL_FIGURE_SYSTEM_PROMPT"),
                {
                    "words_to_user": state["words_to_user"],
                    "current_timestamp": current_timestamp,
                },
            )
        )
    ),
    # 2. 关系与画像上下文
    SystemMessage(content=f"关系与画像上下文：\n{state['context_block']}"),
    # 3. DB召回的长期记忆（真实）
    SystemMessage(
        content=f"可能参考的召回的长期记忆：\n{state['recalled_facts_from_db']}"
    ),
    # 4. Viking召回的长期记忆（不可信）
    SystemMessage(
        content=f"可能参考的召回的长期记忆：\n{json.dumps(state['recalled_facts_from_viking'], ensure_ascii=False)}"
    ),
] + state["messages"]

resp = await arkAinvoke(
    model="DOUBAO_2_0_LITE",
    messages=messages_to_send,
    model_options={
        "temperature": 0.3,
        "reasoning_effort": "low",
    },
)
output = resp["output"]
reasoning_content = resp["reasoning_content"]
ai_message = resp["ai_message"]
```

#### Prompt 备份的教训

2026.3.22，Prompt Minder网站服务跪了。本工程中所有提示词都储存在Prompt Minder平台上，通过`getPrompt()`从远端实时拉取。遗憾的是，这些提示词既没有在本地备份，又没有做兜底。所以一时间本项目中涉及提示词的链路全部挂掉......

事故发生后我迅速在github中[PromptMinder 项目](https://github.com/aircrushin/promptMinder)寻找作者联系方式，是 Monash University 在读硕士......于是我赶快和他联系：

![Email](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_6d04fc5465.png?x-oss-process=image/resize,w_800)

两天后，3月24号，事故终于得到了解决。

这件事情告诉我们：使用不成熟的外部服务（Github就不必😂）一定要做好数据备份，最好设计兜底，不要100%相信，不要把命运交到别人手中......

#### 接入飞书 Bot

> 重中之重，革命性的一集

在项目初期，我就在考虑产品最终的产出最好是什么形式。不论是Web App还是移动端App，都意味着繁重的前端开发。

::: primary
近两年，AI Agent大行其道，RAG、MCP、Skills横空出世。最近几个月爆火的OpenClaw，直到最近我才空下来部署体验。它给我的使用体验是空前的，浅浅研究了它的架构之后，给了我的非常多高质量的ideas和启发。其中很大一部分可以在本项目中得到落地。

虽然有命令行的TUI，但OpenClaw具有巨大价值的特性之一在于可插拔 —— 它支持用户接入各大IM Platforms 作为Channel，如飞书、Discord、WhatsApp。随后用户只需要在日常使用的IM Platform上使用产品，既降低了用户的理解使用成本，又省去了传统前端开发的工作量。

> IM：即时通讯（Instant Messaging）是一个实时通信系统，允许两人或多人使用网络进行实时的文字消息传递以及语音与视频交流。
>
> 应用场景：用于个人或企业在网络环境下进行实时沟通，通过文字、语音或视频快速交流信息，提高沟通效率和协作体验。

![Chat Channels](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_289ba1d3a7.png?x-oss-process=image/resize,w_800)
:::

回到我们的项目，其中主链路Virtual Figure接受用户的输入消息，处理后返回虚拟人的回复消息。这个场景下即便不接入IM Platform，也需要单独构建IM的前端架构。那我们完全可以参考OpenClaw可插拔的特性，直接接入。

**飞书是首选**。

[飞书开放平台](https://open.larkoffice.com/app/) 中提供了非常丰富的应用能力，其中**机器人**能力正是我们需要的。它是与用户在聊天中交互的应用，它可以向用户或群组自动发送消息，响应用户的消息，并能进行群组管理（这个暂时不需要）。另外其支持的API和文档十分完善，在Python项目中通过SDK可以直接调用，且看我操作。

##### 飞书开放平台侧

- 创建一个企业自建应用，启用“机器人”能力
- 获取 app_id 和 app_secret
- 订阅接收消息（im.message.receive_v1）事件，使用基于 SDK 的长连接订阅
- 申请以应用的身份发消息（im:message:send_as_bot）权限
- 创建版本并发布

##### 代码侧

- 安装SDK `lark_oapi`，可参考文档[Python SDK 指南](https://open.larkoffice.com/document/server-side-sdk/python--sdk/preparations-before-development)和[Python SDK Demo](https://github.com/larksuite/oapi-sdk-python-demo).
- 基于 app_id 和 app_secret 鉴权，初始化larkClient
- 封装常用的IM API：`sendText()`、`sendImage()`、`sendFile()`等。
- 创建WebSocketServer，作为服务的唯一入口
- 通过`messageHandler()`将Virtual Figure等已有功能集成到WebSocketServer中
- 引入Menu和特定command，允许用户直接通过发送指令触发特定功能

为了适配用户发的`str`类型的消息和SDK event_handler接受的`P2ImMessageReceiveV1`类型的消息，我专门做了一层`messageAdapter()`依旧作为回调函数适配类型差异。

```python
event_handler = (
    lark.EventDispatcherHandler.builder("", "", lark.LogLevel.INFO)
    .register_p2_im_message_receive_v1(
        lambda data: messageAdapter(data, message_handler)
    )
    .build()
)
```

`messageHandler()`依旧采用**15s缓冲——批量处理——分条返回**的策略。接下来就是通过WebSocketServer向用户推送消息。值得注意的是，飞书SDK向用户推送消息需要一个id对用户进行标识。大致有以下三类id：

![三类用户标识id](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_42d6a4afe3.png?x-oss-process=image/resize,w_800)

我们这里采用open_id标识用户身份。我在数据库User表新开了一个字段`lark_open_id`，将本系统的用户和飞书绑定。至于如何获取open_id，可以参考[如何获取用户的 Open ID](https://open.larkoffice.com/document/faq/trouble-shooting/how-to-obtain-openid)。

后续会通过用户在HeartCompass中的手机号或者邮箱获取open_id来绑定飞书。这就要求用户在本系统中的手机号或者邮箱和飞书账号保持一致。

::: warning
这个链路和之前开发微信小程序时微信登录的鉴权颇有几分神似，回旋镖🪃！当时还专门写了一篇文档，详见 [微信小程序调用微信登录接口实现登录和鉴权的方案](https://charliebu.cn/articles/NzI4NzpDaGFybGllJ3NBcnRpY2xlczoxNzc0NzAxNzM4MjMy)。
:::

##### Menu 设计

在 OpenClaw 中，用户可以通过发送特殊的指令进行对话之外的操作，如`/new`指令用来开启新的对话session。受其启发，我们既然抛弃了前端，那自然也需要留一个接口让用户进行除了对话之外的操作和配置。于是我设计了Menu，包含了一系列`/`开头的指令，如下：

```python
menu = [
    {
        "hint": "/list_available_persons",
        "content": "查找可选对话对象 person_id",
        "regex": r"/list_available_persons",
        "command": listAvailablePersons,
    },
    {
        "hint": "/<person_id>",
        "content": "切换当前对话对象",
        "regex": r"/(\d+)",
        "command": switchRelationChain,
    },
    {
        "hint": "/clear_current_person",
        "content": "清除当前对话对象",
        "regex": r"/clear_current_person",
        "command": clearCurrentRelationChain,
    },
    # todo：提高优先级，通过单独agent操作落库
    {
        "hint": "/add-context-by-narrative:<person_id>\n<narrative>",
        "content": "通过自然语言添加上下文",
        "regex": r"/add-context-by-narrative:(\d+)\n(.*)",
        "command": addContextByNarrative,
    },
    # todo：降低优先级，很少需要
    {
        "hint": "/add-context-by-screenshot:\n<screenshot>\n<additional_context>\n<his_name_or_position_on_screenshot>",
        "content": "通过聊天记录截图添加上下文",
        "regex": r"/add-context-by-screenshot:\n(.*)\n(.*)\n(.*)",
        "command": addContextByScreenshot,
    },
    {
        "hint": "/flush-context:<person_id>",
        "content": "刷新关系与画像上下文（添加上下文后请刷新）",
        "regex": r"/flush-context:(\d+)",
        "command": flushContext,
    },
    {
        "hint": "/menu",
        "content": "显示菜单",
        "regex": r"/menu",
        "command": showMenu,
    },
]
```

`messageHandler()`收到用户消息后，先通过正则判断是否是已有的指令，提取规定的参数。然后直接绕过VirtualFigureGraph链路，直接触发对应的command函数。

#### 接下来的 TODOs

首先请观赏下到目前为止的成果：

![Demo](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/20260327004123_rec__741092ca7b.gif)

从现在VirtualFigureGraph的架构来讲，我把上下文分成5个部分（详见前文 VirtualFigureGraph 上下文设计）。在记忆部分，数据库中存放的是用户根据当前人物的 & 这段关系中的事实填充的**可信的**上下文；而仅仅有真实的可信上下文显然不足。在用户和虚拟人对话过程中，形成的非真实（不是现实中）的记忆也是重要的。否则虚拟人就会像傻子一样对前面对话的内容一无所知......

这些**不可信**的记忆我希望按照两种途径进入上下文 —— 一种LangChain官方支持的短期记忆存储checkpoint（只包含双方的对话记录，HumanMessage和AIMessage）在内存`InMemorySaver()`，这些短期记忆自然会在进程重启后丢失，进程不重启也会大量慢慢膨胀，容易塞满上下文窗口，所以需要不时trim；另种是将两人的对话传入远端记忆库，经过总结、提炼，形成长期记忆落库。

对于远端记忆库，一开始我看到刚刚推出的火山Mem0记忆库，认定是个不错的选择。
