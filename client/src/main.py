import sys
import os
import time
import json
import threading
import shutil
import tempfile
import requests
import subprocess
import atexit
import signal
import datetime
import psutil
import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QTabWidget, QProgressBar, QMessageBox, QFileDialog,
                            QTextEdit, QListWidget, QListWidgetItem, QGroupBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer, QSize, QSettings
from PyQt5.QtGui import QIcon, QPixmap, QFont, QColor, QPalette

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("loader.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Константы
API_URL = "http://localhost:5000/api"  # По умолчанию, можно изменить в config.json
VERSION = "1.0.0"
CONFIG_FILE = "config.json"
MINECRAFT_DIR = os.path.join(os.getenv('APPDATA'), '.minecraft')

# Временная директория для загрузки файлов
TEMP_DIR = tempfile.mkdtemp()
logger.info(f"Создана временная директория: {TEMP_DIR}")

# Список файлов для удаления при закрытии
files_to_delete = []

# Функция для загрузки конфигурации
def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            
            global API_URL
            API_URL = config.get('api_url', API_URL)
            
            logger.info(f"Загружена конфигурация: API_URL={API_URL}")
            return config
        else:
            logger.warning(f"Файл конфигурации {CONFIG_FILE} не найден. Используются значения по умолчанию.")
            return {'api_url': API_URL, 'version': VERSION}
    except Exception as e:
        logger.error(f"Ошибка при загрузке конфигурации: {e}")
        return {'api_url': API_URL, 'version': VERSION}

# Загрузка конфигурации при запуске
config = load_config()

# Функция для очистки временных файлов при закрытии
def cleanup():
    logger.info("Удаление временных файлов...")
    
    # Удаление всех файлов из списка на удаление
    for file_path in files_to_delete:
        try:
            if os.path.exists(file_path):
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
                logger.info(f"Удален файл: {file_path}")
        except Exception as e:
            logger.error(f"Ошибка при удалении файла {file_path}: {e}")
    
    # Удаление временной директории
    try:
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
            logger.info(f"Удалена временная директория: {TEMP_DIR}")
    except Exception as e:
        logger.error(f"Ошибка при удалении временной директории: {e}")

# Регистрация функции очистки при выходе
atexit.register(cleanup)

# Класс для проверки ключа
class KeyVerifier(QObject):
    result_signal = pyqtSignal(dict)
    
    def __init__(self, key):
        super().__init__()
        self.key = key
    
    def verify(self):
        try:
            response = requests.post(f"{API_URL}/keys/verify", json={"key": self.key})
            result = response.json()
            logger.info(f"Результат проверки ключа: {result}")
            self.result_signal.emit(result)
        except Exception as e:
            logger.error(f"Ошибка при проверке ключа: {e}")
            self.result_signal.emit({"valid": False, "message": str(e)})

# Класс для загрузки файлов
class FileDownloader(QObject):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, url, key, destination):
        super().__init__()
        self.url = url
        self.key = key
        self.destination = destination
    
    def download(self):
        try:
            # Создание заголовков для авторизации
            headers = {"Authorization": f"Bearer {self.key}"}
            
            # Запрос файла
            response = requests.get(self.url, headers=headers, stream=True)
            
            if response.status_code != 200:
                self.error_signal.emit(f"Ошибка загрузки: {response.status_code}")
                return
            
            # Получение общего размера файла
            total_size = int(response.headers.get('content-length', 0))
            
            # Открытие файла для записи
            with open(self.destination, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress = int((downloaded / total_size) * 100) if total_size > 0 else 0
                        self.progress_signal.emit(progress)
            
            # Добавление файла в список на удаление при выходе
            files_to_delete.append(self.destination)
            
            self.finished_signal.emit(self.destination)
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке файла: {e}")
            self.error_signal.emit(f"Ошибка загрузки: {str(e)}")

# Класс для запуска Minecraft
class MinecraftLauncher(QObject):
    status_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def __init__(self, key):
        super().__init__()
        self.key = key
        self.minecraft_process = None
    
    def launch(self):
        try:
            # Проверка наличия Java
            try:
                subprocess.run(["java", "-version"], capture_output=True, check=True)
            except Exception as e:
                self.error_signal.emit("Java не найдена. Установите Java для запуска Minecraft.")
                return
            
            # Проверка наличия директории Minecraft
            if not os.path.exists(MINECRAFT_DIR):
                self.error_signal.emit(f"Директория Minecraft не найдена: {MINECRAFT_DIR}")
                return
            
            # Создание команды для запуска Minecraft
            # Обычно вы бы использовали более сложную команду с аргументами Java,
            # но для примера мы просто запустим Minecraft
            cmd = ["java", "-jar", os.path.join(MINECRAFT_DIR, "minecraft_launcher.jar")]
            
            # Запуск Minecraft
            self.status_signal.emit("Запуск Minecraft...")
            self.minecraft_process = subprocess.Popen(cmd)
            
            # Ожидание запуска
            time.sleep(2)
            
            # Проверка, запустился ли процесс
            if self.minecraft_process.poll() is not None:
                exit_code = self.minecraft_process.returncode
                self.error_signal.emit(f"Не удалось запустить Minecraft. Код ошибки: {exit_code}")
                return
            
            self.status_signal.emit("Minecraft запущен успешно!")
            
            # Мониторинг процесса
            while self.minecraft_process.poll() is None:
                time.sleep(1)
            
            # Процесс завершен
            self.status_signal.emit("Minecraft завершен")
            self.finished_signal.emit()
            
        except Exception as e:
            logger.error(f"Ошибка при запуске Minecraft: {e}")
            self.error_signal.emit(f"Ошибка при запуске: {str(e)}")
            self.finished_signal.emit()
    
    def terminate(self):
        if self.minecraft_process and self.minecraft_process.poll() is None:
            try:
                # Попытка штатного завершения
                self.minecraft_process.terminate()
                time.sleep(2)
                
                # Если процесс все еще работает, принудительное завершение
                if self.minecraft_process.poll() is None:
                    self.minecraft_process.kill()
                    
                logger.info("Minecraft процесс принудительно завершен")
            except Exception as e:
                logger.error(f"Ошибка при завершении процесса Minecraft: {e}")

# Класс основного окна лоадера
class LoaderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Настройка окна
        self.setWindowTitle(f"Minecraft Loader Alpha v{VERSION}")
        self.setMinimumSize(800, 600)
        self.setWindowIcon(QIcon("assets/icon.ico"))
        
        # Инициализация настроек
        self.settings = QSettings("MinecraftLoader", "Alpha")
        self.last_key = self.settings.value("last_key", "")
        
        # Инициализация переменных
        self.key = None
        self.key_valid = False
        self.key_expiry = None
        self.username = None
        self.download_threads = []
        self.minecraft_launcher = None
        self.key_check_timer = QTimer()
        self.key_check_timer.timeout.connect(self.check_key_validity)
        
        # Создание центрального виджета
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Создание основного лейаута
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Создание виджетов интерфейса
        self.create_ui()
        
        # Загрузка сохраненного ключа (если есть)
        if self.last_key:
            self.key_input.setText(self.last_key)
            self.verify_key()
    
    def create_ui(self):
        # Заголовок
        header_label = QLabel("Minecraft Loader Alpha")
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        self.main_layout.addWidget(header_label)
        
        # Группа ввода ключа
        key_group = QGroupBox("Авторизация")
        key_layout = QVBoxLayout()
        
        key_input_layout = QHBoxLayout()
        key_label = QLabel("Ключ:")
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Введите ключ в формате XXXX-XXXX-XXXX-XXXX")
        self.verify_button = QPushButton("Проверить")
        self.verify_button.clicked.connect(self.verify_key)
        
        key_input_layout.addWidget(key_label)
        key_input_layout.addWidget(self.key_input)
        key_input_layout.addWidget(self.verify_button)
        
        key_layout.addLayout(key_input_layout)
        
        # Статус ключа
        self.key_status_label = QLabel("Статус: Не проверен")
        self.key_time_left_label = QLabel("")
        key_layout.addWidget(self.key_status_label)
        key_layout.addWidget(self.key_time_left_label)
        
        key_group.setLayout(key_layout)
        self.main_layout.addWidget(key_group)
        
        # Создание вкладок
        self.tab_widget = QTabWidget()
        
        # Вкладка игры
        self.game_tab = QWidget()
        game_layout = QVBoxLayout(self.game_tab)
        
        # Кнопка запуска игры
        self.launch_button = QPushButton("Запустить Minecraft")
        self.launch_button.setEnabled(False)
        self.launch_button.clicked.connect(self.launch_minecraft)
        self.launch_button.setStyleSheet("font-size: 16px; padding: 10px;")
        game_layout.addWidget(self.launch_button)
        
        # Прогресс загрузки
        self.progress_group = QGroupBox("Прогресс загрузки")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        self.status_label = QLabel("Готов к загрузке")
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        
        self.progress_group.setLayout(progress_layout)
        game_layout.addWidget(self.progress_group)
        
        # Логи
        self.log_group = QGroupBox("Логи")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        
        log_layout.addWidget(self.log_text)
        
        self.log_group.setLayout(log_layout)
        game_layout.addWidget(self.log_group)
        
        # Добавление вкладки игры
        self.tab_widget.addTab(self.game_tab, "Игра")
        
        # Добавление вкладок в основной лейаут
        self.main_layout.addWidget(self.tab_widget)
    
    def verify_key(self):
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите ключ")
            return
        
        self.key = key
        self.key_status_label.setText("Статус: Проверка...")
        self.log("Проверка ключа...")
        
        # Создание и запуск потока для проверки ключа
        self.key_verifier = KeyVerifier(key)
        self.key_verifier_thread = QThread()
        self.key_verifier.moveToThread(self.key_verifier_thread)
        
        self.key_verifier.result_signal.connect(self.on_key_verification)
        self.key_verifier_thread.started.connect(self.key_verifier.verify)
        
        self.key_verifier_thread.start()
    
    def on_key_verification(self, result):
        self.key_verifier_thread.quit()
        self.key_verifier_thread.wait()
        
        if result.get('valid', False):
            self.key_valid = True
            self.username = result.get('user', {}).get('username', 'Unknown')
            self.key_expiry = result.get('expires_at')
            time_left = result.get('time_left', 0)
            
            # Сохранение ключа в настройках
            self.settings.setValue("last_key", self.key)
            
            # Обновление интерфейса
            self.key_status_label.setText(f"Статус: Действителен (Пользователь: {self.username})")
            self.key_status_label.setStyleSheet("color: green;")
            
            # Форматирование оставшегося времени
            if time_left > 0:
                days, remainder = divmod(time_left, 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                time_str = ""
                if days > 0:
                    time_str += f"{days} дн. "
                if hours > 0:
                    time_str += f"{hours} ч. "
                if minutes > 0:
                    time_str += f"{minutes} мин. "
                
                self.key_time_left_label.setText(f"Истекает через: {time_str}")
            else:
                self.key_time_left_label.setText("Ключ истек")
            
            # Активация кнопки запуска
            self.launch_button.setEnabled(True)
            
            # Запуск таймера для проверки статуса ключа
            self.key_check_timer.start(60000)  # Проверка каждую минуту
            
            self.log(f"Ключ подтвержден. Пользователь: {self.username}")
        else:
            self.key_valid = False
            error_message = result.get('message', 'Недействительный ключ')
            
            # Обновление интерфейса
            self.key_status_label.setText(f"Статус: Недействителен")
            self.key_status_label.setStyleSheet("color: red;")
            self.key_time_left_label.setText("")
            
            # Деактивация кнопки запуска
            self.launch_button.setEnabled(False)
            
            # Остановка таймера проверки ключа
            self.key_check_timer.stop()
            
            self.log(f"Ошибка проверки ключа: {error_message}")
            QMessageBox.warning(self, "Ошибка ключа", error_message)
    
    def check_key_validity(self):
        # Повторная проверка валидности ключа
        if self.key:
            key_verifier = KeyVerifier(self.key)
            key_verifier_thread = QThread()
            key_verifier.moveToThread(key_verifier_thread)
            
            key_verifier.result_signal.connect(self.update_key_status)
            key_verifier_thread.started.connect(key_verifier.verify)
            
            key_verifier_thread.start()
    
    def update_key_status(self, result):
        if not result.get('valid', False):
            self.key_valid = False
            self.key_status_label.setText("Статус: Недействителен (ключ истек)")
            self.key_status_label.setStyleSheet("color: red;")
            self.key_time_left_label.setText("")
            self.launch_button.setEnabled(False)
            self.key_check_timer.stop()
            
            # Если игра запущена, завершаем ее
            if self.minecraft_launcher and hasattr(self.minecraft_launcher, 'minecraft_process') and self.minecraft_launcher.minecraft_process:
                self.minecraft_launcher.terminate()
                self.log("Игра завершена из-за истечения ключа")
            
            QMessageBox.warning(self, "Ключ истек", "Ваш ключ больше не действителен. Пожалуйста, введите новый ключ.")
        else:
            # Обновление времени до истечения
            time_left = result.get('time_left', 0)
            if time_left > 0:
                days, remainder = divmod(time_left, 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                time_str = ""
                if days > 0:
                    time_str += f"{days} дн. "
                if hours > 0:
                    time_str += f"{hours} ч. "
                if minutes > 0:
                    time_str += f"{minutes} мин. "
                
                self.key_time_left_label.setText(f"Истекает через: {time_str}")
    
    def launch_minecraft(self):
        if not self.key_valid:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите действительный ключ")
            return
        
        self.log("Подготовка к запуску Minecraft...")
        self.status_label.setText("Подготовка к запуску...")
        
        # Загрузка необходимых файлов
        # В реальном приложении здесь был бы код для загрузки модов и других файлов
        
        # Для примера, делаем вид, что загружаем файлы
        self.progress_bar.setValue(0)
        self.status_label.setText("Загрузка модов...")
        
        # В реальном приложении вы бы загружали настоящие файлы с сервера
        # Для примера создадим временный файл
        mod_file = os.path.join(TEMP_DIR, "example_mod.jar")
        with open(mod_file, 'w') as f:
            f.write("Это имитация мода для Minecraft")
        
        # Добавление файла в список на удаление
        files_to_delete.append(mod_file)
        
        # Имитация процесса загрузки
        for i in range(101):
            self.progress_bar.setValue(i)
            if i % 10 == 0:
                self.log(f"Загрузка модов: {i}%")
            time.sleep(0.01)
        
        self.log("Моды успешно загружены")
        self.status_label.setText("Запуск игры...")
        
        # Создание и запуск потока для запуска Minecraft
        self.minecraft_launcher = MinecraftLauncher(self.key)
        self.minecraft_thread = QThread()
        self.minecraft_launcher.moveToThread(self.minecraft_thread)
        
        self.minecraft_launcher.status_signal.connect(self.update_minecraft_status)
        self.minecraft_launcher.error_signal.connect(self.on_minecraft_error)
        self.minecraft_launcher.finished_signal.connect(self.on_minecraft_finished)
        self.minecraft_thread.started.connect(self.minecraft_launcher.launch)
        
        self.launch_button.setEnabled(False)
        self.verify_button.setEnabled(False)
        
        self.minecraft_thread.start()
    
    def update_minecraft_status(self, status):
        self.status_label.setText(status)
        self.log(status)
    
    def on_minecraft_error(self, error):
        self.log(f"Ошибка: {error}")
        QMessageBox.warning(self, "Ошибка", error)
        
        self.launch_button.setEnabled(True)
        self.verify_button.setEnabled(True)
    
    def on_minecraft_finished(self):
        self.minecraft_thread.quit()
        self.minecraft_thread.wait()
        
        self.status_label.setText("Готов к запуску")
        self.log("Сессия Minecraft завершена")
        
        self.launch_button.setEnabled(True)
        self.verify_button.setEnabled(True)
    
    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        logger.info(message)
    
    def closeEvent(self, event):
        # Проверка, запущен ли Minecraft
        if self.minecraft_launcher and hasattr(self.minecraft_launcher, 'minecraft_process') and self.minecraft_launcher.minecraft_process:
            # Завершение процесса
            self.minecraft_launcher.terminate()
            self.log("Minecraft процесс завершен")
        
        # Завершение всех потоков
        for thread in self.download_threads:
            if thread.isRunning():
                thread.quit()
                thread.wait()
        
        if hasattr(self, 'minecraft_thread') and self.minecraft_thread.isRunning():
            self.minecraft_thread.quit()
            self.minecraft_thread.wait()
        
        event.accept()

# Запуск приложения
if __name__ == "__main__":
    # Регистрация обработчиков сигналов
    def signal_handler(sig, frame):
        logger.info(f"Получен сигнал {sig}, завершение работы...")
        cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Создание приложения
    app = QApplication(sys.argv)
    
    # Установка темы
    app.setStyle("Fusion")
    
    # Установка темной темы
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    
    app.setPalette(dark_palette)
    
    # Создание основного окна
    window = LoaderWindow()
    window.show()
    
    # Запуск цикла обработки событий
    sys.exit(app.exec_()) 