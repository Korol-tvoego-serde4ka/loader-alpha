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
        
        # 1. Проверка существования столбца duration
        db = SessionLocal()
        try:
            db.execute(text("SELECT duration FROM keys LIMIT 1"))
            logger.info("Столбец duration уже существует, пропускаем создание")
            duration_exists = True
        except Exception as e:
            logger.info("Столбец duration не существует, создаем его")
            duration_exists = False
        finally:
            db.close()
            
        # Добавляем столбец duration, если его нет
        if not duration_exists:
            db = SessionLocal()
            try:
                db.execute(text("ALTER TABLE keys ADD COLUMN duration INTEGER DEFAULT 86400 NOT NULL"))
                db.commit()
                logger.info("Столбец duration успешно добавлен")
            except Exception as e:
                logger.error(f"Ошибка при добавлении столбца duration: {str(e)}")
                db.rollback()
                db.close()
                return False
            finally:
                db.close()
                
        # 2. Проверка существования столбца expires_at
        db = SessionLocal()
        try:
            db.execute(text("SELECT expires_at FROM keys LIMIT 1"))
            logger.info("Столбец expires_at уже существует, пропускаем создание")
            expires_exists = True
        except Exception as e:
            logger.info("Столбец expires_at не существует, создаем его")
            expires_exists = False
        finally:
            db.close()
        
        # Добавляем столбец expires_at, если его нет
        if not expires_exists:
            db = SessionLocal()
            try:
                db.execute(text("ALTER TABLE keys ADD COLUMN expires_at TIMESTAMP"))
                db.commit()
                logger.info("Столбец expires_at успешно добавлен")
            except Exception as e:
                logger.error(f"Ошибка при добавлении столбца expires_at: {str(e)}")
                db.rollback()
                db.close()
                return False
            finally:
                db.close()
        
        # 3. Обновляем значения expires_at для существующих записей
        db = SessionLocal()
        try:
            # Получаем все ключи
            keys = db.query(Key).all()
            logger.info(f"Найдено {len(keys)} записей ключей")
            
            updated_count = 0
            for key in keys:
                # Проверяем, есть ли необходимость обновить expires_at
                if not key.expires_at:
                    # Вычисляем дату истечения на основе даты создания
                    key.expires_at = key.created_at + datetime.timedelta(days=1)
                    updated_count += 1
            
            if updated_count > 0:
                db.commit()
                logger.info(f"Обновлено {updated_count} записей ключей")
            else:
                logger.info("Нет записей для обновления")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении данных: {str(e)}")
            db.rollback()
            return False
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"Ошибка при миграции таблицы ключей: {str(e)}")
        return False

if __name__ == "__main__":
    success = migrate_keys()
    if success:
        print("Миграция таблицы ключей успешно завершена")
    else:
        print("Миграция таблицы ключей не удалась")
        sys.exit(1) 