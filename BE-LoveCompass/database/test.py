def modify_user():
    with session() as db:
        charlie = db.query(User).filter(User.username == "Charlie").first()
        charlie.personality_tags = ["Optimistic", "Creative"]
        db.commit()
        print(charlie.toJson())


async def add_mbti_to_knowledge():
    # Calculate path to mbti.json
    project_root = Path(__file__).resolve().parent.parent
    json_path = project_root / "mbti.json"

    if not json_path.exists():
        print(f"File not found: {json_path}")
        return

    print(f"Reading MBTI data from {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        mbti_list = json.load(f)

    with session() as db:
        for item in mbti_list:
            mbti_type = item.get("mbti", "Unknown")
            print(f"Processing {mbti_type}...")

            # Convert dictionary to JSON string
            content = json.dumps(item, ensure_ascii=False)

            # Add to knowledge base
            try:
                result = await contextAddKnowledge(db=db, content=content, weight=1.0)
                print(f"Result for {mbti_type}: {result}")
            except Exception as e:
                print(f"Failed to add {mbti_type}: {e}")


if __name__ == "__main__":
    import asyncio
    import sys
    import json
    from pathlib import Path

    if __package__ is None or __package__ == "":
        project_root = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(project_root))

    from server.services.context import contextAddKnowledge
    from database.database import session
    from database.models import User

    # asyncio.run(add_mbti_to_knowledge())
