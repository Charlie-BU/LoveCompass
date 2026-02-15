def test():
    with session() as db:
        charlie = db.query(User).filter(User.username == "Charlie").first()
        charlie.personality_tags = ["Optimistic", "Creative"]
        db.commit()
        print(charlie.toJson())


if __name__ == "__main__":
    import sys
    from pathlib import Path

    if __package__ is None or __package__ == "":
        project_root = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(project_root))

    from database.database import session
    from database.models import User

    test()
