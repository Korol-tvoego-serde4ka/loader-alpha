import secrets
import string
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, KEY_EXPIRATION_DAYS

# Настройки для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Хеширование пароля"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создание JWT токена"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def generate_key(length: int = 32) -> str:
    """Генерация ключа"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_invite_code(length: int = 8) -> str:
    """Генерация кода приглашения"""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def calculate_key_expiration(is_test: bool = False) -> datetime:
    """Расчет времени истечения ключа"""
    if is_test:
        return datetime.utcnow() + timedelta(days=1)
    return datetime.utcnow() + timedelta(days=KEY_EXPIRATION_DAYS)

def format_time_remaining(expires_at: datetime) -> str:
    """Форматирование оставшегося времени"""
    now = datetime.utcnow()
    if expires_at <= now:
        return "Истек"
    
    delta = expires_at - now
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    
    if days > 0:
        return f"{days}д {hours}ч {minutes}м"
    elif hours > 0:
        return f"{hours}ч {minutes}м"
    else:
        return f"{minutes}м"

def generate_discord_code() -> str:
    """Генерация кода для привязки Discord"""
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))

def is_valid_discord_code(code: str) -> bool:
    """Проверка формата кода Discord"""
    return len(code) == 6 and all(c in string.ascii_uppercase + string.digits for c in code) 