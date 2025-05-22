#!/usr/bin/env python
import os
import datetime
import secrets
import string
import getpass
from dotenv import load_dotenv
import sys
import logging

from database.models import init_db, SessionLocal, User, Invite, RoleLimits

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

def create_admin_user(db_session):
    """Создание пользователя-администратора"""
    # Проверка, существует ли уже пользователь admin
    existing_admin = db_session.query(User).filter_by(username="admin").first()
    if existing_admin:
        print("Пользователь admin уже существует")
        return existing_admin
    
    # Получение данных для создания администратора из переменных окружения
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    
    if not admin_password:
        admin_password = input("Введите пароль для администратора: ")
    
    # Создание хеша пароля
    password_hash = generate_password_hash(admin_password)
    
    # Создание пользователя
    admin = User(
        username=admin_username,
        email=admin_email,
        password_hash=password_hash,
        is_admin=True
    )
    
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    
    print(f"Создан аккаунт администратора: {admin_username}")
    return admin

def create_initial_invite(db_session, admin):
    """Создание начального приглашения от администратора"""
    # Установка срока действия на 30 дней
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=30)
    
    invite = Invite(
        created_by_id=admin.id,
        expires_at=expires_at
    )
    
    db_session.add(invite)
    db_session.commit()
    db_session.refresh(invite)
    
    print(f"Создан начальный инвайт-код: {invite.code}")
    return invite

def create_initial_role_limits(db_session):
    """Создание начальных лимитов для ролей"""
    existing_limits = db_session.query(RoleLimits).first()
    if existing_limits:
        print("Лимиты для ролей уже существуют")
        return existing_limits
    
    role_limits = RoleLimits(
        admin_monthly_invites=999,
        support_monthly_invites=10,
        user_monthly_invites=0
    )
    
    db_session.add(role_limits)
    db_session.commit()
    db_session.refresh(role_limits)
    
    print("Созданы начальные лимиты для ролей")
    return role_limits

def generate_password_hash(password):
    """Генерация хеша пароля"""
    import hashlib
    # Простая реализация на основе SHA-256
    return hashlib.sha256(password.encode()).hexdigest()

if __name__ == "__main__":
    try:
        # Инициализация базы данных
        print("Подключение к PostgreSQL...")
        init_db()
        print("Подключение к PostgreSQL успешно установлено")
        
        # Создание сессии для работы с базой данных
        db = SessionLocal()
        
        # Создание администратора
        admin = create_admin_user(db)
        
        # Создание начального инвайта
        invite = create_initial_invite(db, admin)
        
        # Создание начальных лимитов для ролей
        role_limits = create_initial_role_limits(db)
        
        # Закрытие сессии
        db.close()
        
        print("Инициализация базы данных завершена успешно")
    except Exception as e:
        print(f"Ошибка при инициализации базы данных: {e}")
        sys.exit(1) 