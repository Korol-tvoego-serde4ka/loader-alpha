import os
import sys
from sqlalchemy import Column, DateTime, String, text
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

def check_column_exists(session, table, column):
    """Проверяет существование колонки в таблице"""
    try:
        # Используем text() для создания SQL запроса
        sql = text(f"SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='{table}' AND column_name='{column}')")
        result = session.execute(sql).scalar()
        return result
    except Exception as e:
        print(f"Ошибка при проверке колонки {column}: {e}")
        session.rollback()
        return False

def add_user_login_tracking():
    """Добавляет поля last_login и last_ip в таблицу users"""
    print("Добавление полей для отслеживания входов пользователей...")
    
    # Для каждой операции создаем новую сессию
    session = SessionLocal()
    try:
        # Проверка существования колонки last_login
        has_last_login = check_column_exists(session, 'users', 'last_login')
        if has_last_login:
            print("Поле last_login уже существует")
        else:
            # Добавление колонки last_login
            session.execute(text("ALTER TABLE users ADD COLUMN last_login TIMESTAMP"))
            session.commit()
            print("Поле last_login успешно добавлено")
    except Exception as e:
        print(f"Ошибка при добавлении поля last_login: {e}")
        session.rollback()
    finally:
        session.close()
    
    # Для второй операции создаем новую сессию
    session = SessionLocal()
    try:
        # Проверка существования колонки last_ip
        has_last_ip = check_column_exists(session, 'users', 'last_ip')
        if has_last_ip:
            print("Поле last_ip уже существует")
        else:
            # Добавление колонки last_ip
            session.execute(text("ALTER TABLE users ADD COLUMN last_ip VARCHAR(45)"))
            session.commit()
            print("Поле last_ip успешно добавлено")
    except Exception as e:
        print(f"Ошибка при добавлении поля last_ip: {e}")
        session.rollback()
    finally:
        session.close()
    
    print("Обновление структуры таблицы users завершено")

def main():
    """Основная функция обновления базы данных"""
    try:
        add_user_login_tracking()
        print("Обновление базы данных завершено успешно")
    except Exception as e:
        print(f"Ошибка при обновлении базы данных: {e}")

if __name__ == "__main__":
    main() 