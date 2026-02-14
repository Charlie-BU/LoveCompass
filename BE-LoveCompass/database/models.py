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
    text,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from datetime import datetime, timezone

from .enums import (
    UserGender,
    UserLevel,
    MBTI,
    RelationStage,
    ContextType,
    ContextSource,
    ConflictResolutionStatus,
)
from bcrypt import hashpw, gensalt, checkpw

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
    personality_tags = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="用户性格标签",
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


# ---- Crush ----
class Crush(Base, SerializableMixin):
    __tablename__ = "crush"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, comment="Crush 姓名")
    gender = Column(Enum(UserGender), nullable=False, comment="Crush 性别")
    mbti = Column(Enum(MBTI), nullable=True, comment="Crush MBTI 类型")
    personality_tags = Column(
        MutableList.as_mutable(ARRAY(Text)),
        nullable=False,
        default=[],
        comment="Crush 性格标签",
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
        comment="关联用户ID",
    )
    user = relationship("User", backref="relation_chains")

    crush_id = Column(
        Integer,
        ForeignKey("crush.id", ondelete="SET NULL"),
        nullable=False,
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


# ---- 阶段变更历史 ----
class ChainStageHistory(Base, SerializableMixin):
    __tablename__ = "chain_stage_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    relation_chain_id = Column(
        Integer,
        ForeignKey("relation_chain.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联关系链ID",
    )
    relation_chain = relationship("RelationChain", backref="stage_histories")

    trigger_context_id = Column(
        Integer,
        ForeignKey("context.id", ondelete="SET NULL"),
        nullable=True,
        comment="触发变更的上下文ID",
    )
    trigger_context = relationship("Context", backref="stage_histories")

    previous_stage = Column(
        Enum(RelationStage), nullable=True, comment="变更前的关系阶段"
    )
    new_stage = Column(Enum(RelationStage), nullable=False, comment="变更后的关系阶段")
    trigger_reason = Column(Text, nullable=True, comment="触发变更的原因")
    confidence = Column(
        Float, nullable=False, default=1.0, comment="变更后的关系阶段置信度"
    )
    created_at = Column(
        DateTime, default=datetime.now(timezone.utc), comment="变更时间"
    )

    def __repr__(self):
        return f"<ChainStageHistory {self.id}>"


# ---- 上下文 ----
# 注意：Context 添加后内容不可修改
class Context(Base, SerializableMixin):
    __tablename__ = "context"

    id = Column(Integer, primary_key=True, autoincrement=True)
    relation_chain_id = Column(
        Integer,
        ForeignKey("relation_chain.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联关系链ID",
    )
    relation_chain = relationship("RelationChain", backref="contexts")

    type = Column(Enum(ContextType), nullable=False, comment="Context类型")
    content = Column(
        JSONB,
        server_default=text("'{}'::jsonb"),
        nullable=False,
        comment="Context内容",
    )
    weight = Column(
        Float, nullable=False, default=1.0, comment="Context 权重（影响力）"
    )
    confidence = Column(
        Float, nullable=False, default=1.0, comment="Context 置信度（可靠性）"
    )
    summary = Column(Text, nullable=True, comment="Context 摘要")
    source = Column(Enum(ContextSource), nullable=False, comment="Context 来源")

    derived_from_context_id = Column(
        Integer,
        ForeignKey("context.id", ondelete="CASCADE"),
        nullable=True,
        comment="来源上下文ID（如果是派生上下文）",
    )
    derived_from_context = relationship(
        "Context", backref="child_contexts", remote_side=[id]
    )

    is_conflicted = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否与其他上下文冲突",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否有效",
    )
    created_at = Column(
        DateTime, default=datetime.now(timezone.utc), comment="上下文创建时间"
    )
    last_used_at = Column(
        DateTime,
        nullable=True,
        comment="最后使用时间",
    )

    def __repr__(self):
        return f"<Context {self.id}>"


# ---- 上下文冲突 ----
class ContextConflict(Base, SerializableMixin):
    __tablename__ = "context_conflict"

    id = Column(Integer, primary_key=True, autoincrement=True)
    relation_chain_id = Column(
        Integer,
        ForeignKey("relation_chain.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联关系链ID",
    )
    relation_chain = relationship("RelationChain", backref="context_conflicts")

    former_context_id = Column(
        Integer,
        ForeignKey("context.id", ondelete="SET NULL"),
        nullable=False,
        comment="前者上下文ID",
    )
    former_context = relationship("Context", backref="former_conflicts")

    latter_context_id = Column(
        Integer,
        ForeignKey("context.id", ondelete="SET NULL"),
        nullable=False,
        comment="后者上下文ID",
    )
    latter_context = relationship("Context", backref="latter_conflicts")

    conflict_reason = Column(Text, nullable=True, comment="冲突原因")
    resolution_status = Column(
        Enum(ConflictResolutionStatus),
        nullable=False,
        default=ConflictResolutionStatus.PENDING,
        comment="冲突解决状态",
    )
    created_at = Column(
        DateTime, default=datetime.now(timezone.utc), comment="冲突创建时间"
    )
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        comment="冲突更新时间",
    )

    def __repr__(self):
        return f"<ContextConflict {self.id}>"
