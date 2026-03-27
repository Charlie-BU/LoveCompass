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

![graph 目录架构重构](https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_27d6e6fa0a.png?x-oss-process=image/resize,w_800)

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


### TENTH ENTRY - 2026.03.24-27

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

!(可视化 VirtualFigureGraph)[https://charlie-assets.oss-rg-china-mainland.aliyuncs.com/images/article/image_ef2b0b63b1.png?x-oss-process=image/resize,w_1000]

在 VirtualFigureGraph 中，模型输入的上下文分为5个部分：

- 系统提示词，放在`SystemMessage`中
- 关系与画像上下文，从RelationChain中获取；若没有则执行ContextGraph重新计算并落库。放在`SystemMessage`中。
- 数据库召回的长期记忆，包括Event、ChatTopic、InteractionSignal。这些是用户明确添加的关于关系与画像的上下文信息，是可信的。放在`SystemMessage`中。
- Viking 记忆库召回的长期记忆。这些是基于用户和虚拟人交谈对话的内容，经过总结和抽取存在Viking远端的，是不可信的。放在`SystemMessage`中。
- 本轮收到的消息，放在`HumanMessage`中。

##### 推理内容reasoning_content的获取



#### Prompt 备份的教训

#### 接入飞书 Bot

#### 接下来的TODOs
