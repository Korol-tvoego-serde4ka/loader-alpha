from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

# Таблица связей пользователей и их инвайтов
user_invites = Table(
    'user_invites',
    Base.metadata,
    Column('inviter_id', Integer, ForeignKey('users.id')),
    Column('invited_id', Integer, ForeignKey('users.id'))
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    discord_id = Column(String, unique=True, nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Отношения
    keys = relationship("Key", back_populates="user")
    invited_users = relationship(
        "User",
        secondary=user_invites,
        primaryjoin=id==user_invites.c.inviter_id,
        secondaryjoin=id==user_invites.c.invited_id,
        backref="invited_by"
    )

class Key(Base):
    __tablename__ = "keys"

    id = Column(Integer, primary_key=True, index=True)
    key_value = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    is_used = Column(Boolean, default=False)
    is_test = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    used_at = Column(DateTime(timezone=True), nullable=True)

    # Отношения
    user = relationship("User", back_populates="keys", foreign_keys=[user_id])
    creator = relationship("User", foreign_keys=[created_by])

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    version = Column(String)
    file_path = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_token = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    last_activity = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User") 