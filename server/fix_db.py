#!/usr/bin/env python3
"""
Скрипт для восстановления и инициализации базы данных
"""

import os
import sys
import datetime
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Добавление пути к родительской директории
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Абсолютный путь к БД
DB_PATH = os.path.join(current_dir, 'database.db')

# Явно настраиваем путь к БД через переменную окружения
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
logger.info(f"Установлен DATABASE_URL: {os.environ['DATABASE_URL']}")

try:
    # Импорт моделей и инициализация
    from database.models import init_db, SessionLocal, User, Invite, Base, engine
    
    # Проверяем, существует ли файл БД
    if os.path.exists(DB_PATH):
        logger.info(f"База данных найдена: {DB_PATH}")
        logger.info(f"Размер файла: {os.path.getsize(DB_PATH)} байт")
    else:
        logger.warning(f"База данных не найдена по пути: {DB_PATH}")
        logger.info("Будет создана новая база данных")
    
    # Инициализируем базу данных (создаем таблицы)
    logger.info("Инициализация базы данных...")
    init_db()
    logger.info("База данных инициализирована")
    
    # Создаем сессию
    db = SessionLocal()
    
    try:
        # Проверяем, есть ли пользователи в базе
        user_count = db.query(User).count()
        logger.info(f"Количество пользователей в базе: {user_count}")
        
        # Проверяем, есть ли админ
        admin = db.query(User).filter(User.is_admin == True).first()
        if not admin:
            logger.warning("Администратор не найден в базе!")
        else:
            logger.info(f"Администратор найден: {admin.username} (ID: {admin.id})")
            
            # Проверяем количество приглашений
            invite_count = db.query(Invite).count()
            logger.info(f"Количество приглашений в базе: {invite_count}")
            
            # Если приглашений нет, создаем тестовое приглашение от админа
            if invite_count == 0 and admin:
                logger.info("Создание тестового приглашения...")
                # Создаем приглашение со сроком действия 30 дней
                invite_expiry = datetime.datetime.utcnow() + datetime.timedelta(days=30)
                invite = Invite(
                    created_by_id=admin.id,
                    expires_at=invite_expiry
                )
                db.add(invite)
                db.commit()
                db.refresh(invite)
                logger.info(f"Создано тестовое приглашение с кодом {invite.code}")
            
            # Выводим список всех приглашений
            invites = db.query(Invite).all()
            logger.info("Список всех приглашений:")
            for invite in invites:
                status = "Использован" if invite.used else "Активен"
                logger.info(f"ID: {invite.id}, Код: {invite.code}, Статус: {status}, Создатель ID: {invite.created_by_id}")
        
    finally:
        db.close()
    
    logger.info("Проверка базы данных завершена успешно.")
    
except Exception as e:
    logger.error(f"Ошибка при работе с базой данных: {str(e)}")
    # Вывод трассировки
    import traceback
    logger.error(traceback.format_exc()) 