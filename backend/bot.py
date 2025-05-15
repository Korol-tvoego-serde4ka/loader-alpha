import discord
from discord.ext import commands
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from config import (
    DISCORD_TOKEN,
    DISCORD_GUILD_ID,
    ADMIN_ROLE_ID,
    SUPPORT_ROLE_ID,
    SUBS_ROLE_ID,
    API_V1_PREFIX,
    ADMIN_LOG_CHANNEL_ID
)

# Настройки бота
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

# API URL
API_URL = "http://localhost:8000"  # Измените на ваш URL

# Проверка ролей
def is_admin():
    async def predicate(ctx):
        return any(role.id == ADMIN_ROLE_ID for role in ctx.author.roles)
    return commands.check(predicate)

def is_support():
    async def predicate(ctx):
        return any(role.id in [ADMIN_ROLE_ID, SUPPORT_ROLE_ID] for role in ctx.author.roles)
    return commands.check(predicate)

def is_subs():
    async def predicate(ctx):
        return any(role.id in [ADMIN_ROLE_ID, SUPPORT_ROLE_ID, SUBS_ROLE_ID] for role in ctx.author.roles)
    return commands.check(predicate)

# Команды для администраторов
@bot.command(name='genkey')
@is_admin()
async def generate_key(ctx, is_test: bool = False):
    """Генерация нового ключа"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}{API_V1_PREFIX}/keys/",
            json={"is_test": is_test}
        ) as response:
            if response.status == 200:
                key_data = await response.json()
                await ctx.send(f"Сгенерирован новый ключ: `{key_data['key_value']}`")
            else:
                await ctx.send("Ошибка при генерации ключа")

@bot.command(name='genkey')
@is_support()
async def generate_key_support(ctx, is_test: bool = False):
    """Генерация нового ключа (для поддержки)"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}{API_V1_PREFIX}/keys/",
            json={"is_test": is_test}
        ) as response:
            if response.status == 200:
                key_data = await response.json()
                # Отправка ключа в личные сообщения
                await ctx.author.send(f"Сгенерирован новый ключ: `{key_data['key_value']}`")
                await ctx.send("Ключ отправлен в личные сообщения")
                
                # Логирование действия
                admin_channel = ctx.guild.get_channel(ADMIN_LOG_CHANNEL_ID)
                if admin_channel:
                    embed = discord.Embed(
                        title="Лог действия поддержки",
                        description="Генерация ключа",
                        color=discord.Color.blue()
                    )
                    embed.add_field(name="Модератор", value=ctx.author.mention)
                    embed.add_field(name="Тестовый ключ", value=str(is_test))
                    await admin_channel.send(embed=embed)
            else:
                await ctx.send("Ошибка при генерации ключа")

@bot.command(name='ban')
@is_support()
async def ban_user(ctx, member: discord.Member, reason: str = None):
    """Бан пользователя"""
    if any(role.id == ADMIN_ROLE_ID for role in member.roles):
        await ctx.send("Нельзя забанить администратора")
        return
    
    await member.ban(reason=reason)
    await ctx.send(f"Пользователь {member.mention} забанен")
    
    # Логирование действия
    admin_channel = ctx.guild.get_channel(ADMIN_LOG_CHANNEL_ID)
    if admin_channel:
        embed = discord.Embed(
            title="Лог действия поддержки",
            description="Бан пользователя",
            color=discord.Color.red()
        )
        embed.add_field(name="Модератор", value=ctx.author.mention)
        embed.add_field(name="Пользователь", value=member.mention)
        if reason:
            embed.add_field(name="Причина", value=reason)
        await admin_channel.send(embed=embed)

@bot.command(name='unban')
@is_support()
async def unban_user(ctx, user_id: int):
    """Разбан пользователя"""
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"Пользователь {user.mention} разбанен")
        
        # Логирование действия
        admin_channel = ctx.guild.get_channel(ADMIN_LOG_CHANNEL_ID)
        if admin_channel:
            embed = discord.Embed(
                title="Лог действия поддержки",
                description="Разбан пользователя",
                color=discord.Color.green()
            )
            embed.add_field(name="Модератор", value=ctx.author.mention)
            embed.add_field(name="Пользователь", value=user.mention)
            await admin_channel.send(embed=embed)
    except discord.NotFound:
        await ctx.send("Пользователь не найден")
    except discord.HTTPException:
        await ctx.send("Ошибка при разбане пользователя")

@bot.command(name='help')
async def help_command(ctx):
    """Показать список доступных команд"""
    embed = discord.Embed(
        title="Список команд",
        description="Доступные команды бота",
        color=discord.Color.blue()
    )
    
    # Команды для администраторов
    admin_commands = """
    `/genkey [is_test]` - Генерация нового ключа
    `/ban [@user] [причина]` - Бан пользователя
    `/unban [user_id]` - Разбан пользователя
    """
    embed.add_field(name="Команды администратора", value=admin_commands, inline=False)
    
    # Команды для поддержки
    support_commands = """
    `/genkey [is_test]` - Генерация ключа (с логированием)
    `/ban [@user] [причина]` - Бан пользователя (с логированием)
    `/unban [user_id]` - Разбан пользователя (с логированием)
    `/userinfo [@user]` - Информация о пользователе
    """
    embed.add_field(name="Команды поддержки", value=support_commands, inline=False)
    
    # Команды для пользователей
    user_commands = """
    `/code` - Получение кода привязки
    `/redeem [ключ]` - Активация ключа
    `/stats` - Статистика пользователя
    """
    embed.add_field(name="Команды пользователя", value=user_commands, inline=False)
    
    await ctx.send(embed=embed)

# Команды для пользователей
@bot.command(name='code')
@is_subs()
async def get_link_code(ctx):
    """Получение кода для привязки Discord"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}{API_V1_PREFIX}/discord/link/"
        ) as response:
            if response.status == 200:
                data = await response.json()
                await ctx.author.send(f"Ваш код для привязки: `{data['code']}`")
                await ctx.send("Код отправлен в личные сообщения")
            else:
                await ctx.send("Ошибка при получении кода")

@bot.command(name='redeem')
@is_subs()
async def redeem_key(ctx, key: str):
    """Активация ключа"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}{API_V1_PREFIX}/keys/redeem/",
            json={"key_value": key}
        ) as response:
            if response.status == 200:
                key_data = await response.json()
                await ctx.send(f"Ключ успешно активирован! Действует до: {key_data['expires_at']}")
            else:
                error_data = await response.json()
                await ctx.send(f"Ошибка: {error_data['detail']}")

@bot.command(name='stats')
@is_subs()
async def get_stats(ctx):
    """Получение статистики пользователя"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API_URL}{API_V1_PREFIX}/stats/"
        ) as response:
            if response.status == 200:
                stats = await response.json()
                embed = discord.Embed(title="Статистика пользователя", color=discord.Color.blue())
                embed.add_field(name="Всего ключей", value=stats['total_keys'])
                embed.add_field(name="Активных ключей", value=stats['active_keys'])
                embed.add_field(name="Истекших ключей", value=stats['expired_keys'])
                embed.add_field(name="Приглашенных пользователей", value=stats['invited_users'])
                if stats['last_login']:
                    embed.add_field(name="Последний вход", value=stats['last_login'])
                await ctx.send(embed=embed)
            else:
                await ctx.send("Ошибка при получении статистики")

# Команды для поддержки
@bot.command(name='userinfo')
@is_support()
async def get_user_info(ctx, member: discord.Member):
    """Получение информации о пользователе"""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API_URL}{API_V1_PREFIX}/users/{member.id}"
        ) as response:
            if response.status == 200:
                user_data = await response.json()
                embed = discord.Embed(title=f"Информация о пользователе {member.name}", color=discord.Color.green())
                embed.add_field(name="ID", value=user_data['id'])
                embed.add_field(name="Email", value=user_data['email'])
                embed.add_field(name="Дата регистрации", value=user_data['created_at'])
                if user_data['last_login']:
                    embed.add_field(name="Последний вход", value=user_data['last_login'])
                await ctx.send(embed=embed)
            else:
                await ctx.send("Ошибка при получении информации о пользователе")

# Обработка событий
@bot.event
async def on_ready():
    print(f'Бот {bot.user} готов к работе!')
    await bot.change_presence(activity=discord.Game(name="/help для списка команд"))

@bot.event
async def on_member_join(member):
    """Обработка присоединения нового участника"""
    channel = member.guild.system_channel
    if channel:
        await channel.send(f"Добро пожаловать, {member.mention}! Используйте команду /code для получения кода привязки.")

# Запуск бота
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN) 