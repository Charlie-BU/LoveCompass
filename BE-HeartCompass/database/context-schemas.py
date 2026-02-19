from typing import TypedDict, NotRequired, Literal


# 长期稳定信息：偏好、人格、边界、价值观等“慢变化”
class STATIC_PROFILE(TypedDict):
    mbti: NotRequired[str]  # MBTI
    likes: NotRequired[list[str]]  # 喜好
    dislikes: NotRequired[list[str]]  # 不喜欢
    boundaries: NotRequired[list[str]]  # 个人边界
    traits: NotRequired[list[str]]  # 个人特点
    evidence: NotRequired[list[str]]  # 支持证据
    others: NotRequired[dict[str, str]]  # 其他


# 聊天记录：可追溯的原始事实
class CHAT_LOG(TypedDict):
    channel: NotRequired[
        Literal["weixin", "douyin", "sms", "offline", "email", "phone", "other"]
    ]  # 渠道
    speaker: Literal["me", "crush", "third_party"]  # 角色
    content: str  # 内容
    timestamp: str  # 时间戳
    emotion: NotRequired[
        Literal["positive", "neutral", "negative", "mixed", "unknown"]
    ]  # 情感
    additional_info: NotRequired[dict[str, str]]  # 其他额外信息


# 互动信号（通过CHAT_LOG推断）：衡量互动强弱、主动性、回应速度等
class INTERACTION_SIGNAL(TypedDict):
    frequency: Literal["high", "medium", "low"]  # 频率
    attitude: Literal["positive", "neutral", "negative", "unknown"]  # 态度
    note: NotRequired[str]  # 备注
    window: Literal["24h", "3d", "7d", "14d", "30d"]  # 观测时间窗口
    additional_info: NotRequired[dict[str, str]]  # 其他额外信息


# 推断/洞察（从其他上下文推断）
class DERIVED_INSIGHT(TypedDict):
    insight: str  # 洞察内容
    evidence_context_ids: list[int]  # 支持证据上下文id列表
    confidence: float  # 置信度
    additional_info: NotRequired[dict[str, str]]  # 其他额外信息


# 阶段性事件
class STAGE_EVENT(TypedDict):
    event: str  # 事件内容
    date: str  # 事件日期
    summary: NotRequired[str]  # 事件概要
    outcome: Literal["positive", "neutral", "negative", "unknown"]  # 结果导向
    additional_info: NotRequired[dict[str, str]]  # 其他额外信息


# 系统推理当前阶段
class SYSTEM_ANALYSIS(TypedDict):
    analysis: str  # 分析内容
    confidence: float  # 置信度
    stage_suggestion: Literal[
        "stranger", "friend", "ambiguous", "dating", "tension", "broken_up", "failed"
    ]  # 阶段建议
    additional_info: NotRequired[dict[str, str]]  # 其他额外信息
