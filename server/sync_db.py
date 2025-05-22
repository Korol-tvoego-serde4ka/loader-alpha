#!/usr/bin/env python3
"""
Скрипт для синхронизации баз данных server/database.db и server/website/database.db
"""

import os
import sqlite3
import datetime
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Пути к базам данных
MAIN_DB_PATH = "database.db"
WEBSITE_DB_PATH = "website/database.db"

def connect_db(db_path):
    """Подключение к базе данных"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Ошибка подключения к {db_path}: {e}")
        return None

def get_tables(conn):
    """Получение списка таблиц в базе данных"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [row[0] for row in cursor.fetchall()]

def get_table_structure(conn, table_name):
    """Получение структуры таблицы"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    return cursor.fetchall()

def get_table_data(conn, table_name):
    """Получение данных из таблицы"""
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name};")
    return cursor.fetchall()

def sync_invites(source_conn, target_conn):
    """Синхронизация таблицы invites"""
    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()
    
    # Получаем данные из исходной таблицы
    source_cursor.execute("SELECT * FROM invites;")
    source_invites = source_cursor.fetchall()
    
    # Проверяем количество инвайтов в источнике
    logger.info(f"Найдено {len(source_invites)} приглашений в source_db")
    if not source_invites:
        logger.warning("Приглашения не найдены в исходной БД")
        return False
    
    # Очищаем таблицу в целевой БД
    target_cursor.execute("DELETE FROM invites;")
    
    # Копируем все записи
    for invite in source_invites:
        # Получаем имена колонок
        columns = [description[0] for description in source_cursor.description]
        # Создаем SQL запрос с нужными колонками
        placeholders = ", ".join(["?" for _ in range(len(columns))])
        columns_str = ", ".join(columns)
        
        query = f"INSERT INTO invites ({columns_str}) VALUES ({placeholders});"
        target_cursor.execute(query, tuple(invite))
    
    target_conn.commit()
    
    # Проверяем результат синхронизации
    target_cursor.execute("SELECT COUNT(*) FROM invites;")
    count = target_cursor.fetchone()[0]
    logger.info(f"Синхронизировано {count} приглашений")
    
    return True

def main():
    """Основная функция синхронизации"""
    logger.info("Запуск синхронизации баз данных")
    
    # Проверка существования файлов БД
    if not os.path.exists(MAIN_DB_PATH):
        logger.error(f"Основная БД не найдена: {MAIN_DB_PATH}")
        return False
    
    if not os.path.exists(WEBSITE_DB_PATH):
        logger.error(f"БД веб-интерфейса не найдена: {WEBSITE_DB_PATH}")
        return False
    
    # Подключение к базам данных
    source_conn = connect_db(MAIN_DB_PATH)
    target_conn = connect_db(WEBSITE_DB_PATH)
    
    if not source_conn or not target_conn:
        logger.error("Не удалось подключиться к базам данных")
        return False
    
    try:
        # Синхронизация таблицы приглашений
        if sync_invites(source_conn, target_conn):
            logger.info("Синхронизация таблицы invites выполнена успешно")
        else:
            logger.warning("Синхронизация таблицы invites не выполнена")
        
        # Здесь можно добавить синхронизацию других таблиц
        
        logger.info("Синхронизация завершена успешно")
        return True
    except Exception as e:
        logger.error(f"Ошибка при синхронизации: {e}")
        return False
    finally:
        source_conn.close()
        target_conn.close()

if __name__ == "__main__":
    main() 