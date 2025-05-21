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
```

5. Инициализируйте базу данных:
```bash
python database/init_db.py
```

6. Запустите сервисы:
```bash
# Запуск веб-сервера
cd website
python app.py

# Запуск Discord бота (в отдельном терминале)
cd discord_bot
python bot.py
```

7. Настройте Nginx для проксирования запросов (опционально):
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
2. Создайте новое приложение
3. В разделе "Bot" создайте бота и скопируйте токен
4. В разделе "OAuth2" добавьте redirect URL
5. Включите интенты: Message Content, Server Members 