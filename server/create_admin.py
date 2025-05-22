#!/usr/bin/env python3
"""
Скрипт для создания администратора в базе данных
"""

import os
import sys
import logging
from passlib.context import CryptContext

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Настройка шифрования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Добавление пути к родительской директории
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Абсолютный путь к БД
DB_PATH = os.path.join(current_dir, 'database.db')

# Явно настраиваем путь к БД через переменную окружения
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
logger.info(f"Установлен DATABASE_URL: {os.environ['DATABASE_URL']}")

try:
    # Импортируем модели
    from database.models import SessionLocal, User
    
    # Проверяем, существует ли файл БД
    if os.path.exists(DB_PATH):
        logger.info(f"База данных найдена: {DB_PATH}")
    else:
        logger.error(f"База данных не найдена по пути: {DB_PATH}")
        sys.exit(1)
    
    # Создаем сессию
    db = SessionLocal()
    
    # Параметры админа - можно изменить
    admin_username = "admin"
    admin_password = "adminpass123"
    admin_email = "admin@example.com"
    
    try:
        # Проверяем, существует ли уже админ
        existing_admin = db.query(User).filter(User.is_admin == True).first()
        if existing_admin:
            logger.info(f"Администратор уже существует: {existing_admin.username} (ID: {existing_admin.id})")
            sys.exit(0)
        
        # Проверяем, занято ли имя пользователя
        existing_user = db.query(User).filter(User.username == admin_username).first()
        if existing_user:
            logger.error(f"Пользователь с именем {admin_username} уже существует!")
            sys.exit(1)
        
        # Хешируем пароль
        hashed_password = pwd_context.hash(admin_password)
        
        # Создаем администратора
        admin = User(
            username=admin_username,
            email=admin_email,
            password_hash=hashed_password,
            is_admin=True
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        logger.info(f"Администратор успешно создан: {admin.username} (ID: {admin.id})")
        logger.info(f"Пароль администратора: {admin_password} (сохраните его)")
        
    finally:
        db.close()
    
except Exception as e:
    logger.error(f"Ошибка при создании администратора: {str(e)}")
    import traceback
    logger.error(traceback.format_exc()) 