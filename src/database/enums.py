import enum


class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class UserLevel(enum.Enum):
    """用户等级，从高到低"""

    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4


class MBTI(enum.Enum):
    ISTJ = "ISTJ"
    ISFJ = "ISFJ"
    INFJ = "INFJ"
    INTJ = "INTJ"
    ISTP = "ISTP"
    ISFP = "ISFP"
    INFP = "INFP"
    INTP = "INTP"
    ESTP = "ESTP"
    ESFP = "ESFP"
    ENFP = "ENFP"
    ENTP = "ENTP"
    ESTJ = "ESTJ"
    ESFJ = "ESFJ"
    ENFJ = "ENFJ"
    ENTJ = "ENTJ"


class FigureRole(enum.Enum):
    SELF = "self"  # 自己
    FAMILY = "family"  # 家人
    FRIEND = "friend"  # 朋友
    MENTOR = "mentor"  # 导师
    COLLEAGUE = "colleague"  # 同事
    PARTNER = "partner"  # 伴侣
    PUBLIC_FIGURE = "public_figure"  # 公众人物
    STRANGER = "stranger"  # 陌生人


class FineGrainedFeedDimension(enum.Enum):
    PERSONALITY = "personality"  # 性格与价值观
    INTERACTION_STYLE = "interaction_style"  # 互动风格
    PROCEDURAL_INFO = "procedural_info"  # 程序性知识
    MEMORY = "memory"  # 人生记忆与故事
    OTHER = "other"  # 其他


class FineGrainedFeedConfidence(enum.Enum):
    VERBATIM = "verbatim"  # 原话
    ARTIFACT = "artifact"  # 文档/作品/公开内容中的客观陈述
    IMPRESSION = "impression"  # 提供者补充的主观印象


class OriginalSourceType(enum.Enum):
    # 通用
    NARRATIVE_FROM_USER = "narrative_from_user"  # 用户对其的文字表述

    # FigureRole 工作关系：同事/导师
    WORK_RELATION_LONG_FORM = (
        "work_relation_long_form"  # 本人主笔的长文（设计文档、复盘报告、Oncall记录）
    )
    WORK_RELATION_EDIT_TRACE = (
        "work_relation_edit_trace"  # 对他人工作的修改痕迹（CR评论、文档批注）
    )
    WORK_RELATION_GUIDANCE = "work_relation_guidance"  # 指导记录
    WORK_RELATION_ARTIFACT = "work_relation_artifact"  # 创作物（代码、设计稿等）

    # FigureRole 亲密关系：亲人/伴侣/朋友
    CLOSE_RELATION_LONG_FORM = (
        "close_relation_long_form"  # 本人主笔的长文（书信、文章等）
    )
    CLOSE_RELATION_PRIVATE_CHAT = (
        "close_relation_private_chat"  # 私聊记录（最直接的互动痕迹）
    )
    CLOSE_RELATION_SOCIAL_EXPRESSION = (
        "close_relation_social_expression"  # 社交表达（公开的表达、社交媒体发帖）
    )
    CLOSE_RELATION_ARTIFACT = "close_relation_artifact"  # 创作物

    # FigureRole 自己
    SELF_LONG_FORM = "self_long_form"  # 自己写的长文（博客、日记、笔记）
    SELF_CHAT_MESSAGE = "self_chat_message"  # 和他人聊天记录（自己发出的消息）
    SELF_SOCIAL_EXPRESSION = "self_social_expression"  # 社交表达（公开的表达、社交媒体发帖）
    SELF_ARTIFACT = "self_artifact"  # 创作物

    # FigureRole 公众人物
    PUBLIC_FIGURE_ARTICLE_BLOG = "public_figure_article_blog"  # 公开文章/博客
    PUBLIC_FIGURE_INTERVIEW_SPEECH_TRANSCRIPT = (
        "public_figure_interview_speech_transcript"  # 采访/演讲文字
    )
    PUBLIC_FIGURE_SOCIAL_EXPRESSION = "public_figure_social_expression"  # 社交表达（公开的表达、社交媒体发帖）
    PUBLIC_FIGURE_NEWS_REPORT = "public_figure_news_report"  # 新闻报道
    PUBLIC_FIGURE_ARTIFACT = "public_figure_artifact"  # 创作物（代码、设计稿等）


class AnalysisType(enum.Enum):
    CONVERSATION = "conversation"  # 聊天记录分析
    NARRATIVE = "narrative"  # 自然语言叙述分析


def parseEnum(enum_cls, value: str):
    if value in enum_cls.__members__:  # value为枚举键
        return enum_cls[value]
    return enum_cls(value)  # value为枚举值
