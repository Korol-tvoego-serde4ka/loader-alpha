from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# Схемы для пользователей
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    invite_code: str

class UserLogin(BaseModel):
    username: str
    password: str

class User(UserBase):
    id: int
    discord_id: Optional[str]
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        orm_mode = True

# Схемы для ключей
class KeyBase(BaseModel):
    key_value: str
    is_test: bool = False

class KeyCreate(KeyBase):
    pass

class Key(KeyBase):
    id: int
    user_id: Optional[int]
    created_by: int
    is_used: bool
    created_at: datetime
    expires_at: datetime
    used_at: Optional[datetime]

    class Config:
        orm_mode = True

# Схемы для продуктов
class ProductBase(BaseModel):
    name: str
    description: str
    version: str

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    file_path: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True

# Схемы для сессий
class SessionBase(BaseModel):
    session_token: str

class SessionCreate(SessionBase):
    user_id: int
    expires_at: datetime

class Session(SessionBase):
    id: int
    user_id: int
    created_at: datetime
    expires_at: datetime
    last_activity: datetime

    class Config:
        orm_mode = True

# Схемы для токенов
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Схемы для Discord
class DiscordLink(BaseModel):
    code: str

class DiscordUser(BaseModel):
    id: str
    username: str
    discriminator: str
    avatar: Optional[str]

# Схемы для статистики
class UserStats(BaseModel):
    total_keys: int
    active_keys: int
    expired_keys: int
    invited_users: int
    last_login: Optional[datetime] 