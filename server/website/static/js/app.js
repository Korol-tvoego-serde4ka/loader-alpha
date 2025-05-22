"use strict";

// Проверка наличия глобальной переменной API_URL
if (typeof API_URL === 'undefined') {
    console.error('API_URL не определен. Проверьте подключение config.js');
    // Fallback значение
    window.API_URL = '/api';
}

// Глобальные переменные
let token = localStorage.getItem('token');
let userData = null;

// Глобальная система логирования для отладки
window.appLogger = {
    // Максимальное количество логов для хранения
    maxLogs: 100,
    
    // Массив сохраненных логов
    logs: [],
    
    // Типы логов
    types: {
        INFO: 'info',
        ERROR: 'danger',
        WARNING: 'warning',
        DEBUG: 'secondary'
    },
    
    // Добавление лога
    log: function(message, data = null, type = 'INFO') {
        const logEntry = {
            timestamp: new Date(),
            message: message,
            data: data,
            type: this.types[type] || this.types.INFO
        };
        
        // Добавляем в начало массива
        this.logs.unshift(logEntry);
        
        // Ограничиваем размер массива
        if (this.logs.length > this.maxLogs) {
            this.logs.pop();
        }
        
        // Логируем в консоль браузера
        if (type === 'ERROR') {
            console.error(`[${logEntry.timestamp.toLocaleTimeString()}] ${message}`, data);
        } else if (type === 'WARNING') {
            console.warn(`[${logEntry.timestamp.toLocaleTimeString()}] ${message}`, data);
        } else {
            console.log(`[${logEntry.timestamp.toLocaleTimeString()}] ${message}`, data);
        }
        
        // Обновляем отображение логов если панель открыта
        this.updateLogDisplay();
        
        return logEntry;
    },
    
    // Удобные методы для разных типов логов
    logInfo: function(message, data = null) {
        return this.log(message, data, 'INFO');
    },
    
    logError: function(message, data = null) {
        return this.log(message, data, 'ERROR');
    },
    
    logWarning: function(message, data = null) {
        return this.log(message, data, 'WARNING');
    },
    
    logDebug: function(message, data = null) {
        return this.log(message, data, 'DEBUG');
    },
    
    // Очистка всех логов
    clearLogs: function() {
        this.logs = [];
        this.updateLogDisplay();
    },
    
    // Обновление отображения логов
    updateLogDisplay: function() {
        const logContainer = document.getElementById('admin-log-container');
        if (!logContainer) return;
        
        logContainer.innerHTML = '';
        
        // Создаем элементы для каждого лога
        this.logs.forEach(log => {
            const logElement = document.createElement('div');
            logElement.className = `log-entry alert alert-${log.type} mb-2`;
            
            const timestamp = document.createElement('small');
            timestamp.className = 'text-muted';
            timestamp.textContent = `[${log.timestamp.toLocaleTimeString()}] `;
            
            const message = document.createElement('span');
            message.textContent = log.message;
            
            logElement.appendChild(timestamp);
            logElement.appendChild(message);
            
            // Если есть данные, добавляем их в свернутом виде
            if (log.data) {
                const detailsBtn = document.createElement('button');
                detailsBtn.className = 'btn btn-sm btn-link ml-2';
                detailsBtn.textContent = 'Детали';
                
                const detailsContainer = document.createElement('pre');
                detailsContainer.className = 'log-details mt-2 p-2 bg-dark text-light rounded';
                detailsContainer.style.display = 'none';
                let detailsText = '';
                
                try {
                    if (typeof log.data === 'string') {
                        detailsText = log.data;
                    } else if (log.data instanceof Error) {
                        detailsText = `${log.data.name}: ${log.data.message}\n${log.data.stack || ''}`;
                    } else {
                        detailsText = JSON.stringify(log.data, null, 2);
                    }
                } catch (e) {
                    detailsText = 'Не удалось преобразовать данные';
                }
                
                detailsContainer.textContent = detailsText;
                
                detailsBtn.addEventListener('click', function() {
                    detailsContainer.style.display = detailsContainer.style.display === 'none' ? 'block' : 'none';
                });
                
                logElement.appendChild(detailsBtn);
                logElement.appendChild(detailsContainer);
            }
            
            logContainer.appendChild(logElement);
        });
    }
};

// Кэш для хранения данных
const dataCache = {
    users: null,
    keys: null,
    allKeys: null,
    invites: null,
    inviteLimits: null,
    lastFetch: {
        users: 0,
        keys: 0,
        allKeys: 0,
        invites: 0
    },
    cacheLifetime: 60000, // 60 секунд

    // Проверяет актуальность кэша
    isCacheValid: function(type) {
        return this[type] && (Date.now() - this.lastFetch[type] < this.cacheLifetime);
    },

    // Обновляет кэш
    updateCache: function(type, data) {
        this[type] = data;
        this.lastFetch[type] = Date.now();
    },

    // Очищает кэш
    clearCache: function(type = null) {
        if (type) {
            this[type] = null;
            this.lastFetch[type] = 0;
        } else {
            this.users = null;
            this.keys = null;
            this.allKeys = null;
            this.invites = null;
            this.inviteLimits = null;
            this.lastFetch.users = 0;
            this.lastFetch.keys = 0;
            this.lastFetch.allKeys = 0;
            this.lastFetch.invites = 0;
        }
    }
};

// Настройки пагинации
const pagination = {
    pageSize: 10,  // элементов на странице
    currentPage: {
        users: 1,
        keys: 1,
        allKeys: 1,
        invites: 1
    },

    // Сбрасывает текущую страницу
    resetPage: function(type) {
        this.currentPage[type] = 1;
    },

    // Переход на следующую страницу
    nextPage: function(type) {
        this.currentPage[type]++;
    },

    // Переход на предыдущую страницу
    prevPage: function(type) {
        if (this.currentPage[type] > 1) {
            this.currentPage[type]--;
        }
    },

    // Переход на конкретную страницу
    goToPage: function(type, page) {
        this.currentPage[type] = page;
    },

    // Получение текущей страницы данных
    getPageData: function(type, data) {
        const start = (this.currentPage[type] - 1) * this.pageSize;
        const end = start + this.pageSize;
        return data.slice(start, end);
    },

    // Генерация HTML пагинации
    generatePaginationHTML: function(type, totalItems) {
        const totalPages = Math.ceil(totalItems / this.pageSize);
        
        if (totalPages <= 1) {
            return '';
        }

        let html = '<div class="pagination-container mt-3"><ul class="pagination pagination-sm justify-content-center">';
        
        // Кнопка "Предыдущая"
        if (this.currentPage[type] > 1) {
            html += `<li class="page-item"><a class="page-link pagination-link" data-type="${type}" data-page="${this.currentPage[type] - 1}" href="#">&laquo;</a></li>`;
        } else {
            html += '<li class="page-item disabled"><a class="page-link" href="#">&laquo;</a></li>';
        }
        
        // Номера страниц
        const startPage = Math.max(1, this.currentPage[type] - 2);
        const endPage = Math.min(totalPages, this.currentPage[type] + 2);
        
        for (let i = startPage; i <= endPage; i++) {
            if (i === this.currentPage[type]) {
                html += `<li class="page-item active"><a class="page-link" href="#">${i}</a></li>`;
            } else {
                html += `<li class="page-item"><a class="page-link pagination-link" data-type="${type}" data-page="${i}" href="#">${i}</a></li>`;
            }
        }
        
        // Кнопка "Следующая"
        if (this.currentPage[type] < totalPages) {
            html += `<li class="page-item"><a class="page-link pagination-link" data-type="${type}" data-page="${this.currentPage[type] + 1}" href="#">&raquo;</a></li>`;
        } else {
            html += '<li class="page-item disabled"><a class="page-link" href="#">&raquo;</a></li>';
        }
        
        html += '</ul></div>';
        
        return html;
    }
};

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
        
        console.log(`API запрос: ${method} ${API_URL}${endpoint}`, options);
        
        try {
            const response = await fetch(`${API_URL}${endpoint}`, options);
            
            // Логируем статус ответа
            window.appLogger.logInfo(`API ответ статус: ${response.status} ${response.statusText} для ${endpoint}`);
            
            if (!response.ok) {
                // Для ошибок пытаемся получить сообщение из JSON, если это возможно
                try {
                    const errorJson = await response.json();
                    window.appLogger.logError(`API ошибка: ${endpoint}`, errorJson);
                    throw new Error(errorJson.message || `HTTP ошибка ${response.status}`);
                } catch (jsonError) {
                    // Если не удалось распарсить JSON, получаем текст ошибки
                    const errorText = await response.text();
                    window.appLogger.logError(`API ошибка (не JSON): ${endpoint}`, {status: response.status, text: errorText});
                    throw new Error(`Ошибка сервера (${response.status}): Проверьте логи для деталей`);
                }
            }
            
            // Проверяем, что ответ - это JSON
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const jsonResponse = await response.json();
                console.log(`API ответ: ${endpoint}`, jsonResponse);
                return jsonResponse;
            } else {
                const responseText = await response.text();
                window.appLogger.logError(`API ответ не в формате JSON: ${endpoint}`, responseText);
                throw new Error(`Ответ сервера не в формате JSON (проверьте логи)`);
            }
        } catch (error) {
            console.error(`API ошибка: ${endpoint}`, error);
            // Логируем ошибку в глобальный журнал
            if (window.appLogger) {
                window.appLogger.logError(`API ошибка: ${endpoint}`, error);
            }
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
    createInvite: () => {
        console.log('Отправка запроса на создание инвайта');
        return api.request('/invites/generate', 'POST', {});
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
        console.log('Отправка лимитов:', {adminLimit, supportLimit, userLimit});
        return api.request('/admin/invites/limits', 'POST', {
            admin_limit: parseInt(adminLimit),
            support_limit: parseInt(supportLimit),
            user_limit: parseInt(userLimit)
        });
    },
    
    // Генерация кода для привязки Discord
    generateDiscordCode: () => {
        return api.request('/users/discord-code', 'POST');
    },
    
    // Получение списка пользователей (для админов и саппортов)
    getUsers: () => {
        return api.request('/admin/users');
    },
    
    // Получение данных активности пользователей (для админов и саппортов)
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
    },
    
    // Изменение пароля
    changePassword: async (currentPassword, newPassword) => {
        try {
            const response = await fetch(`${API_URL}/change-password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword
                })
            });
            
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.message || 'Ошибка при изменении пароля');
                }
                
                return data;
            } else {
                throw new Error('Ответ сервера не в формате JSON');
            }
        } catch (error) {
            console.error('Ошибка при изменении пароля:', error);
            // Логируем ошибку в глобальный журнал
            if (window.appLogger) {
                window.appLogger.logError('Ошибка при изменении пароля', error);
            }
            throw error;
        }
    },
    
    // Отвязка Discord (для админов)
    unlinkDiscord: (userId) => {
        return api.request(`/admin/users/${userId}/unlink-discord`, 'POST');
    },
    
    // Получение Discord-инвайт ссылки
    getDiscordInviteLink: async () => {
        try {
            const response = await fetch(`${API_URL}/discord/invite-link`);
            
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const data = await response.json();
                return data.invite_link;
            } else {
                throw new Error('Ответ сервера не в формате JSON');
            }
        } catch (error) {
            console.error('Ошибка при получении ссылки Discord:', error);
            // Логируем ошибку в глобальный журнал
            if (window.appLogger) {
                window.appLogger.logError('Ошибка при получении ссылки Discord', error);
            }
            throw error;
        }
    },
    
    // Смена пароля пользователя (для админов)
    adminChangeUserPassword: (userId, newPassword) => {
        return api.request(`/admin/users/${userId}/change-password`, 'POST', { new_password: newPassword });
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
    },
    
    // Показываем уведомление
    showNotification: function(type, message) {
        const notificationContainer = document.getElementById('notification-container');
        if (!notificationContainer) {
            console.error('Notification container not found');
            return;
        }
        
        const notification = document.createElement('div');
        notification.className = `alert alert-${type}`;
        notification.textContent = message;
        
        notificationContainer.appendChild(notification);
        
        // Автоматическое удаление уведомления через 5 секунд
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
};

// Навигация по страницам
const navigation = {
    // Текущая страница
    currentPage: '',
    
    // Переход на страницу
    navigateTo: function(page) {
        try {
            console.log('Navigating to page:', page);
            
            // Скрываем все страницы
            document.querySelectorAll('[id$="-page"]').forEach(el => {
                if (el) el.style.display = 'none';
            });
            
            // Убираем активный класс у всех ссылок
            document.querySelectorAll('.nav-link').forEach(link => {
                if (link) link.classList.remove('active');
            });
            
            this.currentPage = page;
            let showPage = true;
            
            // Проверка доступа к странице
            if (page === 'admin' && (!userData || (!userData.is_admin && !userData.is_support))) {
                showPage = false;
                page = 'home';
                this.currentPage = 'home';
            }
            
            if (['keys', 'invites', 'discord'].includes(page) && !token) {
                showPage = false;
                page = 'login';
                this.currentPage = 'login';
            }
            
            // Показываем выбранную страницу
            const pageEl = document.getElementById(`${page}-page`);
            if (pageEl && showPage) {
                pageEl.style.display = 'block';
                
                // Подсвечиваем активную ссылку
                const navLink = document.querySelector(`.nav-link[href="#${page}"]`);
                if (navLink) {
                    navLink.classList.add('active');
                }
                
                // Обновляем историю
                window.location.hash = `#${page}`;
                
                // Выполняем дополнительные действия при переходе на определенные страницы
                if (page === 'keys') {
                    try {
                    loadKeys();
                    } catch (e) {
                        console.error('Error loading keys:', e);
                    }
                } else if (page === 'invites') {
                    try {
                    loadInvites();
                    } catch (e) {
                        console.error('Error loading invites:', e);
                    }
                } else if (page === 'discord') {
                    try {
                    loadDiscordStatus();
                    } catch (e) {
                        console.error('Error loading discord status:', e);
                    }
                } else if (page === 'admin') {
                    try {
                    loadAdminData();
                    } catch (e) {
                        console.error('Error loading admin data:', e);
                    }
                }
            } else if (page === 'home') {
                const homePage = document.getElementById('home-page');
                if (homePage) homePage.style.display = 'block';
                const navLink = document.querySelector(`.nav-link[href="#home"]`);
                if (navLink) {
                    navLink.classList.add('active');
                }
            } else if (page === 'login') {
                const loginPage = document.getElementById('login-page');
                if (loginPage) loginPage.style.display = 'block';
                const navLink = document.querySelector(`.nav-link[href="#login"]`);
                if (navLink) {
                    navLink.classList.add('active');
                }
            } else if (page === 'register') {
                const registerPage = document.getElementById('register-page');
                if (registerPage) registerPage.style.display = 'block';
                const navLink = document.querySelector(`.nav-link[href="#register"]`);
                if (navLink) {
                    navLink.classList.add('active');
                }
            } else if (page === 'docs') {
                const docsPage = document.getElementById('docs-page');
                if (docsPage) docsPage.style.display = 'block';
                const navLink = document.querySelector(`.nav-link[href="#docs"]`);
                if (navLink) {
                    navLink.classList.add('active');
                }
            } else if (page === 'profile') {
                const profilePage = document.getElementById('profile-page');
                if (profilePage) profilePage.style.display = 'block';
                const navLink = document.querySelector(`.nav-link[href="#profile"]`);
                if (navLink) navLink.classList.add('active');
                // Подгружаем данные пользователя
                if (userData) {
                    displayProfileInfo(userData);
                } else {
                    api.getUserInfo().then(displayProfileInfo);
                }
            }
            
            // Прокручиваем страницу вверх
            try {
                window.scrollTo(0, 0);
            } catch (e) {
                console.error('Error scrolling to top:', e);
            }
            
            console.log('Navigation complete:', page);
        } catch (error) {
            console.error('Navigation error:', error);
            // Восстановление в случае ошибки
            try {
                const homePage = document.getElementById('home-page');
                if (homePage) homePage.style.display = 'block';
            } catch (e) {
                console.error('Failed to recover navigation:', e);
            }
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
            const usernameDisplay = document.getElementById('username-display');
            if (usernameDisplay) usernameDisplay.textContent = userData.username;
            
            // Отображение элементов для авторизованных пользователей
            const loginButtons = document.getElementById('login-buttons');
            const userInfo = document.getElementById('user-info');
            const homeButtons = document.getElementById('home-buttons');
            const downloadButton = document.getElementById('download-button');
            
            if (loginButtons) loginButtons.style.display = 'none';
            if (userInfo) userInfo.style.display = 'flex';
            if (homeButtons) homeButtons.style.display = 'none';
            if (downloadButton) downloadButton.style.display = 'block';
            
            // Отображение навигационных элементов
            const keysNav = document.getElementById('keys-nav');
            const invitesNav = document.getElementById('invites-nav');
            const discordNav = document.getElementById('discord-nav');
            
            if (keysNav) keysNav.style.display = 'block';
            // Скрываем вкладку приглашений, так как она интегрирована в АдминОчку
            if (invitesNav) invitesNav.style.display = userData.is_admin || userData.is_support ? 'none' : 'block';
            if (discordNav) discordNav.style.display = 'block';
            
            // Отображение админ-панели для админов и саппорта
            const navAdmin = document.getElementById('nav-admin');
            const adminCommands = document.getElementById('admin-commands');
            
            if (userData.is_admin || userData.is_support) {
                if (navAdmin) navAdmin.style.display = 'block';
                document.querySelectorAll('.admin-command').forEach(el => {
                    if (el) el.style.display = 'table-row';
                });
                if (adminCommands) adminCommands.style.display = 'table-row';
            } else {
                if (navAdmin) navAdmin.style.display = 'none';
                document.querySelectorAll('.admin-command').forEach(el => {
                    if (el) el.style.display = 'none';
                });
                if (adminCommands) adminCommands.style.display = 'none';
            }
            
            return true;
        } catch (error) {
            console.error('Error during auth check:', error);
            auth.logout();
            return false;
        }
    },
    
    // Выход из системы
    logout: () => {
        token = null;
        userData = null;
        localStorage.removeItem('token');
        
        try {
        // Скрытие элементов для авторизованных пользователей
            const loginButtons = document.getElementById('login-buttons');
            const userInfo = document.getElementById('user-info');
            const homeButtons = document.getElementById('home-buttons');
            const downloadButton = document.getElementById('download-button');
            const navAdmin = document.getElementById('nav-admin');
            
            // Скрываем навигационные элементы
            const keysNav = document.getElementById('keys-nav');
            const invitesNav = document.getElementById('invites-nav');
            const discordNav = document.getElementById('discord-nav');
            
            if (keysNav) keysNav.style.display = 'none';
            if (invitesNav) invitesNav.style.display = 'none';
            if (discordNav) discordNav.style.display = 'none';
            
            if (loginButtons) loginButtons.style.display = 'flex';
            if (userInfo) userInfo.style.display = 'none';
            if (homeButtons) homeButtons.style.display = 'block';
            if (downloadButton) downloadButton.style.display = 'none';
            if (navAdmin) navAdmin.style.display = 'none';
        
        // Переход на главную страницу
        navigation.navigateTo('home');
        } catch (error) {
            console.error('Error during logout:', error);
        }
    }
};

// Загрузка данных

// Загрузка ключей пользователя
async function loadKeys() {
    try {
        const keysLoading = document.getElementById('keys-loading');
        const noKeys = document.getElementById('no-keys');
        const keysList = document.getElementById('keys-list');
        
        if (keysLoading) keysLoading.style.display = 'block';
        if (noKeys) noKeys.style.display = 'none';
        if (keysList) keysList.style.display = 'none';
        
        try {
            let keysData;
            
            // Используем кэш, если он актуален
            if (dataCache.isCacheValid('keys')) {
                keysData = { keys: dataCache.keys };
            } else {
                keysData = await api.getKeys();
                dataCache.updateCache('keys', keysData.keys);
            }
            
        const keys = keysData.keys.filter(key => key.is_active);
        
        if (keys.length === 0) {
                if (noKeys) noKeys.style.display = 'block';
        } else {
            const tableBody = document.getElementById('keys-table-body');
                if (tableBody) tableBody.innerHTML = '';
                
                // Фильтрация по поисковому запросу
                const searchQuery = document.getElementById('keys-search')?.value?.toLowerCase() || '';
                let filteredKeys = keys;
                
                if (searchQuery) {
                    filteredKeys = keys.filter(key => key.key.toLowerCase().includes(searchQuery));
                }
                
                // Получаем данные только для текущей страницы
                const pageKeys = pagination.getPageData('keys', filteredKeys);
                
                if (tableBody) {
                    pageKeys.forEach(key => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${key.key}</td>
                    <td>${utils.formatDate(key.created_at)}</td>
                    <td>${utils.formatDate(key.expires_at)}</td>
                    <td>${utils.formatTimeLeft(key.time_left)}</td>
                `;
                tableBody.appendChild(row);
            });
                }
                
                // Добавляем пагинацию
                const paginationContainer = document.getElementById('keys-pagination');
                if (paginationContainer) {
                    paginationContainer.innerHTML = pagination.generatePaginationHTML('keys', filteredKeys.length);
                    
                    // Добавляем обработчики для кнопок пагинации
                    document.querySelectorAll('.pagination-link[data-type="keys"]').forEach(link => {
                        link.addEventListener('click', function(e) {
                            e.preventDefault();
                            const type = this.getAttribute('data-type');
                            const page = parseInt(this.getAttribute('data-page'));
                            pagination.goToPage(type, page);
                            loadKeys(); // Перезагружаем с новой страницей
                        });
                    });
                }
                
                if (keysList) keysList.style.display = 'block';
        }
    } catch (error) {
        console.error('Ошибка при загрузке ключей:', error);
    } finally {
            if (keysLoading) keysLoading.style.display = 'none';
        }
    } catch (error) {
        console.error('Fatal error in loadKeys function:', error);
    }
}

// Загрузка инвайтов пользователя
async function loadInvites() {
    try {
        const invitesLoading = document.getElementById('invites-loading');
        const noInvites = document.getElementById('no-invites');
        const invitesList = document.getElementById('invites-list');
        const inviteLimits = document.getElementById('invite-limits');
        const adminInviteLimits = document.getElementById('admin-invite-limits');
        const deleteSelectedInvitesButton = document.getElementById('delete-selected-invites-button');
        
        if (invitesLoading) invitesLoading.style.display = 'block';
        if (noInvites) noInvites.style.display = 'none';
        if (invitesList) invitesList.style.display = 'none';
        if (inviteLimits) inviteLimits.style.display = 'none';
        if (adminInviteLimits) adminInviteLimits.style.display = 'none';
        if (deleteSelectedInvitesButton) deleteSelectedInvitesButton.style.display = 'none';
    
    try {
        // Загрузка инвайтов и лимитов одновременно
            let invitesData, limitsData;
            
            if (dataCache.isCacheValid('invites')) {
                invitesData = { invites: dataCache.invites };
                limitsData = dataCache.inviteLimits;
            } else {
                console.log("Запрашиваем новые данные для приглашений");
                [invitesData, limitsData] = await Promise.all([
            api.getInvites(),
            api.getInviteLimits()
        ]);
                
                console.log("Получены данные приглашений:", invitesData);
                
                // Проверяем, что данные получены в правильном формате
                if (!invitesData || !invitesData.invites || !Array.isArray(invitesData.invites)) {
                    console.error("Неверный формат данных приглашений:", invitesData);
                    if (invitesList) invitesList.innerHTML = '<p class="text-danger">Ошибка загрузки приглашений: неверный формат данных</p>';
                    if (invitesLoading) invitesLoading.style.display = 'none';
                    if (invitesList) invitesList.style.display = 'block';
                    return;
                }
                
                dataCache.updateCache('invites', invitesData.invites);
                dataCache.updateCache('inviteLimits', limitsData);
            }
        
        const invites = invitesData.invites;
        
        // Отображение информации о лимитах
            const monthlyLimit = document.getElementById('monthly-limit');
            const usedInvites = document.getElementById('used-invites');
            const remainingInvites = document.getElementById('remaining-invites');
            
            if (monthlyLimit) monthlyLimit.textContent = limitsData.monthly_limit;
            if (usedInvites) usedInvites.textContent = limitsData.used_invites;
            if (remainingInvites) remainingInvites.textContent = limitsData.remaining_invites;
            if (inviteLimits) inviteLimits.style.display = 'block';
        
        // Отображение панели управления лимитами для админов
        if (userData && userData.is_admin) {
                const adminLimitValue = document.getElementById('admin-limit-value');
                const supportLimitValue = document.getElementById('support-limit-value');
                const userLimitValue = document.getElementById('user-limit-value');
                const invitesActionsHeader = document.getElementById('invites-actions-header');
                
                if (adminLimitValue) adminLimitValue.value = limitsData.global_limits.admin;
                if (supportLimitValue) supportLimitValue.value = limitsData.global_limits.support;
                if (userLimitValue) userLimitValue.value = limitsData.global_limits.user;
                if (adminInviteLimits) adminInviteLimits.style.display = 'block';
                if (invitesActionsHeader) invitesActionsHeader.style.display = 'table-cell';
                if (deleteSelectedInvitesButton) deleteSelectedInvitesButton.style.display = 'inline-block';
        } else {
                const invitesActionsHeader = document.getElementById('invites-actions-header');
                if (invitesActionsHeader) invitesActionsHeader.style.display = 'none';
        }
        
        // Проверка, есть ли инвайты для отображения
            if (!invites || invites.length === 0) {
                if (noInvites) noInvites.style.display = 'block';
        } else {
                // Фильтрация по поисковому запросу
                const searchQuery = document.getElementById('invites-search')?.value?.toLowerCase() || '';
                let filteredInvites = invites;
                
                if (searchQuery) {
                    filteredInvites = invites.filter(invite => 
                        invite.code.toLowerCase().includes(searchQuery) || 
                        (invite.created_by && typeof invite.created_by === 'object' && invite.created_by.username && 
                         invite.created_by.username.toLowerCase().includes(searchQuery)) ||
                        (invite.used_by && invite.used_by.toLowerCase().includes(searchQuery))
                    );
                }
                
                // Получаем данные только для текущей страницы
                const pageInvites = pagination.getPageData('invites', filteredInvites);
                
            const tableBody = document.getElementById('invites-table-body');
                if (tableBody) tableBody.innerHTML = '';
            
                if (tableBody) {
                    pageInvites.forEach(invite => {
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
                
                        // Создаем ячейки данных
                        const codeCell = document.createElement('td');
                        codeCell.textContent = invite.code;
                        row.appendChild(codeCell);
                        
                        const createdCell = document.createElement('td');
                        createdCell.textContent = utils.formatDate(invite.created_at);
                        row.appendChild(createdCell);
                        
                        const expiresCell = document.createElement('td');
                        expiresCell.textContent = utils.formatDate(invite.expires_at);
                        row.appendChild(expiresCell);
                        
                        const statusCell = document.createElement('td');
                        statusCell.textContent = status;
                        row.appendChild(statusCell);
                        
                        const creatorCell = document.createElement('td');
                        // Проверяем формат поля created_by
                        if (invite.created_by && typeof invite.created_by === 'object' && invite.created_by.username) {
                            creatorCell.textContent = invite.created_by.username;
                        } else if (invite.created_by && typeof invite.created_by === 'string') {
                            creatorCell.textContent = invite.created_by;
                        } else {
                            creatorCell.textContent = 'Неизвестно';
                        }
                        row.appendChild(creatorCell);
                        
                        const usedByCell = document.createElement('td');
                        usedByCell.textContent = invite.used_by ? invite.used_by : 'Не использован';
                        row.appendChild(usedByCell);
                
                // Добавляем кнопку удаления для админов
                if (userData && userData.is_admin) {
                    const actionCell = document.createElement('td');
                    const deleteButton = document.createElement('button');
                    deleteButton.className = 'btn btn-danger btn-sm';
                    deleteButton.textContent = 'Удалить';
                    deleteButton.addEventListener('click', async () => {
                        if (confirm('Вы уверены, что хотите удалить этот инвайт?')) {
                            try {
                                        deleteButton.disabled = true;
                                        deleteButton.textContent = 'Удаление...';
                                        
                                await api.deleteInvite(invite.id);
                                        dataCache.clearCache('invites'); // Очищаем кэш
                                loadInvites(); // Перезагрузка списка после удаления
                            } catch (error) {
                                alert(`Ошибка при удалении инвайта: ${error.message}`);
                                        deleteButton.disabled = false;
                                        deleteButton.textContent = 'Удалить';
                            }
                        }
                    });
                    actionCell.appendChild(deleteButton);
                    row.appendChild(actionCell);
                }
                
                tableBody.appendChild(row);
            });
                }
                
                // Добавляем пагинацию
                const paginationContainer = document.getElementById('invites-pagination');
                if (paginationContainer) {
                    paginationContainer.innerHTML = pagination.generatePaginationHTML('invites', filteredInvites.length);
                    
                    // Добавляем обработчики для кнопок пагинации
                    document.querySelectorAll('.pagination-link[data-type="invites"]').forEach(link => {
                        link.addEventListener('click', function(e) {
                            e.preventDefault();
                            const type = this.getAttribute('data-type');
                            const page = parseInt(this.getAttribute('data-page'));
                            pagination.goToPage(type, page);
                            loadInvites(); // Перезагружаем с новой страницей
                        });
                    });
                }
                
                if (invitesList) invitesList.style.display = 'block';
            
            // Настройка обработчика для кнопки "Выбрать все"
            const selectAllCheckbox = document.getElementById('select-all-invites');
                if (selectAllCheckbox) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.addEventListener('change', () => {
                document.querySelectorAll('.invite-checkbox:not([disabled])').forEach(checkbox => {
                    checkbox.checked = selectAllCheckbox.checked;
                });
            });
                }
            
            // Настройка обработчика для кнопки "Удалить выбранные"
                const deleteSelectedButton = document.getElementById('delete-selected-invites-button');
                if (deleteSelectedButton) {
                    deleteSelectedButton.addEventListener('click', async () => {
                const selectedInvites = Array.from(document.querySelectorAll('.invite-checkbox:checked'))
                    .map(checkbox => parseInt(checkbox.dataset.inviteId));
                
                if (selectedInvites.length === 0) {
                    alert('Выберите инвайты для удаления');
                    return;
                }
                
                if (confirm(`Вы уверены, что хотите удалить ${selectedInvites.length} инвайтов?`)) {
                    try {
                                deleteSelectedButton.disabled = true;
                                deleteSelectedButton.textContent = 'Удаление...';
                        
                        await api.deleteMultipleInvites(selectedInvites);
                                dataCache.clearCache('invites'); // Очищаем кэш
                        loadInvites(); // Перезагрузка списка после удаления
                    } catch (error) {
                        alert(`Ошибка при удалении инвайтов: ${error.message}`);
                                deleteSelectedButton.disabled = false;
                                deleteSelectedButton.textContent = 'Удалить выбранные';
                    }
                }
            });
                }
        }
    } catch (error) {
        console.error('Ошибка при загрузке инвайтов:', error);
            if (invitesList) invitesList.innerHTML = `<p class="text-danger">Ошибка при загрузке приглашений: ${error.message}</p>`;
    } finally {
            if (invitesLoading) invitesLoading.style.display = 'none';
        }
    } catch (error) {
        console.error('Fatal error in loadInvites function:', error);
    }
}

// Функция для генерации нового приглашения
async function generateInvite() {
    try {
        // Показываем индикатор загрузки
        const invitesLoading = document.getElementById('invites-loading');
        if (invitesLoading) invitesLoading.style.display = 'block';
        
        window.appLogger.logInfo("Отправляем запрос на генерацию приглашения");
        const response = await api.createInvite();
        window.appLogger.logInfo("Ответ сервера при генерации приглашения", response);
        
        if (response && response.code) {
            // Очищаем кэш и перезагружаем список приглашений
            window.appLogger.logInfo("Приглашение успешно создано:", response.code);
            dataCache.clearCache('invites');
            
            // Перезагружаем списки приглашений
            const isAdmin = document.getElementById('admin-tab');
            if (isAdmin && isAdmin.classList.contains('active')) {
                // Если активна вкладка админа, обновляем список в админке
                await loadAdminInvites();
            } else {
                // Иначе обновляем обычный список приглашений
                await loadInvites();
            }
            
            // Показываем уведомление
            utils.showNotification('success', `Новое приглашение создано: ${response.code}`);
        } else {
            window.appLogger.logError("Ошибка при создании приглашения: неверный формат ответа", response);
            utils.showNotification('danger', 'Ошибка при создании приглашения');
        }
    } catch (error) {
        console.error("Ошибка при создании приглашения:", error);
        utils.showNotification('danger', `Ошибка при создании приглашения: ${error.message || 'неизвестная ошибка'}`);
    } finally {
        // Скрываем индикатор загрузки
        const invitesLoading = document.getElementById('invites-loading');
        if (invitesLoading) invitesLoading.style.display = 'none';
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
        
        try {
            const notLinkedBlock = document.getElementById('discord-not-linked');
            if (notLinkedBlock) {
                notLinkedBlock.querySelectorAll('.btn-discord-link').forEach(btn => btn.remove());
            }
            const discordLink = await api.getDiscordInviteLink();
            const discordLinkBtn = document.createElement('a');
            discordLinkBtn.href = discordLink;
            discordLinkBtn.target = '_blank';
            discordLinkBtn.className = 'btn btn-info mt-3 btn-discord-link';
            discordLinkBtn.textContent = 'Перейти в Discord';
            if (notLinkedBlock) notLinkedBlock.appendChild(discordLinkBtn);
        } catch (e) { /* ignore */ }
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
        let usersData;
        
        // Используем кэш, если он актуален
        if (dataCache.isCacheValid('users')) {
            usersData = { users: dataCache.users };
        } else {
            // Получаем данные активности пользователей
            usersData = await api.getUsersActivity();
            dataCache.updateCache('users', usersData.users);
        }
        
        const users = usersData.users;
        const tableBody = document.getElementById('users-table-body');
        tableBody.innerHTML = '';
        
        // Фильтрация по поисковому запросу
        const searchQuery = document.getElementById('users-search')?.value?.toLowerCase() || '';
        let filteredUsers = users;
        
        if (searchQuery) {
            filteredUsers = users.filter(user => 
                user.username.toLowerCase().includes(searchQuery) || 
                user.email.toLowerCase().includes(searchQuery) ||
                (user.discord_username && user.discord_username.toLowerCase().includes(searchQuery))
            );
        }
        
        // Получаем только данные для текущей страницы
        const pageUsers = pagination.getPageData('users', filteredUsers);
        
        // Отображаем текущую страницу данных
        pageUsers.forEach(user => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${user.id}</td>
                <td>${user.username}</td>
                <td>${user.email}</td>
                <td>${utils.getUserRole(user)}</td>
                <td>${user.discord_linked ? user.discord_username : 'Не привязан'}</td>
                <td>${user.is_banned ? 'Заблокирован' : 'Активен'}</td>
                <td>${user.last_login ? new Date(user.last_login).toLocaleString() : 'Никогда'}</td>
                <td>${utils.formatIpAddress(user.last_ip)}</td>
                <td><div class="action-buttons"></div></td>
            `;
            const actionsDiv = row.querySelector('.action-buttons');
            
            // Кнопка бан/разбан
            if (userData && (userData.is_admin || userData.is_support)) {
                if (user.is_banned) {
                    const unbanUserBtn = document.createElement('button');
                    unbanUserBtn.className = 'btn btn-success btn-sm ml-1';
                    unbanUserBtn.textContent = 'Разбл';
                    unbanUserBtn.title = 'Разблокировать пользователя';
                    unbanUserBtn.addEventListener('click', async () => {
                        try {
                            await api.unbanUser(user.id);
                            dataCache.clearCache('users');
                            loadAdminData();
                        } catch (error) {
                            alert(`Ошибка разблокировки пользователя: ${error.message}`);
                        }
                    });
                    actionsDiv.appendChild(unbanUserBtn);
                } else {
                    const banUserBtn = document.createElement('button');
                    banUserBtn.className = 'btn btn-danger btn-sm ml-1';
                    banUserBtn.textContent = 'Блок';
                    banUserBtn.title = 'Заблокировать пользователя';
                    banUserBtn.addEventListener('click', async () => {
                        try {
                            await api.banUser(user.id);
                            dataCache.clearCache('users');
                            loadAdminData();
                        } catch (error) {
                            alert(`Ошибка блокировки пользователя: ${error.message}`);
                        }
                    });
                    actionsDiv.appendChild(banUserBtn);
                }
            }
            
            // Добавляем кнопку смены пароля для админов
            if (userData && userData.is_admin) {
                const changePasswordBtn = document.createElement('button');
                changePasswordBtn.className = 'btn btn-info btn-sm ml-1';
                changePasswordBtn.textContent = 'Пароль';
                changePasswordBtn.title = 'Сменить пароль пользователя';
                changePasswordBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    showChangePasswordModal(user.id, user.username);
                });
                actionsDiv.appendChild(changePasswordBtn);
            }
            
            if (user.discord_linked && userData && userData.is_admin) {
                const unlinkBtn = document.createElement('button');
                unlinkBtn.className = 'btn btn-warning btn-sm ml-1';
                unlinkBtn.textContent = 'Отвязать Discord';
                unlinkBtn.title = 'Отвязать Discord-аккаунт';
                unlinkBtn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    if (confirm('Вы уверены, что хотите отвязать Discord у этого пользователя?')) {
                        unlinkBtn.disabled = true;
                        unlinkBtn.textContent = 'Отключение...';
                        try {
                            await api.unlinkDiscord(user.id);
                            dataCache.clearCache('users');
                            loadAdminData();
                        } catch (error) {
                            alert('Ошибка при отвязке Discord: ' + error.message);
                            unlinkBtn.disabled = false;
                            unlinkBtn.textContent = 'Отвязать Discord';
                        }
                    }
                });
                actionsDiv.appendChild(unlinkBtn);
            }
            if (userData && userData.is_admin) {
                // Кнопки смены ролей
                const makeAdminBtn = document.createElement('button');
                makeAdminBtn.className = 'btn btn-primary btn-sm ml-1';
                makeAdminBtn.textContent = 'A';
                makeAdminBtn.title = 'Сделать администратором';
                makeAdminBtn.addEventListener('click', async () => {
                    try {
                        await api.setUserRole(user.id, 'admin');
                        dataCache.clearCache('users');
                        loadAdminData();
                    } catch (error) {
                        alert(`Ошибка при назначении администратора: ${error.message}`);
                    }
                });
                actionsDiv.appendChild(makeAdminBtn);

                const makeSupportBtn = document.createElement('button');
                makeSupportBtn.className = 'btn btn-info btn-sm ml-1';
                makeSupportBtn.textContent = 'C';
                makeSupportBtn.title = 'Сделать саппортом';
                makeSupportBtn.addEventListener('click', async () => {
                    try {
                        await api.setUserRole(user.id, 'support');
                        dataCache.clearCache('users');
                        loadAdminData();
                    } catch (error) {
                        alert(`Ошибка при назначении саппорта: ${error.message}`);
                    }
                });
                actionsDiv.appendChild(makeSupportBtn);

                const makeUserBtn = document.createElement('button');
                makeUserBtn.className = 'btn btn-secondary btn-sm ml-1';
                makeUserBtn.textContent = 'Ю';
                makeUserBtn.title = 'Сделать обычным пользователем';
                makeUserBtn.addEventListener('click', async () => {
                    try {
                        await api.setUserRole(user.id, 'user');
                        dataCache.clearCache('users');
                        loadAdminData();
                    } catch (error) {
                        alert(`Ошибка при сбросе роли: ${error.message}`);
                    }
                });
                actionsDiv.appendChild(makeUserBtn);
                
                // Кнопка удаления пользователя
                const deleteUserBtn = document.createElement('button');
                deleteUserBtn.className = 'btn btn-danger btn-sm ml-1';
                deleteUserBtn.textContent = 'X';
                deleteUserBtn.title = 'Удалить пользователя';
                deleteUserBtn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    if (confirm(`Вы уверены, что хотите удалить пользователя ${user.username}?`)) {
                        try {
                            // Добавим API-метод для удаления пользователя если он будет создан
                            alert('Функция удаления пользователя пока не реализована');
                            // await api.deleteUser(user.id);
                            // dataCache.clearCache('users');
                            // loadAdminData();
                        } catch (error) {
                            alert(`Ошибка при удалении пользователя: ${error.message}`);
                        }
                    }
                });
                actionsDiv.appendChild(deleteUserBtn);
            }
            row.addEventListener('click', function(e) {
                if (e.target.tagName === 'BUTTON' || e.target.closest('.action-buttons')) return;
                document.querySelectorAll('#users-table tbody tr').forEach(r => r.classList.remove('active-row'));
                row.classList.toggle('active-row');
            });
            tableBody.appendChild(row);
        });
        
        // Добавляем пагинацию
        const paginationContainer = document.getElementById('users-pagination');
        if (paginationContainer) {
            paginationContainer.innerHTML = pagination.generatePaginationHTML('users', filteredUsers.length);
            
            // Добавляем обработчики для кнопок пагинации
            document.querySelectorAll('.pagination-link').forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    const type = this.getAttribute('data-type');
                    const page = parseInt(this.getAttribute('data-page'));
                    pagination.goToPage(type, page);
                    loadAdminData(); // Перезагружаем с новой страницей
                });
            });
        }
        
        document.getElementById('users-loading').style.display = 'none';
        document.getElementById('users-list').style.display = 'block';
        
        // Загрузка приглашений в админке
        loadAdminInvites();
        
        // Загрузка всех ключей
        loadAllKeys();
    } catch (error) {
        console.error('Ошибка при загрузке списка пользователей:', error);
        document.getElementById('users-loading').style.display = 'none';
    }
}

// Загрузка приглашений в админке
async function loadAdminInvites() {
    const adminInvitesLoading = document.getElementById('admin-invites-loading');
    const adminInvitesList = document.getElementById('admin-invites-list');
    
    if (adminInvitesLoading) adminInvitesLoading.style.display = 'block';
    if (adminInvitesList) adminInvitesList.style.display = 'none';
    
    try {
        window.appLogger.logInfo("Начинаем загрузку приглашений в админке");
        let invitesData = { invites: [] };
        let limitsData = { global_limits: { admin: 0, support: 0, user: 0 } };
        
        // Очищаем кэш
        dataCache.clearCache('invites');
        dataCache.clearCache('inviteLimits');
        
        window.appLogger.logInfo("Запрашиваем новые данные для приглашений");
        
        // Запрашиваем данные по очереди для более точной обработки ошибок
        try {
            limitsData = await api.getInviteLimits();
            window.appLogger.logInfo("Получены данные лимитов", limitsData);
        } catch (limitsError) {
            window.appLogger.logError("Ошибка при загрузке лимитов", limitsError);
            utils.showNotification('warning', 'Не удалось загрузить информацию о лимитах');
        }
        
        try {
            invitesData = await api.getInvites();
            window.appLogger.logInfo("Получены данные приглашений", invitesData);
        } catch (invitesError) {
            window.appLogger.logError("Ошибка при загрузке приглашений", invitesError);
            utils.showNotification('warning', 'Не удалось загрузить список приглашений');
        }
        
        console.log("Получены данные приглашений:", invitesData);
        console.log("Получены данные лимитов:", limitsData);
        
        // Проверяем, что данные получены в правильном формате
        if (!invitesData || !invitesData.invites || !Array.isArray(invitesData.invites)) {
            console.error("Неверный формат данных приглашений:", invitesData);
            if (adminInvitesList) adminInvitesList.innerHTML = '<p class="text-danger">Ошибка загрузки приглашений: неверный формат данных</p>';
            if (adminInvitesLoading) adminInvitesLoading.style.display = 'none';
            if (adminInvitesList) adminInvitesList.style.display = 'block';
            return;
        }
        
        dataCache.updateCache('invites', invitesData.invites);
        dataCache.updateCache('inviteLimits', limitsData);
        
        const invites = invitesData.invites;
        console.log(`Количество загруженных приглашений: ${invites ? invites.length : 0}`);
        
        // Копируем значения лимитов в форму в админской вкладке ПриглОчки
        const adminLimitValueAdmin = document.getElementById('admin-limit-value-admin');
        const supportLimitValueAdmin = document.getElementById('support-limit-value-admin');
        const userLimitValueAdmin = document.getElementById('user-limit-value-admin');
        
        if (adminLimitValueAdmin) adminLimitValueAdmin.value = limitsData.global_limits.admin;
        if (supportLimitValueAdmin) supportLimitValueAdmin.value = limitsData.global_limits.support;
        if (userLimitValueAdmin) userLimitValueAdmin.value = limitsData.global_limits.user;
        
        // Отображение приглашений
        if (!invites || invites.length === 0) {
            console.log("Список приглашений пуст");
            if (adminInvitesList) adminInvitesList.innerHTML = '<p>Нет приглашений для отображения.</p>';
        } else {
            // Фильтрация по поисковому запросу
            const searchQuery = document.getElementById('admin-invites-search')?.value?.toLowerCase() || '';
            let filteredInvites = invites;
            
            if (searchQuery) {
                filteredInvites = invites.filter(invite => 
                    invite.code.toLowerCase().includes(searchQuery) || 
                    (invite.created_by && invite.created_by.username && invite.created_by.username.toLowerCase().includes(searchQuery)) ||
                    (invite.used_by && invite.used_by.toLowerCase().includes(searchQuery))
                );
            }
            
            console.log("Отфильтрованные приглашения:", filteredInvites.length);
            
            // Получаем данные только для текущей страницы
            const pageInvites = pagination.getPageData('admin-invites', filteredInvites);
            console.log("Приглашения для текущей страницы:", pageInvites.length);
            
            const tableBody = document.getElementById('admin-invites-table-body');
            console.log("Таблица найдена:", !!tableBody);
            
            if (tableBody) {
                tableBody.innerHTML = '';
                
                pageInvites.forEach(invite => {
                    console.log("Обработка приглашения:", invite);
                    const row = document.createElement('tr');
                    const status = invite.used ? 'Использован' : 'Активен';
                    
                    // Добавляем чекбокс для выбора
                    const checkboxCell = document.createElement('td');
                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.className = 'admin-invite-checkbox';
                    checkbox.dataset.inviteId = invite.id;
                    checkbox.disabled = invite.used; // Нельзя выбрать использованные инвайты
                    checkboxCell.appendChild(checkbox);
                    row.appendChild(checkboxCell);
                    
                    // Создаем ячейки данных
                    const codeCell = document.createElement('td');
                    codeCell.textContent = invite.code;
                    row.appendChild(codeCell);
                    
                    const createdCell = document.createElement('td');
                    createdCell.textContent = utils.formatDate(invite.created_at);
                    row.appendChild(createdCell);
                    
                    const expiresCell = document.createElement('td');
                    expiresCell.textContent = utils.formatDate(invite.expires_at);
                    row.appendChild(expiresCell);
                    
                    const statusCell = document.createElement('td');
                    statusCell.textContent = status;
                    row.appendChild(statusCell);
                    
                    const creatorCell = document.createElement('td');
                    // Проверяем формат поля created_by (может быть объектом или строкой)
                    if (invite.created_by && typeof invite.created_by === 'object' && invite.created_by.username) {
                        creatorCell.textContent = invite.created_by.username;
                    } else if (invite.created_by && typeof invite.created_by === 'string') {
                        creatorCell.textContent = invite.created_by;
                    } else {
                        creatorCell.textContent = 'Неизвестно';
                    }
                    row.appendChild(creatorCell);
                    
                    const usedByCell = document.createElement('td');
                    usedByCell.textContent = invite.used_by ? invite.used_by : 'Не использован';
                    row.appendChild(usedByCell);
                    
                    // Добавляем ячейку действий
                    const actionsCell = document.createElement('td');
                    const actionsDiv = document.createElement('div');
                    actionsDiv.className = 'action-buttons';
                    actionsCell.appendChild(actionsDiv);
                    
                    // Добавляем кнопку удаления
                    if (!invite.used) {
                        const deleteBtn = document.createElement('button');
                        deleteBtn.className = 'btn btn-danger btn-sm';
                        deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
                        deleteBtn.title = 'Удалить приглашение';
                        deleteBtn.addEventListener('click', async (e) => {
                            e.stopPropagation();
                            if (confirm('Вы уверены, что хотите удалить это приглашение?')) {
                                try {
                                    await api.deleteInvite(invite.id);
                                    dataCache.clearCache('invites');
                                    loadAdminInvites();
                } catch (error) {
                                    alert(`Ошибка при удалении приглашения: ${error.message}`);
                                }
                            }
                        });
                        actionsDiv.appendChild(deleteBtn);
                    }
                    
                    row.appendChild(actionsCell);
                    tableBody.appendChild(row);
                });
            }
            
            // Добавляем пагинацию
            const paginationContainer = document.getElementById('admin-invites-pagination');
            if (paginationContainer) {
                paginationContainer.innerHTML = pagination.generatePaginationHTML('admin-invites', filteredInvites.length);
                
                // Добавляем обработчики для кнопок пагинации
                document.querySelectorAll('.pagination-link[data-type="admin-invites"]').forEach(link => {
                    link.addEventListener('click', function(e) {
                        e.preventDefault();
                        const type = this.getAttribute('data-type');
                        const page = parseInt(this.getAttribute('data-page'));
                        pagination.goToPage(type, page);
                        loadAdminInvites(); // Перезагружаем с новой страницей
                    });
                });
            }
        }
    } catch (error) {
        console.error('Ошибка при загрузке приглашений в админке:', error);
        if (adminInvitesList) adminInvitesList.innerHTML = `<p class="text-danger">Ошибка при загрузке приглашений: ${error.message}</p>`;
    } finally {
        if (adminInvitesLoading) adminInvitesLoading.style.display = 'none';
        if (adminInvitesList) adminInvitesList.style.display = 'block';
    }
}

// Функция для настройки обработчиков событий в админ-панели
function setupAdminEventHandlers() {
    // Добавляем обработчик для формы управления лимитами приглашений в админке
    const setInviteLimitsFormAdmin = document.getElementById('set-invite-limits-form-admin');
    if (setInviteLimitsFormAdmin) {
        window.appLogger.logInfo('Найдена форма лимитов админа');
        setInviteLimitsFormAdmin.addEventListener('submit', async (e) => {
            window.appLogger.logInfo('Отправлена форма лимитов приглашений в админ-панели');
            e.preventDefault();
            
            const adminLimit = document.getElementById('admin-limit-value-admin').value;
            const supportLimit = document.getElementById('support-limit-value-admin').value;
            const userLimit = document.getElementById('user-limit-value-admin').value;
            
            window.appLogger.logInfo('Значения лимитов', {adminLimit, supportLimit, userLimit});
            
            const errorElement = document.getElementById('set-limits-error-admin');
            const successElement = document.getElementById('set-limits-success-admin');
            
            if (errorElement) errorElement.style.display = 'none';
            if (successElement) successElement.style.display = 'none';
            
            const saveButton = setInviteLimitsFormAdmin.querySelector('button[type="submit"]');
            if (saveButton) {
                saveButton.disabled = true;
                saveButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Сохранение...';
            }
                
            try {
                window.appLogger.logInfo('Вызов API для установки лимитов приглашений');
                const result = await api.setInviteLimits(adminLimit, supportLimit, userLimit);
                window.appLogger.logInfo('Результат установки лимитов', result);
                
                dataCache.clearCache('inviteLimits');
                
                if (successElement) successElement.style.display = 'block';
                utils.showNotification('success', 'Лимиты приглашений успешно обновлены');
                
                // Обновляем также данные в обычной вкладке приглашений
                const mainAdminLimit = document.getElementById('admin-limit-value');
                const mainSupportLimit = document.getElementById('support-limit-value');
                const mainUserLimit = document.getElementById('user-limit-value');
                
                if (mainAdminLimit) mainAdminLimit.value = adminLimit;
                if (mainSupportLimit) mainSupportLimit.value = supportLimit;
                if (mainUserLimit) mainUserLimit.value = userLimit;
                
                // Перезагружаем данные инвайтов
                await loadAdminInvites();
            } catch (error) {
                window.appLogger.logError('Ошибка при установке лимитов приглашений', error);
                if (errorElement) {
                    errorElement.textContent = `Ошибка: ${error.message}`;
                    errorElement.style.display = 'block';
                }
                utils.showNotification('danger', `Ошибка при установке лимитов: ${error.message}`);
            } finally {
                if (saveButton) {
                    saveButton.disabled = false;
                    saveButton.innerHTML = 'Сохранить';
                }
            }
        });
    } else {
        window.appLogger.logError('Не найдена форма с ID set-invite-limits-form-admin');
    }
    
    // Обработчик для кнопки создания приглашения в админке
    const adminGenerateInviteButton = document.getElementById('admin-generate-invite-button');
    if (adminGenerateInviteButton) {
        adminGenerateInviteButton.addEventListener('click', async () => {
            window.appLogger.logInfo('Нажата кнопка создания приглашения в админ-панели');
            
            adminGenerateInviteButton.disabled = true;
            adminGenerateInviteButton.textContent = 'Создание...';
            
            try {
                window.appLogger.logInfo('Вызов функции generateInvite()');
                await generateInvite();
                window.appLogger.logInfo('Приглашение успешно создано');
            } catch (error) {
                window.appLogger.logError('Ошибка создания приглашения в админ-панели', error);
                utils.showNotification('danger', `Ошибка создания приглашения: ${error.message || 'неизвестная ошибка'}`);
            } finally {
                adminGenerateInviteButton.disabled = false;
                adminGenerateInviteButton.textContent = 'Создать приглашение';
            }
        });
    }
    
    // Обработчик для выбора всех приглашений в админке
    const selectAllAdminInvites = document.getElementById('select-all-admin-invites');
    if (selectAllAdminInvites) {
        selectAllAdminInvites.addEventListener('change', () => {
            const checkboxes = document.querySelectorAll('.admin-invite-checkbox:not(:disabled)');
            checkboxes.forEach(checkbox => {
                checkbox.checked = selectAllAdminInvites.checked;
            });
        });
    }
    
    // Обработчик для удаления выбранных приглашений в админке
    const adminDeleteSelectedInvitesButton = document.getElementById('admin-delete-selected-invites-button');
    if (adminDeleteSelectedInvitesButton) {
        adminDeleteSelectedInvitesButton.addEventListener('click', async () => {
            const selectedInviteIds = getSelectedAdminInviteIds();
            
            if (selectedInviteIds.length === 0) {
                alert('Выберите приглашения для удаления');
                return;
            }
            
            if (confirm(`Вы уверены, что хотите удалить ${selectedInviteIds.length} приглашений?`)) {
                try {
                    window.appLogger.logInfo(`Удаление выбранных приглашений (${selectedInviteIds.length})`);
                    adminDeleteSelectedInvitesButton.disabled = true;
                    adminDeleteSelectedInvitesButton.textContent = 'Удаление...';
                    
                    await api.deleteMultipleInvites(selectedInviteIds);
                    window.appLogger.logInfo(`Удалено ${selectedInviteIds.length} приглашений`);
                    
                    dataCache.clearCache('invites');
                    loadAdminInvites();
                } catch (error) {
                    window.appLogger.logError(`Ошибка при удалении приглашений: ${error.message}`, error);
                    alert(`Ошибка при удалении приглашений: ${error.message}`);
                } finally {
                    adminDeleteSelectedInvitesButton.disabled = false;
                    adminDeleteSelectedInvitesButton.textContent = 'Удалить выбранные';
                }
            }
        });
    }
    
    // Обработчик поиска приглашений в админке
    const adminInvitesSearch = document.getElementById('admin-invites-search');
    if (adminInvitesSearch) {
        adminInvitesSearch.addEventListener('input', debounce(() => {
            loadAdminInvites();
        }, 300));
    }
    
    // Обработчик экспорта списка приглашений в админке
    const exportAdminInvitesBtn = document.getElementById('export-admin-invites-btn');
    if (exportAdminInvitesBtn) {
        exportAdminInvitesBtn.addEventListener('click', () => {
            exportTableToCSV('admin-invites-table', 'Приглашения.csv');
        });
    }
}

// Функция для получения ID выбранных приглашений в админке
function getSelectedAdminInviteIds() {
    const checkboxes = document.querySelectorAll('.admin-invite-checkbox:checked');
    return Array.from(checkboxes).map(checkbox => checkbox.dataset.inviteId);
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
    const allKeysLoading = document.getElementById('all-keys-loading');
    const allKeysList = document.getElementById('all-keys-list');
    
    if (allKeysLoading) allKeysLoading.style.display = 'block';
    if (allKeysList) allKeysList.style.display = 'none';
    
    try {
        let keysData;
        
        // Очищаем кэш для гарантии актуальности данных
        dataCache.clearCache('allKeys');
        
        console.log("Запрашиваем данные всех ключей...");
            keysData = await api.getAllKeys();
        console.log("Получены данные ключей:", keysData);
        
        // Проверяем правильность формата данных
        if (!keysData || !keysData.keys) {
            console.error("Получены некорректные данные:", keysData);
            throw new Error("Неверный формат данных от API");
        }
        
        dataCache.updateCache('allKeys', keysData.keys);
        
        const keys = keysData.keys;
        const tableBody = document.getElementById('all-keys-table-body');
        if (!tableBody) {
            console.error("Не найден элемент таблицы all-keys-table-body");
            throw new Error("Элемент таблицы не найден");
        }
        
        tableBody.innerHTML = '';
        
        // Фильтрация по поисковому запросу
        const searchQuery = document.getElementById('all-keys-search')?.value?.toLowerCase() || '';
        let filteredKeys = keys;
        
        if (searchQuery) {
            filteredKeys = keys.filter(key => 
                key.key.toLowerCase().includes(searchQuery) || 
                (key.user && key.user.username.toLowerCase().includes(searchQuery))
            );
        }
        
        // Получаем данные только для текущей страницы
        const pageKeys = pagination.getPageData('allKeys', filteredKeys);
        
        pageKeys.forEach(key => {
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
        
        // Добавляем пагинацию
        const paginationContainer = document.getElementById('all-keys-pagination');
        if (paginationContainer) {
            paginationContainer.innerHTML = pagination.generatePaginationHTML('allKeys', filteredKeys.length);
            
            // Добавляем обработчики для кнопок пагинации
            document.querySelectorAll('.pagination-link[data-type="allKeys"]').forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    const type = this.getAttribute('data-type');
                    const page = parseInt(this.getAttribute('data-page'));
                    pagination.goToPage(type, page);
                    loadAllKeys(); // Перезагружаем с новой страницей
                });
            });
        }
        
        // Добавляем обработчики для кнопок отзыва ключей
        document.querySelectorAll('.revoke-key-btn').forEach(button => {
            button.addEventListener('click', async () => {
                const keyId = button.getAttribute('data-id');
                if (confirm('Вы уверены, что хотите отозвать этот ключ?')) {
                    try {
                        button.disabled = true;
                        button.textContent = 'Отзыв...';
                        
                        await api.revokeKey(keyId);
                        dataCache.clearCache('allKeys'); // Очищаем кэш
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
                        dataCache.clearCache('allKeys'); // Очищаем кэш
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
        if (selectAllCheckbox) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.addEventListener('change', () => {
            const isChecked = selectAllCheckbox.checked;
            document.querySelectorAll('.key-checkbox').forEach(checkbox => {
                checkbox.checked = isChecked;
            });
        });
        }
        
        if (allKeysList) allKeysList.style.display = 'block';
        
                } catch (error) {
        console.error('Ошибка при загрузке ключей:', error);
        const allKeysError = document.createElement('div');
        allKeysError.className = 'alert alert-danger';
        allKeysError.textContent = `Ошибка при загрузке ключей: ${error.message}`;
        
        if (allKeysList) {
            allKeysList.innerHTML = '';
            allKeysList.appendChild(allKeysError);
            allKeysList.style.display = 'block';
        }
    } finally {
        if (allKeysLoading) allKeysLoading.style.display = 'none';
    }
}

// Вспомогательная функция для получения ID выбранных ключей
function getSelectedKeyIds() {
    const selectedCheckboxes = document.querySelectorAll('.key-checkbox:checked');
    return Array.from(selectedCheckboxes).map(checkbox => parseInt(checkbox.getAttribute('data-id')));
}

// Утилиты для работы с темой
const themeUtils = {
    // Проверяем предпочтительную тему пользователя
    getPreferredTheme: function() {
        try {
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme) {
                return savedTheme;
            }
            
            // Проверяем системные настройки
            return window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
        } catch (error) {
            console.error('Error getting preferred theme:', error);
            return 'dark'; // Дефолтная тема при ошибке
        }
    },
    
    // Устанавливаем тему
    setTheme: function(theme) {
        try {
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
            
            // Обновляем иконку
            const themeIcon = document.querySelector('.theme-icon i');
            const themeCheckbox = document.getElementById('theme-checkbox');
            
            if (theme === 'light') {
                if (themeIcon) themeIcon.className = 'fas fa-sun';
                if (themeCheckbox) themeCheckbox.checked = true;
            } else {
                if (themeIcon) themeIcon.className = 'fas fa-moon';
                if (themeCheckbox) themeCheckbox.checked = false;
            }
            
            console.log('Theme set to:', theme);
        } catch (error) {
            console.error('Error setting theme:', error);
        }
    },
    
    // Переключение темы
    toggleTheme: function() {
        try {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            this.setTheme(newTheme);
            console.log('Theme toggled to:', newTheme);
        } catch (error) {
            console.error('Error toggling theme:', error);
        }
    },
    
    // Инициализация
    init: function() {
        try {
            console.log('Initializing theme system...');
            
            // Устанавливаем начальную тему
            const preferredTheme = this.getPreferredTheme();
            this.setTheme(preferredTheme);
            
            // Настраиваем обработчик переключения
            const themeCheckbox = document.getElementById('theme-checkbox');
            if (themeCheckbox) {
                themeCheckbox.addEventListener('change', () => {
                    this.toggleTheme();
                });
                console.log('Theme toggle handler set up');
            } else {
                console.warn('Theme checkbox element not found');
            }
            
            console.log('Theme system initialized with theme:', preferredTheme);
        } catch (error) {
            console.error('Error initializing theme system:', error);
        }
    }
};

// Многоязычность
const i18n = {
    // Доступные языки
    languages: {
        'ru': 'Русский',
        'en': 'English'
    },
    
    // Текущий язык
    currentLang: 'ru',
    
    // Словари переводов
    translations: {
        'ru': {
            // Общие
            'app_name': 'ZalypaSPB',
            'login': 'Вход',
            'register': 'Регистрация',
            'logout': 'Выход',
            'home': 'Главная',
            'keys': 'Ключи',
            'invites': 'Приглашения',
            'discord': 'Discord',
            'admin': 'Админ-панель',
            'loading': 'Загрузка...',
            'save': 'Сохранить',
            'cancel': 'Отмена',
            'delete': 'Удалить',
            'action_success': 'Операция выполнена успешно',
            'action_error': 'Ошибка при выполнении операции',
            'confirm_action': 'Вы уверены, что хотите выполнить это действие?',
            'yes': 'Да',
            'no': 'Нет',
            'search': 'Поиск',
            'export': 'Экспорт',
            'columns': 'Колонки',
            
            // Пользователи
            'username': 'Имя пользователя',
            'email': 'Email',
            'password': 'Пароль',
            'confirm_password': 'Подтвердите пароль',
            'role': 'Роль',
            'status': 'Статус',
            'last_login': 'Последний вход',
            'ip_address': 'IP-адрес',
            'actions': 'Действия',
            'ban': 'Блокировать',
            'unban': 'Разблокировать',
            'banned': 'Заблокирован',
            'active': 'Активен',
            'admin_role': 'Администратор',
            'support_role': 'Поддержка',
            'user_role': 'Пользователь',
            'make_admin': 'Сделать администратором',
            'make_support': 'Сделать саппортом',
            'make_user': 'Сделать пользователем',
            'user_list': 'Список пользователей',
            'discord_status': 'Discord',
            'not_linked': 'Не привязан',
            
            // Ключи
            'key': 'Ключ',
            'created_at': 'Создан',
            'expires_at': 'Истекает',
            'time_left': 'Осталось',
            'owner': 'Владелец',
            'not_assigned': 'Не привязан',
            'active_keys': 'Активные ключи',
            'all_keys': 'Все ключи',
            'revoke': 'Отозвать',
            'restore': 'Восстановить',
            'revoke_selected': 'Отозвать выбранные',
            'restore_selected': 'Восстановить выбранные',
            'delete_selected': 'Удалить выбранные',
            'generate_key': 'Сгенерировать ключ',
            'select_all': 'Выбрать все',
            'no_keys': 'У вас нет активных ключей',
            
            // Приглашения
            'code': 'Код',
            'creator': 'Создатель',
            'used_by': 'Использован',
            'not_used': 'Не использован',
            'my_invites': 'Мои приглашения',
            'generate_invite': 'Создать приглашение',
            'invite_limits': 'Лимиты приглашений',
            'monthly_limit': 'Ежемесячный лимит',
            'used_invites': 'Использовано приглашений',
            'remaining_invites': 'Осталось приглашений',
            'admin_invite_limits': 'Управление лимитами',
            'admin_limit': 'Лимит для админов',
            'support_limit': 'Лимит для саппортов',
            'user_limit': 'Лимит для пользователей',
            'no_invites': 'У вас нет приглашений',
            
            // Discord
            'discord_integration': 'Интеграция с Discord',
            'discord_instructions': 'Чтобы привязать аккаунт Discord, используйте команду в нашем боте:',
            'discord_code': 'Ваш код привязки',
            'discord_linked': 'Ваш аккаунт Discord успешно привязан',
            'discord_username': 'Имя пользователя Discord',
            'discord_commands': 'Команды бота',
            'discord_command': 'Команда',
            'discord_description': 'Описание',
            
            // Ошибки
            'error_login': 'Ошибка входа. Проверьте имя пользователя и пароль.',
            'error_register': 'Ошибка регистрации',
            'error_empty_fields': 'Пожалуйста, заполните все поля',
            'error_passwords_match': 'Пароли не совпадают',
            'error_server': 'Ошибка сервера. Повторите попытку позже.',
            
            // Сообщения проверки пароля
            'password_too_short': 'Пароль должен содержать не менее 8 символов',
            'password_weak': 'Слабый пароль',
            'password_medium': 'Средний пароль',
            'password_strong': 'Надежный пароль',
            'password_too_weak': 'Пароль слишком слабый. Используйте буквы, цифры и специальные символы',
            'register_success': 'Регистрация прошла успешно!',
            'error_validation': 'Ошибка валидации данных',
            'error_unexpected': 'Произошла непредвиденная ошибка',
            'error_access_denied': 'Доступ запрещен',
        },
        'en': {
            // General
            'app_name': 'ZalypaSPB',
            'login': 'Login',
            'register': 'Register',
            'logout': 'Logout',
            'home': 'Home',
            'keys': 'Keys',
            'invites': 'Invites',
            'discord': 'Discord',
            'admin': 'Admin Panel',
            'loading': 'Loading...',
            'save': 'Save',
            'cancel': 'Cancel',
            'delete': 'Delete',
            'action_success': 'Operation completed successfully',
            'action_error': 'Error performing operation',
            'confirm_action': 'Are you sure you want to perform this action?',
            'yes': 'Yes',
            'no': 'No',
            'search': 'Search',
            'export': 'Export',
            'columns': 'Columns',
            
            // Users
            'username': 'Username',
            'email': 'Email',
            'password': 'Password',
            'confirm_password': 'Confirm Password',
            'role': 'Role',
            'status': 'Status',
            'last_login': 'Last Login',
            'ip_address': 'IP Address',
            'actions': 'Actions',
            'ban': 'Ban',
            'unban': 'Unban',
            'banned': 'Banned',
            'active': 'Active',
            'admin_role': 'Administrator',
            'support_role': 'Support',
            'user_role': 'User',
            'make_admin': 'Make Admin',
            'make_support': 'Make Support',
            'make_user': 'Make User',
            'user_list': 'User List',
            'discord_status': 'Discord',
            'not_linked': 'Not Linked',
            
            // Keys
            'key': 'Key',
            'created_at': 'Created',
            'expires_at': 'Expires',
            'time_left': 'Time Left',
            'owner': 'Owner',
            'not_assigned': 'Not Assigned',
            'active_keys': 'Active Keys',
            'all_keys': 'All Keys',
            'revoke': 'Revoke',
            'restore': 'Restore',
            'revoke_selected': 'Revoke Selected',
            'restore_selected': 'Restore Selected',
            'delete_selected': 'Delete Selected',
            'generate_key': 'Generate Key',
            'select_all': 'Select All',
            'no_keys': 'You have no active keys',
            
            // Invites
            'code': 'Code',
            'creator': 'Creator',
            'used_by': 'Used By',
            'not_used': 'Not Used',
            'my_invites': 'My Invites',
            'generate_invite': 'Generate Invite',
            'invite_limits': 'Invite Limits',
            'monthly_limit': 'Monthly Limit',
            'used_invites': 'Used Invites',
            'remaining_invites': 'Remaining Invites',
            'admin_invite_limits': 'Manage Limits',
            'admin_limit': 'Admin Limit',
            'support_limit': 'Support Limit',
            'user_limit': 'User Limit',
            'no_invites': 'You have no invites',
            
            // Discord
            'discord_integration': 'Discord Integration',
            'discord_instructions': 'To link your Discord account, use the command in our bot:',
            'discord_code': 'Your link code',
            'discord_linked': 'Your Discord account is successfully linked',
            'discord_username': 'Discord Username',
            'discord_commands': 'Bot Commands',
            'discord_command': 'Command',
            'discord_description': 'Description',
            
            // Errors
            'error_login': 'Login error. Check your username and password.',
            'error_register': 'Registration error',
            'error_empty_fields': 'Please fill all fields',
            'error_passwords_match': 'Passwords do not match',
            'error_server': 'Server error. Please try again later.',
            
            // Password check messages
            'password_too_short': 'Password must be at least 8 characters long',
            'password_weak': 'Weak password',
            'password_medium': 'Medium password',
            'password_strong': 'Strong password',
            'password_too_weak': 'Password is too weak. Use letters, numbers and special characters',
            'register_success': 'Registration successful!',
            'error_validation': 'Data validation error',
            'error_unexpected': 'An unexpected error occurred',
            'error_access_denied': 'Access denied',
        }
    },
    
    // Получение перевода
    get: function(key) {
        try {
            if (this.translations[this.currentLang] && this.translations[this.currentLang][key]) {
                return this.translations[this.currentLang][key];
            }
            
            // Если перевод не найден, возвращаем ключ
            return key;
        } catch (error) {
            console.error('Error getting translation for key:', key, error);
            return key;
        }
    },
    
    // Установка языка
    setLanguage: function(lang) {
        try {
            if (this.languages[lang]) {
                console.log('Setting language to:', lang);
                this.currentLang = lang;
                localStorage.setItem('language', lang);
                this.updatePageText();
                console.log('Language set to:', lang);
            }
        } catch (error) {
            console.error('Error setting language:', error);
        }
    },
    
    // Добавление переключателя языка
    addLanguageSwitcher: function() {
        try {
            const navbar = document.querySelector('.navbar-nav');
            if (!navbar) {
                console.warn('Navbar not found, cannot add language switcher');
                return;
            }
            
            const langDropdown = document.createElement('div');
            langDropdown.className = 'nav-item dropdown ml-2';
            langDropdown.innerHTML = `
                <a class="nav-link dropdown-toggle" href="#" id="langDropdown" role="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                    ${this.languages[this.currentLang]}
                </a>
                <div class="dropdown-menu dropdown-menu-right" aria-labelledby="langDropdown">
                    ${Object.entries(this.languages).map(([code, name]) => 
                        `<a class="dropdown-item lang-option" data-lang="${code}" href="#">${name}</a>`
                    ).join('')}
                </div>
            `;
            
            navbar.appendChild(langDropdown);
            
            // Обработчики событий
            document.querySelectorAll('.lang-option').forEach(option => {
                option.addEventListener('click', (e) => {
                    e.preventDefault();
                    const lang = option.getAttribute('data-lang');
                    this.setLanguage(lang);
                    
                    const langDropdownEl = document.getElementById('langDropdown');
                    if (langDropdownEl) {
                        langDropdownEl.textContent = this.languages[lang];
                    }
                });
            });
            
            console.log('Language switcher added');
        } catch (error) {
            console.error('Error adding language switcher:', error);
        }
    },
    
    // Обновление текста на странице
    updatePageText: function() {
        try {
            console.log('Updating page text for language:', this.currentLang);
            
            // Обновляем все элементы с атрибутом data-i18n
            document.querySelectorAll('[data-i18n]').forEach(element => {
                try {
                    const key = element.getAttribute('data-i18n');
                    element.textContent = this.get(key);
                } catch (e) {
                    console.error('Error updating element with key:', key, e);
                }
            });
            
            // Обновляем плейсхолдеры в инпутах
            document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
                try {
                    const key = element.getAttribute('data-i18n-placeholder');
                    element.placeholder = this.get(key);
                } catch (e) {
                    console.error('Error updating placeholder with key:', key, e);
                }
            });
            
            // Обновляем заголовок страницы
            document.title = this.get('app_name');
            
            console.log('Page text updated');
        } catch (error) {
            console.error('Error updating page text:', error);
        }
    },
    
    // Инициализация
    init: function() {
        try {
            console.log('Initializing i18n system...');
            
            // Загружаем сохраненный язык
            const savedLang = localStorage.getItem('language');
            if (savedLang && this.languages[savedLang]) {
                this.currentLang = savedLang;
            } else {
                // Определяем язык по браузеру
                const browserLang = navigator.language.split('-')[0];
                this.currentLang = this.languages[browserLang] ? browserLang : 'ru';
            }
            
            // Добавляем переключатель языка
            this.addLanguageSwitcher();
            
            // Обновляем текст
            this.updatePageText();
            
            console.log('i18n system initialized with language:', this.currentLang);
        } catch (error) {
            console.error('Error initializing i18n system:', error);
        }
    }
};

// Функции для пользовательских настроек
async function initApp() {
    try {
        console.log("Инициализация приложения...");
        
        // Инициализируем системы
        themeUtils.init();
        i18n.init();
        
        // Показываем первое сообщение через logger после его инициализации
        window.appLogger.logInfo("Инициализация приложения...");
        
        // Настройка обработчика ошибок
        errorHandler.setupGlobalHandler();
        
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
    
        // Инициализация утилит для работы с таблицами
        tableUtils.init();
        
        // Настройка обработчиков событий
        setupEventHandlers();
        
        // Настройка обработчиков для логов
        setupLogHandlers();
        
        // Настройка обработчиков админ-панели
        setupAdminEventHandlers();
        
        window.appLogger.logInfo("Инициализация приложения завершена успешно");
    } catch (error) {
        console.error("Error during app initialization:", error);
        // Отображение ошибки пользователю
        const errorElement = document.createElement('div');
        errorElement.className = 'alert alert-danger';
        errorElement.style.position = 'fixed';
        errorElement.style.top = '10px';
        errorElement.style.left = '50%';
        errorElement.style.transform = 'translateX(-50%)';
        errorElement.style.zIndex = '9999';
        errorElement.style.maxWidth = '80%';
        errorElement.style.padding = '15px 20px';
        errorElement.style.borderRadius = '4px';
        errorElement.innerHTML = `<i class="fas fa-exclamation-circle"></i> Произошла непредвиденная ошибка: ${error.message}`;
        document.body.appendChild(errorElement);
        
        // Удаление сообщения об ошибке через 5 секунд
        setTimeout(() => {
            if (errorElement.parentNode) {
                errorElement.parentNode.removeChild(errorElement);
            }
        }, 5000);
        
        // Попытка перехода на главную страницу
        try {
            navigation.navigateTo('home');
        } catch (navError) {
            console.error("Failed to navigate to home page:", navError);
        }
    }
}

// Настройка обработчиков событий
function setupEventHandlers() {
    try {
    // Обработка навигации
    document.querySelectorAll('.navbar-nav a').forEach(link => {
        link.addEventListener('click', (e) => {
                if (link.getAttribute('href')?.startsWith('#')) {
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
        const logoutButton = document.getElementById('logout-button');
        if (logoutButton) {
            logoutButton.addEventListener('click', (e) => {
        e.preventDefault();
        auth.logout();
    });
        }
    
    // Форма входа
        const loginForm = document.getElementById('login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
                const username = document.getElementById('login-username')?.value || '';
                const password = document.getElementById('login-password')?.value || '';
                const loginError = document.getElementById('login-error');
        
                if (loginError) loginError.style.display = 'none';
        
        try {
            const result = await api.login(username, password);
            token = result.token;
            localStorage.setItem('token', token);
            
            await auth.checkAuth();
            navigation.navigateTo('home');
        } catch (error) {
                    if (loginError) {
                        loginError.textContent = error.message;
                        loginError.style.display = 'block';
                    }
                }
            });
        }
    
    // Форма регистрации
        const registerForm = document.getElementById('register-form');
        if (registerForm) {
            registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
                const username = document.getElementById('register-username')?.value || '';
                const email = document.getElementById('register-email')?.value || '';
                const password = document.getElementById('register-password')?.value || '';
                const confirmPassword = document.getElementById('register-confirm-password')?.value || '';
                const invite_code = document.getElementById('register-invite')?.value || '';
                const registerError = document.getElementById('register-error');
                
                // Проверка совпадения паролей
                if (password !== confirmPassword) {
                    if (registerError) {
                        registerError.textContent = i18n.get('error_passwords_match');
                        registerError.style.display = 'block';
                    }
                    return;
                }
                
                // Проверка сложности пароля
                const passwordStrength = secureAuth.checkPasswordStrength(password);
                if (passwordStrength.score < 2) {
                    if (registerError) {
                        registerError.textContent = i18n.get('password_too_weak');
                        registerError.style.display = 'block';
                    }
                    return;
                }
                
                if (registerError) registerError.style.display = 'none';
                
                try {
                    const registerButton = document.querySelector('#register-form button[type="submit"]');
                    if (registerButton) {
                        registerButton.disabled = true;
                        registerButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Регистрация...';
                    }
                    
            await api.register(username, email, password, invite_code);
                    
                    // Показываем уведомление об успешной регистрации
                    notifications.show(i18n.get('register_success'), 'success');
            
            // Автоматический вход после регистрации
            const loginResult = await api.login(username, password);
            token = loginResult.token;
            localStorage.setItem('token', token);
            
            await auth.checkAuth();
            navigation.navigateTo('keys');
        } catch (error) {
                    if (registerError) {
                        registerError.textContent = error.message;
                        registerError.style.display = 'block';
                    }
                } finally {
                    const registerButton = document.querySelector('#register-form button[type="submit"]');
                    if (registerButton) {
                        registerButton.disabled = false;
                        registerButton.textContent = 'Зарегистрироваться';
                    }
                }
            });
        }
        
        // Проверка надежности пароля при вводе
        const passwordField = document.getElementById('register-password');
        if (passwordField) {
            passwordField.addEventListener('input', function() {
                secureAuth.showPasswordStrength(this.value, 'password-strength');
            });
        }
    
    // Форма активации ключа
        const redeemKeyForm = document.getElementById('redeem-key-form');
        if (redeemKeyForm) {
            redeemKeyForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
                const key = document.getElementById('redeem-key')?.value || '';
                const redeemError = document.getElementById('redeem-error');
                const redeemSuccess = document.getElementById('redeem-success');
        
                if (redeemError) redeemError.style.display = 'none';
                if (redeemSuccess) redeemSuccess.style.display = 'none';
        
        try {
            await api.redeemKey(key);
            
                    if (redeemSuccess) redeemSuccess.style.display = 'block';
                    const keyField = document.getElementById('redeem-key');
                    if (keyField) keyField.value = '';
            
            // Обновление списка ключей
            loadKeys();
        } catch (error) {
                    if (redeemError) {
                        redeemError.textContent = error.message;
                        redeemError.style.display = 'block';
                    }
                }
            });
        }
    
    // Кнопка создания приглашения
        const generateInviteButton = document.getElementById('generate-invite-button');
        if (generateInviteButton) {
            generateInviteButton.addEventListener('click', async () => {
            const button = generateInviteButton;
                if (button) {
        button.disabled = true;
        button.textContent = 'Создание...';
                }
        
        try {
                await generateInvite();
        } catch (error) {
                utils.showNotification('danger', `Ошибка создания приглашения: ${error.message}`);
        } finally {
                    if (button) {
            button.disabled = false;
            button.textContent = 'Создать приглашение';
                    }
        }
    });
        }
    
    // Форма установки лимитов приглашений
        const setInviteLimitsForm = document.getElementById('set-invite-limits-form');
        if (setInviteLimitsForm) {
            setInviteLimitsForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
                const adminLimit = parseInt(document.getElementById('admin-limit-value')?.value || '0');
                const supportLimit = parseInt(document.getElementById('support-limit-value')?.value || '0');
                const userLimit = parseInt(document.getElementById('user-limit-value')?.value || '0');
                
                const setLimitsError = document.getElementById('set-limits-error');
                const setLimitsSuccess = document.getElementById('set-limits-success');
                
                if (setLimitsError) setLimitsError.style.display = 'none';
                if (setLimitsSuccess) setLimitsSuccess.style.display = 'none';
        
        try {
            await api.setInviteLimits(adminLimit, supportLimit, userLimit);
                    if (setLimitsSuccess) setLimitsSuccess.style.display = 'block';
            
            // Перезагрузка данных
            dataCache.clearCache('inviteLimits');
            setTimeout(() => {
                loadInvites();
            }, 2000);
            
            // Синхронизируем значения с формой в административной панели
            const adminLimitAdmin = document.getElementById('admin-limit-value-admin');
            const supportLimitAdmin = document.getElementById('support-limit-value-admin');
            const userLimitAdmin = document.getElementById('user-limit-value-admin');
            
            if (adminLimitAdmin) adminLimitAdmin.value = adminLimit;
            if (supportLimitAdmin) supportLimitAdmin.value = supportLimit;
            if (userLimitAdmin) userLimitAdmin.value = userLimit;
        } catch (error) {
                    if (setLimitsError) {
                        setLimitsError.textContent = error.message;
                        setLimitsError.style.display = 'block';
                    }
                }
            });
        }
    
    // Кнопка генерации кода Discord
        const generateDiscordCodeButton = document.getElementById('generate-discord-code-button');
        if (generateDiscordCodeButton) {
            generateDiscordCodeButton.addEventListener('click', async () => {
        try {
            const result = await api.generateDiscordCode();
            
                    const discordCode = document.getElementById('discord-code');
                    const discordCodeCard = document.getElementById('discord-code-card');
                    
                    if (discordCode) discordCode.textContent = result.code;
                    if (discordCodeCard) discordCodeCard.style.display = 'block';
        } catch (error) {
            alert(`Ошибка генерации кода: ${error.message}`);
        }
    });
        }
    
    // Форма генерации ключа (админ)
        const generateKeyForm = document.getElementById('generate-key-form');
        if (generateKeyForm) {
            generateKeyForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
                const duration = parseInt(document.getElementById('key-duration')?.value || '24');
                const userIdValue = document.getElementById('key-user')?.value || '';
        const userId = userIdValue ? parseInt(userIdValue) : null;
                const customKey = (document.getElementById('key-custom')?.value || '').trim();
                
                const generateKeyError = document.getElementById('generate-key-error');
                const generateKeySuccess = document.getElementById('generate-key-success');
                
                if (generateKeyError) generateKeyError.style.display = 'none';
                if (generateKeySuccess) generateKeySuccess.style.display = 'none';
        
        try {
            const result = await api.generateKey(duration, userId, customKey || null);
            
                    const generatedKey = document.getElementById('generated-key');
                    if (generatedKey) generatedKey.textContent = result.key;
                    if (generateKeySuccess) generateKeySuccess.style.display = 'block';
        } catch (error) {
                    if (generateKeyError) {
                        generateKeyError.textContent = error.message;
                        generateKeyError.style.display = 'block';
                    }
                }
            });
        }
    } catch (error) {
        console.error("Error setting up event handlers:", error);
    }
}

// Добавляем обработчики для системы логов
function setupLogHandlers() {
    // Очистка логов
    document.getElementById('clear-logs-btn')?.addEventListener('click', () => {
        if (confirm('Вы уверены, что хотите очистить все логи?')) {
            window.appLogger.clearLogs();
        }
    });
    
    // Переключение автоскролла
    const autoScrollBtn = document.getElementById('toggle-auto-scroll-logs');
    let autoScroll = true;
    
    autoScrollBtn?.addEventListener('click', () => {
        autoScroll = !autoScroll;
        autoScrollBtn.innerHTML = autoScroll ? 
            '<i class="fas fa-scroll"></i> Авто-прокрутка: ВКЛ' : 
            '<i class="fas fa-scroll"></i> Авто-прокрутка: ВЫКЛ';
        
        if (autoScroll) {
            const logContainer = document.getElementById('admin-log-container');
            if (logContainer) {
                logContainer.scrollTop = 0; // Скролл в начало, так как логи отображаются в обратном порядке
            }
        }
    });
    
    // Фильтрация логов
    document.getElementById('filter-all-logs')?.addEventListener('click', function() {
        filterLogs('all');
        setActiveFilterButton(this);
    });
    
    document.getElementById('filter-info-logs')?.addEventListener('click', function() {
        filterLogs('info');
        setActiveFilterButton(this);
    });
    
    document.getElementById('filter-warning-logs')?.addEventListener('click', function() {
        filterLogs('warning');
        setActiveFilterButton(this);
    });
    
    document.getElementById('filter-error-logs')?.addEventListener('click', function() {
        filterLogs('danger');
        setActiveFilterButton(this);
    });
    
    // Поиск в логах
    document.getElementById('log-search')?.addEventListener('input', debounce(function() {
        filterLogs(currentLogFilter, this.value);
    }, 300));
    
    // Обработчик загрузки логов при открытии вкладки
    document.getElementById('logs-tab')?.addEventListener('click', () => {
        window.appLogger.updateLogDisplay();
    });
}

// Глобальная переменная для текущего фильтра логов
let currentLogFilter = 'all';

// Функция для установки активной кнопки фильтра
function setActiveFilterButton(buttonElement) {
    document.querySelectorAll('.btn-group button').forEach(btn => {
        btn.classList.remove('active');
    });
    buttonElement.classList.add('active');
}

// Функция для фильтрации логов
function filterLogs(type = 'all', searchText = '') {
    currentLogFilter = type;
    
    const logEntries = document.querySelectorAll('.log-entry');
    const searchLower = searchText.toLowerCase();
    
    logEntries.forEach(entry => {
        let showByType = type === 'all' || entry.classList.contains(`alert-${type}`);
        let showBySearch = !searchText || entry.textContent.toLowerCase().includes(searchLower);
        
        entry.style.display = showByType && showBySearch ? 'block' : 'none';
    });
}

// Запуск приложения при загрузке страницы
document.addEventListener('DOMContentLoaded', initApp); 

// Утилиты для экспорта данных
const exportUtils = {
    // Экспорт таблицы в CSV
    exportTableToCSV: function(tableId, filename) {
        const table = document.getElementById(tableId);
        if (!table) return;
        
        const rows = table.querySelectorAll('tr');
        let csv = [];
        
        // Получаем заголовки (исключая колонку с чекбоксами и действиями)
        const headers = Array.from(rows[0].querySelectorAll('th'))
            .filter((th, index) => {
                // Пропускаем колонки с чекбоксами и действиями
                const headerText = th.textContent.trim();
                return !th.querySelector('input[type="checkbox"]') && headerText !== 'Действия';
            })
            .map(th => `"${th.textContent.trim()}"`);
        
        csv.push(headers.join(','));
        
        // Получаем данные строк
        for (let i = 1; i < rows.length; i++) {
            const row = rows[i];
            const cols = row.querySelectorAll('td');
            
            // Пропускаем строки без данных
            if (cols.length === 0) continue;
            
            let rowData = [];
            
            // Собираем данные из ячеек (исключая колонки с чекбоксами и действиями)
            for (let j = 0; j < cols.length; j++) {
                // Пропускаем колонки с чекбоксами и действиями
                if (cols[j].querySelector('input[type="checkbox"]') || 
                    cols[j].querySelector('button') ||
                    j === cols.length - 1) {
                    continue;
                }
                
                // Очищаем текст от HTML и экранируем кавычки
                let text = cols[j].textContent.trim().replace(/"/g, '""');
                rowData.push(`"${text}"`);
            }
            
            csv.push(rowData.join(','));
        }
        
        // Скачиваем файл
        const csvContent = csv.join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    },
    
    // Настраиваем обработчики для кнопок экспорта
    setupExportHandlers: function() {
        // Экспорт списка пользователей
        document.getElementById('export-users-btn')?.addEventListener('click', () => {
            this.exportTableToCSV('users-table', 'users_export.csv');
        });
        
        // Экспорт списка всех ключей
        document.getElementById('export-all-keys-btn')?.addEventListener('click', () => {
            this.exportTableToCSV('all-keys-table', 'all_keys_export.csv');
        });
        
        // Экспорт списка приглашений
        document.getElementById('export-invites-btn')?.addEventListener('click', () => {
            this.exportTableToCSV('invites-table', 'invites_export.csv');
        });
    }
};

// Управление колонками таблиц
const tableUtils = {
    // Состояние видимости колонок для разных таблиц
    columnVisibility: {
        'users': {},
        'all-keys': {},
        'keys': {},
        'invites': {}
    },
    
    // Инициализация видимости колонок
    initColumnVisibility: function(tableId) {
        const table = document.getElementById(tableId);
        if (!table) return;
        
        const headerCells = table.querySelectorAll('thead th');
        this.columnVisibility[tableId] = {};
        
        // Устанавливаем начальное состояние (все колонки видимы)
        headerCells.forEach((cell, index) => {
            this.columnVisibility[tableId][index] = true;
        });
        
        // Проверяем сохраненное состояние
        const savedState = localStorage.getItem(`columnVisibility_${tableId}`);
        if (savedState) {
            try {
                const parsedState = JSON.parse(savedState);
                Object.assign(this.columnVisibility[tableId], parsedState);
                this.applyColumnVisibility(tableId);
            } catch (e) {
                console.error('Ошибка при загрузке состояния видимости колонок:', e);
            }
        }
    },
    
    // Применение видимости колонок
    applyColumnVisibility: function(tableId) {
        const table = document.getElementById(tableId);
        if (!table) return;
        
        const headerCells = table.querySelectorAll('thead th');
        const rows = table.querySelectorAll('tbody tr');
        
        // Применяем к заголовкам
        headerCells.forEach((cell, index) => {
            cell.style.display = this.columnVisibility[tableId][index] ? '' : 'none';
        });
        
        // Применяем к ячейкам строк
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            cells.forEach((cell, index) => {
                if (index < Object.keys(this.columnVisibility[tableId]).length) {
                    cell.style.display = this.columnVisibility[tableId][index] ? '' : 'none';
                }
            });
        });
        
        // Сохраняем состояние
        localStorage.setItem(`columnVisibility_${tableId}`, JSON.stringify(this.columnVisibility[tableId]));
    },
    
    // Переключение видимости колонки
    toggleColumn: function(tableId, columnIndex) {
        if (!this.columnVisibility[tableId]) {
            this.initColumnVisibility(tableId);
        }
        
        this.columnVisibility[tableId][columnIndex] = !this.columnVisibility[tableId][columnIndex];
        this.applyColumnVisibility(tableId);
    },
    
    // Настройка обработчиков переключения видимости колонок
    setupColumnToggleHandlers: function() {
        document.querySelectorAll('.toggle-column').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const tableId = item.getAttribute('data-table');
                const columnIndex = parseInt(item.getAttribute('data-column'));
                this.toggleColumn(tableId, columnIndex);
            });
        });
    },
    
    // Обработчик поиска в реальном времени
    setupSearchHandlers: function() {
        // Поиск пользователей
        document.getElementById('users-search')?.addEventListener('input', debounce(() => {
            pagination.resetPage('users');
            loadAdminData();
        }, 300));
        
        // Поиск всех ключей
        document.getElementById('all-keys-search')?.addEventListener('input', debounce(() => {
            pagination.resetPage('allKeys');
            loadAllKeys();
        }, 300));
        
        // Поиск личных ключей
        document.getElementById('keys-search')?.addEventListener('input', debounce(() => {
            pagination.resetPage('keys');
            loadKeys();
        }, 300));
        
        // Поиск приглашений
        document.getElementById('invites-search')?.addEventListener('input', debounce(() => {
            pagination.resetPage('invites');
            loadInvites();
        }, 300));
    },
    
    // Инициализация всех обработчиков и видимости колонок
    init: function() {
        // Инициализация видимости колонок для всех таблиц
        ['users-table', 'all-keys-table', 'keys-table', 'invites-table'].forEach(tableId => {
            this.initColumnVisibility(tableId);
        });
        
        // Настройка обработчиков
        this.setupColumnToggleHandlers();
        this.setupSearchHandlers();
        
        // Настройка обработчиков экспорта
        exportUtils.setupExportHandlers();
    }
};

// Функция для предотвращения слишком частых вызовов (debounce)
function debounce(func, delay) {
    let timeout;
    return function() {
        const context = this;
        const args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), delay);
    };
}

// Система уведомлений
const notifications = {
    // Типы уведомлений
    types: {
        success: {
            icon: 'fa-check-circle',
            color: 'var(--success-color)',
            timeout: 5000
        },
        error: {
            icon: 'fa-exclamation-circle',
            color: 'var(--danger-color)',
            timeout: 8000
        },
        warning: {
            icon: 'fa-exclamation-triangle',
            color: '#ffc107',
            timeout: 7000
        },
        info: {
            icon: 'fa-info-circle',
            color: 'var(--primary-color)',
            timeout: 6000
        }
    },
    
    // Контейнер для уведомлений
    createContainer: function() {
        try {
            let container = document.getElementById('notification-container');
            
            if (!container) {
                container = document.createElement('div');
                container.id = 'notification-container';
                container.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 9999;
                    max-width: 350px;
                    max-height: 100vh;
                    overflow-y: auto;
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                `;
                document.body.appendChild(container);
            }
            
            return container;
        } catch (error) {
            console.error('Error creating notification container:', error);
            return null;
        }
    },
    
    // Создание уведомления
    show: function(message, type = 'info') {
        try {
            const container = this.createContainer();
            if (!container) {
                console.error('Failed to create notification container');
                return null;
            }
            
            const notifyType = this.types[type] || this.types.info;
            
            // Создаем уведомление
            const notification = document.createElement('div');
            notification.style.cssText = `
                background-color: var(--card-bg);
                color: var(--text-color);
                border-left: 5px solid ${notifyType.color};
                padding: 15px 20px;
                border-radius: 4px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
                display: flex;
                align-items: flex-start;
                transform: translateX(100%);
                transition: transform 0.3s ease;
                position: relative;
            `;
            
            // Добавляем иконку
            notification.innerHTML = `
                <i class="fas ${notifyType.icon}" style="color: ${notifyType.color}; margin-right: 10px; font-size: 1.2rem;"></i>
                <div style="flex-grow: 1">${message}</div>
                <i class="fas fa-times" style="cursor: pointer; margin-left: 10px;"></i>
            `;
            
            // Добавляем кнопку закрытия
            const closeBtn = notification.querySelector('.fa-times');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    this.close(notification);
                });
            }
            
            // Добавляем в контейнер
            container.appendChild(notification);
            
            // Анимация появления
            setTimeout(() => {
                notification.style.transform = 'translateX(0)';
            }, 10);
            
            // Автоматическое закрытие
            if (notifyType.timeout) {
                setTimeout(() => {
                    if (notification.parentNode) {
                        this.close(notification);
                    }
                }, notifyType.timeout);
            }
            
            return notification;
        } catch (error) {
            console.error('Error showing notification:', error);
            return null;
        }
    },
    
    // Закрытие уведомления
    close: function(notification) {
        try {
            if (!notification) return;
            
            notification.style.transform = 'translateX(100%)';
            notification.style.opacity = '0';
            
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        } catch (error) {
            console.error('Error closing notification:', error);
            // Принудительное удаление при ошибке
            try {
                if (notification && notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            } catch (e) {
                console.error('Failed to force remove notification:', e);
            }
        }
    }
};

// Система обработки ошибок
const errorHandler = {
    // Обработка сетевых ошибок
    handleNetworkError: function(error) {
        console.error('Network error:', error);
        window.appLogger.logError('Сетевая ошибка', error);
        
        // Показываем уведомление
        notifications.show(i18n.get('error_server'), 'error');
        
        // Проверяем, не истекла ли сессия
        if (error.status === 401) {
            window.appLogger.logWarning('Сессия истекла, выполняется выход');
            auth.logout();
            navigation.navigateTo('login');
            return;
        }
        
        // Проверяем, не отказано ли в доступе
        if (error.status === 403) {
            window.appLogger.logWarning('Доступ запрещен (403)');
            notifications.show(i18n.get('error_access_denied'), 'error');
            return;
        }
        
        // Возвращаем ошибку для дальнейшей обработки
        return error;
    },
    
    // Обработка ошибок валидации
    handleValidationError: function(error) {
        console.error('Validation error:', error);
        window.appLogger.logError('Ошибка валидации', error);
        
        if (Array.isArray(error.errors)) {
            // Показываем первую ошибку валидации
            notifications.show(error.errors[0].message, 'warning');
        } else {
            notifications.show(error.message || i18n.get('error_validation'), 'warning');
        }
    },
    
    // Глобальный обработчик необработанных ошибок
    setupGlobalHandler: function() {
        try {
            window.addEventListener('error', (event) => {
                console.error('Unhandled error:', event.error);
                window.appLogger.logError('Необработанная ошибка', {
                    message: event.error?.message,
                    stack: event.error?.stack,
                    source: event.filename,
                    line: event.lineno,
                    column: event.colno
                });
                
                try {
                    notifications.show(i18n.get('error_unexpected'), 'error');
                } catch (e) {
                    console.error('Failed to show notification:', e);
                    alert('Произошла непредвиденная ошибка');
                }
            });
            
            window.addEventListener('unhandledrejection', (event) => {
                console.error('Unhandled promise rejection:', event.reason);
                window.appLogger.logError('Необработанная ошибка в промисе', event.reason);
                
                try {
                    notifications.show(i18n.get('error_unexpected'), 'error');
                } catch (e) {
                    console.error('Failed to show notification:', e);
                    alert('Произошла непредвиденная ошибка при асинхронной операции');
                }
            });
            window.appLogger.logInfo('Глобальные обработчики ошибок установлены');
        } catch (e) {
            console.error('Failed to set up global error handlers:', e);
            window.appLogger.logError('Ошибка при установке глобальных обработчиков', e);
        }
    }
};

// Усиленная аутентификация
const secureAuth = {
    // Проверка сложности пароля
    checkPasswordStrength: function(password) {
        // Минимальная длина
        if (password.length < 8) {
            return {
                score: 0,
                message: i18n.get('password_too_short')
            };
        }
        
        let score = 0;
        
        // Наличие цифр
        if (/\d/.test(password)) score++;
        
        // Наличие строчных букв
        if (/[a-z]/.test(password)) score++;
        
        // Наличие заглавных букв
        if (/[A-Z]/.test(password)) score++;
        
        // Наличие специальных символов
        if (/[^a-zA-Z0-9]/.test(password)) score++;
        
        // Дополнительный балл за длину > 12
        if (password.length > 12) score++;
        
        // Результат
        let message;
        if (score < 2) {
            message = i18n.get('password_weak');
        } else if (score < 4) {
            message = i18n.get('password_medium');
        } else {
            message = i18n.get('password_strong');
        }
        
        return { score, message };
    },
    
    // Показ индикатора сложности пароля
    showPasswordStrength: function(password, elementId) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        const strength = this.checkPasswordStrength(password);
        
        let color;
        if (strength.score < 2) {
            color = 'var(--danger-color)';
        } else if (strength.score < 4) {
            color = '#ffc107';
        } else {
            color = 'var(--success-color)';
        }
        
        element.style.display = 'block';
        element.innerHTML = `
            <div class="progress mt-2" style="height: 5px;">
                <div class="progress-bar" role="progressbar" 
                     style="width: ${(strength.score / 5) * 100}%; background-color: ${color};" 
                     aria-valuenow="${strength.score}" aria-valuemin="0" aria-valuemax="5"></div>
            </div>
            <small class="mt-1 d-block" style="color: ${color};">${strength.message}</small>
        `;
    },
    
    // Добавление CSRF защиты
    addCSRFProtection: function(token) {
        // Добавляем токен к заголовкам всех запросов
        const originalFetch = window.fetch;
        window.fetch = function(url, options = {}) {
            options.headers = options.headers || {};
            options.headers['X-CSRF-Token'] = token;
            return originalFetch(url, options);
        };
    }
};

// Функция для отображения информации о профиле
function displayProfileInfo(userData) {
    const profileInfo = document.getElementById('profile-info');
    if (profileInfo) {
        profileInfo.innerHTML = `
            <div class="mb-3">
                <strong>Имя пользователя:</strong> ${userData.username}
            </div>
            <div class="mb-3">
                <strong>Email:</strong> ${userData.email}
            </div>
            <div class="mb-3">
                <strong>Дата регистрации:</strong> ${new Date(userData.created_at).toLocaleString()}
            </div>
            <div class="mb-3">
                <strong>Discord:</strong> ${userData.discord_linked ? userData.discord_username : 'Не привязан'}
            </div>
        `;
    }
}

// Обработчик формы изменения пароля
const changePasswordForm = document.getElementById('change-password-form');
if (changePasswordForm) {
    changePasswordForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const currentPassword = document.getElementById('current-password')?.value || '';
        const newPassword = document.getElementById('new-password')?.value || '';
        const confirmNewPassword = document.getElementById('confirm-new-password')?.value || '';
        const changePasswordError = document.getElementById('change-password-error');
        
        if (changePasswordError) changePasswordError.style.display = 'none';
        
        // Проверка совпадения паролей
        if (newPassword !== confirmNewPassword) {
            if (changePasswordError) {
                changePasswordError.textContent = i18n.get('error_passwords_match');
                changePasswordError.style.display = 'block';
            }
            return;
        }
        
        // Проверка сложности пароля
        const passwordStrength = secureAuth.checkPasswordStrength(newPassword);
        if (passwordStrength.score < 2) {
            if (changePasswordError) {
                changePasswordError.textContent = i18n.get('password_too_weak');
                changePasswordError.style.display = 'block';
            }
            return;
        }
        
        try {
            const changePasswordButton = document.querySelector('#change-password-form button[type="submit"]');
            if (changePasswordButton) {
                changePasswordButton.disabled = true;
                changePasswordButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Изменение...';
            }
            
            await api.changePassword(currentPassword, newPassword);
            
            // Показываем уведомление об успешном изменении пароля
            notifications.show('Пароль успешно изменен', 'success');
            
            // Очищаем форму
            changePasswordForm.reset();
            
        } catch (error) {
            if (changePasswordError) {
                changePasswordError.textContent = error.message;
                changePasswordError.style.display = 'block';
            }
        } finally {
            const changePasswordButton = document.querySelector('#change-password-form button[type="submit"]');
            if (changePasswordButton) {
                changePasswordButton.disabled = false;
                changePasswordButton.textContent = 'Изменить пароль';
            }
        }
    });
}

// Проверка надежности нового пароля при вводе
const newPasswordField = document.getElementById('new-password');
if (newPasswordField) {
    newPasswordField.addEventListener('input', function() {
        secureAuth.showPasswordStrength(this.value, 'new-password-strength');
    });
}

// ... existing code ... 

// Функция setupEventHandlers
const usernameDisplay = document.getElementById('username-display');
if (usernameDisplay) {
    usernameDisplay.addEventListener('click', (e) => {
        e.preventDefault();
        navigation.navigateTo('profile');
    });
}
// ... existing code ... 

// ... existing code ...
row.addEventListener('click', function(e) {
    if (e.target.tagName === 'BUTTON' || e.target.closest('.action-buttons')) return;
    document.querySelectorAll('#users-table tbody tr').forEach(r => r.classList.remove('active-row'));
    row.classList.toggle('active-row');
});
// ... existing code ...

// Добавим функцию showChangePasswordModal
function showChangePasswordModal(userId, username) {
    // Удаляем старое модальное окно если есть
    document.getElementById('admin-change-password-modal')?.remove();
    const modal = document.createElement('div');
    modal.id = 'admin-change-password-modal';
    modal.innerHTML = `
    <div class="modal fade show" tabindex="-1" style="display:block; background:rgba(0,0,0,0.5);">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Смена пароля для пользователя: ${username}</h5>
            <button type="button" class="close" id="close-admin-change-password-modal">&times;</button>
          </div>
          <div class="modal-body">
            <input type="password" class="form-control mb-2" id="admin-new-password" placeholder="Новый пароль">
            <input type="password" class="form-control mb-2" id="admin-confirm-password" placeholder="Подтвердите пароль">
            <div class="alert alert-danger" id="admin-change-password-error" style="display:none"></div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="close-admin-change-password-modal2">Отмена</button>
            <button class="btn btn-primary" id="admin-change-password-submit">Сменить</button>
          </div>
        </div>
      </div>
    </div>`;
    document.body.appendChild(modal);
    // Закрытие
    const closeModal = () => modal.remove();
    document.getElementById('close-admin-change-password-modal').onclick = closeModal;
    document.getElementById('close-admin-change-password-modal2').onclick = closeModal;
    // Сабмит
    document.getElementById('admin-change-password-submit').onclick = async () => {
        const newPassword = document.getElementById('admin-new-password').value;
        const confirmPassword = document.getElementById('admin-confirm-password').value;
        const errorDiv = document.getElementById('admin-change-password-error');
        errorDiv.style.display = 'none';
        if (newPassword !== confirmPassword) {
            errorDiv.textContent = 'Пароли не совпадают';
            errorDiv.style.display = 'block';
            return;
        }
        if (newPassword.length < 8) {
            errorDiv.textContent = 'Пароль слишком короткий';
            errorDiv.style.display = 'block';
            return;
        }
        try {
            await api.adminChangeUserPassword(userId, newPassword);
            notifications.show('Пароль успешно изменён', 'success');
            closeModal();
        } catch (e) {
            errorDiv.textContent = e.message;
            errorDiv.style.display = 'block';
        }
    };
}

// Обработчики переключения вкладок администратора
document.querySelector('#all-keys-tab')?.addEventListener('click', loadAllKeys);
document.querySelector('#invites-admin-tab')?.addEventListener('click', () => {
    // Загружаем данные приглашений при открытии вкладки ПриглОчки
    loadAdminInvites();
    
    // Синхронизируем значения лимитов из основной формы, если они уже заполнены
    if (dataCache.inviteLimits) {
        const adminLimitAdmin = document.getElementById('admin-limit-value-admin');
        const supportLimitAdmin = document.getElementById('support-limit-value-admin');
        const userLimitAdmin = document.getElementById('user-limit-value-admin');
        
        if (adminLimitAdmin) adminLimitAdmin.value = dataCache.inviteLimits.global_limits.admin;
        if (supportLimitAdmin) supportLimitAdmin.value = dataCache.inviteLimits.global_limits.support;
        if (userLimitAdmin) userLimitAdmin.value = dataCache.inviteLimits.global_limits.user;
    }
});

// Обработчик поиска ключей