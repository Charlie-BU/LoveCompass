import logging
from typing import Annotated
from langchain_core.tools import tool

from src.database.database import session
from src.database.models import RelationChain

logger = logging.getLogger(__name__)


@tool
def useKnowledge(relation_chain_id: Annotated[int, "Relation chain id"]) -> str:
    """Use relevant knowledge from relation chain"""
    logger.info(f"useKnowledge Tool called with relation_chain_id: {relation_chain_id}")
    with session() as db:
        relation_chain = db.get(RelationChain, relation_chain_id)
        if relation_chain is None:
            logger.error(f"Relation chain {relation_chain_id} not found")
            return ""
        return relation_chain.relevant_knowledge
