# 模式2：StateGraph 工作流
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
import pprint
import json
import asyncio

from database.database import session
from database.models import (
    User,
    Crush,
    RelationChain,
    ChainStageHistory,
    Knowledge,
    Event,
    ChatTopic,
    InteractionSignal,
    DerivedInsight,
)
from database.enums import RelationStage
from server.services.ai import generateRecallQueriesFromScreenshots
from .state import LLMOutput, GraphState
from ..llm import prepareLLM
from ..prompt import getPrompt

# 全局单例
_graph_instance: CompiledStateGraph | None = None
_graph_lock = asyncio.Lock()


async def nodeLoadEntity(state: GraphState) -> dict:
    with session() as db:
        user = db.get(User, state["request"]["user_id"])
        relation_chain = db.get(RelationChain, state["request"]["relation_chain_id"])
        crush: Crush = relation_chain.crush
        stage_histories = (
            db.query(ChainStageHistory)
            .filter(ChainStageHistory.relation_chain_id == relation_chain.id)
            .order_by(ChainStageHistory.created_at.desc())
            .all()
        )
        return {
            "entities": {
                "user": user,
                "crush": crush,
                "relation_chain": relation_chain,
                "stage_histories": stage_histories,
            }
        }


async def nodeBuildCrushProfileContext(state: GraphState) -> dict:
    crush = state["entities"].get("crush")
    crush_profile = {}
    crush_mbti = None
    if crush is not None:
        crush_mbti = crush.mbti.value if crush.mbti else None

        def _setIfValue(
            key: str, value: str | list | dict | None, chinese_key: str | None = None
        ):
            if value is None:
                return
            if isinstance(value, str) and not value.strip():
                return
            if (isinstance(value, list) or isinstance(value, dict)) and len(value) == 0:
                return
            crush_profile[chinese_key or key] = value

        _setIfValue("name", crush.name, "姓名")
        _setIfValue("gender", crush.gender.value if crush.gender else None, "性别")
        _setIfValue("mbti", crush.mbti.value if crush.mbti else None, "MBTI 类型")
        _setIfValue("birthday", crush.birthday, "生日")
        _setIfValue("occupation", crush.occupation, "职业")
        _setIfValue("education", crush.education, "教育背景")
        _setIfValue("residence", crush.residence, "常住地")
        _setIfValue("hometown", crush.hometown, "家乡")
        _setIfValue("communication_style", crush.communication_style, "交流风格")
        _setIfValue("personality_tags", crush.personality_tags, "性格")
        _setIfValue("likes", crush.likes, "喜好")
        _setIfValue("dislikes", crush.dislikes, "不喜欢")
        _setIfValue("boundaries", crush.boundaries, "个人边界")
        _setIfValue("traits", crush.traits, "个人特点")
        _setIfValue("lifestyle_tags", crush.lifestyle_tags, "生活方式")
        _setIfValue("values", crush.values, "价值观")
        _setIfValue("appearance_tags", crush.appearance_tags, "外在特征")
        _setIfValue("other_info", crush.other_info, "其他信息")
    return {
        "crush_profile_context": {
            "crush_mbti": crush_mbti,
            "crush_profile": crush_profile,
        }
    }


async def nodeBuildRecallQueries(state: GraphState) -> dict:
    screenshot_urls = state["request"].get("conversation_screenshots")
    additional_context = state["request"].get("additional_context")
    is_self = (
        state["entities"].get("relation_chain").current_stage == RelationStage.SELF
        if state["entities"].get("relation_chain")
        else False
    )
    try:
        recall_queries = json.loads(
            await generateRecallQueriesFromScreenshots(
                screenshot_urls=screenshot_urls,
                additional_context=additional_context,
                is_self=is_self,
            )
        )
        knowledge_query = recall_queries.get("knowledge_query")
        non_knowledge_query = recall_queries.get("non_knowledge_query")
    except json.JSONDecodeError:
        recall_queries = {}
    return {
        "recall_queries": {
            "knowledge_query": knowledge_query,
            "non_knowledge_query": non_knowledge_query,
            "knowledge_vector": [],
            "non_knowledge_vector": [],
        },
    }


async def node4(state: GraphState) -> dict:
    pass


async def node5(state: GraphState) -> dict:
    pass


async def node6(state: GraphState) -> dict:
    pass


async def node7(state: GraphState) -> dict:
    pass


async def node8(state: GraphState) -> dict:
    pprint.pprint(state)
    return {
        "reply_candidates": state["llm_output"]["reply_candidates"],
        "reasoning": state["llm_output"]["reasoning"],
        "evidence": state["llm_output"]["evidence"],
    }


async def getStateGraph() -> CompiledStateGraph:
    global _graph_instance
    if _graph_instance is not None:
        return _graph_instance
    # 双检查锁模式，确保线程安全
    async with _graph_lock:
        if _graph_instance is not None:
            return _graph_instance
        # todo: 放到节点中
        # system_prompt = await getPrompt(os.getenv("SYSTEM_PROMPT"))
        # llm: ChatOpenAI = prepareLLM()
        graph = StateGraph(
            state_schema=GraphState, input_schema=GraphState, output_schema=LLMOutput
        )
        graph.add_node("nodeLoadEntity", nodeLoadEntity)
        graph.add_node("nodeBuildCrushProfileContext", nodeBuildCrushProfileContext)
        graph.add_node("nodeBuildRecallQueries", nodeBuildRecallQueries)
        graph.add_node("node4", node4)
        graph.add_node("node5", node5)
        graph.add_node("node6", node6)
        graph.add_node("node7", node7)
        graph.add_node("node8", node8)

        graph.set_entry_point("nodeLoadEntity")
        graph.add_edge("nodeLoadEntity", "nodeBuildCrushProfileContext")
        graph.add_edge("nodeBuildCrushProfileContext", "nodeBuildRecallQueries")
        graph.add_edge("nodeBuildRecallQueries", "node4")
        graph.add_edge("node4", "node5")
        graph.add_edge("node5", "node6")
        graph.add_edge("node6", "node7")
        graph.add_edge("node7", "node8")
        graph.add_edge("node8", END)

        _graph_instance = graph.compile()
        return _graph_instance
