import os
import sys
import datetime

# Добавление пути к серверу, чтобы импорт работал корректно
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database.models import SessionLocal, User, Invite

def create_invite():
    db = SessionLocal()
    try:
        # Найти администратора
        admin = db.query(User).filter(User.is_admin == True).first()
        
        if not admin:
            print("Ошибка: администратор не найден в базе данных")
            return
        
        # Создать приглашение
        invite = Invite(
            created_by_id=admin.id,
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=30)
        )
        
        db.add(invite)
        db.commit()
        db.refresh(invite)
        
        print(f"Создан инвайт-код: {invite.code}")
        print(f"Срок действия до: {invite.expires_at}")
        
    except Exception as e:
        print(f"Ошибка при создании приглашения: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    create_invite() 