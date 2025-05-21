"use strict";

// Глобальные переменные
let token = localStorage.getItem('token');
let userData = null;

// Константы API
const API_URL = '/api';

// Утилиты для работы с API
const api = {
    // Отправка запроса
    request: async (endpoint, method = 'GET', data = null, includeToken = true) => {
        const headers = {
            'Content-Type': 'application/json'
        };
        
        if (includeToken && token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        const options = {
            method,
            headers
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        try {
            const response = await fetch(`${API_URL}${endpoint}`, options);
            
            // Проверяем, что ответ - это JSON
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                const text = await response.text();
                throw new Error(`Сервер вернул неверный формат данных: ${text.substring(0, 100)}...`);
            }
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.message || 'Ошибка запроса');
            }
            
            return result;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },
    
    // Авторизация
    login: (username, password) => {
        return api.request('/auth/login', 'POST', { username, password }, false);
    },
    
    // Регистрация
    register: (username, email, password, invite_code) => {
        return api.request('/users/register', 'POST', { username, email, password, invite_code }, false);
    },
    
    // Получение информации о пользователе
    getUserInfo: () => {
        return api.request('/users/me');
    },
    
    // Получение ключей пользователя
    getKeys: () => {
        return api.request('/keys');
    },
    
    // Активация ключа
    redeemKey: (key) => {
        return api.request('/keys/redeem', 'POST', { key });
    },
    
    // Получение инвайтов пользователя
    getInvites: () => {
        return api.request('/invites');
    },
    
    // Создание инвайта
    generateInvite: () => {
        return api.request('/invites/generate', 'POST');
    },
    
    // Получение лимитов инвайтов
    getInviteLimits: () => {
        return api.request('/invites/limits');
    },
    
    // Удаление инвайта (для админов)
    deleteInvite: (inviteId) => {
        return api.request(`/admin/invites/${inviteId}/delete`, 'POST');
    },
    
    // Удаление нескольких инвайтов (для админов)
    deleteMultipleInvites: (inviteIds) => {
        return api.request('/admin/invites/delete', 'POST', { invite_ids: inviteIds });
    },
    
    // Получение всех ключей (для админов)
    getAllKeys: () => {
        return api.request('/admin/keys');
    },
    
    // Отзыв ключа (для админов)
    revokeKey: (keyId) => {
        return api.request(`/admin/keys/${keyId}/revoke`, 'POST');
    },
    
    // Восстановление ключа (для админов)
    restoreKey: (keyId) => {
        return api.request(`/admin/keys/${keyId}/restore`, 'POST');
    },
    
    // Массовые операции с ключами (для админов)
    bulkKeyAction: (keyIds, action) => {
        return api.request('/admin/keys/bulk-action', 'POST', {
            key_ids: keyIds,
            action: action
        });
    },
    
    // Установка лимитов инвайтов (для админов)
    setInviteLimits: (adminLimit, supportLimit, userLimit) => {
        return api.request('/admin/invites/limits', 'POST', {
            admin_limit: adminLimit,
            support_limit: supportLimit,
            user_limit: userLimit
        });
    },
    
    // Генерация кода для привязки Discord
    generateDiscordCode: () => {
        return api.request('/users/discord-code', 'POST');
    },
    
    // Получение списка пользователей (для админов)
    getUsers: () => {
        return api.request('/admin/users');
    },
    
    // Получение данных активности пользователей (для админов)
    getUsersActivity: () => {
        return api.request('/admin/users/activity');
    },
    
    // Бан пользователя
    banUser: (userId) => {
        return api.request(`/admin/users/${userId}/ban`, 'POST');
    },
    
    // Разбан пользователя
    unbanUser: (userId) => {
        return api.request(`/admin/users/${userId}/unban`, 'POST');
    },
    
    // Генерация ключа (для админов)
    generateKey: (duration_hours, user_id = null, custom_key = null) => {
        const data = { duration_hours };
        if (user_id) {
            data.user_id = user_id;
        }
        if (custom_key) {
            data.custom_key = custom_key;
        }
        return api.request('/keys/generate', 'POST', data);
    },
    
    // Изменение роли пользователя (для админов)
    setUserRole: (userId, role) => {
        return api.request(`/admin/users/${userId}/role`, 'POST', { role });
    }
};

// Утилиты для форматирования
const utils = {
    // Форматирование даты
    formatDate: (isoString) => {
        const date = new Date(isoString);
        return date.toLocaleString('ru-RU');
    },
    
    // Форматирование оставшегося времени
    formatTimeLeft: (seconds) => {
        if (seconds <= 0) {
            return 'истек';
        }
        
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        let result = '';
        if (days > 0) {
            result += `${days} дн. `;
        }
        if (hours > 0) {
            result += `${hours} ч. `;
        }
        if (minutes > 0) {
            result += `${minutes} мин.`;
        }
        
        return result.trim() || 'менее минуты';
    },
    
    // Определение роли пользователя
    getUserRole: (user) => {
        if (user.is_admin) {
            return 'Администратор';
        } else if (user.is_support) {
            return 'Саппорт';
        } else {
            return 'Пользователь';
        }
    },
    
    // Форматирование IP-адреса
    formatIpAddress: (ip) => {
        if (!ip) return 'Неизвестно';
        
        // Проверка на локальные IP-адреса
        if (ip === '127.0.0.1' || ip === 'localhost' || ip === '::1') {
            return `${ip} (Локальный адрес)`;
        } else if (ip.startsWith('192.168.') || ip.startsWith('10.') || 
                  (ip.startsWith('172.') && parseInt(ip.split('.')[1]) >= 16 && parseInt(ip.split('.')[1]) <= 31)) {
            return `${ip} (Внутренняя сеть)`;
        } else {
            return ip; // Внешний IP-адрес
        }
    }
};

// Навигация по страницам
const navigation = {
    // Текущая страница
    currentPage: null,
    
    // Переход на страницу
    navigateTo: (page) => {
        // Скрытие всех страниц
        document.querySelectorAll('.page-content').forEach(content => {
            content.style.display = 'none';
        });
        
        // Отображение нужной страницы
        const pageElement = document.getElementById(`${page}-page`);
        if (pageElement) {
            pageElement.style.display = 'block';
            navigation.currentPage = page;
            
            // Обновление состояния страницы
            switch (page) {
                case 'keys':
                    loadKeys();
                    break;
                case 'invites':
                    loadInvites();
                    break;
                case 'discord':
                    loadDiscordStatus();
                    break;
                case 'admin':
                    loadAdminData();
                    break;
            }
            
            // Обновление URL
            if (page === 'home') {
                history.pushState(null, '', '#');
            } else {
                history.pushState(null, '', `#${page}`);
            }
        } else {
            console.error(`Страница "${page}" не найдена`);
        }
    }
};

// Аутентификация
const auth = {
    // Проверка авторизации
    checkAuth: async () => {
        if (!token) {
            auth.logout();
            return false;
        }
        
        try {
            userData = await api.getUserInfo();
            
            // Отображение имени пользователя
            document.getElementById('username-display').textContent = userData.username;
            
            // Отображение элементов для авторизованных пользователей
            document.getElementById('login-buttons').style.display = 'none';
            document.getElementById('user-info').style.display = 'flex';
            document.getElementById('home-buttons').style.display = 'none';
            document.getElementById('download-button').style.display = 'block';
            
            // Отображение админ-панели для админов и саппорта
            if (userData.is_admin || userData.is_support) {
                document.getElementById('nav-admin').style.display = 'block';
                document.querySelectorAll('.admin-command').forEach(el => {
                    el.style.display = 'table-row';
                });
                document.getElementById('admin-commands').style.display = 'table-row';
            } else {
                document.getElementById('nav-admin').style.display = 'none';
                document.querySelectorAll('.admin-command').forEach(el => {
                    el.style.display = 'none';
                });
                document.getElementById('admin-commands').style.display = 'none';
            }
            
            return true;
        } catch (error) {
            auth.logout();
            return false;
        }
    },
    
    // Выход из системы
    logout: () => {
        token = null;
        userData = null;
        localStorage.removeItem('token');
        
        // Скрытие элементов для авторизованных пользователей
        document.getElementById('login-buttons').style.display = 'flex';
        document.getElementById('user-info').style.display = 'none';
        document.getElementById('home-buttons').style.display = 'block';
        document.getElementById('download-button').style.display = 'none';
        document.getElementById('nav-admin').style.display = 'none';
        
        // Переход на главную страницу
        navigation.navigateTo('home');
    }
};

// Загрузка данных

// Загрузка ключей пользователя
async function loadKeys() {
    document.getElementById('keys-loading').style.display = 'block';
    document.getElementById('no-keys').style.display = 'none';
    document.getElementById('keys-list').style.display = 'none';
    
    try {
        const keysData = await api.getKeys();
        const keys = keysData.keys.filter(key => key.is_active);
        
        if (keys.length === 0) {
            document.getElementById('no-keys').style.display = 'block';
        } else {
            const tableBody = document.getElementById('keys-table-body');
            tableBody.innerHTML = '';
            
            keys.forEach(key => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${key.key}</td>
                    <td>${utils.formatDate(key.created_at)}</td>
                    <td>${utils.formatDate(key.expires_at)}</td>
                    <td>${utils.formatTimeLeft(key.time_left)}</td>
                `;
                tableBody.appendChild(row);
            });
            
            document.getElementById('keys-list').style.display = 'block';
        }
    } catch (error) {
        console.error('Ошибка при загрузке ключей:', error);
    } finally {
        document.getElementById('keys-loading').style.display = 'none';
    }
}

// Загрузка инвайтов пользователя
async function loadInvites() {
    document.getElementById('invites-loading').style.display = 'block';
    document.getElementById('no-invites').style.display = 'none';
    document.getElementById('invites-list').style.display = 'none';
    document.getElementById('invite-limits').style.display = 'none';
    document.getElementById('admin-invite-limits').style.display = 'none';
    document.getElementById('delete-selected-invites-button').style.display = 'none';
    
    try {
        // Загрузка инвайтов и лимитов одновременно
        const [invitesData, limitsData] = await Promise.all([
            api.getInvites(),
            api.getInviteLimits()
        ]);
        
        const invites = invitesData.invites;
        
        // Отображение информации о лимитах
        document.getElementById('monthly-limit').textContent = limitsData.monthly_limit;
        document.getElementById('used-invites').textContent = limitsData.used_invites;
        document.getElementById('remaining-invites').textContent = limitsData.remaining_invites;
        document.getElementById('invite-limits').style.display = 'block';
        
        // Отображение панели управления лимитами для админов
        if (userData && userData.is_admin) {
            document.getElementById('admin-limit-value').value = limitsData.global_limits.admin;
            document.getElementById('support-limit-value').value = limitsData.global_limits.support;
            document.getElementById('user-limit-value').value = limitsData.global_limits.user;
            document.getElementById('admin-invite-limits').style.display = 'block';
            document.getElementById('invites-actions-header').style.display = 'table-cell';
            document.getElementById('delete-selected-invites-button').style.display = 'inline-block';
        } else {
            document.getElementById('invites-actions-header').style.display = 'none';
        }
        
        // Проверка, есть ли инвайты для отображения
        if (invites.length === 0) {
            document.getElementById('no-invites').style.display = 'block';
        } else {
            const tableBody = document.getElementById('invites-table-body');
            tableBody.innerHTML = '';
            
            invites.forEach(invite => {
                const row = document.createElement('tr');
                const status = invite.used ? 'Использован' : 'Активен';
                
                // Добавляем чекбокс для выбора
                const checkboxCell = document.createElement('td');
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.className = 'invite-checkbox';
                checkbox.dataset.inviteId = invite.id;
                checkbox.disabled = invite.used; // Нельзя выбрать использованные инвайты
                checkboxCell.appendChild(checkbox);
                row.appendChild(checkboxCell);
                
                // Добавляем информацию об инвайте
                row.innerHTML += `
                    <td>${invite.code}</td>
                    <td>${utils.formatDate(invite.created_at)}</td>
                    <td>${utils.formatDate(invite.expires_at)}</td>
                    <td>${status}</td>
                    <td>${invite.created_by.username}</td>
                    <td>${invite.used_by ? invite.used_by : 'Не использован'}</td>
                `;
                
                // Добавляем кнопку удаления для админов
                if (userData && userData.is_admin) {
                    const actionCell = document.createElement('td');
                    const deleteButton = document.createElement('button');
                    deleteButton.className = 'btn btn-danger btn-sm';
                    deleteButton.textContent = 'Удалить';
                    deleteButton.addEventListener('click', async () => {
                        if (confirm('Вы уверены, что хотите удалить этот инвайт?')) {
                            try {
                                await api.deleteInvite(invite.id);
                                loadInvites(); // Перезагрузка списка после удаления
                            } catch (error) {
                                alert(`Ошибка при удалении инвайта: ${error.message}`);
                            }
                        }
                    });
                    actionCell.appendChild(deleteButton);
                    row.appendChild(actionCell);
                }
                
                tableBody.appendChild(row);
            });
            
            document.getElementById('invites-list').style.display = 'block';
            
            // Настройка обработчика для кнопки "Выбрать все"
            const selectAllCheckbox = document.getElementById('select-all-invites');
            selectAllCheckbox.checked = false;
            selectAllCheckbox.addEventListener('change', () => {
                document.querySelectorAll('.invite-checkbox:not([disabled])').forEach(checkbox => {
                    checkbox.checked = selectAllCheckbox.checked;
                });
            });
            
            // Настройка обработчика для кнопки "Удалить выбранные"
            document.getElementById('delete-selected-invites-button').addEventListener('click', async () => {
                const selectedInvites = Array.from(document.querySelectorAll('.invite-checkbox:checked'))
                    .map(checkbox => parseInt(checkbox.dataset.inviteId));
                
                if (selectedInvites.length === 0) {
                    alert('Выберите инвайты для удаления');
                    return;
                }
                
                if (confirm(`Вы уверены, что хотите удалить ${selectedInvites.length} инвайтов?`)) {
                    try {
                        const button = document.getElementById('delete-selected-invites-button');
                        button.disabled = true;
                        button.textContent = 'Удаление...';
                        
                        await api.deleteMultipleInvites(selectedInvites);
                        loadInvites(); // Перезагрузка списка после удаления
                    } catch (error) {
                        alert(`Ошибка при удалении инвайтов: ${error.message}`);
                        const button = document.getElementById('delete-selected-invites-button');
                        button.disabled = false;
                        button.textContent = 'Удалить выбранные';
                    }
                }
            });
        }
    } catch (error) {
        console.error('Ошибка при загрузке инвайтов:', error);
    } finally {
        document.getElementById('invites-loading').style.display = 'none';
    }
}

// Загрузка статуса Discord
async function loadDiscordStatus() {
    document.getElementById('discord-status-loading').style.display = 'block';
    document.getElementById('discord-not-linked').style.display = 'none';
    document.getElementById('discord-linked').style.display = 'none';
    document.getElementById('discord-code-card').style.display = 'none';
    
    try {
        const userData = await api.getUserInfo();
        
        if (userData.discord_linked) {
            document.getElementById('discord-username').textContent = userData.discord_username;
            document.getElementById('discord-linked').style.display = 'block';
        } else {
            document.getElementById('discord-not-linked').style.display = 'block';
        }
    } catch (error) {
        console.error('Ошибка при загрузке статуса Discord:', error);
    } finally {
        document.getElementById('discord-status-loading').style.display = 'none';
    }
}

// Загрузка админ-данных
async function loadAdminData() {
    // Загрузка списка пользователей
    document.getElementById('users-loading').style.display = 'block';
    document.getElementById('users-list').style.display = 'none';
    
    try {
        // Получаем данные активности пользователей
        const usersData = await api.getUsersActivity();
        const users = usersData.users;
        
        const tableBody = document.getElementById('users-table-body');
        tableBody.innerHTML = '';
        
        users.forEach(user => {
            const row = document.createElement('tr');
            const role = utils.getUserRole(user);
            const status = user.is_banned ? 'Заблокирован' : 'Активен';
            const discordStatus = user.discord_linked ? user.discord_username : 'Не привязан';
            
            row.innerHTML = `
                <td>${user.id}</td>
                <td>${user.username}</td>
                <td>${user.email}</td>
                <td>${role}</td>
                <td>${discordStatus}</td>
                <td>${status}</td>
                <td>${user.last_login ? new Date(user.last_login).toLocaleString() : 'Никогда'}</td>
                <td>${utils.formatIpAddress(user.last_ip)}</td>
                <td>
                    <div class="action-buttons">
                        ${user.is_banned ? 
                            `<button class="btn btn-success btn-sm unban-user" data-id="${user.id}">Разбл</button>` :
                            `<button class="btn btn-danger btn-sm ban-user" data-id="${user.id}">Блок</button>`
                        }
                        <div class="user-role-buttons d-inline-flex" data-user-id="${user.id}"></div>
                    </div>
                </td>
            `;
            
            tableBody.appendChild(row);
        });
        
        // Обработчики событий для кнопок бана/разбана
        document.querySelectorAll('.ban-user').forEach(button => {
            button.addEventListener('click', async () => {
                const userId = button.getAttribute('data-id');
                try {
                    await api.banUser(userId);
                    loadAdminData();
                } catch (error) {
                    alert(`Ошибка блокировки пользователя: ${error.message}`);
                }
            });
        });
        
        document.querySelectorAll('.unban-user').forEach(button => {
            button.addEventListener('click', async () => {
                const userId = button.getAttribute('data-id');
                try {
                    await api.unbanUser(userId);
                    loadAdminData();
                } catch (error) {
                    alert(`Ошибка разблокировки пользователя: ${error.message}`);
                }
            });
        });
        
        // Добавляем кнопки управления ролями
        addRoleManagementButtons();
        
        document.getElementById('users-list').style.display = 'block';
        
        // Обработчики переключения вкладок
        document.querySelector('#all-keys-tab').addEventListener('click', loadAllKeys);
        
    } catch (error) {
        console.error('Ошибка при загрузке списка пользователей:', error);
    } finally {
        document.getElementById('users-loading').style.display = 'none';
    }
}

// Добавляем функции для управления ролями пользователей
function updateUsersList() {
    loadAdminData();
}

function addRoleManagementButtons() {
    document.querySelectorAll('.user-role-buttons').forEach(container => {
        const userId = container.getAttribute('data-user-id');
        
        // Очищаем контейнер сначала
        container.innerHTML = '';
        
        // Добавляем кнопки управления ролями
        const makeAdminBtn = document.createElement('button');
        makeAdminBtn.className = 'btn btn-primary btn-sm ml-1';
        makeAdminBtn.style.padding = '0.2rem 0.4rem';
        makeAdminBtn.style.fontSize = '0.75rem';
        makeAdminBtn.textContent = 'A';
        makeAdminBtn.title = 'Сделать администратором';
        makeAdminBtn.addEventListener('click', async () => {
            try {
                await api.setUserRole(userId, 'admin');
                updateUsersList();
            } catch (error) {
                alert(`Ошибка при назначении администратора: ${error.message}`);
            }
        });
        
        const makeSupportBtn = document.createElement('button');
        makeSupportBtn.className = 'btn btn-info btn-sm ml-1';
        makeSupportBtn.style.padding = '0.2rem 0.4rem';
        makeSupportBtn.style.fontSize = '0.75rem';
        makeSupportBtn.textContent = 'С';
        makeSupportBtn.title = 'Сделать саппортом';
        makeSupportBtn.addEventListener('click', async () => {
            try {
                await api.setUserRole(userId, 'support');
                updateUsersList();
            } catch (error) {
                alert(`Ошибка при назначении саппорта: ${error.message}`);
            }
        });
        
        const makeUserBtn = document.createElement('button');
        makeUserBtn.className = 'btn btn-secondary btn-sm ml-1';
        makeUserBtn.style.padding = '0.2rem 0.4rem';
        makeUserBtn.style.fontSize = '0.75rem';
        makeUserBtn.textContent = 'Ю';
        makeUserBtn.title = 'Сделать обычным пользователем';
        makeUserBtn.addEventListener('click', async () => {
            try {
                await api.setUserRole(userId, 'user');
                updateUsersList();
            } catch (error) {
                alert(`Ошибка при сбросе роли: ${error.message}`);
            }
        });
        
        container.appendChild(makeAdminBtn);
        container.appendChild(makeSupportBtn);
        container.appendChild(makeUserBtn);
    });
}

// Загрузка всех ключей (для админов)
async function loadAllKeys() {
    document.getElementById('all-keys-loading').style.display = 'block';
    document.getElementById('all-keys-list').style.display = 'none';
    
    try {
        const keysData = await api.getAllKeys();
        const keys = keysData.keys;
        
        const tableBody = document.getElementById('all-keys-table-body');
        tableBody.innerHTML = '';
        
        keys.forEach(key => {
            const row = document.createElement('tr');
            const isActive = key.is_active ? 'Активен' : 'Отозван';
            const status = key.is_active ? (key.time_left > 0 ? 'Активен' : 'Истёк') : 'Отозван';
            
            row.innerHTML = `
                <td><input type="checkbox" class="key-checkbox" data-id="${key.id}"></td>
                <td>${key.id}</td>
                <td>${key.key}</td>
                <td>${utils.formatDate(key.created_at)}</td>
                <td>${utils.formatDate(key.expires_at)}</td>
                <td>${utils.formatTimeLeft(key.time_left)}</td>
                <td>${key.user ? key.user.username : 'Не привязан'}</td>
                <td>${status}</td>
                <td>
                    ${key.is_active ? 
                        `<button class="btn btn-danger btn-sm revoke-key-btn" data-id="${key.id}">Отозвать</button>` : 
                        `<button class="btn btn-success btn-sm restore-key-btn" data-id="${key.id}">Восстановить</button>`
                    }
                </td>
            `;
            
            tableBody.appendChild(row);
        });
        
        // Добавляем обработчики для кнопок отзыва ключей
        document.querySelectorAll('.revoke-key-btn').forEach(button => {
            button.addEventListener('click', async () => {
                const keyId = button.getAttribute('data-id');
                if (confirm('Вы уверены, что хотите отозвать этот ключ?')) {
                    try {
                        button.disabled = true;
                        button.textContent = 'Отзыв...';
                        
                        await api.revokeKey(keyId);
                        loadAllKeys(); // Перезагрузка списка после отзыва
                    } catch (error) {
                        alert(`Ошибка при отзыве ключа: ${error.message}`);
                        button.disabled = false;
                        button.textContent = 'Отозвать';
                    }
                }
            });
        });
        
        // Добавляем обработчики для кнопок восстановления ключей
        document.querySelectorAll('.restore-key-btn').forEach(button => {
            button.addEventListener('click', async () => {
                const keyId = button.getAttribute('data-id');
                if (confirm('Вы уверены, что хотите восстановить этот ключ?')) {
                    try {
                        button.disabled = true;
                        button.textContent = 'Восстановление...';
                        
                        await api.restoreKey(keyId);
                        loadAllKeys(); // Перезагрузка списка после восстановления
                    } catch (error) {
                        alert(`Ошибка при восстановлении ключа: ${error.message}`);
                        button.disabled = false;
                        button.textContent = 'Восстановить';
                    }
                }
            });
        });
        
        // Обработчик для выбора всех ключей
        const selectAllCheckbox = document.getElementById('select-all-keys');
        selectAllCheckbox.addEventListener('change', () => {
            const isChecked = selectAllCheckbox.checked;
            document.querySelectorAll('.key-checkbox').forEach(checkbox => {
                checkbox.checked = isChecked;
            });
        });
        
        // Обработчики для кнопок массовых операций
        document.getElementById('revoke-selected-keys-button').addEventListener('click', async () => {
            const selectedKeyIds = getSelectedKeyIds();
            if (selectedKeyIds.length === 0) {
                alert('Выберите ключи для отзыва');
                return;
            }
            
            if (confirm(`Вы уверены, что хотите отозвать ${selectedKeyIds.length} ключ(ей)?`)) {
                try {
                    await api.bulkKeyAction(selectedKeyIds, 'revoke');
                    loadAllKeys();
                } catch (error) {
                    alert(`Ошибка при массовом отзыве ключей: ${error.message}`);
                }
            }
        });
        
        document.getElementById('restore-selected-keys-button').addEventListener('click', async () => {
            const selectedKeyIds = getSelectedKeyIds();
            if (selectedKeyIds.length === 0) {
                alert('Выберите ключи для восстановления');
                return;
            }
            
            if (confirm(`Вы уверены, что хотите восстановить ${selectedKeyIds.length} ключ(ей)?`)) {
                try {
                    await api.bulkKeyAction(selectedKeyIds, 'restore');
                    loadAllKeys();
                } catch (error) {
                    alert(`Ошибка при массовом восстановлении ключей: ${error.message}`);
                }
            }
        });
        
        document.getElementById('delete-selected-keys-button').addEventListener('click', async () => {
            const selectedKeyIds = getSelectedKeyIds();
            if (selectedKeyIds.length === 0) {
                alert('Выберите ключи для удаления');
                return;
            }
            
            if (confirm(`Вы уверены, что хотите удалить ${selectedKeyIds.length} ключ(ей)? Это действие необратимо!`)) {
                try {
                    await api.bulkKeyAction(selectedKeyIds, 'delete');
                    loadAllKeys();
                } catch (error) {
                    alert(`Ошибка при массовом удалении ключей: ${error.message}`);
                }
            }
        });
        
        document.getElementById('all-keys-list').style.display = 'block';
    } catch (error) {
        console.error('Ошибка при загрузке ключей:', error);
    } finally {
        document.getElementById('all-keys-loading').style.display = 'none';
    }
}

// Вспомогательная функция для получения ID выбранных ключей
function getSelectedKeyIds() {
    const selectedCheckboxes = document.querySelectorAll('.key-checkbox:checked');
    return Array.from(selectedCheckboxes).map(checkbox => parseInt(checkbox.getAttribute('data-id')));
}

// Инициализация приложения
async function initApp() {
    // Проверка авторизации
    const isAuthenticated = await auth.checkAuth();
    
    // Определение стартовой страницы
    const hash = window.location.hash.substring(1);
    if (hash) {
        if (hash === 'login' || hash === 'register') {
            if (isAuthenticated) {
                navigation.navigateTo('home');
            } else {
                navigation.navigateTo(hash);
            }
        } else if (['keys', 'invites', 'discord', 'admin'].includes(hash)) {
            if (isAuthenticated) {
                navigation.navigateTo(hash);
            } else {
                navigation.navigateTo('login');
            }
        } else {
            navigation.navigateTo('home');
        }
    } else {
        navigation.navigateTo('home');
    }
    
    // Обработчики событий
    
    // Обработка навигации
    document.querySelectorAll('.navbar-nav a').forEach(link => {
        link.addEventListener('click', (e) => {
            if (link.getAttribute('href').startsWith('#')) {
                e.preventDefault();
                const page = link.getAttribute('href').substring(1) || 'home';
                navigation.navigateTo(page);
            }
        });
    });
    
    // Обработка хэша URL
    window.addEventListener('hashchange', () => {
        const hash = window.location.hash.substring(1) || 'home';
        navigation.navigateTo(hash);
    });
    
    // Выход из системы
    document.getElementById('logout-button').addEventListener('click', (e) => {
        e.preventDefault();
        auth.logout();
    });
    
    // Форма входа
    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        
        document.getElementById('login-error').style.display = 'none';
        
        try {
            const result = await api.login(username, password);
            token = result.token;
            localStorage.setItem('token', token);
            
            await auth.checkAuth();
            navigation.navigateTo('home');
        } catch (error) {
            document.getElementById('login-error').textContent = error.message;
            document.getElementById('login-error').style.display = 'block';
        }
    });
    
    // Форма регистрации
    document.getElementById('register-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const username = document.getElementById('register-username').value;
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;
        const invite_code = document.getElementById('register-invite').value;
        
        document.getElementById('register-error').style.display = 'none';
        
        try {
            await api.register(username, email, password, invite_code);
            
            // Автоматический вход после регистрации
            const loginResult = await api.login(username, password);
            token = loginResult.token;
            localStorage.setItem('token', token);
            
            await auth.checkAuth();
            navigation.navigateTo('keys');
        } catch (error) {
            document.getElementById('register-error').textContent = error.message;
            document.getElementById('register-error').style.display = 'block';
        }
    });
    
    // Форма активации ключа
    document.getElementById('redeem-key-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const key = document.getElementById('redeem-key').value;
        
        document.getElementById('redeem-error').style.display = 'none';
        document.getElementById('redeem-success').style.display = 'none';
        
        try {
            await api.redeemKey(key);
            
            document.getElementById('redeem-success').style.display = 'block';
            document.getElementById('redeem-key').value = '';
            
            // Обновление списка ключей
            loadKeys();
        } catch (error) {
            document.getElementById('redeem-error').textContent = error.message;
            document.getElementById('redeem-error').style.display = 'block';
        }
    });
    
    // Кнопка создания приглашения
    document.getElementById('generate-invite-button').addEventListener('click', async () => {
        const button = document.getElementById('generate-invite-button');
        button.disabled = true;
        button.textContent = 'Создание...';
        
        try {
            await api.generateInvite();
            loadInvites();
        } catch (error) {
            alert(`Ошибка создания приглашения: ${error.message}`);
        } finally {
            button.disabled = false;
            button.textContent = 'Создать приглашение';
        }
    });
    
    // Форма установки лимитов приглашений
    document.getElementById('set-invite-limits-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const adminLimit = parseInt(document.getElementById('admin-limit-value').value);
        const supportLimit = parseInt(document.getElementById('support-limit-value').value);
        const userLimit = parseInt(document.getElementById('user-limit-value').value);
        
        document.getElementById('set-limits-error').style.display = 'none';
        document.getElementById('set-limits-success').style.display = 'none';
        
        try {
            await api.setInviteLimits(adminLimit, supportLimit, userLimit);
            document.getElementById('set-limits-success').style.display = 'block';
            
            // Перезагрузка данных
            setTimeout(() => {
                loadInvites();
            }, 2000);
        } catch (error) {
            document.getElementById('set-limits-error').textContent = error.message;
            document.getElementById('set-limits-error').style.display = 'block';
        }
    });
    
    // Кнопка генерации кода Discord
    document.getElementById('generate-discord-code-button').addEventListener('click', async () => {
        try {
            const result = await api.generateDiscordCode();
            
            document.getElementById('discord-code').textContent = result.code;
            document.getElementById('discord-code-card').style.display = 'block';
        } catch (error) {
            alert(`Ошибка генерации кода: ${error.message}`);
        }
    });
    
    // Форма генерации ключа (админ)
    document.getElementById('generate-key-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const duration = parseInt(document.getElementById('key-duration').value);
        const userIdValue = document.getElementById('key-user').value;
        const userId = userIdValue ? parseInt(userIdValue) : null;
        const customKey = document.getElementById('key-custom').value.trim();
        
        document.getElementById('generate-key-error').style.display = 'none';
        document.getElementById('generate-key-success').style.display = 'none';
        
        try {
            const result = await api.generateKey(duration, userId, customKey || null);
            
            document.getElementById('generated-key').textContent = result.key;
            document.getElementById('generate-key-success').style.display = 'block';
        } catch (error) {
            document.getElementById('generate-key-error').textContent = error.message;
            document.getElementById('generate-key-error').style.display = 'block';
        }
    });
}

// Запуск приложения при загрузке страницы
document.addEventListener('DOMContentLoaded', initApp); 