from sqlalchemy import (
    inspect,
    Column,
    String,
    Integer,
    Float,
    Boolean,
    ForeignKey,
    Enum,
    Text,
    DateTime,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from pgvector.sqlalchemy import Vector
from bcrypt import hashpw, gensalt, checkpw
from datetime import datetime, timezone

from .enums import (
    AnalysisType,
    UserGender,
    UserLevel,
    MBTI,
    RelationStage,
    Attitude,
    ChatChannel,
    Degree,
    WindowOnListen,
    EmbeddingType,
)

Base = declarative_base()
# 数据库表名和列名的命名规范
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
Base.metadata.naming_convention = naming_convention


# 可序列化Mixin基类，提供toJson方法将模型实例转换为JSON
class SerializableMixin:
    def toJson(self, include=None, exclude=["password"], include_relations=False):
        include = set(include) if include else None
        exclude = set(exclude) if exclude else set()
        mapper = inspect(self.__class__)
        if not mapper:
            return {}

        data = {}
        for column in mapper.columns:
            name = column.key
            if include:
                if name not in include:
                    continue
                # 若有 include，则要检查关系是否在 include 中
                for rel in mapper.relationships:
                    if rel.key in include:
                        value = getattr(self, rel.key)
                        data[rel.key] = value.toJson() if value else None
                        continue
            if name in exclude:
                continue
            value = getattr(self, name)
            if isinstance(value, datetime):
                value = value.isoformat()
            data[name] = value

        if include_relations:
            for rel in mapper.relationships:
                if rel.key in exclude:
                    continue
                value = getattr(self, rel.key)
                if value is None:
                    data[rel.key] = None
                elif isinstance(value, list):
                    data[rel.key] = [v.toJson() for v in value]
                else:
                    data[rel.key] = value.toJson()
        return data


# ---- 用户 ----
class User(Base, SerializableMixin):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)

    username = Column(
        String(64), unique=True, nullable=False, index=True, comment="用户唯一用户名"
    )
    password = Column(String(128), nullable=False, comment="用户密码")
    nickname = Column(String(64), nullable=True, index=True, comment="用户昵称")
    gender = Column(Enum(UserGender), nullable=False, comment="用户性别")
    email = Column(String(128), nullable=True, unique=True, comment="用户邮箱")
    level = Column(Enum(UserLevel), default=UserLevel.L4, comment="用户等级")
    mbti = Column(Enum(MBTI), nullable=True, comment="用户MBTI类型")
    created_at = Column(
        DateTime, default=datetime.now(timezone.utc), comment="用户创建时间"
    )

    @staticmethod
    def hashPassword(password):
        hashed = hashpw(password.encode("utf-8"), gensalt())
        return hashed.decode("utf-8")

    def checkPassword(self, password):
        return checkpw(password.encode("utf-8"), self.password.encode("utf-8"))

    def __repr__(self):
        return f"<User {self.username}>"


# ---- Crush ----
class Crush(Base, SerializableMixin):
    __tablename__ = "crush"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, comment="Crush 姓名")
    gender = Column(Enum(UserGender), nullable=False, comment="Crush 性别")
    mbti = Column(Enum(MBTI), nullable=True, comment="Crush MBTI 类型")
    birthday = Column(Text, nullable=True, comment="生日")
    occupation = Column(String(128), nullable=True, comment="职业")
    education = Column(String(128), nullable=True, comment="教育背景")
    residence = Column(String(128), nullable=True, comment="常住地")
    hometown = Column(String(128), nullable=True, comment="家乡")
    communication_style = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="交流风格",
    )
    likes = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="喜好",
    )
    dislikes = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="不喜欢",
    )
    boundaries = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="个人边界",
    )
    traits = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="个人特点",
    )  # 模型根据上下文推断
    lifestyle_tags = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="生活方式",
    )
    values = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="价值观",
    )
    appearance_tags = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="外在特征",
    )
    other_info = Column(
        MutableList.as_mutable(ARRAY(JSONB)),
        nullable=False,
        default=[],
        comment="其他信息",
    )
    # 重要：双方对彼此的语言风格，决定虚拟形象准确与否的关键
    words_to_user = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="ta对我讲的话",
    )
    words_from_user = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="我对ta讲的话",
    )

    created_at = Column(
        DateTime, default=datetime.now(timezone.utc), comment="Crush 创建时间"
    )

    def __repr__(self):
        return f"<Crush {self.name}>"


# ---- 关系链 ----
class RelationChain(Base, SerializableMixin):
    __tablename__ = "relation_chain"
    # 每个用户只能有一个与每个Crush的关系链
    __table_args__ = (
        UniqueConstraint("user_id", "crush_id", name="uq_user_crush_relation"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联用户ID",
    )
    user = relationship("User", backref="relation_chains")

    crush_id = Column(
        Integer,
        ForeignKey("crush.id"),
        nullable=False,
        index=True,
        comment="关联CrushID",
    )
    crush = relationship("Crush", backref="relation_chains")

    current_stage = Column(
        Enum(RelationStage),
        default=RelationStage.STRANGER,
        nullable=False,
        comment="当前关系阶段",
    )
    stage_confidence = Column(
        Float,
        nullable=False,
        default=1.0,
        comment="当前关系阶段置信度",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否进行中",
    )

    # 在虚拟形象对话中，放到SystemMessage中
    context_block = Column(Text, nullable=True, comment="关系与画像上下文")

    created_at = Column(
        DateTime, default=datetime.now(timezone.utc), comment="关系链创建时间"
    )
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        comment="关系链更新时间",
    )

    def __repr__(self):
        return f"<RelationChain {self.id}>"


# ---- 以下均为上下文 ----
# ---- 事件 ----
class Event(Base, SerializableMixin):
    __tablename__ = "event"

    id = Column(Integer, primary_key=True, autoincrement=True)
    relation_chain_id = Column(
        Integer,
        ForeignKey("relation_chain.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联关系链ID",
    )
    relation_chain = relationship("RelationChain", backref="events")

    content = Column(Text, nullable=False, comment="事件内容")
    weight = Column(
        Float, nullable=False, index=True, default=1.0, comment="事件权重（重要性）"
    )
    date = Column(
        Text,
        nullable=True,
        comment="事件日期（自然语言描述）",
    )
    summary = Column(Text, nullable=True, comment="事件摘要")
    outcome = Column(
        Enum(Attitude),
        nullable=False,
        index=True,
        comment="事件结果导向",
    )
    other_info = Column(
        MutableList.as_mutable(ARRAY(JSONB)),
        nullable=False,
        default=[],
        comment="其他信息",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否有效",
    )
    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        index=True,
        comment="事件创建时间",
    )
    last_used_at = Column(
        DateTime,
        nullable=True,
        index=True,
        comment="最后使用时间",
    )

    def __repr__(self):
        return f"<Event {self.summary}>"


# ---- 聊天话题 ----
class ChatTopic(Base, SerializableMixin):
    __tablename__ = "chat_topic"

    id = Column(Integer, primary_key=True, autoincrement=True)
    relation_chain_id = Column(
        Integer,
        ForeignKey("relation_chain.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联关系链ID",
    )
    relation_chain = relationship("RelationChain", backref="chat_topics")

    title = Column(String(128), nullable=False, comment="话题标题")
    summary = Column(Text, nullable=True, comment="话题摘要")
    content = Column(Text, nullable=False, comment="话题内容")
    tags = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="话题标签",
    )
    participants = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="参与者",
    )
    source_urls = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="来源截图url",
    )
    topic_time = Column(
        String(128),
        nullable=True,
        comment="话题相关时间",
    )
    channel = Column(
        Enum(ChatChannel),
        nullable=True,
        comment="渠道",
    )
    attitude = Column(
        Enum(Attitude),
        nullable=True,
        comment="话题情绪",
    )
    weight = Column(
        Float, nullable=False, index=True, default=1.0, comment="权重（重要性）"
    )
    other_info = Column(
        MutableList.as_mutable(ARRAY(JSONB)),
        nullable=False,
        default=[],
        comment="其他信息",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否有效",
    )
    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        index=True,
        comment="创建时间",
    )
    last_used_at = Column(
        DateTime,
        nullable=True,
        index=True,
        comment="最后使用时间",
    )

    def __repr__(self):
        return f"<ChatTopic {self.summary}>"


# ---- 互动信号（通过CHAT_TOPIC推断）（暂未启用） ----
class InteractionSignal(Base, SerializableMixin):
    __tablename__ = "interaction_signal"

    id = Column(Integer, primary_key=True, autoincrement=True)
    relation_chain_id = Column(
        Integer,
        ForeignKey("relation_chain.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联关系链ID",
    )
    relation_chain = relationship("RelationChain", backref="interaction_signals")

    frequency = Column(Enum(Degree), nullable=False, comment="互动频率")
    attitude = Column(Enum(Attitude), nullable=False, comment="态度")
    window = Column(Enum(WindowOnListen), nullable=False, comment="观测时间窗口")
    note = Column(Text, nullable=True, comment="备注")
    confidence = Column(Float, nullable=False, comment="置信度（可靠性）")
    weight = Column(
        Float, nullable=False, index=True, default=1.0, comment="洞察权重（重要性）"
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否有效",
    )
    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        index=True,
        comment="创建时间",
    )
    last_used_at = Column(
        DateTime,
        nullable=True,
        index=True,
        comment="最后使用时间",
    )

    def __repr__(self):
        return f"<InteractionSignal {self.id}>"


# ---- 推断/洞察（Crush信息、事件和聊天话题综合推断） ----
class DerivedInsight(Base, SerializableMixin):
    __tablename__ = "derived_insight"

    id = Column(Integer, primary_key=True, autoincrement=True)
    relation_chain_id = Column(
        Integer,
        ForeignKey("relation_chain.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联关系链ID",
    )
    relation_chain = relationship("RelationChain", backref="derived_insights")

    insight = Column(Text, nullable=False, comment="洞察内容")

    from_crush_info = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="来源crush信息",
    )
    from_event_ids = Column(
        MutableList.as_mutable(ARRAY(Integer)),
        nullable=False,
        default=[],
        comment="来源事件id",
    )
    from_chat_topic_ids = Column(
        MutableList.as_mutable(ARRAY(Integer)),
        nullable=False,
        default=[],
        comment="来源聊天话题id",
    )
    confidence = Column(Float, nullable=False, comment="洞察置信度（可靠性）")
    weight = Column(
        Float, nullable=False, index=True, default=1.0, comment="洞察权重（重要性）"
    )
    additional_info = Column(
        MutableList.as_mutable(ARRAY(JSONB)),
        nullable=False,
        default=[],
        comment="其他信息",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否有效",
    )
    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        index=True,
        comment="创建时间",
    )
    last_used_at = Column(
        DateTime,
        nullable=True,
        index=True,
        comment="最后使用时间",
    )

    def __repr__(self):
        return f"<DerivedInsight {self.insight}>"


# ---- 向量化上下文 ----
class ContextEmbedding(Base, SerializableMixin):
    __tablename__ = "context_embedding"
    # 使用HNSW索引加速余弦相似度向量检索
    __table_args__ = (
        Index(
            "ix_context_embedding_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    type = Column(Enum(EmbeddingType), nullable=False, index=True, comment="类型")

    # 从静态知识库生成时，关联知识ID
    knowledge_id = Column(
        Integer,
        ForeignKey("knowledge.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,  # 每个知识只能有一个向量化上下文
        comment="关联知识ID",
    )
    knowledge = relationship("Knowledge", backref="embeddings")
    # 从 Crush 个人资料生成时，关联 Crush ID
    crush_id = Column(
        Integer,
        ForeignKey("crush.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,  # 每个 Crush 只能有一个向量化上下文
        comment="关联 Crush ID",
    )
    crush = relationship("Crush", backref="embeddings")
    # 从事件生成时，关联事件ID
    event_id = Column(
        Integer,
        ForeignKey("event.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,  # 每个事件只能有一个向量化上下文
        comment="关联事件ID",
    )
    event = relationship("Event", backref="embeddings")
    # 从聊天话题生成时，关联聊天话题ID
    chat_topic_id = Column(
        Integer,
        ForeignKey("chat_topic.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,  # 每个聊天话题只能有一个向量化上下文
        comment="关联聊天话题ID",
    )
    chat_topic = relationship("ChatTopic", backref="embeddings")
    # 从推断/洞察生成时，关联推断/洞察ID
    derived_insight_id = Column(
        Integer,
        ForeignKey("derived_insight.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,  # 每个推断/洞察只能有一个向量化上下文
        comment="关联推断/洞察ID",
    )
    derived_insight = relationship("DerivedInsight", backref="embeddings")

    model_name = Column(
        String(128),
        nullable=False,
        comment="Embedding模型名称",
    )
    embedding = Column(
        Vector(1024), nullable=False, comment="向量表示"
    )  # 重要：模型只支持1024、2048维向量，但hnsw索引要求维度必须小于2000
    created_at = Column(
        DateTime, default=datetime.now(timezone.utc), comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        comment="更新时间",
    )

    def __repr__(self):
        return f"<ContextEmbedding {self.id}>"


# ---- 静态知识库 ----
class Knowledge(Base, SerializableMixin):
    __tablename__ = "knowledge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False, comment="知识库内容")
    weight = Column(
        Float, nullable=False, index=True, default=1.0, comment="知识库权重（重要性）"
    )
    summary = Column(Text, nullable=True, comment="知识库摘要")
    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        index=True,
        comment="知识库创建时间",
    )
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        comment="知识库更新时间",
    )

    def __repr__(self):
        return f"<Knowledge {self.summary}>"


# ---- 分析 ----
class Analysis(Base, SerializableMixin):
    __tablename__ = "analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    relation_chain_id = Column(
        Integer,
        ForeignKey("relation_chain.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联关系链ID",
    )
    relation_chain = relationship("RelationChain", backref="analyses")

    type = Column(Enum(AnalysisType), nullable=False, index=True, comment="分析类型")
    # 聊天记录分析
    conversation_screenshots = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=True,
        default=[],
        comment="聊天记录截图url",
    )
    additional_context = Column(Text, nullable=True, comment="补充上下文")
    # 自然语言叙述分析
    narrative = Column(Text, nullable=True, comment="自然语言叙述")

    # 分析结果
    message_candidates = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="下一步消息候选",
    )
    risks = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="风险提示",
    )
    suggestions = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="下一步推进话题或行动建议",
    )

    context_block = Column(
        Text, nullable=False, default="", comment="关系与画像上下文"
    )  # 用于记忆

    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        index=True,
        comment="分析创建时间",
    )

    def __repr__(self):
        return f"<Analysis {self.id}>"


# # ---- 上下文冲突（暂时弃用） ----
# class ContextConflict(Base, SerializableMixin):
#     __tablename__ = "context_conflict"

#     id = Column(Integer, primary_key=True, autoincrement=True)
#     relation_chain_id = Column(
#         Integer,
#         ForeignKey("relation_chain.id", ondelete="CASCADE"),
#         nullable=False,
#         comment="关联关系链ID",
#     )
#     relation_chain = relationship("RelationChain", backref="context_conflicts")

#     type = Column(Enum(ConflictType), nullable=False, index=True, comment="冲突类型")

#     # 与已有上下文冲突时，前者上下文ID
#     former_context_id = Column(
#         Integer,
#         ForeignKey("context.id", ondelete="SET NULL"),
#         nullable=True,
#         comment="前者上下文ID",
#     )
#     former_context = relationship(
#         "Context",
#         foreign_keys=[former_context_id],
#         backref="former_conflicts",
#     )

#     # 与知识库冲突时，知识ID
#     former_knowledge_id = Column(
#         Integer,
#         ForeignKey("knowledge.id", ondelete="SET NULL"),
#         nullable=True,
#         comment="前者知识ID",
#     )
#     former_knowledge = relationship("Knowledge", backref="former_conflicts")

#     latter_context_id = Column(
#         Integer,
#         ForeignKey("context.id", ondelete="SET NULL"),
#         nullable=False,
#         comment="后者上下文ID",
#     )
#     latter_context = relationship(
#         "Context",
#         foreign_keys=[latter_context_id],
#         backref="latter_conflicts",
#     )

#     conflict_reason = Column(Text, nullable=True, comment="冲突原因")
#     resolution_status = Column(
#         Enum(ConflictResolutionStatus),
#         nullable=False,
#         default=ConflictResolutionStatus.PENDING,
#         comment="冲突解决状态",
#     )
#     created_at = Column(
#         DateTime, default=datetime.now(timezone.utc), comment="冲突创建时间"
#     )
#     updated_at = Column(
#         DateTime,
#         default=datetime.now(timezone.utc),
#         onupdate=datetime.now(timezone.utc),
#         comment="冲突更新时间",
#     )

#     def __repr__(self):
#         return f"<ContextConflict {self.id}>"
