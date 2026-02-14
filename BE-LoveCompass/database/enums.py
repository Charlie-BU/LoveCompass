import enum


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


class ContextType(enum.Enum):
    STATIC_PROFILE = "static_profile"  # 静态个人信息
    CHAT_LOG = "chat_log"  # 聊天记录
    INTERACTION_SIGNAL = "interaction_signal"  # 交互信号
    DERIVED_INSIGHT = "derived_insight"  # 其他上下文派生
    STAGE_EVENT = "stage_event"  # 阶段事件
    SYSTEM_ANALYSIS = "system_analysis"  # 系统推理分析


class ContextSource(enum.Enum):
    USER_INPUT = "user_input"  # 用户直接输入
    SYSTEM_INFERENCE = "system_inference"  # 系统推理生成
    LLM_GENERATED = "llm_generated"  # LLM 生成
    EXTERNAL_API = "external_api"  # 外部 API 上传


class ConflictResolutionStatus(enum.Enum):
    PENDING = "pending"  # 待解决
    RESOLVED_KEEP_NEW = "resolved_keep_new"  # 解决并保留新上下文
    RESOLVED_KEEP_OLD = "resolved_keep_old"  # 解决并保留旧上下文
    BOTH_DOWNGRADED = "both_downgraded"  # 双方都降级
