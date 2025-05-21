import os
import sys
import datetime
from passlib.context import CryptContext
from dotenv import load_dotenv

# Добавление пути к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import init_db, SessionLocal, User, Invite

# Загрузка переменных окружения
load_dotenv()

# Настройка шифрования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password):
    return pwd_context.hash(password)

def create_admin_user(db_session):
    """Создание администратора по умолчанию"""
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    
    # Проверка, существует ли уже пользователь с таким именем
    existing_user = db_session.query(User).filter(User.username == admin_username).first()
    if existing_user:
        print(f"Пользователь {admin_username} уже существует.")
        return existing_user
    
    # Создание нового пользователя-администратора
    admin = User(
        username=admin_username,
        email=admin_email,
        password_hash=hash_password(admin_password),
        is_admin=True
    )
    
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    
    print(f"Создан пользователь-администратор: {admin_username}")
    return admin

def create_initial_invite(db_session, admin):
    """Создание начального приглашения от администратора"""
    # Установка срока действия на 30 дней
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=30)
    
    invite = Invite(
        created_by_id=admin.id,
        expires_at=expires_at
    )
    
    db_session.add(invite)
    db_session.commit()
    db_session.refresh(invite)
    
    print(f"Создан начальный инвайт-код: {invite.code}")
    return invite

def main():
    """Основная функция инициализации базы данных"""
    print("Инициализация базы данных...")
    
    # Создание таблиц в базе данных
    init_db()
    print("Таблицы базы данных созданы.")
    
    # Создание сессии для работы с базой данных
    db = SessionLocal()
    
    try:
        # Создание администратора
        admin = create_admin_user(db)
        
        # Создание начального инвайт-кода
        invite = create_initial_invite(db, admin)
        
        print("Инициализация базы данных завершена успешно.")
        print(f"Администратор: {admin.username}")
        print(f"Инвайт-код: {invite.code}")
        
    except Exception as e:
        print(f"Ошибка при инициализации базы данных: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main() 