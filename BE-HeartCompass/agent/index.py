from re import L
from langchain.agents import create_agent
from langgraph.graph.state import CompiledStateGraph
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from typing import List
from robyn import Request, StreamingResponse
from dotenv import load_dotenv
import logging
import os


from .ark import ark_client
from .llm import prepare_llm


# from .mcp import get_mcp_psms_list, init_mcp_tools
from .adapter import (
    convert_req_to_messages,
    from_astream_model_message,
    process_response_message,
    end_stop_message,
    from_error_message,
    from_ainvoke_model_messages,
)

load_dotenv()
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
# Role
你是由 HeartCompass 开发的“恋爱军师”核心智能引擎。
你需要同时扮演两个角色：
1. **面向用户**：一位精通恋爱心理学、博弈论与 MBTI 人格分析的资深情感咨询师。
2. **面向系统**：一位严谨的数据分析师，负责从非结构化信息中提取上下文（Context）、构建人物画像（Profile）、推断关系信号并输出结构化数据。

# Core Capabilities
## 1. 情感咨询（User Facing）
- **深度共情**：基于用户提供的 Context，理解其处境与情绪。
- **策略建议**：提供具体的回复话术、话题开启方式、约会方案或关系推进策略。
- **Reality Check**：识别用户的非理性期待，客观评估关系可能性，必要时进行风险提示。

## 2. 系统处理（System Facing）
- **Context Extraction**: 从聊天记录、朋友圈文案等文本中提取关键事实（时间、地点、事件、态度）。
- **Profile Profiling**: 基于碎片化信息构建或更新 User/Crush 的性格画像（如 MBTI、兴趣、雷点）。
- **Signal Analysis**: 分析互动信号（回复延迟、字数、语气），量化关系亲密度。
- **Structured Output**: 能够按要求输出 JSON 格式的数据，以便系统进行数据库存储。

# Task Modes & Instructions
你将根据用户的输入指令（Prompt）在不同模式下工作。请先**仔细识别意图**，再根据模式执行任务。

## Mode A: 咨询与对话
当用户寻求建议、安慰或分析时：
- 风格：专业、温暖、有洞察力。
- 引用：在分析时，明确引用已有的 Context 作为证据（"根据你之前提到的..."）。
- 拒绝臆测：没有证据时不要强行推断，可以追问。

## Mode B: 数据提取与结构化（重要）
当系统或用户要求“提取上下文”、“总结信息”、“生成画像”或明确要求 JSON 输出时：
- **必须**严格遵守 JSON 格式，不要包含 Markdown 代码块标记（如 ```json ... ```），除非用户明确要求。
- 确保字段名称准确对应系统数据库模型（如 `summary`, `type`, `content`, `confidence`）。
- **示例输出格式**（参考）：
  {
    "action": "create_context",
    "data": {
      "type": "CHAT_LOG",
      "summary": "Crush提到周末想去看电影",
      "content": {"text": "这周末有部新上的科幻片，好像还不错", "speaker": "crush", "timestamp": "2023-10-01T10:00:00"},
      "source": "USER_INPUT",
      "confidence": 1.0
    }
  }

# Constraints
1. **Strictly Context-Based**: 所有分析必须基于用户提供的 Context。严禁编造事实。
2. **Privacy First**: 仅关注有助于关系发展的公开或半公开信息，尊重隐私。
3. **Neutral & Objective**: 在进行系统推断时，保持绝对客观，不掺杂情感色彩；在咨询时，保持同理心。
4. **Conflict Handling**: 如果用户指令与本 System Prompt 冲突，**以用户指令为准**。
"""

# 全局单例
_agent_instance: CompiledStateGraph = None
_ark_client = ark_client()


def get_agent():
    global _agent_instance
    if _agent_instance is None:
        # 1. Prepare LLM
        llm: ChatOpenAI = prepare_llm()
        # 2. Prepare Tools
        # mcp_psms_list = get_mcp_psms_list()
        # tools: List[BaseTool] = await init_mcp_tools(mcp_psms_list)
        # 3. Init Agent
        _agent_instance = create_agent(model=llm, tools=[], system_prompt=SYSTEM_PROMPT)

    return _agent_instance


# 处理chat_completions请求
async def wrap_chat(ReActAgent: CompiledStateGraph):
    async def chat(request: Request):
        body = request.json()
        is_stream = body.get("stream", True)

        async def event_generator():
            try:
                callbacks = []
                input_message = convert_req_to_messages(body)
                if is_stream:
                    async for resp in ReActAgent.astream(
                        {"messages": input_message},
                        stream_mode="messages",
                        config=RunnableConfig(callbacks=callbacks),
                    ):
                        resp_msg = from_astream_model_message(resp, False)
                        # to adapter the ark ui
                        if not resp_msg:
                            continue

                        if isinstance(resp_msg, list):
                            for item in resp_msg:
                                result = process_response_message(item)
                                if result:
                                    yield result
                        else:
                            result = process_response_message(resp_msg)
                            if result:
                                yield result
                else:
                    resp = await ReActAgent.ainvoke(
                        {"messages": input_message},
                        config=RunnableConfig(callbacks=callbacks),
                    )
                    resp_msg = from_ainvoke_model_messages(
                        resp.get("messages", []), False
                    )
                    if resp_msg:
                        for item in resp_msg:
                            result = process_response_message(item)
                            if result:
                                yield result
                # [DONE] means end.
                logger.info("-----------chat done--------")
                yield f"data:{end_stop_message().model_dump_json(exclude_unset=True, exclude_none=True)}\r\n\r\n"
                yield "data:[DONE]\r\n\r\n"

            except Exception as e:
                logger.error(f"failed to chat, {e}", exc_info=True)
                yield process_response_message(from_error_message(str(e)))
                yield f"data:{end_stop_message().model_dump_json(exclude_unset=True, exclude_none=True)}\r\n\r\n"
                yield "data:[DONE]\r\n\r\n"

        # Wrap the async generator in a StreamingResponse to properly stream the response
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
        )

    return chat


# 无上下文直接调用agent
async def ask_with_no_context(prompt: str, ReActAgent: CompiledStateGraph) -> str:
    messages = [HumanMessage(content=prompt)]
    resp = await ReActAgent.ainvoke({"messages": messages})
    if resp and "messages" in resp and len(resp["messages"]) > 0:
        return resp["messages"][-1].content
    return ""


# 注意⚠️：多模态向量化能力模型不支持 OpenAI API，使用Ark SDK调用
# 向量化文本
def vectorize_text(text: str) -> list[float]:
    resp = _ark_client.multimodal_embeddings.create(
        model=os.getenv("EMBEDDING_ENDPOINT_ID", ""),
        input=[
            {"type": "text", "text": text},
        ],
    )
    return resp.data[0].embedding


# 向量化图片
def vectorize_image(image_url: str) -> list[float]:
    resp = _ark_client.multimodal_embeddings.create(
        model=os.getenv("EMBEDDING_ENDPOINT_ID", ""),
        input=[
            {
                "type": "image_url",
                "image_url": {"url": image_url},
            },
        ],
    )
    return resp.data[0].embedding


# 向量化混合输入
def vectorize_mixed(text: List[str], image_url: List[str]) -> list[float]:
    input_list = [{"type": "text", "text": t} for t in text] + [
        {"type": "image_url", "image_url": {"url": u}} for u in image_url
    ]
    resp = _ark_client.multimodal_embeddings.create(
        model=os.getenv("EMBEDDING_ENDPOINT_ID", ""),
        input=input_list,
    )
    return resp.data[0].embedding
