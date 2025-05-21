import os
import sys
import datetime
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Добавление пути к корню проекта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.models import Base, SessionLocal, User, Key, Invite, DiscordCode, RoleLimits

def update_database():
    """Обновление базы данных с добавлением новых таблиц и полей"""
    print("Начало обновления базы данных...")
    
    try:
        # Создание сессии для работы с базой данных
        db = SessionLocal()
        
        # Создание таблицы лимитов ролей, если она не существует
        try:
            # Проверка, существует ли уже запись лимитов
            limits = db.query(RoleLimits).first()
            if not limits:
                print("Создание записи лимитов ролей...")
                # Создание записи с лимитами по умолчанию
                limits = RoleLimits(
                    admin_monthly_invites=999,  # Практически неограниченно для админов
                    support_monthly_invites=10,
                    user_monthly_invites=0
                )
                db.add(limits)
                db.commit()
                print("Запись лимитов ролей создана успешно.")
            else:
                print("Запись лимитов ролей уже существует.")
                
        except Exception as e:
            print(f"Ошибка при работе с таблицей лимитов: {e}")
            db.rollback()
        
        # Обновление can_create_invite для поддержки саппортов
        # Это обрабатывается в модели, логика изменена
        
        print("Обновление базы данных завершено успешно.")
        
    except Exception as e:
        print(f"Ошибка при обновлении базы данных: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Создание новых таблиц в базе данных
    engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///./database.db"))
    Base.metadata.create_all(bind=engine)
    print("Структура базы данных обновлена.")
    
    # Обновление данных
    update_database() 