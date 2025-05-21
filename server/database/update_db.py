import os
import sys
from sqlalchemy import Column, DateTime, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Добавление пути к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Загрузка переменных окружения
load_dotenv()

# Настройка подключения к базе данных
DB_USER = os.getenv("DB_USER", "loader_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "loader_alpha")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Подключение к базе данных
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

def add_user_login_tracking():
    """Добавляет поля last_login и last_ip в таблицу users"""
    print("Добавление полей для отслеживания входов пользователей...")
    
    try:
        # Проверка существования колонки last_login
        session.execute("SELECT last_login FROM users LIMIT 1")
        print("Поле last_login уже существует")
    except Exception:
        # Добавление колонки last_login
        session.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")
        print("Поле last_login успешно добавлено")
    
    try:
        # Проверка существования колонки last_ip
        session.execute("SELECT last_ip FROM users LIMIT 1")
        print("Поле last_ip уже существует")
    except Exception:
        # Добавление колонки last_ip
        session.execute("ALTER TABLE users ADD COLUMN last_ip VARCHAR(45)")
        print("Поле last_ip успешно добавлено")
    
    session.commit()
    print("Обновление структуры таблицы users завершено")

def main():
    """Основная функция обновления базы данных"""
    try:
        add_user_login_tracking()
        print("Обновление базы данных завершено успешно")
    except Exception as e:
        print(f"Ошибка при обновлении базы данных: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main() 