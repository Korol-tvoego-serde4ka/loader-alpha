from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, create_engine, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func
import os
import secrets
import string
import datetime
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка подключения к базе данных
DB_USER = os.getenv("DB_USER", "loader_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "loader_alpha")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Создание базового класса для моделей
Base = declarative_base()

# Создание генератора случайных строк для ключей и кодов
def generate_random_string(length=4, segments=4):
    """Генерирует случайную строку в формате XXXX-XXXX-XXXX-XXXX"""
    chars = string.ascii_uppercase + string.digits
    segments_list = []
    for _ in range(segments):
        segment = ''.join(secrets.choice(chars) for _ in range(length))
        segments_list.append(segment)
    return "-".join(segments_list)

# Модель пользователя
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    is_admin = Column(Boolean, default=False)
    is_support = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    
    # Discord интеграция
    discord_id = Column(String(50), unique=True, nullable=True)
    discord_username = Column(String(100), nullable=True)
    
    # Информация о последнем входе
    last_login = Column(DateTime, nullable=True)
    last_ip = Column(String(45), nullable=True)  # IPv6 может быть до 45 символов
    
    # Отношения
    keys = relationship("Key", back_populates="user")
    created_invites = relationship("Invite", back_populates="created_by", foreign_keys="Invite.created_by_id")
    used_invite = relationship("Invite", uselist=False, back_populates="used_by", foreign_keys="Invite.used_by_id")
    discord_codes = relationship("DiscordCode", back_populates="user")
    
    def update_login_info(self, ip_address):
        """Обновляет информацию о последнем входе пользователя"""
        self.last_login = datetime.datetime.utcnow()
        self.last_ip = ip_address
        
    def can_create_invite(self):
        """Проверяет, может ли пользователь создавать инвайты"""
        return self.is_admin or self.is_support  # Админы и саппорты могут создавать инвайты

# Модель ключа
class Key(Base):
    __tablename__ = "keys"

    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True, nullable=False, default=lambda: generate_random_string())
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Может быть не привязан к пользователю
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    activated_at = Column(DateTime, nullable=True)  # Время привязки к аккаунту
    
    # Отношения
    user = relationship("User", back_populates="keys")
    
    def is_expired(self):
        """Проверяет, истёк ли ключ"""
        return datetime.datetime.utcnow() > self.expires_at

    def time_left(self):
        """Возвращает оставшееся время действия ключа в секундах"""
        if self.is_expired():
            return 0
        delta = self.expires_at - datetime.datetime.utcnow()
        return max(0, int(delta.total_seconds()))
        
    @classmethod
    def create_custom_key(cls, key_value, user_id=None, duration_hours=24):
        """Создает ключ с пользовательским значением"""
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=duration_hours)
        return cls(
            key=key_value,
            user_id=user_id,
            expires_at=expires_at
        )

# Модель инвайт-кода
class Invite(Base):
    __tablename__ = "invites"

    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False, default=lambda: generate_random_string())
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    used_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Отношения
    created_by = relationship("User", back_populates="created_invites", foreign_keys=[created_by_id])
    used_by = relationship("User", back_populates="used_invite", foreign_keys=[used_by_id])
    
    def is_expired(self):
        """Проверяет, истёк ли инвайт-код"""
        return datetime.datetime.utcnow() > self.expires_at

# Модель кода для привязки Discord аккаунта
class DiscordCode(Base):
    __tablename__ = "discord_codes"

    id = Column(Integer, primary_key=True)
    code = Column(String(10), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    
    # Отношения
    user = relationship("User", back_populates="discord_codes")
    
    def is_expired(self):
        """Проверяет, истёк ли код привязки"""
        return datetime.datetime.utcnow() > self.expires_at

# Модель лимитов ролей для инвайтов
class RoleLimits(Base):
    __tablename__ = "role_limits"
    
    id = Column(Integer, primary_key=True)
    admin_monthly_invites = Column(Integer, nullable=False, default=999)  # Практически неограниченно для админов
    support_monthly_invites = Column(Integer, nullable=False, default=10)
    user_monthly_invites = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

# Создание соединения с базой данных
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Функция для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Функция для инициализации базы данных
def init_db():
    Base.metadata.create_all(bind=engine) 