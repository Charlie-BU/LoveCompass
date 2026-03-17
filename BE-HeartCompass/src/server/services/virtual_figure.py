import logging

from src.database.database import session
from src.database.models import RelationChain
from src.agent.graph.ContextGraph.graph import getContextGraph
from src.agent.graph.ContextGraph.state import (
    ContextGraphOutput,
    initContextGraphState,
)

logger = logging.getLogger(__name__)


async def vfRecalculateContextBlock(
    user_id: int, relation_chain_id: int, narrative: str | None
):
    # 鉴权
    with session() as db:
        relation_chain = db.get(RelationChain, int(relation_chain_id))
        if relation_chain is None:
            return {
                "status": -1,
                "message": "Relation chain not found",
            }
        if relation_chain.user_id != user_id:
            return {
                "status": -2,
                "message": "You are not in this relation chain",
            }
    # 调用图
    context_graph = getContextGraph()
    initial_state = initContextGraphState(
        {
            "user_id": user_id,
            "relation_chain_id": int(relation_chain_id),
            "type": (
                "narrative"
                if narrative is not None and narrative.strip() != ""
                else "no_material"
            ),
            "for_virtual_figure": True,
            "narrative": narrative,
        }
    )
    try:
        context: ContextGraphOutput = await context_graph.ainvoke(initial_state)
    except Exception as e:
        logger.exception(f"Failed to run ContextGraph: {e}")
        return {
            "status": -3,
            "message": "Failed to recalculate context block",
        }

    context_block = context.get("context_block")
    relevant_knowledge = context.get("relevant_knowledge")
    
    with session() as db:
        relation_chain = db.get(RelationChain, int(relation_chain_id))
        if relation_chain is None:
            return {
                "status": -1,
                "message": "Relation chain not found",
            }
        relation_chain.context_block = context_block
        relation_chain.relevant_knowledge = relevant_knowledge
        db.commit()

    return {
        "status": 200,
        "message": "Success",
        "context_block": context_block,
        "relevant_knowledge": relevant_knowledge,
    }
