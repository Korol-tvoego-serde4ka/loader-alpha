from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, create_engine, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func
import os
import secrets
import string
import datetime
from dotenv import load_dotenv
import logging

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Настройка подключения к базе данных
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "loader_alpha")

# URL для PostgreSQL
PG_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# URL для SQLite (запасной вариант)
SQLITE_DATABASE_URL = "sqlite:///./database.db"

# Сначала пробуем использовать PostgreSQL, если не получится - используем SQLite
try:
    # Пробуем создать движок PostgreSQL
    engine = create_engine(PG_DATABASE_URL)
    # Пробуем подключиться
    conn = engine.connect()
    conn.close()
    DATABASE_URL = PG_DATABASE_URL
    print("Подключение к PostgreSQL успешно установлено")
except Exception as e:
    print(f"Не удалось подключиться к PostgreSQL: {str(e)}. Используем SQLite.")
    # Используем SQLite
    DATABASE_URL = SQLITE_DATABASE_URL
    engine = create_engine(SQLITE_DATABASE_URL, connect_args={"check_same_thread": False})

# Создание базового класса для моделей
Base = declarative_base()

# Создание генератора случайных строк для ключей и кодов
def generate_random_string(length=16):
    """Генерация случайной строки заданной длины"""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

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
    key = Column(String(50), unique=True, nullable=False, default=lambda: generate_random_string(32))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    activated_at = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=False, default=86400)  # Длительность в секундах (по умолчанию 1 день)
    is_active = Column(Boolean, default=True)  # Активен ли ключ (можно отозвать)
    
    # Отношения
    user = relationship("User", back_populates="keys")
    
    @property
    def expires_at(self):
        """Возвращает дату/время истечения ключа"""
        if not self.activated_at:
            # Если ключ не активирован, возвращаем дату создания + продолжительность
            return self.created_at + datetime.timedelta(seconds=self.duration)
        return self.activated_at + datetime.timedelta(seconds=self.duration)
    
    def is_expired(self):
        """Проверяет, истек ли ключ"""
        # Если ключ не активирован, он не истекает
        if not self.activated_at:
            return False
        return datetime.datetime.utcnow() > self.expires_at
    
    @property
    def time_left(self):
        """Возвращает оставшееся время действия ключа в секундах"""
        if not self.is_active:
            return 0
        
        # Если ключ не активирован, возвращаем полную продолжительность
        if not self.activated_at:
            return self.duration
            
        if self.is_expired():
            return 0
        
        remaining = (self.expires_at - datetime.datetime.utcnow()).total_seconds()
        return max(0, int(remaining))

    @classmethod
    def create_custom_key(cls, db, duration_hours=24, user_id=None, custom_key=None):
        """Создает ключ с заданными параметрами"""
        duration_seconds = duration_hours * 3600
        
        key = Key(
            user_id=user_id,
            duration=duration_seconds
        )
        
        if custom_key:
            # Проверяем, существует ли такой ключ
            existing_key = db.query(Key).filter(Key.key == custom_key).first()
            if existing_key:
                raise ValueError("Ключ с таким значением уже существует")
            key.key = custom_key
        
        db.add(key)
        db.commit()
        db.refresh(key)
        
        return key

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
    code = Column(String(8), unique=True, nullable=False, default=lambda: generate_random_string(8))
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
    try:
        logger.info("Начало создания таблиц в базе данных...")
        Base.metadata.create_all(bind=engine)
        
        # Создаем запись с лимитами, если её нет
        db = SessionLocal()
        try:
            role_limits = db.query(RoleLimits).first()
            if not role_limits:
                logger.info("Создание начальных лимитов для ролей...")
                role_limits = RoleLimits()
                db.add(role_limits)
                db.commit()
                logger.info("Начальные лимиты для ролей созданы успешно")
        except Exception as e:
            logger.error(f"Ошибка при создании лимитов для ролей: {str(e)}")
        finally:
            db.close()
        
        logger.info("Таблицы успешно созданы")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {str(e)}")
        raise 