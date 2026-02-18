import enum


def parse_enum(enum_cls, value: str):
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


# todo：不同类型上下文内容应当具有固定的schema
class ContextType(enum.Enum):
    STATIC_PROFILE = "static_profile"  # 长期稳定信息
    CHAT_LOG = "chat_log"  # 聊天记录
    INTERACTION_SIGNAL = "interaction_signal"  # 互动信号
    DERIVED_INSIGHT = "derived_insight"  # 推断/洞察
    STAGE_EVENT = "stage_event"  # 阶段性事件
    SYSTEM_ANALYSIS = "system_analysis"  # 系统推理分析


class ContextSource(enum.Enum):
    USER_INPUT = "user_input"  # 用户直接输入
    SYSTEM_INFERENCE = "system_inference"  # 系统推理生成
    LLM_GENERATED = "llm_generated"  # LLM 生成
    EXTERNAL_API = "external_api"  # 外部 API 上传


class ConflictType(enum.Enum):
    WITH_CONTEXT = "with_context"  # 与已有上下文冲突
    WITH_KNOWLEDGE = "with_knowledge"  # 与静态知识库冲突


class ConflictResolutionStatus(enum.Enum):
    PENDING = "pending"  # 待解决
    RESOLVED_KEEP_NEW = "resolved_keep_new"  # 解决并保留新上下文
    RESOLVED_KEEP_OLD = "resolved_keep_old"  # 解决并保留旧上下文
    BOTH_DOWNGRADED = "both_downgraded"  # 双方都降级


class EmbeddingType(enum.Enum):
    FROM_CONTEXT = "from_context"  # 从上下文生成
    FROM_KNOWLEDGE = "from_knowledge"  # 从静态知识库生成
