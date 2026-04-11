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
    SELF = "self"
    FAMILY = "family"
    FRIEND = "friend"
    MENTOR = "mentor"
    PARTNER = "partner"
    PUBLIC_FIGURE = "public_figure"
    STRANGER = "stranger"


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


class AnalysisType(enum.Enum):
    CONVERSATION = "conversation"  # 聊天记录分析
    NARRATIVE = "narrative"  # 自然语言叙述分析


def parseEnum(enum_cls, value: str):
    if value in enum_cls.__members__:  # value为枚举键
        return enum_cls[value]
    return enum_cls(value)  # value为枚举值
