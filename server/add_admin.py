#!/usr/bin/env python3
import sys
import os
from passlib.context import CryptContext

# Добавление пути к корню проекта
parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(parent_dir)

# Установка пути к базе данных
os.environ["DATABASE_URL"] = f"sqlite:////{os.path.join(parent_dir, 'database.db')}"
print(f"Используем базу данных: {os.environ['DATABASE_URL']}")

# Импорт моделей и сессии
from database.models import User, SessionLocal, Base, engine

# Настройка шифрования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password):
    return pwd_context.hash(password)

def create_tables():
    """Создает все таблицы в базе данных, если их не существует"""
    try:
        print("Создание структуры базы данных...")
        Base.metadata.create_all(bind=engine)
        print("Таблицы базы данных успешно созданы")
        return True
    except Exception as e:
        print(f"Ошибка при создании таблиц: {str(e)}")
        return False

def create_admin_user(username, email, password):
    # Получаем сессию базы данных
    db = SessionLocal()
    
    try:
        # Проверяем, существует ли пользователь с таким именем
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"Пользователь с именем {username} уже существует.")
            return False
        
        # Проверяем, существует ли пользователь с таким email
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            print(f"Пользователь с email {email} уже существует.")
            return False
        
        # Создаем нового пользователя с правами администратора
        new_admin = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            is_admin=True
        )
        
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        
        print(f"Администратор {username} успешно создан!")
        return True
    except Exception as e:
        db.rollback()
        print(f"Ошибка при создании администратора: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    # Сначала создаем таблицы
    if not create_tables():
        print("Не удалось создать необходимые таблицы в базе данных.")
        sys.exit(1)

    if len(sys.argv) != 4:
        print("Использование: python add_admin.py <username> <email> <password>")
        sys.exit(1)
    
    username = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    
    if create_admin_user(username, email, password):
        print("Администратор успешно создан!")
    else:
        print("Не удалось создать администратора.") 