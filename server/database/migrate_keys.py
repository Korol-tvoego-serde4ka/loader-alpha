#!/usr/bin/env python
import os
import sys
import datetime
from dotenv import load_dotenv
import logging

# Добавляем текущую директорию в путь Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import SessionLocal, Key, engine
from sqlalchemy import text

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

def migrate_keys():
    """
    Миграция таблицы ключей: изменение структуры и обновление данных
    """
    try:
        logger.info("Начало миграции таблицы ключей...")
        db = SessionLocal()
        
        # Проверка существования столбца expires_at
        try:
            db.execute(text("SELECT expires_at FROM keys LIMIT 1"))
            logger.info("Столбец expires_at уже существует, пропускаем создание")
            column_exists = True
        except:
            logger.info("Столбец expires_at не существует, создаем его")
            column_exists = False
        
        # Добавляем столбец, если его нет
        if not column_exists:
            try:
                db.execute(text("ALTER TABLE keys ADD COLUMN expires_at TIMESTAMP"))
                logger.info("Столбец expires_at успешно добавлен")
            except Exception as e:
                logger.error(f"Ошибка при добавлении столбца: {str(e)}")
                return False
        
        # Обновляем значения expires_at для существующих записей
        try:
            # Получаем все ключи
            keys = db.query(Key).all()
            updated_count = 0
            
            for key in keys:
                if not hasattr(key, "expires_at") or key.expires_at is None:
                    # Вычисляем дату истечения
                    if key.activated_at:
                        key.expires_at = key.activated_at + datetime.timedelta(seconds=key.duration)
                    else:
                        key.expires_at = key.created_at + datetime.timedelta(seconds=key.duration)
                    updated_count += 1
            
            db.commit()
            logger.info(f"Обновлено {updated_count} записей ключей")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении данных: {str(e)}")
            db.rollback()
            return False
        
    except Exception as e:
        logger.error(f"Ошибка при миграции таблицы ключей: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = migrate_keys()
    if success:
        print("Миграция таблицы ключей успешно завершена")
    else:
        print("Миграция таблицы ключей не удалась")
        sys.exit(1) 