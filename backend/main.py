from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
import redis
import json

from database import get_db, engine
import models
import schemas
import utils
from config import (
    API_V1_PREFIX,
    PROJECT_NAME,
    REDIS_URL,
    KEY_CODE_EXPIRATION_MINUTES
)

# Создание таблиц в базе данных
models.Base.metadata.create_all(bind=engine)

# Инициализация Redis
redis_client = redis.from_url(REDIS_URL)

# Инициализация FastAPI
app = FastAPI(title=PROJECT_NAME)

# OAuth2 схема для аутентификации
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{API_V1_PREFIX}/token")

# Зависимости
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Неверные учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = utils.jwt.decode(token, utils.SECRET_KEY, algorithms=[utils.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Неактивный пользователь")
    return current_user

# Эндпоинты аутентификации
@app.post(f"{API_V1_PREFIX}/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not utils.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Обновление времени последнего входа
    user.last_login = datetime.utcnow()
    db.commit()
    
    access_token = utils.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# Эндпоинты пользователей
@app.post(f"{API_V1_PREFIX}/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Проверка существования пользователя
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    
    # Проверка инвайт-кода
    inviter = db.query(models.User).filter(
        models.User.invite_code == user.invite_code
    ).first()
    if not inviter:
        raise HTTPException(status_code=400, detail="Неверный инвайт-код")
    
    # Создание пользователя
    hashed_password = utils.get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Создание связи с пригласившим пользователем
    db_user.invited_by.append(inviter)
    db.commit()
    
    return db_user

# Эндпоинты ключей
@app.post(f"{API_V1_PREFIX}/keys/", response_model=schemas.Key)
def create_key(
    key: schemas.KeyCreate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    db_key = models.Key(
        key_value=utils.generate_key(),
        created_by=current_user.id,
        expires_at=utils.calculate_key_expiration(key.is_test)
    )
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    return db_key

@app.get(f"{API_V1_PREFIX}/keys/", response_model=List[schemas.Key])
def get_keys(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if current_user.is_admin:
        return db.query(models.Key).all()
    return db.query(models.Key).filter(models.Key.user_id == current_user.id).all()

@app.post(f"{API_V1_PREFIX}/keys/redeem/", response_model=schemas.Key)
def redeem_key(
    key_value: str,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_key = db.query(models.Key).filter(
        models.Key.key_value == key_value,
        models.Key.is_used == False
    ).first()
    
    if not db_key:
        raise HTTPException(status_code=400, detail="Неверный или использованный ключ")
    
    if db_key.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Ключ истек")
    
    db_key.user_id = current_user.id
    db_key.is_used = True
    db_key.used_at = datetime.utcnow()
    db.commit()
    db.refresh(db_key)
    return db_key

# Эндпоинты Discord
@app.post(f"{API_V1_PREFIX}/discord/link/")
def create_discord_link(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if current_user.discord_id:
        raise HTTPException(status_code=400, detail="Discord уже привязан")
    
    code = utils.generate_discord_code()
    redis_client.setex(
        f"discord_link:{code}",
        KEY_CODE_EXPIRATION_MINUTES * 60,
        json.dumps({"user_id": current_user.id})
    )
    return {"code": code}

@app.post(f"{API_V1_PREFIX}/discord/verify/")
def verify_discord_link(
    code: str,
    discord_id: str,
    db: Session = Depends(get_db)
):
    data = redis_client.get(f"discord_link:{code}")
    if not data:
        raise HTTPException(status_code=400, detail="Неверный или истекший код")
    
    user_data = json.loads(data)
    user = db.query(models.User).filter(models.User.id == user_data["user_id"]).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    user.discord_id = discord_id
    db.commit()
    
    # Удаление кода из Redis
    redis_client.delete(f"discord_link:{code}")
    
    return {"status": "success"}

# Эндпоинты статистики
@app.get(f"{API_V1_PREFIX}/stats/", response_model=schemas.UserStats)
def get_user_stats(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    keys = db.query(models.Key).filter(models.Key.user_id == current_user.id).all()
    total_keys = len(keys)
    active_keys = sum(1 for k in keys if k.expires_at > datetime.utcnow() and k.is_used)
    expired_keys = sum(1 for k in keys if k.expires_at <= datetime.utcnow() or not k.is_used)
    invited_users = len(current_user.invited_users)
    
    return schemas.UserStats(
        total_keys=total_keys,
        active_keys=active_keys,
        expired_keys=expired_keys,
        invited_users=invited_users,
        last_login=current_user.last_login
    ) 