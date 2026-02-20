import enum


def parseEnum(enum_cls, value: str):
    if value in enum_cls.__members__:  # value为枚举键
        return enum_cls[value]
    return enum_cls(value)  # value为枚举值


# 用户性别
class UserGender(enum.Enum):
    MALE = "男"
    FEMALE = "女"
    OTHER = "其他"


# 用户等级，从高到低
class UserLevel(enum.Enum):
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


class RelationStage(enum.Enum):
    STRANGER = "stranger"
    FRIEND = "friend"
    AMBIGUOUS = "ambiguous"
    DATING = "dating"
    TENSION = "tension"
    BROKEN_UP = "broken_up"
    FAILED = "failed"


class Attitude(enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    UNKNOWN = "unknown"


class ChatSpeaker(enum.Enum):
    ME = "me"
    CRUSH = "crush"
    THIRD_PARTY = "third_party"


class ChatChannel(enum.Enum):
    OFFLINE = "offline"
    WEIXIN = "weixin"
    DOUYIN = "douyin"
    SMS = "sms"
    EMAIL = "email"
    PHONE = "phone"
    OTHER = "other"


class Degree(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class WindowOnListen(enum.Enum):
    H24 = "24h"
    D3 = "3d"
    D7 = "7d"
    D14 = "14d"
    D30 = "30d"
    UNKNOWN = "unknown"


class ConflictResolutionStatus(enum.Enum):
    PENDING = "pending"  # 待解决
    RESOLVED_KEEP_NEW = "resolved_keep_new"  # 解决并保留新上下文
    RESOLVED_KEEP_OLD = "resolved_keep_old"  # 解决并保留旧上下文
    BOTH_DOWNGRADED = "both_downgraded"  # 双方都降级


class EmbeddingType(enum.Enum):
    FROM_KNOWLEDGE = "from_knowledge"  # 从静态知识库生成
    FROM_CRUSH_PROFILE = "from_crush_profile"  # 从 Crush 个人资料生成
    FROM_EVENT = "from_event"  # 从事件生成
    FROM_CHAT_LOG = "from_chat_log"  # 从聊天记录生成
    FROM_INTERACTION_SIGNAL = "from_interaction_signal"  # 从互动信号生成
    FROM_DERIVED_INSIGHT = "from_derived_insight"  # 从推断/洞察生成
