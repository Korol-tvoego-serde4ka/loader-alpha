#!/usr/bin/env python3
"""
Скрипт для генерации хеша пароля для прямого обновления базы данных
"""

import os
import sys
import sqlite3
import logging
from passlib.context import CryptContext

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Настройка шифрования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Путь к базе данных
current_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(current_dir, 'database.db')
WEBSITE_DB_PATH = os.path.join(current_dir, 'website', 'database.db')

# Пароль для хеширования
password = "adminpass123"
hashed_password = pwd_context.hash(password)

print(f"Сгенерированный хеш для пароля '{password}':")
print(hashed_password)
print("\nSQL запрос для обновления пароля администратора:")
print(f"UPDATE users SET password_hash='{hashed_password}' WHERE username='admin';")

# Обновление пароля в базе данных
try:
    # Основная база
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username='admin'")
        admin_id = cursor.fetchone()
        
        if admin_id:
            cursor.execute(f"UPDATE users SET password_hash=? WHERE username='admin'", (hashed_password,))
            conn.commit()
            print(f"Пароль успешно обновлен в базе {DB_PATH}")
        else:
            print(f"Администратор не найден в базе {DB_PATH}")
        conn.close()
    else:
        print(f"База данных не найдена: {DB_PATH}")
        
    # Веб-база
    if os.path.exists(WEBSITE_DB_PATH):
        conn = sqlite3.connect(WEBSITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username='admin'")
        admin_id = cursor.fetchone()
        
        if admin_id:
            cursor.execute(f"UPDATE users SET password_hash=? WHERE username='admin'", (hashed_password,))
            conn.commit()
            print(f"Пароль успешно обновлен в базе {WEBSITE_DB_PATH}")
        else:
            # Если админа нет, создаем его
            cursor.execute("""
            INSERT INTO users (username, email, password_hash, is_admin) 
            VALUES (?, ?, ?, ?)
            """, ("admin", "admin@example.com", hashed_password, True))
            conn.commit()
            print(f"Администратор создан в базе {WEBSITE_DB_PATH}")
        conn.close()
    else:
        print(f"База данных веб-интерфейса не найдена: {WEBSITE_DB_PATH}")
        
except Exception as e:
    print(f"Ошибка при обновлении пароля: {str(e)}") 