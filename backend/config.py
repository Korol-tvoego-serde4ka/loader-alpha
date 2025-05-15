import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройки базы данных
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://loader_user:your_password@localhost/minecraft_loader")

# Настройки Discord
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")

# Настройки безопасности
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Настройки Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Настройки ключей
KEY_EXPIRATION_DAYS = 1  # Срок действия ключа по умолчанию
TEST_KEY_EXPIRATION_DAYS = 1  # Срок действия тестового ключа
KEY_CODE_EXPIRATION_MINUTES = 15  # Время жизни кода привязки

# Роли Discord
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID", "0"))
SUPPORT_ROLE_ID = int(os.getenv("SUPPORT_ROLE_ID", "0"))
SUBS_ROLE_ID = int(os.getenv("SUBS_ROLE_ID", "0"))

# Каналы Discord
ADMIN_LOG_CHANNEL_ID = int(os.getenv("ADMIN_LOG_CHANNEL_ID", "0"))

# Настройки API
API_V1_PREFIX = "/api/v1"
PROJECT_NAME = "Minecraft Loader API"
DEBUG = os.getenv("DEBUG", "False").lower() == "true" 