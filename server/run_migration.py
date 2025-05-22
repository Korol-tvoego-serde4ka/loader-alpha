#!/usr/bin/env python3
import os
import sys

# Добавляем текущую директорию в путь Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    try:
        print("Запуск миграций базы данных...")
        
        # Импортируем и запускаем функцию миграции ключей
        from database.migrate_keys import migrate_keys
        keys_migration_success = migrate_keys()
        
        if keys_migration_success:
            print("Миграция ключей успешно завершена")
        else:
            print("Миграция ключей не удалась")
            sys.exit(1)
        
        # Здесь можно добавить другие миграции в будущем
        
        print("Все миграции успешно завершены")
    except Exception as e:
        print(f"Ошибка при выполнении миграций: {str(e)}")
        sys.exit(1) 