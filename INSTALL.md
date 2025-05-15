# Инструкция по установке и сборке

## Серверная часть (Ubuntu 20.04)

### 1. Установка зависимостей

```bash
# Обновление системы
sudo apt update
sudo apt upgrade -y

# Установка Python и зависимостей
sudo apt install python3.8 python3.8-venv python3-pip -y

# Установка PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Установка Redis
sudo apt install redis-server -y

# Установка Nginx
sudo apt install nginx -y

# Установка Node.js
curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
sudo apt install nodejs -y
```

### 2. Настройка базы данных

```bash
# Вход в PostgreSQL
sudo -u postgres psql

# Создание базы данных и пользователя
CREATE DATABASE minecraft_loader;
CREATE USER loader_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE minecraft_loader TO loader_user;
\q
```

### 3. Настройка проекта

```bash
# Клонирование репозитория
git clone [repository_url]
cd minecraft-loader

# Создание виртуального окружения Python
python3.8 -m venv venv
source venv/bin/activate

# Установка Python зависимостей
pip install -r requirements.txt

# Копирование и настройка переменных окружения
cp .env.example .env
# Отредактируйте .env файл, указав необходимые параметры
```

### 4. Настройка Nginx

```bash
# Создание конфигурации
sudo nano /etc/nginx/sites-available/minecraft-loader

# Добавьте следующую конфигурацию:
server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Активация конфигурации
sudo ln -s /etc/nginx/sites-available/minecraft-loader /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 5. Запуск сервисов

```bash
# Запуск Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Запуск PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Запуск API
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000

# Запуск Discord бота
python bot.py
```

## Клиентская часть (Windows)

### 1. Требования

- Windows 10/11
- .NET Framework 4.7.2 или выше
- Visual Studio 2019/2022 (для сборки из исходников)

### 2. Сборка из исходников

1. Откройте решение `client/Loader.sln` в Visual Studio
2. Восстановите NuGet пакеты
3. Выберите конфигурацию Release
4. Соберите решение (Build -> Build Solution)

### 3. Создание установщика

1. Установите WiX Toolset
2. Откройте файл `client/Setup.wxs`
3. Соберите установщик

### 4. Установка

1. Запустите созданный установщик
2. Следуйте инструкциям установщика
3. После установки запустите лоадер
4. Введите ключ для активации

## Настройка Discord бота

1. Создайте приложение в [Discord Developer Portal](https://discord.com/developers/applications)
2. Получите токен бота
3. Добавьте бота на сервер
4. Настройте роли:
   - Admin
   - Support
   - Subs
5. Создайте канал для логов действий поддержки
6. Укажите ID ролей и канала логов в файле `.env`:
   ```
   ADMIN_ROLE_ID=your_admin_role_id
   SUPPORT_ROLE_ID=your_support_role_id
   SUBS_ROLE_ID=your_subs_role_id
   ADMIN_LOG_CHANNEL_ID=your_log_channel_id
   ```

## Безопасность

- Все ключи шифруются в базе данных
- Используется HTTPS для всех соединений
- Реализована защита от повторной регистрации
- Система автоматического удаления файлов при закрытии лоадера

## Поддержка

При возникновении проблем обращайтесь в Discord сервер поддержки. 