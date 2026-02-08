from sqlalchemy import (
    inspect,
    Table,
    Column,
    String,
    Integer,
    Boolean,
    ForeignKey,
    Enum,
    Text,
    DateTime,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, timezone

from .enums import (
    HttpMethod,
    ApiLevel,
    ParamLocation,
    ParamType,
    UserRole,
    UserLevel,
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


# ---- 用户表 ----
class User(Base, SerializableMixin):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)

    username = Column(String(64), unique=True, nullable=False, index=True)
    password = Column(String(128), nullable=False)
    nickname = Column(String(64), nullable=True, index=True)
    email = Column(String(128), nullable=True, unique=True)
    level = Column(Enum(UserLevel), default=UserLevel.L4)
    created_at = Column(DateTime, server_default=func.now())

    @staticmethod
    def hashPassword(password):
        hashed = hashpw(password.encode("utf-8"), gensalt())
        return hashed.decode("utf-8")

    def checkPassword(self, password):
        return checkpw(password.encode("utf-8"), self.password.encode("utf-8"))

    def __repr__(self):
        return f"<User {self.username}>"
