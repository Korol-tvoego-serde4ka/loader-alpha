import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import sys
import asyncio
import datetime
import requests
import json
import aiohttp
from dotenv import load_dotenv

# Добавление пути к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import SessionLocal, User, Key, DiscordCode

# Загрузка переменных окружения
load_dotenv()

# Настройка Discord бота
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SERVER_API_URL = os.getenv("SERVER_API_URL", "http://localhost:5000/api")

# Настройка ролей на сервере Discord
ADMIN_ROLE_NAME = "Admin"
SUPPORT_ROLE_NAME = "Support"
SUBSCRIBER_ROLE_NAME = "Subs"

# Создание интенций бота
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Создание бота
bot = commands.Bot(command_prefix='!', intents=intents)

# Создание API клиента для взаимодействия с сервером
class APIClient:
    @staticmethod
    def verify_discord_code(code, discord_id, discord_username):
        """Проверка кода привязки Discord аккаунта"""
        url = f"{SERVER_API_URL}/discord/verify-code"
        data = {
            "code": code,
            "discord_id": discord_id,
            "discord_username": discord_username
        }
        
        try:
            response = requests.post(url, json=data)
            return response.json(), response.status_code
        except Exception as e:
            print(f"Ошибка при запросе к API: {e}")
            return {"success": False, "message": "Ошибка сервера"}, 500
    
    @staticmethod
    def redeem_key(key, discord_id):
        """Привязка ключа к аккаунту через Discord"""
        url = f"{SERVER_API_URL}/discord/redeem-key"
        data = {
            "key": key,
            "discord_id": discord_id
        }
        
        try:
            response = requests.post(url, json=data)
            return response.json(), response.status_code
        except Exception as e:
            print(f"Ошибка при запросе к API: {e}")
            return {"success": False, "message": "Ошибка сервера"}, 500
    
    @staticmethod
    def generate_key(duration_hours=24, token=None):
        """Генерация ключа для админов/модераторов"""
        url = f"{SERVER_API_URL}/keys/generate"
        data = {
            "duration_hours": duration_hours
        }
        headers = {}
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        try:
            response = requests.post(url, json=data, headers=headers)
            return response.json(), response.status_code
        except Exception as e:
            print(f"Ошибка при запросе к API: {e}")
            return {"success": False, "message": "Ошибка сервера"}, 500

# Функция для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

# Функция для форматирования времени
def format_time_left(seconds):
    """Возвращает отформатированное оставшееся время"""
    if seconds <= 0:
        return "истек"
    
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} дн.")
    if hours > 0:
        parts.append(f"{hours} ч.")
    if minutes > 0:
        parts.append(f"{minutes} мин.")
    if seconds > 0 and not parts:  # Показываем секунды только если нет дней/часов/минут
        parts.append(f"{seconds} сек.")
    
    return " ".join(parts)

# Проверка роли пользователя
def is_admin(interaction: discord.Interaction):
    """Проверяет, имеет ли пользователь роль админа"""
    return any(role.name == ADMIN_ROLE_NAME for role in interaction.user.roles)

def is_support(interaction: discord.Interaction):
    """Проверяет, имеет ли пользователь роль саппорта"""
    return any(role.name == SUPPORT_ROLE_NAME for role in interaction.user.roles)

def is_subscriber(interaction: discord.Interaction):
    """Проверяет, имеет ли пользователь роль подписчика"""
    return any(role.name == SUBSCRIBER_ROLE_NAME for role in interaction.user.roles)

def is_admin_or_support(interaction: discord.Interaction):
    """Проверяет, имеет ли пользователь роль админа или саппорта"""
    return is_admin(interaction) or is_support(interaction)

# События бота
@bot.event
async def on_ready():
    """Вызывается при успешном подключении бота"""
    print(f'Бот успешно подключен как {bot.user.name}')
    
    # Отключение автоматического получения списка участников - это исправит ошибку
    bot.member_cache_flags.joined = True
    
    # Синхронизация команд с Discord
    try:
        synced = await bot.tree.sync()
        print(f"Синхронизировано {len(synced)} команд")
    except Exception as e:
        print(f"Ошибка при синхронизации команд: {e}")
    
    # Запуск задачи проверки истекших ключей
    check_expired_keys.start()

@tasks.loop(hours=1)
async def check_expired_keys():
    """Проверка и удаление истекших ключей подписчиков"""
    print("Проверка истекших ключей...")
    
    db = get_db()
    
    try:
        # Получение всех пользователей с привязанным Discord ID
        users_with_discord = db.query(User).filter(User.discord_id != None).all()
        
        for user in users_with_discord:
            # Получение активных ключей пользователя
            active_keys = db.query(Key).filter(
                Key.user_id == user.id,
                Key.is_active == True
            ).all()
            
            has_valid_key = False
            for key in active_keys:
                if not key.is_expired():
                    has_valid_key = True
                    break
            
            # Если у пользователя нет активных ключей, но есть роль подписчика
            if not has_valid_key:
                # Поиск сервера и участника
                for guild in bot.guilds:
                    member = guild.get_member(int(user.discord_id))
                    if member:
                        # Поиск роли подписчика
                        subscriber_role = discord.utils.get(guild.roles, name=SUBSCRIBER_ROLE_NAME)
                        if subscriber_role and subscriber_role in member.roles:
                            # Удаление роли подписчика
                            try:
                                await member.remove_roles(subscriber_role)
                                print(f"У пользователя {member.name} удалена роль {SUBSCRIBER_ROLE_NAME}")
                            except Exception as e:
                                print(f"Ошибка при удалении роли у {member.name}: {e}")
    
    except Exception as e:
        print(f"Ошибка при проверке истекших ключей: {e}")
    finally:
        db.close()

# Обработчик ошибок
@bot.event
async def on_error(event, *args, **kwargs):
    """Обработчик ошибок бота"""
    print(f"Произошла ошибка в событии {event}: {sys.exc_info()}")

# Команды бота
@bot.tree.command(name="code", description="Привязка аккаунта сайта к Discord")
@app_commands.describe(code="6-значный код привязки с сайта")
async def link_discord(interaction: discord.Interaction, code: str):
    """Привязка Discord аккаунта к аккаунту на сайте"""
    await interaction.response.defer(ephemeral=True)  # Приватный ответ
    
    # Получение информации о пользователе
    discord_id = str(interaction.user.id)
    discord_username = f"{interaction.user.name}"
    
    # Проверка кода через API
    result, status_code = APIClient.verify_discord_code(code, discord_id, discord_username)
    
    if status_code == 200 and result.get("success", False):
        # Успешная привязка
        await interaction.followup.send("✅ Ваш Discord аккаунт успешно привязан к аккаунту на сайте.")
        
        # Проверка наличия активных ключей и выдача роли подписчика
        db = get_db()
        try:
            user_id = result.get("user_id")
            active_keys = db.query(Key).filter(
                Key.user_id == user_id,
                Key.is_active == True
            ).all()
            
            has_valid_key = False
            for key in active_keys:
                if not key.is_expired():
                    has_valid_key = True
                    break
            
            if has_valid_key:
                subscriber_role = discord.utils.get(interaction.guild.roles, name=SUBSCRIBER_ROLE_NAME)
                if subscriber_role:
                    await interaction.user.add_roles(subscriber_role)
                    await interaction.followup.send("🔑 Вам выдана роль подписчика.")
        except Exception as e:
            print(f"Ошибка при проверке ключей пользователя: {e}")
        finally:
            db.close()
    else:
        # Ошибка при привязке
        error_message = result.get("message", "Неизвестная ошибка")
        await interaction.followup.send(f"❌ Ошибка привязки аккаунта: {error_message}")

@bot.tree.command(name="redeem", description="Активация ключа подписки")
@app_commands.describe(key="Ключ в формате XXXX-XXXX-XXXX-XXXX")
async def redeem_key(interaction: discord.Interaction, key: str):
    """Активация ключа подписки"""
    await interaction.response.defer(ephemeral=True)  # Приватный ответ
    
    # Получение информации о пользователе
    discord_id = str(interaction.user.id)
    
    # Привязка ключа через API
    result, status_code = APIClient.redeem_key(key, discord_id)
    
    if status_code == 200 and result.get("success", False):
        # Успешная активация ключа
        expires_at = result.get("expires_at")
        time_left = result.get("time_left", 0)
        
        # Форматирование времени
        formatted_time = format_time_left(time_left)
        
        # Добавление роли подписчика
        subscriber_role = discord.utils.get(interaction.guild.roles, name=SUBSCRIBER_ROLE_NAME)
        if subscriber_role:
            await interaction.user.add_roles(subscriber_role)
        
        await interaction.followup.send(f"✅ Ключ успешно активирован!\nСрок действия: {formatted_time}")
    else:
        # Ошибка при активации ключа
        error_message = result.get("message", "Неизвестная ошибка")
        await interaction.followup.send(f"❌ Ошибка активации ключа: {error_message}")

@bot.tree.command(name="status", description="Проверка статуса подписки")
async def check_status(interaction: discord.Interaction):
    """Проверка статуса подписки пользователя"""
    await interaction.response.defer(ephemeral=True)  # Приватный ответ
    
    # Получение информации о пользователе
    discord_id = str(interaction.user.id)
    
    db = get_db()
    try:
        # Поиск пользователя по Discord ID
        user = db.query(User).filter(User.discord_id == discord_id).first()
        
        if not user:
            await interaction.followup.send("❌ Ваш Discord аккаунт не привязан к аккаунту на сайте.")
            return
        
        if user.is_banned:
            await interaction.followup.send("🚫 Ваш аккаунт заблокирован.")
            return
        
        # Получение активных ключей пользователя
        active_keys = db.query(Key).filter(
            Key.user_id == user.id,
            Key.is_active == True
        ).all()
        
        # Создание списка активных ключей
        valid_keys = []
        for key in active_keys:
            if not key.is_expired():
                valid_keys.append({
                    "key": key.key,
                    "time_left": key.time_left(),
                    "expires_at": key.expires_at
                })
        
        if not valid_keys:
            await interaction.followup.send("⚠️ У вас нет активных ключей.")
            return
        
        # Отправка информации о ключах
        embed = discord.Embed(
            title="Статус подписки",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Имя пользователя",
            value=user.username,
            inline=False
        )
        
        for i, key_info in enumerate(valid_keys, 1):
            formatted_time = format_time_left(key_info["time_left"])
            embed.add_field(
                name=f"Ключ {i}",
                value=f"```{key_info['key']}```\nОсталось: {formatted_time}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        print(f"Ошибка при проверке статуса: {e}")
        await interaction.followup.send("❌ Произошла ошибка при проверке статуса.")
    finally:
        db.close()

@bot.tree.command(name="genkey", description="Генерация ключа (только для админов и саппорта)")
@app_commands.describe(duration="Продолжительность ключа в часах (по умолчанию 24)")
async def generate_key(interaction: discord.Interaction, duration: int = 24):
    """Генерация ключа (только для админов и саппорта)"""
    await interaction.response.defer(ephemeral=True)  # Приватный ответ
    
    # Проверка роли пользователя
    if not is_admin_or_support(interaction):
        await interaction.followup.send("❌ У вас недостаточно прав для выполнения этой команды.")
        return
    
    # Генерация ключа через API
    result, status_code = APIClient.generate_key(duration_hours=duration)
    
    if status_code == 200 and "key" in result:
        # Успешная генерация ключа
        key = result["key"]
        expires_at = result.get("expires_at")
        
        # Создание эмбеда с информацией о ключе
        embed = discord.Embed(
            title="Сгенерирован новый ключ",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Ключ",
            value=f"```{key}```",
            inline=False
        )
        
        embed.add_field(
            name="Срок действия",
            value=f"{duration} часов",
            inline=True
        )
        
        embed.add_field(
            name="Сгенерирован",
            value=f"<@{interaction.user.id}>",
            inline=True
        )
        
        await interaction.followup.send(embed=embed)
    else:
        # Ошибка при генерации ключа
        error_message = result.get("message", "Неизвестная ошибка")
        await interaction.followup.send(f"❌ Ошибка генерации ключа: {error_message}")

@bot.tree.command(name="ban", description="Бан пользователя (только для админов и саппорта)")
@app_commands.describe(username="Имя пользователя на сайте")
async def ban_user(interaction: discord.Interaction, username: str):
    """Бан пользователя (только для админов и саппорта)"""
    await interaction.response.defer(ephemeral=True)  # Приватный ответ
    
    # Проверка роли пользователя
    if not is_admin_or_support(interaction):
        await interaction.followup.send("❌ У вас недостаточно прав для выполнения этой команды.")
        return
    
    db = get_db()
    try:
        # Поиск пользователя по имени
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            await interaction.followup.send(f"❌ Пользователь {username} не найден.")
            return
        
        # Проверка прав на бан
        is_requester_admin = is_admin(interaction)
        if not is_requester_admin and (user.is_admin or user.is_support):
            await interaction.followup.send("❌ У вас недостаточно прав для бана администратора или саппорта.")
            return
        
        # Бан пользователя
        user.is_banned = True
        db.commit()
        
        # Если у пользователя есть привязанный Discord аккаунт, удаляем роль подписчика
        if user.discord_id:
            try:
                member = interaction.guild.get_member(int(user.discord_id))
                if member:
                    subscriber_role = discord.utils.get(interaction.guild.roles, name=SUBSCRIBER_ROLE_NAME)
                    if subscriber_role and subscriber_role in member.roles:
                        await member.remove_roles(subscriber_role)
            except Exception as e:
                print(f"Ошибка при удалении роли: {e}")
        
        await interaction.followup.send(f"✅ Пользователь {username} заблокирован.")
        
    except Exception as e:
        print(f"Ошибка при бане пользователя: {e}")
        await interaction.followup.send("❌ Произошла ошибка при бане пользователя.")
    finally:
        db.close()

@bot.tree.command(name="unban", description="Разбан пользователя (только для админов и саппорта)")
@app_commands.describe(username="Имя пользователя на сайте")
async def unban_user(interaction: discord.Interaction, username: str):
    """Разбан пользователя (только для админов и саппорта)"""
    await interaction.response.defer(ephemeral=True)  # Приватный ответ
    
    # Проверка роли пользователя
    if not is_admin_or_support(interaction):
        await interaction.followup.send("❌ У вас недостаточно прав для выполнения этой команды.")
        return
    
    db = get_db()
    try:
        # Поиск пользователя по имени
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            await interaction.followup.send(f"❌ Пользователь {username} не найден.")
            return
        
        # Проверка прав на разбан
        is_requester_admin = is_admin(interaction)
        if not is_requester_admin and (user.is_admin or user.is_support):
            await interaction.followup.send("❌ У вас недостаточно прав для разбана администратора или саппорта.")
            return
        
        # Разбан пользователя
        user.is_banned = False
        db.commit()
        
        # Если у пользователя есть привязанный Discord аккаунт и активный ключ, возвращаем роль подписчика
        if user.discord_id:
            active_keys = db.query(Key).filter(
                Key.user_id == user.id,
                Key.is_active == True
            ).all()
            
            has_valid_key = False
            for key in active_keys:
                if not key.is_expired():
                    has_valid_key = True
                    break
            
            if has_valid_key:
                try:
                    member = interaction.guild.get_member(int(user.discord_id))
                    if member:
                        subscriber_role = discord.utils.get(interaction.guild.roles, name=SUBSCRIBER_ROLE_NAME)
                        if subscriber_role:
                            await member.add_roles(subscriber_role)
                except Exception as e:
                    print(f"Ошибка при добавлении роли: {e}")
        
        await interaction.followup.send(f"✅ Пользователь {username} разблокирован.")
        
    except Exception as e:
        print(f"Ошибка при разбане пользователя: {e}")
        await interaction.followup.send("❌ Произошла ошибка при разбане пользователя.")
    finally:
        db.close()

@bot.tree.command(name="user", description="Информация о пользователе (только для админов и саппорта)")
@app_commands.describe(username="Имя пользователя на сайте")
async def user_info(interaction: discord.Interaction, username: str):
    """Получение информации о пользователе (только для админов и саппорта)"""
    await interaction.response.defer(ephemeral=True)  # Приватный ответ
    
    # Проверка роли пользователя
    if not is_admin_or_support(interaction):
        await interaction.followup.send("❌ У вас недостаточно прав для выполнения этой команды.")
        return
    
    db = get_db()
    try:
        # Поиск пользователя по имени
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            await interaction.followup.send(f"❌ Пользователь {username} не найден.")
            return
        
        # Получение активных ключей пользователя
        active_keys = db.query(Key).filter(
            Key.user_id == user.id,
            Key.is_active == True
        ).all()
        
        # Создание эмбеда с информацией о пользователе
        embed = discord.Embed(
            title=f"Информация о пользователе {username}",
            color=discord.Color.blue() if not user.is_banned else discord.Color.red()
        )
        
        embed.add_field(
            name="ID",
            value=str(user.id),
            inline=True
        )
        
        embed.add_field(
            name="Email",
            value=user.email,
            inline=True
        )
        
        embed.add_field(
            name="Создан",
            value=user.created_at.strftime("%d.%m.%Y %H:%M"),
            inline=True
        )
        
        embed.add_field(
            name="Роль",
            value="Администратор" if user.is_admin else "Саппорт" if user.is_support else "Пользователь",
            inline=True
        )
        
        embed.add_field(
            name="Статус",
            value="Заблокирован" if user.is_banned else "Активен",
            inline=True
        )
        
        embed.add_field(
            name="Discord привязка",
            value=f"<@{user.discord_id}>" if user.discord_id else "Нет",
            inline=True
        )
        
        # Добавление информации о ключах
        if active_keys:
            valid_keys = []
            for key in active_keys:
                if not key.is_expired():
                    valid_keys.append(key)
            
            if valid_keys:
                keys_info = []
                for key in valid_keys:
                    formatted_time = format_time_left(key.time_left())
                    keys_info.append(f"{key.key} (осталось: {formatted_time})")
                
                embed.add_field(
                    name=f"Активные ключи ({len(valid_keys)})",
                    value="\n".join(keys_info) if len(keys_info) <= 5 else "\n".join(keys_info[:5]) + f"\n... и ещё {len(keys_info) - 5}",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Активные ключи",
                    value="Нет",
                    inline=False
                )
        else:
            embed.add_field(
                name="Активные ключи",
                value="Нет",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        print(f"Ошибка при получении информации о пользователе: {e}")
        await interaction.followup.send("❌ Произошла ошибка при получении информации о пользователе.")
    finally:
        db.close()

# Запуск бота
def main():
    if not DISCORD_TOKEN:
        print("Ошибка: DISCORD_TOKEN не найден в переменных окружения.")
        return
    
    try:
        bot.run(DISCORD_TOKEN, reconnect=True)
    except discord.errors.HTTPException as e:
        print(f"Ошибка HTTP при запуске бота: {e}")
        if str(e).startswith("429"):
            print("Слишком много запросов (rate limit). Подождите некоторое время.")
    except discord.errors.LoginFailure:
        print("Неверный токен бота. Проверьте DISCORD_TOKEN в .env файле.")
    except aiohttp.client_exceptions.ClientConnectionError:
        print("Ошибка подключения к Discord. Проверьте интернет-соединение.")
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")

if __name__ == "__main__":
    main() 