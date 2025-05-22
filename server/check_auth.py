#!/usr/bin/env python3
"""
Скрипт для проверки аутентификации напрямую через базу данных
"""
import os
import sys
import logging
from passlib.context import CryptContext
import sqlite3

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Путь к базе данных
current_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(current_dir, 'database.db')

# Настройка контекста паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def check_auth(username, password):
    """Проверяет учетные данные напрямую через базу"""
    try:
        # Подключаемся к базе данных
        print(f"Проверка подключения к базе: {DB_PATH}")
        print(f"База существует: {os.path.exists(DB_PATH)}")
        
        if not os.path.exists(DB_PATH):
            print("ОШИБКА: База данных не найдена!")
            return False
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Запрашиваем структуру таблицы users
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        print(f"Структура таблицы users: {columns}")
        
        # Запрашиваем пользователя
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if not user:
            print(f"Пользователь '{username}' не найден в базе")
            # Выводим всех пользователей
            cursor.execute("SELECT id, username, password_hash FROM users")
            all_users = cursor.fetchall()
            print(f"Всего пользователей в базе: {len(all_users)}")
            for user_data in all_users:
                print(f"ID: {user_data[0]}, Имя: {user_data[1]}")
            return False
        
        # Получаем хеш пароля из базы
        # Учитываем порядок полей в таблице
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        password_hash = cursor.fetchone()[0]
        
        print(f"Хеш в базе для пользователя {username}: {password_hash}")
        
        # Проверяем пароль
        password_match = pwd_context.verify(password, password_hash)
        print(f"Пароль верный: {password_match}")
        
        return password_match
    except Exception as e:
        print(f"Ошибка при проверке аутентификации: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def create_admin_directly():
    """Создает учетную запись администратора напрямую через SQL"""
    try:
        # Проверяем, существует ли файл БД
        if not os.path.exists(DB_PATH):
            print(f"База данных не найдена: {DB_PATH}")
            return False
            
        # Подключаемся к базе
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем, есть ли таблица пользователей
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("Таблица users не существует, создаем...")
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
            conn.commit()
            print("Таблица users создана")
        
        # Генерируем хеш пароля
        password = "adminpass123"
        hashed_password = pwd_context.hash(password)
        
        # Проверяем, существует ли уже админ
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        admin = cursor.fetchone()
        
        if admin:
            # Обновляем пароль админа
            cursor.execute("UPDATE users SET password_hash = ? WHERE username = 'admin'", (hashed_password,))
            conn.commit()
            print("Пароль администратора обновлен")
        else:
            # Создаем нового администратора
            cursor.execute('''
            INSERT INTO users (username, email, password_hash, is_admin)
            VALUES (?, ?, ?, ?)
            ''', ('admin', 'admin@example.com', hashed_password, True))
            conn.commit()
            print("Администратор создан")
        
        return True
        
    except Exception as e:
        print(f"Ошибка при создании администратора: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("=== Диагностика аутентификации ===")
    
    username = "admin"
    password = "adminpass123"
    
    # Создаем учетную запись администратора напрямую
    print("\n--- Создание учетной записи администратора ---")
    create_admin_directly()
    
    # Проверяем аутентификацию
    print("\n--- Проверка аутентификации ---")
    auth_result = check_auth(username, password)
    
    print(f"\nРезультат аутентификации: {'Успешно' if auth_result else 'Неудачно'}") 