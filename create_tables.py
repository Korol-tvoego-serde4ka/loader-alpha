import os
import sys
import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Добавление пути к корню проекта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server.database.models import Base, SessionLocal, RoleLimits

# Настройка подключения к базе данных
DB_USER = os.getenv("DB_USER", "loader_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "loader_alpha")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def create_role_limits_table():
    """Создаем таблицу role_limits в базе данных PostgreSQL"""
    try:
        # Создаем подключение к PostgreSQL
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Проверяем, существует ли таблица
        cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'role_limits')")
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("Создание таблицы role_limits...")
            # Создаем таблицу
            cursor.execute("""
            CREATE TABLE role_limits (
                id SERIAL PRIMARY KEY,
                admin_monthly_invites INTEGER NOT NULL DEFAULT 999,
                support_monthly_invites INTEGER NOT NULL DEFAULT 10,
                user_monthly_invites INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            """)
            print("Таблица role_limits успешно создана.")
            
            # Добавляем начальную запись
            cursor.execute("""
            INSERT INTO role_limits (admin_monthly_invites, support_monthly_invites, user_monthly_invites)
            VALUES (999, 10, 0)
            """)
            print("Начальные значения добавлены в таблицу role_limits.")
        else:
            print("Таблица role_limits уже существует.")
        
        # Закрываем соединение
        cursor.close()
        conn.close()
        
        print("Операция завершена успешно.")
        return True
    except Exception as e:
        print(f"Ошибка при создании таблицы: {str(e)}")
        return False

if __name__ == "__main__":
    print("Начало создания таблицы role_limits...")
    success = create_role_limits_table()
    if success:
        print("Таблица успешно создана!")
    else:
        print("Не удалось создать таблицу.") 