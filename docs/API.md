# API Документация

## Аутентификация

### Получение токена

```
POST /api/auth/login
```

**Запрос:**
```json
{
    "username": "user",
    "password": "password"
}
```

**Ответ:**
```json
{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_at": "2023-05-01T00:00:00Z"
}
```

### Проверка ключа (для лоадера)

```
POST /api/keys/verify
```

**Запрос:**
```json
{
    "key": "XXXX-XXXX-XXXX-XXXX"
}
```

**Ответ:**
```json
{
    "valid": true,
    "expires_at": "2023-05-01T00:00:00Z",
    "user": {
        "id": 1,
        "username": "user"
    }
}
```

## Ключи

### Получение списка ключей пользователя

```
GET /api/keys
```

**Заголовки:**
```
Authorization: Bearer <token>
```

**Ответ:**
```json
{
    "keys": [
        {
            "id": 1,
            "key": "XXXX-XXXX-XXXX-XXXX",
            "created_at": "2023-04-01T00:00:00Z",
            "expires_at": "2023-05-01T00:00:00Z",
            "is_active": true
        }
    ]
}
```

### Генерация ключа (только для администраторов)

```
POST /api/keys/generate
```

**Заголовки:**
```
Authorization: Bearer <token>
```

**Запрос:**
```json
{
    "duration_hours": 24,
    "user_id": 1,  // Опционально, если не указан, ключ будет свободным
    "custom_key": "XXXX-XXXX-XXXX-XXXX"  // Опционально, если не указан, будет сгенерирован случайный ключ
}
```

**Ответ:**
```json
{
    "key": "XXXX-XXXX-XXXX-XXXX",
    "created_at": "2023-04-01T00:00:00Z",
    "expires_at": "2023-05-01T00:00:00Z"
}
```

### Привязка ключа к аккаунту

```
POST /api/keys/redeem
```

**Заголовки:**
```
Authorization: Bearer <token>
```

**Запрос:**
```json
{
    "key": "XXXX-XXXX-XXXX-XXXX"
}
```

**Ответ:**
```json
{
    "success": true,
    "key": {
        "id": 1,
        "key": "XXXX-XXXX-XXXX-XXXX",
        "created_at": "2023-04-01T00:00:00Z",
        "expires_at": "2023-05-01T00:00:00Z",
        "is_active": true
    }
}
```

## Пользователи

### Регистрация пользователя

```
POST /api/users/register
```

**Запрос:**
```json
{
    "username": "new_user",
    "password": "password",
    "email": "user@example.com",
    "invite_code": "INVITE-CODE"
}
```

**Ответ:**
```json
{
    "id": 2,
    "username": "new_user",
    "created_at": "2023-04-01T00:00:00Z"
}
```

### Генерация кода для привязки Discord аккаунта

```
POST /api/users/discord-code
```

**Заголовки:**
```
Authorization: Bearer <token>
```

**Ответ:**
```json
{
    "code": "XXXXXX",
    "expires_at": "2023-04-01T00:15:00Z"
}
```

### Информация о пользователе

```
GET /api/users/me
```

**Заголовки:**
```
Authorization: Bearer <token>
```

**Ответ:**
```json
{
    "id": 1,
    "username": "user",
    "email": "user@example.com",
    "created_at": "2023-04-01T00:00:00Z",
    "is_admin": false,
    "is_support": false,
    "discord_linked": true,
    "discord_username": "user#1234"
}
```

## Инвайты

### Создание инвайт-кода (только для пользователей)

```
POST /api/invites/generate
```

**Заголовки:**
```
Authorization: Bearer <token>
```

**Ответ:**
```json
{
    "code": "INVITE-CODE",
    "created_at": "2023-04-01T00:00:00Z",
    "expires_at": "2023-05-01T00:00:00Z"
}
```

### Получение списка инвайтов пользователя

```
GET /api/invites
```

**Заголовки:**
```
Authorization: Bearer <token>
```

**Ответ:**
```json
{
    "invites": [
        {
            "id": 1,
            "code": "INVITE-CODE",
            "created_at": "2023-04-01T00:00:00Z",
            "expires_at": "2023-05-01T00:00:00Z",
            "used": false,
            "used_by": null
        }
    ]
}
```

## Discord Bot API

### Проверка кода для привязки Discord аккаунта

```
POST /api/discord/verify-code
```

**Запрос:**
```json
{
    "code": "XXXXXX",
    "discord_id": "123456789012345678",
    "discord_username": "user#1234"
}
```

**Ответ:**
```json
{
    "success": true,
    "user_id": 1
}
```

### Привязка ключа через Discord

```
POST /api/discord/redeem-key
```

**Запрос:**
```json
{
    "key": "XXXX-XXXX-XXXX-XXXX",
    "discord_id": "123456789012345678"
}
```

**Ответ:**
```json
{
    "success": true,
    "expires_at": "2023-05-01T00:00:00Z"
}
```

## Управление пользователями (только для администраторов)

### Изменение роли пользователя

```
POST /api/admin/users/{user_id}/role
```

**Заголовки:**
```
Authorization: Bearer <token>
```

**Запрос:**
```json
{
    "role": "admin"  // Возможные значения: "admin", "support", "user"
}
```

**Ответ:**
```json
{
    "message": "Роль пользователя user1 изменена на admin",
    "id": 1,
    "username": "user1",
    "is_admin": true,
    "is_support": false
}
``` 