from database.database import session
from database.models import RelationChain
from agent.graph.ContextGraph import getContextGraph
from agent.graph.state import (
    ContextGraphState,
    initContextGraphState,
)


async def vfRecalculateContextBlock(
    user_id: int, relation_chain_id: int, narrative: str
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
    context_graph = await getContextGraph()
    initial_state = initContextGraphState(
        {
            "user_id": user_id,
            "relation_chain_id": int(relation_chain_id),
            "narrative": narrative,
        }
    )
    context_state: ContextGraphState = await context_graph.ainvoke(initial_state)
    context_block = context_state["context_block"]
    with session() as db:
        relation_chain = db.get(RelationChain, int(relation_chain_id))
        relation_chain.context_block = context_block
        db.commit()

    return {
        "status": 200,
        "message": "Success",
        "context_block": context_block,
    }
