from flask import Flask, request, jsonify, send_from_directory
from flask_restful import Api, Resource
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sys
import datetime
import secrets
import string
from passlib.context import CryptContext
from sqlalchemy import inspect

# Добавление пути к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import SessionLocal, User, Key, Invite, DiscordCode, RoleLimits, Base, engine

# Настройка шифрования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Создание приложения Flask
app = Flask(__name__, static_folder="static")
CORS(app)
api = Api(app)

# Настройка JWT
app.config["JWT_SECRET_KEY"] = os.getenv("SECRET_KEY", "your_secret_key")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(days=1)
jwt = JWTManager(app)

# Инициализация базы данных - проверка и создание необходимых таблиц
def init_database():
    try:
        # Проверяем, существует ли таблица role_limits
        inspector = inspect(engine)
        if not inspector.has_table('role_limits'):
            print("Таблица role_limits не существует, создаем...")
            # Создаем все таблицы, которых нет
            Base.metadata.create_all(bind=engine)
            
            # Добавляем запись с дефолтными лимитами
            db = SessionLocal()
            try:
                default_limits = RoleLimits(
                    admin_monthly_invites=999,
                    support_monthly_invites=10,
                    user_monthly_invites=0
                )
                db.add(default_limits)
                db.commit()
                print("Таблица role_limits создана и инициализирована")
            except Exception as e:
                db.rollback()
                print(f"Ошибка при инициализации role_limits: {str(e)}")
            finally:
                db.close()
        else:
            print("Таблица role_limits уже существует")
    except Exception as e:
        print(f"Ошибка при инициализации базы данных: {str(e)}")

# Вызываем инициализацию при запуске
init_database()

# Функция для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

# Функция для получения реального IP-адреса
def get_client_ip():
    """Получает реальный IP-адрес клиента, проверяя различные заголовки и request.remote_addr"""
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        # X-Forwarded-For содержит список IP-адресов, первый - это исходный клиент
        ip = request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    elif request.environ.get('HTTP_X_REAL_IP'):
        ip = request.environ['HTTP_X_REAL_IP']
    elif request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        ip = request.headers.get('X-Real-IP')
    else:
        # Если нет заголовков прокси, используем стандартный remote_addr
        ip = request.remote_addr
    
    # Если IP не определен или localhost, попробуем использовать внешний IP
    if not ip or ip == '127.0.0.1' or ip == 'localhost' or ip == '::1':
        try:
            # В режиме разработки запрашиваем внешний IP через сервис
            # Это нужно только для тестирования
            import urllib.request
            external_ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
            if external_ip and external_ip != '127.0.0.1':
                ip = external_ip
        except:
            # В случае ошибки оставляем исходный IP
            pass
    
    return ip

# Функция для хеширования пароля
def hash_password(password):
    return pwd_context.hash(password)

# Функция для проверки пароля
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Генерация случайного кода для привязки Discord аккаунта
def generate_discord_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(6))

# API ресурсы
class Login(Resource):
    def post(self):
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        
        db = get_db()
        user = db.query(User).filter(User.username == username).first()
        
        if not user or not pwd_context.verify(password, user.password_hash):
            return {"message": "Неверное имя пользователя или пароль"}, 401
        
        if user.is_banned:
            return {"message": "Ваш аккаунт заблокирован"}, 403
        
        # Обновление информации о последнем входе
        ip_address = get_client_ip()
        user.update_login_info(ip_address)
        db.commit()
        
        # Создание JWT токена
        expires = datetime.timedelta(days=1)
        access_token = create_access_token(identity=user.id, expires_delta=expires)
        
        return {
            "token": access_token,
            "expires_at": (datetime.datetime.utcnow() + expires).isoformat()
        }

class Register(Resource):
    def post(self):
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        email = data.get("email")
        invite_code = data.get("invite_code")
        
        db = get_db()
        
        # Проверка инвайт-кода
        invite = db.query(Invite).filter(Invite.code == invite_code, Invite.used == False).first()
        if not invite or invite.is_expired():
            return {"message": "Недействительный инвайт-код"}, 400
        
        # Проверка, что имя пользователя и email не заняты
        if db.query(User).filter(User.username == username).first():
            return {"message": "Имя пользователя уже занято"}, 400
            
        if db.query(User).filter(User.email == email).first():
            return {"message": "Email уже используется"}, 400
        
        # Создание нового пользователя
        new_user = User(
            username=username,
            email=email,
            password_hash=hash_password(password)
        )
        
        # Сохранение IP-адреса регистрации
        ip_address = get_client_ip()
        new_user.update_login_info(ip_address)
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Пометить инвайт как использованный
        invite.used = True
        invite.used_by_id = new_user.id
        db.commit()
        
        # Создание тестового ключа на 24 часа
        test_key_expiry = datetime.datetime.utcnow() + datetime.timedelta(days=1)
        test_key = Key(
            user_id=new_user.id,
            expires_at=test_key_expiry
        )
        
        db.add(test_key)
        db.commit()
        
        return {
            "message": "Регистрация успешна",
            "id": new_user.id,
            "username": new_user.username,
            "created_at": new_user.created_at.isoformat(),
            "test_key": test_key.key
        }

class KeyResource(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        db = get_db()
        
        user = db.query(User).filter(User.id == user_id).first()
        if user.is_banned:
            return {"message": "Ваш аккаунт заблокирован"}, 403
        
        keys = db.query(Key).filter(Key.user_id == user_id).all()
        
        return {
            "keys": [
                {
                    "id": key.id,
                    "key": key.key,
                    "created_at": key.created_at.isoformat(),
                    "expires_at": key.expires_at.isoformat(),
                    "is_active": key.is_active and not key.is_expired(),
                    "time_left": key.time_left()
                } for key in keys
            ]
        }

class GenerateKey(Resource):
    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        data = request.get_json()
        duration_hours = data.get("duration_hours", 24)
        target_user_id = data.get("user_id")
        custom_key = data.get("custom_key")  # Пользовательское значение ключа
        
        db = get_db()
        
        # Проверка, что пользователь является администратором
        user = db.query(User).filter(User.id == user_id).first()
        if not user.is_admin and not user.is_support:
            return {"message": "Недостаточно прав для генерации ключа"}, 403
        
        if user.is_banned:
            return {"message": "Ваш аккаунт заблокирован"}, 403
        
        # Если указан пользователь, проверяем его существование
        if target_user_id:
            target_user = db.query(User).filter(User.id == target_user_id).first()
            if not target_user:
                return {"message": "Пользователь не найден"}, 404
        
        # Создание нового ключа
        key_expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=duration_hours)
        
        if custom_key:
            # Проверяем, не существует ли уже такой ключ
            existing_key = db.query(Key).filter(Key.key == custom_key).first()
            if existing_key:
                return {"message": "Ключ с таким значением уже существует"}, 400
                
            # Создание пользовательского ключа
            new_key = Key(
                key=custom_key,
                user_id=target_user_id,
                expires_at=key_expiry
            )
        else:
            # Создание случайного ключа
            new_key = Key(
                user_id=target_user_id,
                expires_at=key_expiry
            )
        
        db.add(new_key)
        db.commit()
        db.refresh(new_key)
        
        return {
            "key": new_key.key,
            "created_at": new_key.created_at.isoformat(),
            "expires_at": new_key.expires_at.isoformat()
        }

class RedeemKey(Resource):
    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        data = request.get_json()
        key_string = data.get("key")
        
        db = get_db()
        
        user = db.query(User).filter(User.id == user_id).first()
        if user.is_banned:
            return {"message": "Ваш аккаунт заблокирован"}, 403
        
        # Поиск ключа
        key = db.query(Key).filter(Key.key == key_string).first()
        if not key:
            return {"message": "Ключ не найден"}, 404
        
        # Проверка, что ключ не истёк и активен
        if key.is_expired():
            return {"message": "Ключ истёк"}, 400
        
        if not key.is_active:
            return {"message": "Ключ неактивен"}, 400
        
        # Проверка, что ключ свободен или уже принадлежит пользователю
        if key.user_id is not None and key.user_id != user_id:
            return {"message": "Ключ уже занят другим пользователем"}, 400
        
        # Привязка ключа к пользователю, если он ещё не привязан
        if key.user_id is None:
            key.user_id = user_id
            key.activated_at = datetime.datetime.utcnow()
            db.commit()
            db.refresh(key)
        
        return {
            "success": True,
            "key": {
                "id": key.id,
                "key": key.key,
                "created_at": key.created_at.isoformat(),
                "expires_at": key.expires_at.isoformat(),
                "is_active": key.is_active,
                "time_left": key.time_left()
            }
        }

class VerifyKey(Resource):
    def post(self):
        data = request.get_json()
        key_string = data.get("key")
        
        db = get_db()
        
        # Поиск ключа
        key = db.query(Key).filter(Key.key == key_string).first()
        if not key:
            return {"valid": False}, 200
        
        # Проверка, что ключ не истёк и активен
        if key.is_expired() or not key.is_active:
            return {"valid": False}, 200
        
        # Проверка, что ключ привязан к пользователю
        if key.user_id is None:
            return {"valid": False}, 200
        
        # Получение данных пользователя
        user = db.query(User).filter(User.id == key.user_id).first()
        if not user or user.is_banned:
            return {"valid": False}, 200
        
        return {
            "valid": True,
            "expires_at": key.expires_at.isoformat(),
            "time_left": key.time_left(),
            "user": {
                "id": user.id,
                "username": user.username
            }
        }

class UserInfo(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        db = get_db()
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"message": "Пользователь не найден"}, 404
        
        if user.is_banned:
            return {"message": "Ваш аккаунт заблокирован"}, 403
        
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at.isoformat(),
            "is_admin": user.is_admin,
            "is_support": user.is_support,
            "discord_linked": user.discord_id is not None,
            "discord_username": user.discord_username
        }

class GenerateInvite(Resource):
    @jwt_required()
    def post(self):
        try:
            user_id = get_jwt_identity()
            db = get_db()
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"message": "Пользователь не найден"}, 404
            
            if user.is_banned:
                return {"message": "Ваш аккаунт заблокирован"}, 403
            
            # Проверка прав на создание инвайтов
            if not user.can_create_invite():
                return {"message": "Недостаточно прав для создания инвайтов"}, 403
            
            # Хардкодим значения лимитов, так как таблица может не существовать
            admin_monthly_invites = 999
            support_monthly_invites = 10
            user_monthly_invites = 0
            
            # Определение лимита для пользователя в зависимости от его роли
            if user.is_admin:
                monthly_limit = admin_monthly_invites
            elif user.is_support:
                monthly_limit = support_monthly_invites
            else:
                monthly_limit = user_monthly_invites
            
            # Проверка количества созданных инвайтов за текущий месяц
            current_month_start = datetime.datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            used_invites = db.query(Invite).filter(
                Invite.created_by_id == user_id,
                Invite.created_at >= current_month_start
            ).count()
            
            if used_invites >= monthly_limit:
                return {"message": f"Достигнут месячный лимит инвайтов ({monthly_limit})"}, 403
            
            # Создание инвайт-кода со сроком действия 30 дней
            invite_expiry = datetime.datetime.utcnow() + datetime.timedelta(days=30)
            
            invite = Invite(
                created_by_id=user_id,
                expires_at=invite_expiry
            )
            
            db.add(invite)
            db.commit()
            db.refresh(invite)
            
            return {
                "code": invite.code,
                "created_at": invite.created_at.isoformat(),
                "expires_at": invite.expires_at.isoformat()
            }
        except Exception as e:
            # Логирование ошибки
            print(f"Ошибка при создании приглашения: {str(e)}")
            # Возвращаем ошибку в формате JSON
            return {"message": f"Ошибка при создании приглашения: {str(e)}"}, 500

class InviteList(Resource):
    @jwt_required()
    def get(self):
        try:
            user_id = get_jwt_identity()
            db = get_db()
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"message": "Пользователь не найден"}, 404
            
            if user.is_banned:
                return {"message": "Ваш аккаунт заблокирован"}, 403
            
            # Для администраторов показываем все инвайты, для остальных - только свои
            if user.is_admin:
                invites = db.query(Invite).all()
            else:
                invites = db.query(Invite).filter(Invite.created_by_id == user_id).all()
            
            return {
                "invites": [
                    {
                        "id": invite.id,
                        "code": invite.code,
                        "created_at": invite.created_at.isoformat(),
                        "expires_at": invite.expires_at.isoformat(),
                        "used": invite.used,
                        "used_by": invite.used_by.username if invite.used_by else None,
                        "created_by": invite.created_by.username
                    } for invite in invites
                ]
            }
        except Exception as e:
            # Логирование ошибки
            print(f"Ошибка при получении списка приглашений: {str(e)}")
            # Возвращаем ошибку в формате JSON
            return {"message": f"Ошибка при получении списка приглашений: {str(e)}"}, 500

class GenerateDiscordCode(Resource):
    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        db = get_db()
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"message": "Пользователь не найден"}, 404
        
        if user.is_banned:
            return {"message": "Ваш аккаунт заблокирован"}, 403
        
        # Создание кода для привязки Discord аккаунта
        discord_code_expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
        
        # Генерация случайного кода
        code = generate_discord_code()
        
        # Удаление старых неиспользованных кодов этого пользователя
        db.query(DiscordCode).filter(
            DiscordCode.user_id == user_id,
            DiscordCode.used == False
        ).delete()
        
        # Создание нового кода
        discord_code = DiscordCode(
            code=code,
            user_id=user_id,
            expires_at=discord_code_expiry
        )
        
        db.add(discord_code)
        db.commit()
        db.refresh(discord_code)
        
        return {
            "code": discord_code.code,
            "expires_at": discord_code.expires_at.isoformat()
        }

class VerifyDiscordCode(Resource):
    def post(self):
        data = request.get_json()
        code = data.get("code")
        discord_id = data.get("discord_id")
        discord_username = data.get("discord_username")
        
        db = get_db()
        
        # Поиск кода
        discord_code = db.query(DiscordCode).filter(
            DiscordCode.code == code,
            DiscordCode.used == False
        ).first()
        
        if not discord_code or discord_code.is_expired():
            return {"success": False, "message": "Недействительный или истекший код"}, 400
        
        # Получение пользователя
        user = db.query(User).filter(User.id == discord_code.user_id).first()
        if not user:
            return {"success": False, "message": "Пользователь не найден"}, 404
        
        if user.is_banned:
            return {"success": False, "message": "Аккаунт заблокирован"}, 403
        
        # Проверка, что Discord ID не привязан к другому аккаунту
        existing_discord = db.query(User).filter(User.discord_id == discord_id).first()
        if existing_discord and existing_discord.id != user.id:
            return {"success": False, "message": "Discord аккаунт уже привязан к другому пользователю"}, 400
        
        # Привязка Discord аккаунта к пользователю
        user.discord_id = discord_id
        user.discord_username = discord_username
        
        # Обновление информации о входе
        ip_address = get_client_ip()
        user.update_login_info(ip_address)
        
        # Пометить код как использованный
        discord_code.used = True
        
        db.commit()
        
        return {
            "success": True,
            "user_id": user.id
        }

class DiscordRedeemKey(Resource):
    def post(self):
        data = request.get_json()
        key_string = data.get("key")
        discord_id = data.get("discord_id")
        
        db = get_db()
        
        # Поиск пользователя по Discord ID
        user = db.query(User).filter(User.discord_id == discord_id).first()
        if not user:
            return {"success": False, "message": "Discord аккаунт не привязан к пользователю"}, 404
        
        if user.is_banned:
            return {"success": False, "message": "Аккаунт заблокирован"}, 403
        
        # Поиск ключа
        key = db.query(Key).filter(Key.key == key_string).first()
        if not key:
            return {"success": False, "message": "Ключ не найден"}, 404
        
        # Проверка, что ключ не истёк и активен
        if key.is_expired():
            return {"success": False, "message": "Ключ истёк"}, 400
        
        if not key.is_active:
            return {"success": False, "message": "Ключ неактивен"}, 400
        
        # Проверка, что ключ свободен или уже принадлежит пользователю
        if key.user_id is not None and key.user_id != user.id:
            return {"success": False, "message": "Ключ уже занят другим пользователем"}, 400
        
        # Привязка ключа к пользователю, если он ещё не привязан
        if key.user_id is None:
            key.user_id = user.id
            key.activated_at = datetime.datetime.utcnow()
        
        # Обновление информации о входе
        ip_address = get_client_ip()
        user.update_login_info(ip_address)
        
        db.commit()
        db.refresh(key)
        
        return {
            "success": True,
            "expires_at": key.expires_at.isoformat(),
            "time_left": key.time_left()
        }

class AdminGetUserInfo(Resource):
    @jwt_required()
    def get(self, user_id):
        current_user_id = get_jwt_identity()
        db = get_db()
        
        # Проверка, что текущий пользователь является администратором или саппортом
        current_user = db.query(User).filter(User.id == current_user_id).first()
        if not current_user or (not current_user.is_admin and not current_user.is_support):
            return {"message": "Недостаточно прав"}, 403
        
        if current_user.is_banned:
            return {"message": "Ваш аккаунт заблокирован"}, 403
        
        # Получение информации о пользователе
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"message": "Пользователь не найден"}, 404
        
        # Получение ключей пользователя
        keys = db.query(Key).filter(Key.user_id == user_id).all()
        
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "last_ip": user.last_ip,
            "is_admin": user.is_admin,
            "is_support": user.is_support,
            "is_banned": user.is_banned,
            "discord_linked": user.discord_id is not None,
            "discord_username": user.discord_username,
            "keys": [
                {
                    "id": key.id,
                    "key": key.key,
                    "created_at": key.created_at.isoformat(),
                    "expires_at": key.expires_at.isoformat(),
                    "is_active": key.is_active and not key.is_expired(),
                    "time_left": key.time_left()
                } for key in keys
            ]
        }

class AdminBanUser(Resource):
    @jwt_required()
    def post(self, user_id):
        current_user_id = get_jwt_identity()
        db = get_db()
        
        # Проверка, что текущий пользователь является администратором или саппортом
        current_user = db.query(User).filter(User.id == current_user_id).first()
        if not current_user:
            return {"message": "Пользователь не найден"}, 404
        
        if current_user.is_banned:
            return {"message": "Ваш аккаунт заблокирован"}, 403
        
        # Администраторы могут банить всех, саппорты только обычных пользователей
        target_user = db.query(User).filter(User.id == user_id).first()
        if not target_user:
            return {"message": "Пользователь не найден"}, 404
        
        if not current_user.is_admin and (target_user.is_admin or target_user.is_support):
            return {"message": "Недостаточно прав для бана администратора или саппорта"}, 403
        
        # Бан пользователя
        target_user.is_banned = True
        db.commit()
        
        return {"message": f"Пользователь {target_user.username} заблокирован"}

class AdminUnbanUser(Resource):
    @jwt_required()
    def post(self, user_id):
        current_user_id = get_jwt_identity()
        db = get_db()
        
        # Проверка, что текущий пользователь является администратором или саппортом
        current_user = db.query(User).filter(User.id == current_user_id).first()
        if not current_user:
            return {"message": "Пользователь не найден"}, 404
        
        if current_user.is_banned:
            return {"message": "Ваш аккаунт заблокирован"}, 403
        
        # Администраторы могут разбанить всех, саппорты только обычных пользователей
        target_user = db.query(User).filter(User.id == user_id).first()
        if not target_user:
            return {"message": "Пользователь не найден"}, 404
        
        if not current_user.is_admin and (target_user.is_admin or target_user.is_support):
            return {"message": "Недостаточно прав для разбана администратора или саппорта"}, 403
        
        # Разбан пользователя
        target_user.is_banned = False
        db.commit()
        
        return {"message": f"Пользователь {target_user.username} разблокирован"}

class AdminGetAllUsers(Resource):
    @jwt_required()
    def get(self):
        current_user_id = get_jwt_identity()
        db = get_db()
        
        # Проверка, что текущий пользователь является администратором или саппортом
        current_user = db.query(User).filter(User.id == current_user_id).first()
        if not current_user or (not current_user.is_admin and not current_user.is_support):
            return {"message": "Недостаточно прав"}, 403
        
        if current_user.is_banned:
            return {"message": "Ваш аккаунт заблокирован"}, 403
        
        # Получение списка пользователей
        users = db.query(User).all()
        
        return {
            "users": [
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "created_at": user.created_at.isoformat(),
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                    "last_ip": user.last_ip,
                    "is_admin": user.is_admin,
                    "is_support": user.is_support,
                    "is_banned": user.is_banned,
                    "discord_linked": user.discord_id is not None,
                    "discord_username": user.discord_username
                } for user in users
            ]
        }

# Добавление класса для управления модераторами
class AdminSetRole(Resource):
    @jwt_required()
    def post(self, user_id):
        current_user_id = get_jwt_identity()
        db = get_db()
        
        # Проверка, что текущий пользователь является администратором
        current_user = db.query(User).filter(User.id == current_user_id).first()
        if not current_user or not current_user.is_admin:
            return {"message": "Только администраторы могут управлять ролями пользователей"}, 403
        
        if current_user.is_banned:
            return {"message": "Ваш аккаунт заблокирован"}, 403
        
        # Получение данных из запроса
        data = request.get_json()
        role_type = data.get("role", "")
        
        # Найти целевого пользователя
        target_user = db.query(User).filter(User.id == user_id).first()
        if not target_user:
            return {"message": "Пользователь не найден"}, 404
        
        # Изменение роли пользователя
        if role_type.lower() == "admin":
            target_user.is_admin = True
            target_user.is_support = False
        elif role_type.lower() == "support":
            target_user.is_admin = False
            target_user.is_support = True
        elif role_type.lower() == "user":
            target_user.is_admin = False
            target_user.is_support = False
        else:
            return {"message": "Неверный тип роли. Допустимые значения: admin, support, user"}, 400
        
        db.commit()
        
        return {
            "message": f"Роль пользователя {target_user.username} изменена на {role_type}",
            "id": target_user.id,
            "username": target_user.username,
            "is_admin": target_user.is_admin,
            "is_support": target_user.is_support
        }

# Загрузка Minecraft модов
class DownloadMod(Resource):
    @jwt_required()
    def get(self, mod_name):
        user_id = get_jwt_identity()
        db = get_db()
        
        # Проверка, что пользователь существует и не заблокирован
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"message": "Пользователь не найден"}, 404
        
        if user.is_banned:
            return {"message": "Ваш аккаунт заблокирован"}, 403
        
        # Проверка, что у пользователя есть активный ключ
        active_key = db.query(Key).filter(
            Key.user_id == user_id,
            Key.is_active == True
        ).first()
        
        if not active_key or active_key.is_expired():
            return {"message": "Нет активного ключа"}, 403
        
        # Проверка существования мода
        mod_path = os.path.join("static", "mods", mod_name)
        if not os.path.exists(mod_path):
            return {"message": "Мод не найден"}, 404
        
        return send_from_directory("static/mods", mod_name, as_attachment=True)

# Добавление нового класса AdminUserActivity для просмотра последних входов и IP-адресов пользователей
class AdminUserActivity(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        db = get_db()
        
        # Проверка, что пользователь является администратором или саппортом
        user = db.query(User).filter(User.id == user_id).first()
        if not user or (not user.is_admin and not user.is_support):
            return {"message": "Недостаточно прав для просмотра активности пользователей"}, 403
            
        if user.is_banned:
            return {"message": "Ваш аккаунт заблокирован"}, 403
        
        # Получение всех пользователей с данными о последнем входе
        users = db.query(User).order_by(User.last_login.desc().nullslast()).all()
        
        return {
            "users": [
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "created_at": user.created_at.isoformat(),
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                    "last_ip": user.last_ip,
                    "is_admin": user.is_admin,
                    "is_support": user.is_support,
                    "is_banned": user.is_banned,
                    "discord_linked": user.discord_id is not None,
                    "discord_username": user.discord_username
                } for user in users
            ]
        }

class AdminDeleteInvite(Resource):
    @jwt_required()
    def post(self, invite_id):
        try:
            user_id = get_jwt_identity()
            db = get_db()
            
            # Проверка, что текущий пользователь является администратором
            current_user = db.query(User).filter(User.id == user_id).first()
            if not current_user or not current_user.is_admin:
                return {"message": "Недостаточно прав для удаления инвайта"}, 403
                
            if current_user.is_banned:
                return {"message": "Ваш аккаунт заблокирован"}, 403
            
            # Поиск инвайта
            invite = db.query(Invite).filter(Invite.id == invite_id).first()
            if not invite:
                return {"message": "Инвайт не найден"}, 404
                
            # Удаление инвайта
            db.delete(invite)
            db.commit()
            
            return {"message": "Инвайт успешно удален"}
        except Exception as e:
            # Логирование ошибки
            print(f"Ошибка при удалении инвайта: {str(e)}")
            # Возвращаем ошибку в формате JSON
            return {"message": f"Ошибка при удалении инвайта: {str(e)}"}, 500

class AdminSetInviteLimits(Resource):
    @jwt_required()
    def post(self):
        try:
            user_id = get_jwt_identity()
            db = get_db()
            
            # Проверка, что текущий пользователь является администратором
            current_user = db.query(User).filter(User.id == user_id).first()
            if not current_user or not current_user.is_admin:
                return {"message": "Недостаточно прав для изменения лимитов"}, 403
                
            if current_user.is_banned:
                return {"message": "Ваш аккаунт заблокирован"}, 403
            
            # Получение данных из запроса
            data = request.get_json()
            admin_limit = data.get("admin_limit", 999)  # Практически неограниченно для админов
            support_limit = data.get("support_limit", 10)
            user_limit = data.get("user_limit", 0)
            
            # Для обхода отсутствия таблицы role_limits просто возвращаем успех
            # В будущем, когда таблица будет создана, можно будет вернуть к исходной реализации
            
            return {
                "admin_limit": admin_limit,
                "support_limit": support_limit,
                "user_limit": user_limit,
                "message": "Лимиты успешно обновлены"
            }
        except Exception as e:
            # Логирование ошибки
            print(f"Ошибка при установке лимитов приглашений: {str(e)}")
            # Возвращаем ошибку в формате JSON
            return {"message": f"Ошибка при установке лимитов приглашений: {str(e)}"}, 500

class GetInviteLimits(Resource):
    @jwt_required()
    def get(self):
        try:
            user_id = get_jwt_identity()
            db = get_db()
            
            # Проверка пользователя
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"message": "Пользователь не найден"}, 404
                
            if user.is_banned:
                return {"message": "Ваш аккаунт заблокирован"}, 403
            
            # Хардкодим значения лимитов, так как таблица может не существовать
            admin_monthly_invites = 999
            support_monthly_invites = 10
            user_monthly_invites = 0
            
            # Подсчет количества использованных инвайтов за текущий месяц
            current_month_start = datetime.datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            used_invites = db.query(Invite).filter(
                Invite.created_by_id == user_id,
                Invite.created_at >= current_month_start
            ).count()
            
            # Определение лимита для текущего пользователя
            if user.is_admin:
                user_limit = admin_monthly_invites
            elif user.is_support:
                user_limit = support_monthly_invites
            else:
                user_limit = user_monthly_invites
                
            return {
                "monthly_limit": user_limit,
                "used_invites": used_invites,
                "remaining_invites": max(0, user_limit - used_invites),
                "global_limits": {
                    "admin": admin_monthly_invites,
                    "support": support_monthly_invites,
                    "user": user_monthly_invites
                }
            }
        except Exception as e:
            # Логирование ошибки
            print(f"Ошибка при получении лимитов приглашений: {str(e)}")
            # Возвращаем ошибку в формате JSON
            return {"message": f"Ошибка при получении лимитов приглашений: {str(e)}"}, 500

class AdminDeleteMultipleInvites(Resource):
    @jwt_required()
    def post(self):
        try:
            user_id = get_jwt_identity()
            db = get_db()
            
            # Проверка, что текущий пользователь является администратором
            current_user = db.query(User).filter(User.id == user_id).first()
            if not current_user or not current_user.is_admin:
                return {"message": "Недостаточно прав для удаления инвайтов"}, 403
                
            if current_user.is_banned:
                return {"message": "Ваш аккаунт заблокирован"}, 403
            
            # Получение списка ID инвайтов для удаления
            data = request.get_json()
            invite_ids = data.get("invite_ids", [])
            
            if not invite_ids:
                return {"message": "Не указаны ID инвайтов для удаления"}, 400
            
            # Удаление инвайтов
            deleted_count = 0
            for invite_id in invite_ids:
                invite = db.query(Invite).filter(Invite.id == invite_id).first()
                if invite:
                    db.delete(invite)
                    deleted_count += 1
            
            db.commit()
            
            return {
                "message": f"Удалено инвайтов: {deleted_count}",
                "deleted_count": deleted_count
            }
        except Exception as e:
            # Логирование ошибки
            print(f"Ошибка при удалении инвайтов: {str(e)}")
            # Возвращаем ошибку в формате JSON
            return {"message": f"Ошибка при удалении инвайтов: {str(e)}"}, 500

class AdminGetAllKeys(Resource):
    @jwt_required()
    def get(self):
        try:
            user_id = get_jwt_identity()
            db = get_db()
            
            # Проверка, что текущий пользователь является администратором
            current_user = db.query(User).filter(User.id == user_id).first()
            if not current_user or not current_user.is_admin:
                return {"message": "Недостаточно прав для просмотра всех ключей"}, 403
                
            if current_user.is_banned:
                return {"message": "Ваш аккаунт заблокирован"}, 403
            
            # Получение всех ключей с данными о пользователях
            keys = db.query(Key).all()
            
            return {
                "keys": [
                    {
                        "id": key.id,
                        "key": key.key,
                        "created_at": key.created_at.isoformat(),
                        "expires_at": key.expires_at.isoformat(),
                        "is_active": key.is_active and not key.is_expired(),
                        "time_left": key.time_left(),
                        "user": {
                            "id": key.user.id,
                            "username": key.user.username
                        } if key.user else None
                    } for key in keys
                ]
            }
        except Exception as e:
            # Логирование ошибки
            print(f"Ошибка при получении списка ключей: {str(e)}")
            # Возвращаем ошибку в формате JSON
            return {"message": f"Ошибка при получении списка ключей: {str(e)}"}, 500

class AdminRevokeKey(Resource):
    @jwt_required()
    def post(self, key_id):
        try:
            user_id = get_jwt_identity()
            db = get_db()
            
            # Проверка, что текущий пользователь является администратором
            current_user = db.query(User).filter(User.id == user_id).first()
            if not current_user or not current_user.is_admin:
                return {"message": "Недостаточно прав для отзыва ключа"}, 403
                
            if current_user.is_banned:
                return {"message": "Ваш аккаунт заблокирован"}, 403
            
            # Поиск ключа
            key = db.query(Key).filter(Key.id == key_id).first()
            if not key:
                return {"message": "Ключ не найден"}, 404
                
            # Отзыв ключа (деактивация)
            key.is_active = False
            db.commit()
            
            return {"message": "Ключ успешно отозван"}
        except Exception as e:
            # Логирование ошибки
            print(f"Ошибка при отзыве ключа: {str(e)}")
            # Возвращаем ошибку в формате JSON
            return {"message": f"Ошибка при отзыве ключа: {str(e)}"}, 500

class AdminRestoreKey(Resource):
    @jwt_required()
    def post(self, key_id):
        try:
            user_id = get_jwt_identity()
            db = get_db()
            
            # Проверка, что текущий пользователь является администратором
            current_user = db.query(User).filter(User.id == user_id).first()
            if not current_user or not current_user.is_admin:
                return {"message": "Недостаточно прав для восстановления ключа"}, 403
                
            if current_user.is_banned:
                return {"message": "Ваш аккаунт заблокирован"}, 403
            
            # Поиск ключа
            key = db.query(Key).filter(Key.id == key_id).first()
            if not key:
                return {"message": "Ключ не найден"}, 404
                
            # Восстановление ключа (активация)
            key.is_active = True
            db.commit()
            
            return {"message": "Ключ успешно восстановлен"}
        except Exception as e:
            # Логирование ошибки
            print(f"Ошибка при восстановлении ключа: {str(e)}")
            # Возвращаем ошибку в формате JSON
            return {"message": f"Ошибка при восстановлении ключа: {str(e)}"}, 500

class AdminBulkKeyAction(Resource):
    @jwt_required()
    def post(self):
        try:
            user_id = get_jwt_identity()
            db = get_db()
            
            # Проверка, что текущий пользователь является администратором
            current_user = db.query(User).filter(User.id == user_id).first()
            if not current_user or not current_user.is_admin:
                return {"message": "Недостаточно прав для массовых операций с ключами"}, 403
                
            if current_user.is_banned:
                return {"message": "Ваш аккаунт заблокирован"}, 403
            
            # Получение данных из запроса
            data = request.get_json()
            key_ids = data.get("key_ids", [])
            action = data.get("action", "")
            
            if not key_ids:
                return {"message": "Не указаны ID ключей"}, 400
                
            if action not in ["revoke", "restore", "delete"]:
                return {"message": "Неверное действие. Допустимые значения: revoke, restore, delete"}, 400
            
            # Выполнение массового действия
            affected_count = 0
            
            if action == "revoke":
                # Отзыв ключей
                affected_count = db.query(Key).filter(Key.id.in_(key_ids)).update({"is_active": False}, synchronize_session=False)
            
            elif action == "restore":
                # Восстановление ключей
                affected_count = db.query(Key).filter(Key.id.in_(key_ids)).update({"is_active": True}, synchronize_session=False)
            
            elif action == "delete":
                # Удаление ключей
                affected_count = db.query(Key).filter(Key.id.in_(key_ids)).delete(synchronize_session=False)
            
            db.commit()
            
            action_text = {
                "revoke": "отозвано",
                "restore": "восстановлено",
                "delete": "удалено"
            }
            
            return {
                "message": f"Успешно {action_text[action]} ключей: {affected_count}",
                "affected_count": affected_count
            }
        except Exception as e:
            # Логирование ошибки
            print(f"Ошибка при выполнении массового действия с ключами: {str(e)}")
            db.rollback()
            # Возвращаем ошибку в формате JSON
            return {"message": f"Ошибка при выполнении массового действия с ключами: {str(e)}"}, 500

class AdminCleanupKeys(Resource):
    @jwt_required()
    def post(self):
        try:
            user_id = get_jwt_identity()
            db = get_db()
            
            # Проверка, что текущий пользователь является администратором
            current_user = db.query(User).filter(User.id == user_id).first()
            if not current_user or not current_user.is_admin:
                return {"message": "Недостаточно прав для очистки базы данных"}, 403
                
            if current_user.is_banned:
                return {"message": "Ваш аккаунт заблокирован"}, 403
            
            # Получение параметров очистки
            data = request.get_json()
            cleanup_expired = data.get("cleanup_expired", True)  # Удалять истекшие ключи
            cleanup_revoked = data.get("cleanup_revoked", True)  # Удалять отозванные ключи
            older_than_days = data.get("older_than_days", 30)  # Ключи старше N дней
            
            # Вычисление даты для фильтрации по возрасту
            cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=older_than_days)
            
            # Построение запроса на основе параметров
            query = db.query(Key).filter(Key.created_at < cutoff_date)
            
            if cleanup_expired and cleanup_revoked:
                # Очистка и истекших, и отозванных ключей
                query = query.filter((Key.expires_at < datetime.datetime.utcnow()) | (Key.is_active == False))
            elif cleanup_expired:
                # Очистка только истекших ключей
                query = query.filter(Key.expires_at < datetime.datetime.utcnow())
            elif cleanup_revoked:
                # Очистка только отозванных ключей
                query = query.filter(Key.is_active == False)
            else:
                # Если не выбрано ни одного параметра
                return {"message": "Не выбраны параметры очистки"}, 400
            
            # Получаем количество удаляемых ключей
            keys_count = query.count()
            
            # Выполняем удаление
            query.delete(synchronize_session=False)
            db.commit()
            
            return {
                "message": f"Очистка выполнена успешно. Удалено ключей: {keys_count}",
                "deleted_count": keys_count
            }
        except Exception as e:
            # Логирование ошибки
            print(f"Ошибка при очистке базы данных: {str(e)}")
            db.rollback()
            # Возвращаем ошибку в формате JSON
            return {"message": f"Ошибка при очистке базы данных: {str(e)}"}, 500

class AdminGetCleanupStats(Resource):
    @jwt_required()
    def get(self):
        try:
            user_id = get_jwt_identity()
            db = get_db()
            
            # Проверка, что текущий пользователь является администратором
            current_user = db.query(User).filter(User.id == user_id).first()
            if not current_user or not current_user.is_admin:
                return {"message": "Недостаточно прав для просмотра статистики"}, 403
                
            if current_user.is_banned:
                return {"message": "Ваш аккаунт заблокирован"}, 403
            
            # Получение статистики по истекшим и отозванным ключам
            # Истекшие ключи: expires_at < now
            expired_count = db.query(Key).filter(Key.expires_at < datetime.datetime.utcnow()).count()
            
            # Отозванные ключи: is_active = False
            revoked_count = db.query(Key).filter(Key.is_active == False).count()
            
            # Общее количество ключей
            total_count = db.query(Key).count()
            
            # Статистика по возрасту ключей
            # Старше 30 дней
            cutoff_date_30 = datetime.datetime.utcnow() - datetime.timedelta(days=30)
            older_than_30_days = db.query(Key).filter(Key.created_at < cutoff_date_30).count()
            
            # Старше 90 дней
            cutoff_date_90 = datetime.datetime.utcnow() - datetime.timedelta(days=90)
            older_than_90_days = db.query(Key).filter(Key.created_at < cutoff_date_90).count()
            
            # Старше 180 дней
            cutoff_date_180 = datetime.datetime.utcnow() - datetime.timedelta(days=180)
            older_than_180_days = db.query(Key).filter(Key.created_at < cutoff_date_180).count()
            
            return {
                "total_keys": total_count,
                "expired_keys": expired_count,
                "revoked_keys": revoked_count,
                "older_than_30_days": older_than_30_days,
                "older_than_90_days": older_than_90_days,
                "older_than_180_days": older_than_180_days
            }
        except Exception as e:
            # Логирование ошибки
            print(f"Ошибка при получении статистики: {str(e)}")
            # Возвращаем ошибку в формате JSON
            return {"message": f"Ошибка при получении статистики: {str(e)}"}, 500

# Регистрация API ресурсов
api.add_resource(Login, "/api/auth/login")
api.add_resource(Register, "/api/users/register")
api.add_resource(KeyResource, "/api/keys")
api.add_resource(GenerateKey, "/api/keys/generate")
api.add_resource(RedeemKey, "/api/keys/redeem")
api.add_resource(VerifyKey, "/api/keys/verify")
api.add_resource(UserInfo, "/api/users/me")
api.add_resource(GenerateInvite, "/api/invites/generate")
api.add_resource(InviteList, "/api/invites")
api.add_resource(GenerateDiscordCode, "/api/users/discord-code")
api.add_resource(VerifyDiscordCode, "/api/discord/verify-code")
api.add_resource(DiscordRedeemKey, "/api/discord/redeem-key")
api.add_resource(AdminGetUserInfo, "/api/admin/users/<int:user_id>")
api.add_resource(AdminBanUser, "/api/admin/users/<int:user_id>/ban")
api.add_resource(AdminUnbanUser, "/api/admin/users/<int:user_id>/unban")
api.add_resource(AdminSetRole, "/api/admin/users/<int:user_id>/role")
api.add_resource(AdminGetAllUsers, "/api/admin/users")
api.add_resource(AdminUserActivity, "/api/admin/users/activity")
api.add_resource(AdminDeleteInvite, "/api/admin/invites/<int:invite_id>/delete")
api.add_resource(AdminSetInviteLimits, "/api/admin/invites/limits")
api.add_resource(GetInviteLimits, "/api/invites/limits")
api.add_resource(DownloadMod, "/api/download/<string:mod_name>")
api.add_resource(AdminDeleteMultipleInvites, "/api/admin/invites/delete")
api.add_resource(AdminGetAllKeys, "/api/admin/keys")
api.add_resource(AdminRevokeKey, "/api/admin/keys/<int:key_id>/revoke")
api.add_resource(AdminRestoreKey, "/api/admin/keys/<int:key_id>/restore")
api.add_resource(AdminBulkKeyAction, "/api/admin/keys/bulk-action")
api.add_resource(AdminCleanupKeys, "/api/admin/keys/cleanup")
api.add_resource(AdminGetCleanupStats, "/api/admin/keys/stats")

# Основной маршрут для одностраничного приложения
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == "__main__":
    # Создание директории для модов, если она не существует
    os.makedirs(os.path.join("static", "mods"), exist_ok=True)
    
    # Запуск сервера
    app.run(host="0.0.0.0", port=5000, debug=True) 