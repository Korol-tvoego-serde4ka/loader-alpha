#!/usr/bin/env python3
"""
Скрипт для полного сброса и повторной инициализации базы данных
"""

import os
import sys
import sqlite3
import datetime
import logging
import shutil
from passlib.context import CryptContext

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Настройка шифрования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Пути к базам данных
current_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(current_dir, 'database.db')
WEBSITE_DB_PATH = os.path.join(current_dir, 'website', 'database.db')
BACKUP_PATH = os.path.join(current_dir, 'database.db.bak')

# Учетные данные по умолчанию
DEFAULT_ADMIN = {
    "username": "admin",
    "password": "adminpass123",
    "email": "admin@example.com"
}

def backup_database():
    """Создает резервную копию базы данных, если она существует"""
    if os.path.exists(DB_PATH):
        try:
            logger.info(f"Создание резервной копии базы данных: {BACKUP_PATH}")
            shutil.copy2(DB_PATH, BACKUP_PATH)
            logger.info("Резервная копия создана успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка при создании резервной копии: {str(e)}")
            return False
    else:
        logger.warning("База данных не найдена, резервная копия не создана")
        return False

def reset_database():
    """Удаляет существующие базы данных и создает новую пустую БД"""
    # Удаление основной базы данных
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            logger.info(f"Файл базы данных {DB_PATH} удален")
        except Exception as e:
            logger.error(f"Ошибка при удалении файла базы данных {DB_PATH}: {str(e)}")
            return False

    # Удаление базы данных в директории website, если есть
    if os.path.exists(WEBSITE_DB_PATH):
        try:
            os.remove(WEBSITE_DB_PATH)
            logger.info(f"Файл базы данных {WEBSITE_DB_PATH} удален")
        except Exception as e:
            logger.error(f"Ошибка при удалении файла базы данных {WEBSITE_DB_PATH}: {str(e)}")
            # Продолжаем выполнение, это не критичная ошибка

    # Создание новой пустой базы данных
    try:
        conn = sqlite3.connect(DB_PATH)
        logger.info(f"Создана новая пустая база данных: {DB_PATH}")
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании новой базы данных: {str(e)}")
        return False

def create_tables():
    """Создает все необходимые таблицы в базе данных"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(100) NOT NULL UNIQUE,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_admin BOOLEAN DEFAULT 0,
            is_support BOOLEAN DEFAULT 0,
            is_banned BOOLEAN DEFAULT 0,
            discord_id VARCHAR(50) UNIQUE,
            discord_username VARCHAR(100),
            last_login TIMESTAMP,
            last_ip VARCHAR(45)
        )
        ''')
        logger.info("Таблица users создана")
        
        # Таблица ключей
        cursor.execute('''
        CREATE TABLE keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key VARCHAR(50) NOT NULL UNIQUE,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            activated_at TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            duration INTEGER NOT NULL DEFAULT 86400,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        logger.info("Таблица keys создана")
        
        # Таблица инвайтов
        cursor.execute('''
        CREATE TABLE invites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code VARCHAR(50) NOT NULL UNIQUE,
            created_by_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT 0,
            used_by_id INTEGER,
            FOREIGN KEY (created_by_id) REFERENCES users (id),
            FOREIGN KEY (used_by_id) REFERENCES users (id)
        )
        ''')
        logger.info("Таблица invites создана")
        
        # Таблица кодов Discord
        cursor.execute('''
        CREATE TABLE discord_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code VARCHAR(8) NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        logger.info("Таблица discord_codes создана")
        
        # Таблица лимитов ролей
        cursor.execute('''
        CREATE TABLE role_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_monthly_invites INTEGER NOT NULL DEFAULT 999,
            support_monthly_invites INTEGER NOT NULL DEFAULT 10,
            user_monthly_invites INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        logger.info("Таблица role_limits создана")
        
        # Создаем запись с лимитами для ролей
        cursor.execute('''
        INSERT INTO role_limits (admin_monthly_invites, support_monthly_invites, user_monthly_invites)
        VALUES (?, ?, ?)
        ''', (999, 10, 0))
        logger.info("Добавлены лимиты для ролей")
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def create_admin():
    """Создает учетную запись администратора"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Генерация хеша пароля
        hashed_password = pwd_context.hash(DEFAULT_ADMIN["password"])
        
        # Создание администратора
        cursor.execute('''
        INSERT INTO users (username, email, password_hash, is_admin, created_at)
        VALUES (?, ?, ?, ?, ?)
        ''', (
            DEFAULT_ADMIN["username"],
            DEFAULT_ADMIN["email"],
            hashed_password,
            True,
            datetime.datetime.utcnow()
        ))
        
        admin_id = cursor.lastrowid
        logger.info(f"Создан администратор: {DEFAULT_ADMIN['username']} (ID: {admin_id})")
        
        conn.commit()
        
        # Проверим, создан ли администратор
        cursor.execute("SELECT id, username FROM users WHERE is_admin = 1")
        admin = cursor.fetchone()
        if admin:
            logger.info(f"Проверка администратора: ID={admin[0]}, Имя={admin[1]}")
        else:
            logger.warning("Администратор не найден в базе после создания!")
        
        conn.close()
        return admin_id
    except Exception as e:
        logger.error(f"Ошибка при создании администратора: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def create_invite(admin_id):
    """Создает тестовое приглашение от имени администратора"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Функция для генерации случайной строки
        import secrets
        import string
        
        def generate_random_string(length=16):
            """Генерация случайной строки заданной длины"""
            characters = string.ascii_letters + string.digits
            return ''.join(secrets.choice(characters) for _ in range(length))
        
        # Создание инвайта
        invite_code = generate_random_string()
        invite_expiry = datetime.datetime.utcnow() + datetime.timedelta(days=30)
        
        cursor.execute('''
        INSERT INTO invites (code, created_by_id, expires_at, created_at)
        VALUES (?, ?, ?, ?)
        ''', (
            invite_code,
            admin_id,
            invite_expiry,
            datetime.datetime.utcnow()
        ))
        
        invite_id = cursor.lastrowid
        logger.info(f"Создано тестовое приглашение: {invite_code} (ID: {invite_id})")
        
        conn.commit()
        
        # Проверка создания приглашения
        cursor.execute("SELECT id, code, created_by_id FROM invites")
        invite = cursor.fetchone()
        if invite:
            logger.info(f"Проверка приглашения: ID={invite[0]}, Код={invite[1]}, Создатель={invite[2]}")
        else:
            logger.warning("Приглашение не найдено в базе после создания!")
        
        conn.close()
        return invite_code
    except Exception as e:
        logger.error(f"Ошибка при создании приглашения: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def sync_database():
    """Синхронизирует основную базу данных с базой в директории website"""
    try:
        # Создаем символическую ссылку или копируем базу в директорию website
        if not os.path.exists(os.path.dirname(WEBSITE_DB_PATH)):
            os.makedirs(os.path.dirname(WEBSITE_DB_PATH), exist_ok=True)
            
        if os.path.exists(WEBSITE_DB_PATH):
            os.remove(WEBSITE_DB_PATH)
            
        # Пробуем создать символическую ссылку
        try:
            if hasattr(os, 'symlink'):
                os.symlink(DB_PATH, WEBSITE_DB_PATH)
                logger.info(f"Создана символическая ссылка от {DB_PATH} к {WEBSITE_DB_PATH}")
            else:
                # Если symlink не поддерживается (Windows), копируем файл
                shutil.copy2(DB_PATH, WEBSITE_DB_PATH)
                logger.info(f"База данных скопирована из {DB_PATH} в {WEBSITE_DB_PATH}")
        except Exception as e:
            logger.warning(f"Не удалось создать символическую ссылку, копируем файл: {str(e)}")
            shutil.copy2(DB_PATH, WEBSITE_DB_PATH)
            logger.info(f"База данных скопирована из {DB_PATH} в {WEBSITE_DB_PATH}")
            
        return True
    except Exception as e:
        logger.error(f"Ошибка при синхронизации базы данных: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def verify_database():
    """Проверяет корректность базы данных"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Список таблиц, которые должны быть в базе
        tables = ["users", "keys", "invites", "discord_codes", "role_limits"]
        
        # Проверка наличия всех таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [table[0] for table in cursor.fetchall()]
        
        missing_tables = [table for table in tables if table not in existing_tables]
        if missing_tables:
            logger.warning(f"Отсутствуют таблицы: {', '.join(missing_tables)}")
        else:
            logger.info("Все необходимые таблицы присутствуют в базе данных")
        
        # Проверка наличия администратора
        cursor.execute("SELECT id, username FROM users WHERE is_admin = 1")
        admin = cursor.fetchone()
        if admin:
            logger.info(f"Найден администратор: ID={admin[0]}, Имя={admin[1]}")
        else:
            logger.warning("Администратор не найден в базе данных")
        
        # Проверка наличия приглашений
        cursor.execute("SELECT COUNT(*) FROM invites")
        invite_count = cursor.fetchone()[0]
        logger.info(f"Количество приглашений в базе: {invite_count}")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при проверке базы данных: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("========== СБРОС И РЕИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ==========")
    
    # Спрашиваем подтверждение перед сбросом
    confirmation = input("Вы уверены, что хотите полностью сбросить базу данных? (y/n): ")
    if confirmation.lower() != 'y':
        print("Операция отменена пользователем.")
        sys.exit(0)
    
    print("\n1. Создание резервной копии существующей базы данных...")
    backup_database()
    
    print("\n2. Удаление и пересоздание базы данных...")
    if not reset_database():
        print("Ошибка при сбросе базы данных. Операция прервана.")
        sys.exit(1)
    
    print("\n3. Создание таблиц в базе данных...")
    if not create_tables():
        print("Ошибка при создании таблиц. Операция прервана.")
        sys.exit(1)
    
    print("\n4. Создание учетной записи администратора...")
    admin_id = create_admin()
    if not admin_id:
        print("Ошибка при создании администратора. Операция прервана.")
        sys.exit(1)
    
    print("\n5. Создание тестового приглашения...")
    invite_code = create_invite(admin_id)
    if not invite_code:
        print("Ошибка при создании приглашения. Операция прервана.")
        sys.exit(1)
    
    print("\n6. Синхронизация базы данных с директорией website...")
    if not sync_database():
        print("Ошибка при синхронизации базы данных. Операция прервана.")
        sys.exit(1)
    
    print("\n7. Проверка базы данных...")
    verify_database()
    
    print("\n========== ОПЕРАЦИЯ ЗАВЕРШЕНА УСПЕШНО ==========")
    print(f"База данных сброшена и реинициализирована.")
    print(f"Создан администратор: {DEFAULT_ADMIN['username']}")
    print(f"Пароль администратора: {DEFAULT_ADMIN['password']}")
    print(f"Создано тестовое приглашение с кодом: {invite_code}")
    print("Вы можете войти в систему используя указанные учетные данные.") 