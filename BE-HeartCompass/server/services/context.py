import json
import logging
from typing import List
from sqlalchemy.orm import Session

from .ai import (
    extractContextFromScreenshots,
    extractKnowledge,
    extractContextFromNaturalLanguage,
)
from .embedding import createOrUpdateEmbedding
from database.models import RelationChain, Knowledge, Event, ChatTopic
from database.enums import parseEnum, Attitude, ChatChannel
from utils import cleanList

logger = logging.getLogger(__name__)


async def contextAddKnowledge(
    db: Session,
    content: str,
    with_embedding: bool,
) -> dict:
    try:
        knowledges = json.loads(await extractKnowledge(content))
    except Exception as e:
        return {"status": -1, "message": f"Failed to extract knowledge: {e}"}

    if not isinstance(knowledges, list):
        return {"status": -1, "message": "Failed to extract knowledge: invalid format"}

    logger.info(f"Extracted knowledge: \n{json.dumps(knowledges, indent=4)}")

    if len(knowledges) == 0:
        return {
            "status": -2,
            "message": "No knowledge extracted",
        }

    knowledge_items: list[Knowledge] = []
    try:
        transaction_ctx = db.begin_nested() if db.in_transaction() else db.begin()
        with transaction_ctx:
            for idx, item in enumerate(knowledges):
                if not isinstance(item, dict):
                    return {
                        "status": -3,
                        "message": f"Invalid knowledge item at index {idx}",
                    }
                item_content = item.get("content")
                item_summary = item.get("summary")
                item_weight = item.get("weight")
                if not isinstance(item_content, str) or item_content.strip() == "":
                    return {
                        "status": -4,
                        "message": f"Invalid content at index {idx}",
                    }
                if item_summary is not None and not isinstance(item_summary, str):
                    return {
                        "status": -5,
                        "message": f"Invalid summary at index {idx}",
                    }
                if not isinstance(item_weight, (int, float)) or not (
                    0 <= float(item_weight) <= 1
                ):
                    return {
                        "status": -6,
                        "message": f"Invalid weight at index {idx}",
                    }
                knowledge = Knowledge(
                    content=item_content,
                    weight=float(item_weight),
                    summary=item_summary,
                )
                db.add(knowledge)
                knowledge_items.append(knowledge)
            db.flush()
    except Exception as e:
        return {"status": -7, "message": f"Error saving knowledge: {e}"}

    for knowledge in knowledge_items:
        db.refresh(knowledge)

    embedding_result = []
    if with_embedding:
        for knowledge in knowledge_items:
            embedding_result.append(
                await createOrUpdateEmbedding(
                    db=db, from_where="knowledge", knowledge=knowledge
                )
            )

    return {
        "status": 200,
        "message": "Knowledge added",
        "count": len(knowledge_items),
        "knowledge_ids": [item.id for item in knowledge_items],
        "embedding": embedding_result,
    }


async def contextAddContextByNaturalLanguage(
    db: Session,
    relation_chain_id: int,
    content: str,
    with_embedding: bool,
) -> dict:
    relation_chain = db.get(RelationChain, relation_chain_id)
    if relation_chain is None:
        return {"status": -1, "message": "Relation chain not found"}
    if not content or content.strip() == "":
        return {"status": -2, "message": "Content is empty"}

    try:
        normalized_context = json.loads(
            await extractContextFromNaturalLanguage(content)
        )
    except json.JSONDecodeError:
        return {"status": -3, "message": "Failed to normalize context"}

    if not isinstance(normalized_context, dict):
        return {"status": -3, "message": "Failed to normalize context"}

    crush_profile = normalized_context.get("crush_profile")
    event = normalized_context.get("event")
    if crush_profile is None and event is None:
        return {"status": -4, "message": "No valid context found"}

    if crush_profile is not None and not isinstance(crush_profile, dict):
        return {"status": -5, "message": "Invalid crush_profile format"}

    if event is not None and not isinstance(event, dict):
        return {"status": -6, "message": "Invalid event format"}

    print(
        "normalized_context:\n",
        json.dumps(normalized_context, indent=4, ensure_ascii=False),
    )

    # 提前声明，后续需要refresh
    crush = None
    new_event = None
    try:
        # 使用事务一次性写入两类 Context，避免部分成功导致数据不一致
        transaction_ctx = db.begin_nested() if db.in_transaction() else db.begin()
        with transaction_ctx:
            # 包含crush_profile：直接在Crush表添加
            if crush_profile is not None:
                crush = relation_chain.crush
                if crush is None:
                    return {"status": -7, "message": "Crush not found"}
                new_likes = crush_profile.get("likes")
                new_dislikes = crush_profile.get("dislikes")
                new_boundaries = crush_profile.get("boundaries")
                new_traits = crush_profile.get("traits")
                new_lifestyle_tags = crush_profile.get("lifestyle_tags")
                new_values = crush_profile.get("values")
                new_appearance_tags = crush_profile.get("appearance_tags")
                new_other_info = crush_profile.get("other_info")
                new_birthday = crush_profile.get("birthday")
                new_occupation = crush_profile.get("occupation")
                new_education = crush_profile.get("education")
                new_residence = crush_profile.get("residence")
                new_hometown = crush_profile.get("hometown")
                new_communication_style = crush_profile.get("communication_style")

                if new_likes is not None and isinstance(new_likes, list):
                    current_likes = set(cleanList(crush.likes))
                    for item in cleanList(new_likes):
                        if item not in current_likes:
                            crush.likes.append(item)
                            current_likes.add(item)
                if new_dislikes is not None and isinstance(new_dislikes, list):
                    current_dislikes = set(cleanList(crush.dislikes))
                    for item in cleanList(new_dislikes):
                        if item not in current_dislikes:
                            crush.dislikes.append(item)
                            current_dislikes.add(item)
                if new_boundaries is not None and isinstance(new_boundaries, list):
                    current_boundaries = set(cleanList(crush.boundaries))
                    for item in cleanList(new_boundaries):
                        if item not in current_boundaries:
                            crush.boundaries.append(item)
                            current_boundaries.add(item)
                if new_traits is not None and isinstance(new_traits, list):
                    current_traits = set(cleanList(crush.traits))
                    for item in cleanList(new_traits):
                        if item not in current_traits:
                            crush.traits.append(item)
                            current_traits.add(item)
                if new_lifestyle_tags is not None and isinstance(
                    new_lifestyle_tags, list
                ):
                    current_lifestyle_tags = set(cleanList(crush.lifestyle_tags))
                    for item in cleanList(new_lifestyle_tags):
                        if item not in current_lifestyle_tags:
                            crush.lifestyle_tags.append(item)
                            current_lifestyle_tags.add(item)
                if new_values is not None and isinstance(new_values, list):
                    current_values = set(cleanList(crush.values))
                    for item in cleanList(new_values):
                        if item not in current_values:
                            crush.values.append(item)
                            current_values.add(item)
                if new_appearance_tags is not None and isinstance(
                    new_appearance_tags, list
                ):
                    current_appearance_tags = set(cleanList(crush.appearance_tags))
                    for item in cleanList(new_appearance_tags):
                        if item not in current_appearance_tags:
                            crush.appearance_tags.append(item)
                            current_appearance_tags.add(item)
                if new_other_info is not None and isinstance(new_other_info, dict):
                    crush.other_info.append(new_other_info)
                if isinstance(new_birthday, str) and new_birthday.strip():
                    crush.birthday = new_birthday.strip()
                if isinstance(new_occupation, str) and new_occupation.strip():
                    crush.occupation = new_occupation.strip()
                if isinstance(new_education, str) and new_education.strip():
                    crush.education = new_education.strip()
                if isinstance(new_residence, str) and new_residence.strip():
                    crush.residence = new_residence.strip()
                if isinstance(new_hometown, str) and new_hometown.strip():
                    crush.hometown = new_hometown.strip()
                if new_communication_style is not None and isinstance(
                    new_communication_style, list
                ):
                    current_communication_style = set(
                        cleanList(crush.communication_style)
                    )
                    for item in cleanList(new_communication_style):
                        if item not in current_communication_style:
                            crush.communication_style.append(item)
                            current_communication_style.add(item)

            # 包含event：在Event表新增
            if event is not None:
                # 对event结构做校验
                event_content = None
                event_weight = 1.0
                event_date = None
                event_summary = None
                event_outcome = None
                event_other_info = None
                if event is not None:
                    event_content = event.get("content")
                    if not isinstance(event_content, str) or not event_content.strip():
                        return {"status": -6, "message": "Invalid event content"}
                    event_weight = event.get("weight", 1.0)
                    if not isinstance(event_weight, (int, float)) or not (
                        0 <= float(event_weight) <= 1
                    ):
                        return {"status": -6, "message": "Invalid event weight"}
                    event_date = event.get("date")
                    if isinstance(event_date, str) and not event_date.strip():
                        event_date = None
                    event_summary = event.get("summary")
                    if event_summary is not None and not isinstance(event_summary, str):
                        return {"status": -6, "message": "Invalid event summary"}
                    outcome_value = event.get("outcome", Attitude.UNKNOWN.value)
                    try:
                        event_outcome = parseEnum(Attitude, outcome_value)
                    except ValueError:
                        return {"status": -6, "message": "Invalid event outcome"}
                    event_other_info = event.get("other_info")
                    if event_other_info is not None and not isinstance(
                        event_other_info, dict
                    ):
                        return {"status": -6, "message": "Invalid event other_info"}

                new_event = Event(
                    relation_chain_id=relation_chain_id,
                    content=event_content,
                    weight=float(event_weight),
                    date=event_date,
                    summary=event_summary,
                    outcome=event_outcome,
                )
                if event_other_info is not None:
                    new_event.other_info = [event_other_info]
                db.add(new_event)

            db.flush()
    except Exception as e:
        return {"status": -8, "message": f"Error saving context: {e}"}

    crush_embedding_res = None
    event_embedding_res = None
    if crush is not None:
        db.refresh(crush)
        crush_embedding_res = {
            "status": 0,
            "message": "Embedding not created",
        }
        # 若需向量化，向量化并落库
        if with_embedding:
            crush_embedding_res = await createOrUpdateEmbedding(
                db, from_where="crush_profile", crush=crush
            )

    if new_event is not None:
        db.refresh(new_event)
        event_embedding_res = {
            "status": 0,
            "message": "Embedding not created",
        }
        # 若需向量化，向量化并落库
        if with_embedding:
            event_embedding_res = await createOrUpdateEmbedding(
                db, from_where="event", event=new_event
            )

    embedding_result = {}
    if crush_embedding_res is not None:
        embedding_result["crush"] = crush_embedding_res
    if event_embedding_res is not None:
        embedding_result["event"] = event_embedding_res
    return {
        "status": 200,
        "message": "Create context success",
        "normalized_context": normalized_context,
        "embedding": embedding_result,
    }


async def contextAddContextByScreenshots(
    db: Session,
    with_embedding: bool,
    relation_chain_id: int,
    screenshot_urls: List[str],
    crush_name: str,
    additional_context: str = "",
) -> dict:
    relation_chain = db.get(RelationChain, relation_chain_id)
    if relation_chain is None:
        return {"status": -1, "message": "Relation chain not found"}
    if (
        not screenshot_urls
        or not isinstance(screenshot_urls, list)
        or len(screenshot_urls) == 0
    ):
        return {"status": -2, "message": "No screenshot urls provided"}

    try:
        normalized_context = json.loads(
            await extractContextFromScreenshots(
                screenshot_urls=screenshot_urls,
                additional_context=additional_context,
                crush_name=crush_name,
                username=(
                    relation_chain.user.nickname
                    if relation_chain.user.nickname != ""
                    else relation_chain.user.username
                ),
            )
        )
    except json.JSONDecodeError:
        return {"status": -3, "message": "Failed to normalize context"}

    if not isinstance(normalized_context, dict):
        return {"status": -3, "message": "Failed to normalize context"}

    crush_profile = normalized_context.get("crush_profile")
    chat_topic = normalized_context.get("chat_topic")
    if crush_profile is None and chat_topic is None:
        return {"status": -4, "message": "No valid context found"}

    if crush_profile is not None and not isinstance(crush_profile, dict):
        return {"status": -5, "message": "Invalid crush_profile format"}

    if chat_topic is not None and not isinstance(chat_topic, dict):
        return {"status": -6, "message": "Invalid chat_topic format"}

    print(
        "normalized_context:\n",
        json.dumps(normalized_context, indent=4, ensure_ascii=False),
    )

    # 提前声明，后续需要refresh
    crush = None
    new_chat_topic = None
    try:
        # 使用事务一次性写入两类 Context，避免部分成功导致数据不一致
        transaction_ctx = db.begin_nested() if db.in_transaction() else db.begin()
        with transaction_ctx:
            # 包含crush_profile：直接在Crush表添加
            if crush_profile is not None:
                crush = relation_chain.crush
                if crush is None:
                    return {"status": -7, "message": "Crush not found"}
                new_likes = crush_profile.get("likes")
                new_dislikes = crush_profile.get("dislikes")
                new_boundaries = crush_profile.get("boundaries")
                new_traits = crush_profile.get("traits")
                new_lifestyle_tags = crush_profile.get("lifestyle_tags")
                new_values = crush_profile.get("values")
                new_appearance_tags = crush_profile.get("appearance_tags")
                new_other_info = crush_profile.get("other_info")
                new_birthday = crush_profile.get("birthday")
                new_occupation = crush_profile.get("occupation")
                new_education = crush_profile.get("education")
                new_residence = crush_profile.get("residence")
                new_hometown = crush_profile.get("hometown")
                new_communication_style = crush_profile.get("communication_style")

                if new_likes is not None and isinstance(new_likes, list):
                    current_likes = set(cleanList(crush.likes))
                    for item in cleanList(new_likes):
                        if item not in current_likes:
                            crush.likes.append(item)
                            current_likes.add(item)
                if new_dislikes is not None and isinstance(new_dislikes, list):
                    current_dislikes = set(cleanList(crush.dislikes))
                    for item in cleanList(new_dislikes):
                        if item not in current_dislikes:
                            crush.dislikes.append(item)
                            current_dislikes.add(item)
                if new_boundaries is not None and isinstance(new_boundaries, list):
                    current_boundaries = set(cleanList(crush.boundaries))
                    for item in cleanList(new_boundaries):
                        if item not in current_boundaries:
                            crush.boundaries.append(item)
                            current_boundaries.add(item)
                if new_traits is not None and isinstance(new_traits, list):
                    current_traits = set(cleanList(crush.traits))
                    for item in cleanList(new_traits):
                        if item not in current_traits:
                            crush.traits.append(item)
                            current_traits.add(item)
                if new_lifestyle_tags is not None and isinstance(
                    new_lifestyle_tags, list
                ):
                    current_lifestyle_tags = set(cleanList(crush.lifestyle_tags))
                    for item in cleanList(new_lifestyle_tags):
                        if item not in current_lifestyle_tags:
                            crush.lifestyle_tags.append(item)
                            current_lifestyle_tags.add(item)
                if new_values is not None and isinstance(new_values, list):
                    current_values = set(cleanList(crush.values))
                    for item in cleanList(new_values):
                        if item not in current_values:
                            crush.values.append(item)
                            current_values.add(item)
                if new_appearance_tags is not None and isinstance(
                    new_appearance_tags, list
                ):
                    current_appearance_tags = set(cleanList(crush.appearance_tags))
                    for item in cleanList(new_appearance_tags):
                        if item not in current_appearance_tags:
                            crush.appearance_tags.append(item)
                            current_appearance_tags.add(item)
                if new_other_info is not None and isinstance(new_other_info, dict):
                    crush.other_info.append(new_other_info)
                if isinstance(new_birthday, str) and new_birthday.strip():
                    crush.birthday = new_birthday.strip()
                if isinstance(new_occupation, str) and new_occupation.strip():
                    crush.occupation = new_occupation.strip()
                if isinstance(new_education, str) and new_education.strip():
                    crush.education = new_education.strip()
                if isinstance(new_residence, str) and new_residence.strip():
                    crush.residence = new_residence.strip()
                if isinstance(new_hometown, str) and new_hometown.strip():
                    crush.hometown = new_hometown.strip()
                if new_communication_style is not None and isinstance(
                    new_communication_style, list
                ):
                    current_communication_style = set(
                        cleanList(crush.communication_style)
                    )
                    for item in cleanList(new_communication_style):
                        if item not in current_communication_style:
                            crush.communication_style.append(item)
                            current_communication_style.add(item)

            # 包含chat_topic：在ChatTopic表新增
            if chat_topic is not None:
                topic_title = chat_topic.get("title")
                if not isinstance(topic_title, str) or not topic_title.strip():
                    return {"status": -6, "message": "Invalid chat_topic title"}
                topic_weight = chat_topic.get("weight", 1.0)
                if not isinstance(topic_weight, (int, float)) or not (
                    0 <= float(topic_weight) <= 1
                ):
                    return {"status": -6, "message": "Invalid chat_topic weight"}
                topic_summary = chat_topic.get("summary")
                if topic_summary is not None and not isinstance(topic_summary, str):
                    return {"status": -6, "message": "Invalid chat_topic summary"}
                topic_content = chat_topic.get("content")
                if topic_content is not None and not isinstance(topic_content, str):
                    return {"status": -6, "message": "Invalid chat_topic content"}
                topic_tags = chat_topic.get("tags")
                if topic_tags is not None and not isinstance(topic_tags, list):
                    return {"status": -6, "message": "Invalid chat_topic tags"}
                topic_participants = chat_topic.get("participants")
                if topic_participants is not None and not isinstance(
                    topic_participants, list
                ):
                    return {"status": -6, "message": "Invalid chat_topic participants"}
                topic_source_urls = chat_topic.get("source_urls")
                if topic_source_urls is not None and not isinstance(
                    topic_source_urls, list
                ):
                    return {"status": -6, "message": "Invalid chat_topic source_urls"}

                topic_time = chat_topic.get("topic_time")
                if topic_time is not None and not isinstance(topic_time, str):
                    return {"status": -6, "message": "Invalid chat_topic topic_time"}
                if isinstance(topic_time, str) and not topic_time.strip():
                    topic_time = None

                topic_channel = chat_topic.get("channel")
                if topic_channel is not None:
                    try:
                        topic_channel = parseEnum(ChatChannel, topic_channel)
                    except ValueError:
                        return {"status": -6, "message": "Invalid chat_topic channel"}

                topic_attitude = chat_topic.get("attitude")
                if topic_attitude is not None:
                    try:
                        topic_attitude = parseEnum(Attitude, topic_attitude)
                    except ValueError:
                        return {"status": -6, "message": "Invalid chat_topic attitude"}

                topic_other_info = chat_topic.get("other_info")
                if topic_other_info is not None and not isinstance(
                    topic_other_info, dict
                ):
                    return {"status": -6, "message": "Invalid chat_topic other_info"}

                new_chat_topic = ChatTopic(
                    relation_chain_id=relation_chain_id,
                    title=topic_title.strip(),
                    summary=(
                        topic_summary.strip()
                        if isinstance(topic_summary, str)
                        else None
                    ),
                    content=(
                        topic_content.strip()
                        if isinstance(topic_content, str)
                        else None
                    ),
                    tags=cleanList(topic_tags) if isinstance(topic_tags, list) else [],
                    participants=(
                        cleanList(topic_participants)
                        if isinstance(topic_participants, list)
                        else []
                    ),
                    source_urls=(
                        cleanList(topic_source_urls)
                        if isinstance(topic_source_urls, list)
                        else cleanList(screenshot_urls)
                    ),
                    topic_time=(
                        topic_time.strip() if isinstance(topic_time, str) else None
                    ),
                    channel=topic_channel,
                    attitude=topic_attitude,
                    weight=float(topic_weight),
                )
                if topic_other_info is not None:
                    new_chat_topic.other_info = [topic_other_info]
                db.add(new_chat_topic)

            db.flush()
    except Exception as e:
        return {"status": -8, "message": f"Error saving context: {e}"}

    crush_embedding_res = None
    chat_topic_embedding_res = None
    if crush is not None:
        db.refresh(crush)
        crush_embedding_res = {
            "status": 0,
            "message": "Embedding not created",
        }
        # 若需向量化，向量化并落库
        if with_embedding:
            crush_embedding_res = await createOrUpdateEmbedding(
                db, from_where="crush_profile", crush=crush
            )

    if new_chat_topic is not None:
        db.refresh(new_chat_topic)
        chat_topic_embedding_res = {
            "status": 0,
            "message": "Embedding not created",
        }
        # 若需向量化，向量化并落库
        if with_embedding:
            chat_topic_embedding_res = await createOrUpdateEmbedding(
                db, from_where="chat_topic", chat_topic=new_chat_topic
            )

    embedding_result = {}
    if crush_embedding_res is not None:
        embedding_result["crush"] = crush_embedding_res
    if chat_topic_embedding_res is not None:
        embedding_result["chat_topic"] = chat_topic_embedding_res
    return {
        "status": 200,
        "message": "Create context success",
        "normalized_context": normalized_context,
        "embedding": embedding_result,
    }
