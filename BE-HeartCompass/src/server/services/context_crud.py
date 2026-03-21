import logging
from sqlalchemy.orm import Session

from src.database.models import RelationChain, Event

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
