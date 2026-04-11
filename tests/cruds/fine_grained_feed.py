import asyncio

from dotenv import load_dotenv

load_dotenv()

from src.database.enums import FineGrainedFeedConfidence, FineGrainedFeedDimension, OriginalSourceType
from src.services.fine_grained_feed import (
    addFineGrainedFeed,
    addFineGrainedFeedConflict,
    addOriginalSource,
    deleteFineGrainedFeed,
    deleteOriginalSource,
    getAllFineGrainedFeed,
    getAllFineGrainedFeedConflict,
    getAllOriginalSource,
    getFineGrainedFeed,
    getFineGrainedFeedConflict,
    getOriginalSource,
    hardDeleteFineGrainedFeedConflict,
    recallFineGrainedFeeds,
    resolveFineGrainedFeedConflict,
    updateFineGrainedFeed,
)


def testAddOriginalSource(fr_id: int):
    res = addOriginalSource(
        user_id=1,
        fr_id=fr_id,
        type=OriginalSourceType.NARRATIVE_FROM_USER,
        confidence=FineGrainedFeedConfidence.VERBATIM,
        included_dimensions=[
            FineGrainedFeedDimension.PERSONALITY,
            FineGrainedFeedDimension.INTERACTION_STYLE,
        ],
        content="xxxxxx",
        approx_date="2026-01-20",
    )
    return res


def testDeleteOriginalSource(fr_id: int, original_source_id: int):
    res = deleteOriginalSource(
        user_id=1,
        fr_id=fr_id,
        original_source_id=original_source_id,
    )
    return res


def testGetOriginalSource(fr_id: int, original_source_id: int):
    res = getOriginalSource(
        user_id=1,
        fr_id=fr_id,
        original_source_id=original_source_id,
    )
    return res


def testGetAllOriginalSource(fr_id: int):
    res = getAllOriginalSource(
        user_id=1,
        fr_id=fr_id,
    )
    return res


async def testAddFineGrainedFeed(fr_id: int, original_source_id: int):
    mock = [
        {
            "content": "她在分歧出现时会先复述对方观点，确认理解一致后再表达立场。",
            "sub_dimension": "冲突调解",
        },
        {
            "content": "遇到高压项目时，她会把任务拆成小时级清单并在看板实时更新。",
            "sub_dimension": "任务管理",
        },
        {
            "content": "她偏好语音沟通复杂问题，文字仅用于留痕和结论确认。",
            "sub_dimension": "沟通媒介偏好",
        },
        {
            "content": "每周五她会主动发一份复盘，包含本周失误、改进动作和下周实验计划。",
            "sub_dimension": "复盘习惯",
        },
        {
            "content": "她对时间非常敏感，会议迟到五分钟以上会明显不耐烦。",
            "sub_dimension": "时间边界",
        },
        {
            "content": "在陌生社交场合她会先观察氛围，通常二十分钟后才开始主动发言。",
            "sub_dimension": "社交启动节奏",
        },
        {
            "content": "面对含糊需求时，她会连续追问三层“为什么”，直到目标可量化。",
            "sub_dimension": "问题澄清方式",
        },
        {
            "content": "她不喜欢被临时打断深度工作，常把下午两点到四点设为免打扰时段。",
            "sub_dimension": "专注保护策略",
        },
        {
            "content": "收到负面反馈后她会先沉默记录，再在24小时内给出结构化回应。",
            "sub_dimension": "反馈处理机制",
        },
        {
            "content": "她会记住同事的小偏好，比如咖啡口味和禁忌话题，用来降低协作摩擦。",
            "sub_dimension": "关系维护细节",
        },
    ]
    ress = []
    for item in mock:
        res = await addFineGrainedFeed(
            user_id=1,
            fr_id=fr_id,
            original_source_id=original_source_id,
            dimension=FineGrainedFeedDimension.INTERACTION_STYLE,
            confidence=FineGrainedFeedConfidence.IMPRESSION,
            content=item["content"],
            sub_dimension=item["sub_dimension"],
        )
        ress.append(res)
    
    return ress


def testDeleteFineGrainedFeed(fr_id: int, fine_grained_feed_id: int):
    res = deleteFineGrainedFeed(
        user_id=1,
        fr_id=fr_id,
        fine_grained_feed_id=fine_grained_feed_id,
    )
    return res


async def testUpdateFineGrainedFeed(
    fr_id: int,
    fine_grained_feed_id: int,
    new_original_source_id: int,
):
    res = await updateFineGrainedFeed(
        user_id=1,
        fr_id=fr_id,
        fine_grained_feed_id=fine_grained_feed_id,
        new_original_source_id=new_original_source_id,
        new_content="她会在冲突出现前先确认彼此目标，避免误解。",
        new_sub_dimension="冲突处理",
    )
    return res


def testGetFineGrainedFeed(fr_id: int, fine_grained_feed_id: int):
    res = getFineGrainedFeed(
        user_id=1,
        fr_id=fr_id,
        fine_grained_feed_id=fine_grained_feed_id,
    )
    return res


def testGetAllFineGrainedFeed(fr_id: int):
    res = getAllFineGrainedFeed(
        user_id=1,
        fr_id=fr_id,
    )
    return res


async def testRecallFineGrainedFeeds(fr_id: int, query: str, top_k: int):
    res = await recallFineGrainedFeeds(
        user_id=1,
        fr_id=fr_id,
        query=query,
        top_k=top_k,
    )
    return res


def testAddFineGrainedFeedConflict(fr_id: int, feed_ids: list[int]):
    res = addFineGrainedFeedConflict(
        user_id=1,
        fr_id=fr_id,
        dimension=FineGrainedFeedDimension.PERSONALITY,
        feed_ids=feed_ids,
        description="同一人物在不同时间表现出外向与内向两种明显特征。",
        resolved=False,
    )
    return res


def testHardDeleteFineGrainedFeedConflict(
    fr_id: int, fine_grained_feed_conflict_id: int
):
    res = hardDeleteFineGrainedFeedConflict(
        user_id=1,
        fr_id=fr_id,
        fine_grained_feed_conflict_id=fine_grained_feed_conflict_id,
    )
    return res


def testResolveFineGrainedFeedConflict(fr_id: int, fine_grained_feed_conflict_id: int):
    res = resolveFineGrainedFeedConflict(
        user_id=1,
        fr_id=fr_id,
        fine_grained_feed_conflict_id=fine_grained_feed_conflict_id,
    )
    return res


def testGetFineGrainedFeedConflict(fr_id: int, fine_grained_feed_conflict_id: int):
    res = getFineGrainedFeedConflict(
        user_id=1,
        fr_id=fr_id,
        fine_grained_feed_conflict_id=fine_grained_feed_conflict_id,
    )
    return res


def testGetAllFineGrainedFeedConflict(
    fr_id: int,
    scope: str = "unresolved",
):
    res = getAllFineGrainedFeedConflict(
        user_id=1,
        fr_id=fr_id,
        scope=scope,
    )
    return res


if __name__ == "__main__":
    # print(testAddOriginalSource(fr_id=1))
    # print(asyncio.run(testAddFineGrainedFeed(fr_id=1, original_source_id=2)))
    print(asyncio.run(testRecallFineGrainedFeeds(fr_id=1, query="人际交往", top_k=3)))
