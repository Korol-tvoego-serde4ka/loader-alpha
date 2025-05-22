#!/usr/bin/env python3
import os
import sys

# Добавляем текущую директорию в путь Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем и запускаем функцию инициализации из init_db
from database.init_db import create_admin_user, create_initial_invite, create_initial_role_limits, init_db

if __name__ == "__main__":
    try:
        # Инициализация базы данных
        print("Подключение к PostgreSQL...")
        init_db()
        print("Подключение к PostgreSQL успешно установлено")
        
        # Создание сессии для работы с базой данных
        from database.models import SessionLocal
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