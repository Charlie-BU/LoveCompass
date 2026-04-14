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
    Index,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.dialects.postgresql import ARRAY
from pgvector.sqlalchemy import Vector
from bcrypt import hashpw, gensalt, checkpw
from datetime import datetime, timezone

from src.database.enums import (
    MBTI,
    AnalysisType,
    ConflictStatus,
    FigureRole,
    FineGrainedFeedConfidence,
    FineGrainedFeedDimension,
    Gender,
    UserLevel,
    OriginalSourceType,
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


class SerializableMixin:
    """
    可序列化Mixin基类，提供toJson方法将模型实例转换为JSON
    """

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


class User(Base, SerializableMixin):
    """用户"""

    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)

    username = Column(
        String(64), unique=True, nullable=False, index=True, comment="用户唯一用户名"
    )
    password = Column(String(128), nullable=False, comment="用户密码")
    nickname = Column(String(64), nullable=True, index=True, comment="用户昵称")
    gender = Column(Enum(Gender), nullable=False, comment="用户性别")
    email = Column(String(128), nullable=True, unique=True, comment="用户邮箱")
    level = Column(Enum(UserLevel), default=UserLevel.L4, comment="用户等级")

    lark_open_id = Column(
        String(128), nullable=True, unique=True, comment="用户飞书open_id"
    )
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


class FigureAndRelation(Base, SerializableMixin):
    """人物及关系"""

    __tablename__ = "figure_and_relation"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(
        Integer, ForeignKey("user.id"), nullable=False, comment="创建的用户ID"
    )
    user = relationship("User", backref="figure_and_relations")

    figure_role = Column(
        Enum(FigureRole),
        default=FigureRole.STRANGER,
        nullable=False,
        comment="Figure 角色",
    )
    # Figure 基本信息
    figure_name = Column(String(64), nullable=False, comment="Figure 姓名")
    figure_gender = Column(Enum(Gender), nullable=False, comment="Figure 性别")
    figure_mbti = Column(Enum(MBTI), nullable=True, comment="Figure MBTI 类型")
    figure_birthday = Column(String(128), nullable=True, comment="Figure 生日")
    figure_occupation = Column(String(128), nullable=True, comment="Figure 职业")
    figure_education = Column(String(128), nullable=True, comment="Figure 教育背景")
    figure_residence = Column(String(128), nullable=True, comment="Figure 常住地")
    figure_hometown = Column(String(128), nullable=True, comment="Figure 家乡地")
    figure_appearance = Column(String(128), nullable=True, comment="Figure 外在特征")
    figure_likes = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="Figure 喜好",
    )
    figure_dislikes = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="Figure 不喜欢",
    )

    # 重要：双方对彼此的语言风格，决定虚拟形象准确与否的关键
    words_figure2user = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="Figure 真实对用户讲的话",
    )
    words_user2figure = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="用户真实对 Figure 讲的话",
    )

    # 详细信息（markdown 动态填充）
    exact_relation = Column(
        Text,
        nullable=False,
        default="",
        comment="精确关系描述",
    )

    # 以下四个字段为细粒度信息表提炼而来
    # 以下两个字段低语境依赖，需尽量详细
    core_personality = Column(
        Text,
        nullable=False,
        default="",
        comment="核心性格与价值观",
    )
    core_interaction_style = Column(
        Text,
        nullable=False,
        default="",
        comment="核心互动风格",
    )
    # 以下两个字段高语境依赖，需极简
    core_procedural_info = Column(
        Text,
        nullable=False,
        default="",
        comment="核心程序性知识（ta怎么做事）",
    )
    core_memory = Column(
        Text,
        nullable=False,
        default="",
        comment="核心人生记忆与故事",
    )

    is_deleted = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否删除",
    )
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
        return f"<FigureAndRelation {self.name}>"


class FineGrainedFeed(Base, SerializableMixin):
    """细粒度信息，包含：
    性格与价值观 personality、
    互动风格 interaction_style、
    程序性知识 procedural_info、
    人生记忆与故事 memory
    其他 other
    【支持向量化召回】
    """

    __tablename__ = "fine_grained_feed"
    # 使用HNSW索引加速余弦相似度向量检索
    __table_args__ = (
        Index(
            "ix_fine_grained_feed_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    fr_id = Column(
        Integer,
        ForeignKey("figure_and_relation.id"),
        nullable=False,
        comment="关联的 FigureAndRelation ID",
    )
    figure_and_relation = relationship(
        "FigureAndRelation",
        backref="fine_grained_feeds",
        lazy="select",
    )
    original_source_id = Column(
        Integer,
        ForeignKey("original_source.id"),
        nullable=False,
        comment="关联原始输入材料ID",
    )
    original_source = relationship(
        "OriginalSource",
        backref="fine_grained_feeds",
        lazy="select",  # 关联查询原始输入材料时，只查询关联的原始输入材料，不查询所有原始输入材料
    )

    dimension = Column(
        Enum(FineGrainedFeedDimension),
        nullable=False,
        comment="维度",
    )
    sub_dimension = Column(
        String(64),
        nullable=True,
        comment="子维度",
    )
    confidence = Column(
        Enum(FineGrainedFeedConfidence),
        nullable=False,
        comment="证据级别",
    )

    content = Column(Text, nullable=False, comment="文本内容")

    # 向量化
    embedding_model_name = Column(
        String(128),
        nullable=False,
        comment="Embedding 模型名称",
    )
    embedding = Column(
        Vector(1024), nullable=False, comment="向量表示"
    )  # 重要：模型只支持1024、2048维向量，但hnsw索引要求维度必须小于2000

    is_deleted = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否删除",
    )
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
        return f"<FineGrainedFeed {self.id}>"


class OriginalSource(Base, SerializableMixin):
    """原始信息来源（经预处理后）"""

    __tablename__ = "original_source"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fr_id = Column(
        Integer,
        ForeignKey("figure_and_relation.id"),
        nullable=False,
        comment="关联的 FigureAndRelation ID",
    )
    figure_and_relation = relationship(
        "FigureAndRelation",
        backref="original_sources",
        lazy="select",
    )

    # 元数据
    type = Column(
        Enum(OriginalSourceType),
        nullable=False,
        comment="来源类型",
    )
    approx_date = Column(
        String(32), nullable=True, comment="大致日期：2025-Q3 / 2026-01-15"
    )
    confidence = Column(
        Enum(FineGrainedFeedConfidence),
        nullable=False,
        comment="证据级别",
    )
    included_dimensions = Column(
        ARRAY(Enum(FineGrainedFeedDimension)),
        nullable=False,
        comment="涉及维度",
    )

    # 内容
    content = Column(Text, nullable=False, comment="原始文本内容")

    is_deleted = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否删除",
    )
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
        return f"<OriginalSource {self.id}>"


class FineGrainedFeedConflict(Base, SerializableMixin):
    """细粒度信息冲突记录"""

    __tablename__ = "fine_grained_feed_conflict"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fr_id = Column(
        Integer,
        ForeignKey("figure_and_relation.id"),
        nullable=False,
        comment="关联的 FigureAndRelation ID",
    )
    figure_and_relation = relationship(
        "FigureAndRelation",
        backref="fine_grained_feed_conflicts",
        lazy="select",
    )

    dimension = Column(
        Enum(FineGrainedFeedDimension),
        nullable=False,
        comment="冲突所在维度",
    )
    feed_ids = Column(
        MutableList.as_mutable(ARRAY(Integer)),
        nullable=False,
        comment="冲突的细粒度信息ID列表",
    )
    conflict_detail = Column(Text, nullable=False, comment="冲突详情")
    status = Column(
        Enum(ConflictStatus),
        nullable=False,
        default=ConflictStatus.PENDING,
        comment="冲突状态",
    )

    created_at = Column(
        DateTime, default=datetime.now(timezone.utc), comment="创建时间"
    )

    def __repr__(self):
        return f"<FineGrainedFeedConflict {self.id}>"


class FROverallUpdateLog(Base, SerializableMixin):
    """FR 相关所有信息变动日志（包含 fr 内在字段和 feed 变动）"""

    __tablename__ = "fr_overall_update_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    fr_id = Column(
        Integer,
        ForeignKey("figure_and_relation.id"),
        nullable=False,
        comment="关联的 FigureAndRelation ID",
    )
    figure_and_relation = relationship(
        "FigureAndRelation",
        backref="fr_overall_update_logs",
        lazy="select",
    )

    update_field_or_sub_dimension = Column(
        String(128),
        nullable=False,
        default="",
        comment="变动字段（fr 内在字段变动）或子维度（feed 变动）",
    )
    update_dimension = Column(
        Enum(FineGrainedFeedDimension),
        nullable=True,
        comment="变动维度（只有 feed 变动时存在）",
    )
    old_value = Column(
        Text,
        nullable=True,
        comment="变动前的值",
    )
    new_value = Column(
        Text,
        nullable=True,
        comment="变动后的值",
    )

    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        comment="变动时间",
    )

    def __repr__(self):
        return f"<FROverallUpdateLog {self.id}>"


class Knowledge(Base, SerializableMixin):
    """私有知识库"""

    __tablename__ = "knowledge"
    # 使用HNSW索引加速余弦相似度向量检索
    __table_args__ = (
        Index(
            "ix_knowledge_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(
        Integer, ForeignKey("user.id"), nullable=False, comment="创建的用户ID"
    )
    user = relationship("User", backref="knowledge_pieces")

    content = Column(Text, nullable=False, comment="知识内容")
    weight = Column(
        Float, nullable=False, index=True, default=1.0, comment="知识权重（重要性）"
    )

    # 向量化
    embedding_model_name = Column(
        String(128),
        nullable=False,
        comment="Embedding 模型名称",
    )
    embedding = Column(
        Vector(1024), nullable=False, comment="向量表示"
    )  # 重要：模型只支持1024、2048维向量，但hnsw索引要求维度必须小于2000

    is_deleted = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否删除",
    )
    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        index=True,
        comment="知识创建时间",
    )
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        comment="知识更新时间",
    )

    def __repr__(self):
        return f"<Knowledge {self.id}>"


class Analysis(Base, SerializableMixin):
    """分析记录"""

    __tablename__ = "analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fr_id = Column(
        Integer,
        ForeignKey("figure_and_relation.id"),
        nullable=False,
        comment="关联的 FigureAndRelation ID",
    )
    figure_and_relation = relationship(
        "FigureAndRelation",
        backref="analyses",
        lazy="select",
    )

    type = Column(Enum(AnalysisType), nullable=False, index=True, comment="分析类型")
    # 聊天记录分析
    screenshots = Column(
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
        comment="回复消息候选",
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

    created_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        index=True,
        comment="创建时间",
    )

    def __repr__(self):
        return f"<Analysis {self.id}>"
