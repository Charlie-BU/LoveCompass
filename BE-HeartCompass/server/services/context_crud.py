from sqlalchemy.orm import Session

from database.models import Event


async def ccDeleteEvent(db: Session, id: int) -> dict:
    event = db.query(Event).filter(Event.id == id).first()
    if not event:
        return {
            "status": -1,
            "message": "Event not found",
        }
    db.delete(event)
    db.commit()
    return {
        "status": 200,
        "message": "Event deleted",
    }