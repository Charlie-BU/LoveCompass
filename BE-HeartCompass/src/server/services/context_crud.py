import logging
from sqlalchemy.orm import Session

from src.database.enums import UserGender, RelationStage, MBTI
from src.database.models import RelationChain, Event, Crush, User

logger = logging.getLogger(__name__)


async def ccDeleteEvent(db: Session, user_id: int, event_id: int) -> dict:
    try:
        event = db.get(Event, event_id)
        if not event:
            return {
                "status": -1,
                "message": "Event not found",
            }
        if event.relation_chain.user_id != user_id:
            return {
                "status": -2,
                "message": "You are not authorized to delete this event",
            }
        if not event.is_active:
            return {
                "status": -3,
                "message": "Event is not active",
            }
        event.is_active = False
        db.commit()
        return {
            "status": 200,
            "message": "Event deleted",
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting event {event_id}: {e}")
        return {
            "status": -4,
            "message": "Error deleting event",
        }


async def ccHardDeleteEvent(db: Session, user_id: int, event_id: int) -> dict:
    try:
        event = db.get(Event, event_id)
        if not event:
            return {
                "status": -1,
                "message": "Event not found",
            }
        if event.relation_chain.user_id != user_id:
            return {
                "status": -2,
                "message": "You are not authorized to delete this event",
            }

        db.delete(event)
        db.commit()
        return {
            "status": 200,
            "message": "Event hard deleted",
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error hard deleting event {event_id}: {e}")
        return {
            "status": -4,
            "message": "Error hard deleting event",
        }


async def ccGetEventById(db: Session, user_id: int, event_id: int) -> dict:
    event = db.get(Event, event_id)
    if not event:
        return {
            "status": -1,
            "message": "Event not found",
        }
    if event.relation_chain.user_id != user_id:
        return {
            "status": -2,
            "message": "You are not authorized to get this event",
        }
    if not event.is_active:
        return {
            "status": -3,
            "message": "Event has been deleted",
        }
    return {
        "status": 200,
        "message": "Get event success",
        "event": event.toJson(),
    }


async def ccGetEventsByRelationChainId(
    db: Session, user_id: int, relation_chain_id: int, page_size: int, current_page: int
) -> dict:
    relation_chain = db.get(RelationChain, relation_chain_id)
    if not relation_chain:
        return {
            "status": -1,
            "message": "Relation chain not found",
        }
    if relation_chain.user_id != user_id:
        return {
            "status": -2,
            "message": "You are not authorized to get events in this relation chain",
        }
    query = (
        db.query(Event)
        .filter(Event.relation_chain_id == relation_chain_id, Event.is_active == True)
        .order_by(Event.created_at.desc())
    )
    events = query.limit(page_size).offset((current_page - 1) * page_size).all()
    return {
        "status": 200,
        "message": "Get events success",
        "total": query.count(),
        "events": [event.toJson() for event in events],
    }


async def ccCreateCrush(
    db: Session,
    user_id: int,
    crush_name: str,
    gender: UserGender,
    mbti: MBTI,
) -> dict:
    try:
        new_crush = Crush(
            creator_id=user_id,
            name=crush_name,
            gender=gender,
            mbti=mbti,
        )
        db.add(new_crush)
        db.commit()
        return {
            "status": 200,
            "message": "Crush created",
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create crush for user {user_id}: {e}")
        return {"status": -1, "message": "Internal Database Error"}


async def ccCreateRelationChain(
    db: Session, user_id: int, crush_id: int, stage: RelationStage
) -> dict:
    try:
        crush = db.get(Crush, crush_id)
        if not crush:
            return {"status": -1, "message": "Crush not found"}

        if crush.creator_id != user_id:
            return {
                "status": -2,
                "message": "Permission denied: This is not your crush",
            }

        existing_chain_lenth = (
            db.query(RelationChain).filter(RelationChain.crush_id == crush_id).count()
        )
        if existing_chain_lenth > 0:
            return {"status": -3, "message": "Crush ID conflict: already bound"}
        new_relation_chain = RelationChain(
            user_id=user_id,
            crush_id=crush_id,
            current_stage=stage,
            is_active=True,
        )
        db.add(new_relation_chain)
        db.commit()
        return {
            "status": 200,
            "message": "Relation chain created",
        }

    except Exception as e:
        db.rollback()
        logger.error(
            f"Failed to create relation for user {user_id} and crush {crush_id}: {e}"
        )
        return {"status": -4, "message": "Internal Database Error"}


async def ccDeleteCrush(db: Session, user_id: int, crush_id: int) -> dict:
    try:
        crush = db.get(Crush, crush_id)
        if not crush:
            return {"status": -1, "message": "Crush not found"}
        if crush.creator_id != user_id:
            return {
                "status": -2,
                "message": "Permission denied: This is not your crush",
            }
        # TODO:添加is_active后改成软删
        db.delete(crush)
        db.commit()
        return {"status": 200, "message": "Crush deleted"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete crush {crush_id}:{e}")
        return {"status": -3, "message": "Internal Database Error"}


async def ccDeleteRelationChain(
    db: Session, user_id: int, relation_chain_id: int
) -> dict:
    try:
        relation_chain = db.get(RelationChain, relation_chain_id)
        if not relation_chain:
            return {"status": -1, "message": "RelationChain not found"}
        if relation_chain.user_id != user_id:
            return {
                "status": -2,
                "message": "Permission denied: This is not your relationChain",
            }
        if not relation_chain.is_active:
            return {"status": -3, "message": "RelationChain has been deleted"}
        relation_chain.is_active = False
        db.commit()
        return {"status": 200, "message": "RelationChain deleted"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete relationChain {relation_chain_id}:{e}")
        return {"status": -4, "message": "Internal Database Error"}


async def ccGetCrushById(db: Session, user_id: int, crush_id: int) -> dict:
    crush = db.get(Crush, crush_id)
    if not crush:
        return {"status": -1, "message": "Crush not found"}
    if crush.creator_id != user_id:
        return {"status": -2, "message": "Permission denied: This is not your crush"}
    # TODO: 待添加 is_active 字段后，取消下方注释
    # if not crush.is_active:
    #     return {"status": -1, "message": "Crush deleted"}
    return {"status": 200, "message": "Get crush success", "crush": crush.toJson()}


async def ccGetCrushByUser(
    db: Session, user_id: int, page_size: int, current_page: int
) -> dict:
    # TODO:Crush.is_active=True
    query = (
        db.query(Crush)
        .filter(Crush.creator_id == user_id)
        .order_by(Crush.created_at.desc())
    )
    # TODO:如果crush未创建，怎么防御
    crush = query.limit(page_size).offset((current_page - 1) * page_size).all()
    return {
        "status": 200,
        "message": "Get crush success",
        "total": query.count(),
        "crushes": [crush.toJson() for crush in crush],
    }


async def ccGetRelationChainById(
    db: Session, user_id: int, relation_chain_id: int
) -> dict:
    relation_chain = db.get(RelationChain, relation_chain_id)
    if not relation_chain:
        return {"status": -1, "message": "RelationChain not found"}
    if relation_chain.user_id != user_id:
        return {
            "status": -2,
            "message": "Permission denied: This is not your relationChain",
        }
    if not relation_chain.is_active:
        return {"status": -3, "message": "RelationChain has been deleted"}
    return {
        "status": 200,
        "message": "Get relationChain success",
        "relation_chain": relation_chain.toJson(),
        "crush_name": relation_chain.crush.name,
    }


async def ccGetRelationChainByUser(
    db: Session, user_id: int, page_size: int, current_page: int
) -> dict:
    query = (
        db.query(RelationChain)
        .filter(RelationChain.user_id == user_id)
        .order_by(RelationChain.created_at.desc())
    )
    relation_chain = query.limit(page_size).offset((current_page - 1) * page_size).all()
    # TODO:如果relation_chain未创建，怎么防御
    return {
        "status": 200,
        "message": "Get relationChain success",
        "total": query.count(),
        "relation_chains": [
            relation_chain.toJson() for relation_chain in relation_chain
        ],
        # TODO       "crush_name":
    }


async def ccUpdateCrush(db: Session, user_id: int, crush_id: int, body: dict) -> dict:
    try:
        crush = db.get(Crush, crush_id)
        if not crush:
            return {"status": -1, "message": "Crush not found"}
        if crush.creator_id != user_id:
            return {
                "status": -2,
                "message": "Permission denied: This is not your crush",
            }
        # TODO: 待添加 is_active 字段后，取消下方注释
        # if not crush.is_active:
        #    return {"status":-3,"message":"Crush has been deleted"}
        editable_columns = ["name", "mbti", "gender"]
        update_count = 0
        for key in body:
            if key in editable_columns:
                new_value = body[key]
                setattr(crush, key, new_value)
                update_count += 1
        if update_count > 0:
            db.commit()
        return {"status": 200, "message": "Crush updated"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update crush {crush_id}:{e}")
        return {"status": -4, "message": "Internal Database Error"}
