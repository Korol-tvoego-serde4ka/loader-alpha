# Инструкция по установке Minecraft Loader Alpha

## Серверная часть (Ubuntu 20.04)

### Требования
- Python 3.8+
- PostgreSQL
- Node.js 14+
- npm
- Discord Developer Account

### Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/Korol-tvoego-serde4ka/loader-alpha.git
cd loader-alpha/server
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте базу данных PostgreSQL:
```bash
sudo -u postgres psql
postgres=# CREATE DATABASE loader_alpha;
postgres=# CREATE USER loader_user WITH PASSWORD 'your_password';
postgres=# GRANT ALL PRIVILEGES ON DATABASE loader_alpha TO loader_user;
postgres=# \q
```

4. Настройте переменные окружения (создайте .env файл):
```
   DB_NAME=loader_alpha
   DB_USER=loader_user
   DB_PASSWORD=your_secure_password
   DB_HOST=localhost
   DB_PORT=5432
   SECRET_KEY=your_secret_key_for_jwt
   DISCORD_TOKEN=your_discord_bot_token
   DISCORD_CLIENT_ID=your_discord_app_id
   DISCORD_CLIENT_SECRET=your_discord_app_secret
   DISCORD_REDIRECT_URI=http://your-domain.com/auth/discord/callback
   SERVER_API_URL=http://localhost:5000/api
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=admin_password
   ADMIN_EMAIL=admin@example.com
   
   # ID ролей Discord (рекомендуется использовать вместо имен)
   DISCORD_ADMIN_ROLE_ID=123456789012345678
   DISCORD_SUPPORT_ROLE_ID=123456789012345678
   DISCORD_SUBSCRIBER_ROLE_ID=123456789012345678
```

5. Инициализируйте базу данных:
```bash
python database/init_db.py
```

6. Создайте директории для загрузки клиента:
```bash
mkdir -p website/static/downloads
```

7. Скопируйте собранный лоадер в директорию загрузок:
```bash
# После сборки клиента на Windows
cp /путь/к/собранному/minecraft-loader-alpha.exe website/static/downloads/
```

8. Запустите сервисы:
```bash
# Запуск веб-сервера
cd website
python app.py

# Запуск Discord бота (в отдельном терминале)
cd discord_bot
python bot.py
```

9. Настройте Nginx для проксирования запросов (опционально):
```bash
sudo apt install nginx
sudo nano /etc/nginx/sites-available/loader-alpha
```
Добавьте следующую конфигурацию:
```
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
```bash
sudo ln -s /etc/nginx/sites-available/loader-alpha /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Клиентская часть (Windows)

### Сборка лоадера

1. Установите Python 3.8+ и pip.

2. Установите PyInstaller:
```bash
pip install pyinstaller
```

3. Установите зависимости:
```bash
cd client
pip install -r requirements.txt
```

4. Соберите исполняемый файл:
```bash
pyinstaller --onefile --noconsole --icon=assets/icon.ico src/main.py --name minecraft-loader-alpha
```

5. Исполняемый файл будет создан в директории `dist/`.

### Настройка лоадера

1. Создайте файл конфигурации `config.json`:
```json
{
    "api_url": "http://your-domain.com/api",
    "version": "1.0.0"
}
```

2. Поместите файл конфигурации рядом с исполняемым файлом.

## Обслуживание

### Автозапуск сервисов (Ubuntu)

1. Создайте systemd сервисы для веб-сайта и Discord бота:

```bash
sudo nano /etc/systemd/system/loader-website.service
```
```
[Unit]
Description=Minecraft Loader Alpha Website
After=network.target

[Service]
User=your_user
WorkingDirectory=/path/to/loader-alpha/server/website
ExecStart=/usr/bin/python3 app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo nano /etc/systemd/system/loader-discord-bot.service
```
```
[Unit]
Description=Minecraft Loader Alpha Discord Bot
After=network.target

[Service]
User=your_user
WorkingDirectory=/path/to/loader-alpha/server/discord_bot
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

2. Активируйте и запустите сервисы:
```bash
sudo systemctl enable loader-website.service
sudo systemctl start loader-website.service
sudo systemctl enable loader-discord-bot.service
sudo systemctl start loader-discord-bot.service
```

3. Проверьте статус сервисов:
```bash
sudo systemctl status loader-website.service
sudo systemctl status loader-discord-bot.service
```

### Установка PostgreSQL
```bash
# Для Ubuntu 20.04
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Настройка Discord бота
1. Перейдите на [Discord Developer Portal](https://discord.com/developers/applications)
2. Создайте новое приложение:
   - Нажмите кнопку "New Application"
   - Укажите название для вашего приложения
   - Примите условия использования и нажмите "Create"

3. В разделе "Bot" создайте бота:
   - Нажмите на кнопку "Add Bot"
   - Подтвердите создание бота
   - В настройках бота включите следующие опции:
     - PUBLIC BOT: Отключено (если не планируете добавлять бота на разные серверы)
     - REQUIRES OAUTH2 CODE GRANT: Отключено
     - Включите все "Privileged Gateway Intents":
       - PRESENCE INTENT
       - SERVER MEMBERS INTENT
       - MESSAGE CONTENT INTENT

4. Скопируйте TOKEN бота (кнопка "Reset Token" / "Copy"):
   - Токен должен оставаться конфиденциальным и использоваться в .env файле
   - Запишите его в параметр DISCORD_TOKEN в файле .env

5. В разделе "OAuth2":
   - Выберите подраздел "General"
   - Добавьте Redirect URL: http://your-domain.com/auth/discord/callback
   - Нажмите "Save Changes"
   - Скопируйте CLIENT ID и CLIENT SECRET для настройки .env файла

6. Создайте URL для добавления бота на сервер:
   - Выберите подраздел "URL Generator"
   - В "Scopes" выберите:
     - bot
     - applications.commands
   - В "Bot Permissions" выберите:
     - Manage Roles
     - Send Messages
     - Use Slash Commands
     - Read Message History
   - Используйте сгенерированный URL для добавления бота на ваш сервер

7. Создайте необходимые роли на вашем Discord сервере:
   - Admin (для администраторов)
   - Support (для саппорта)
   - Subs (для подписчиков с активными ключами)
   
8. Получите ID созданных ролей:
   - Включите режим разработчика в Discord (Settings > Advanced > Developer Mode)
   - Кликните правой кнопкой мыши на роль и выберите "Copy ID"
   - Укажите полученные ID в .env файле:
     - DISCORD_ADMIN_ROLE_ID=123456789012345678 (замените на ID вашей роли Admin)
     - DISCORD_SUPPORT_ROLE_ID=123456789012345678 (замените на ID вашей роли Support)
     - DISCORD_SUBSCRIBER_ROLE_ID=123456789012345678 (замените на ID вашей роли Subs)
   - ВАЖНО: Бот использует только ID ролей, не имена. Вы можете менять названия ролей в Discord без изменения кода.