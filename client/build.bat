@echo off
echo Создание исполняемого файла Minecraft Loader Alpha...

:: Проверка наличия PyInstaller
python -c "import PyInstaller" 2>nul
if %errorlevel% neq 0 (
    echo PyInstaller не найден. Установка...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo Ошибка установки PyInstaller. Убедитесь, что Python установлен и доступен в PATH.
        pause
        exit /b 1
    )
)

:: Проверка наличия зависимостей
echo Установка зависимостей...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Ошибка установки зависимостей.
    pause
    exit /b 1
)

:: Создание директории для сборки, если её нет
if not exist "dist" mkdir dist

:: Очистка предыдущей сборки
if exist "dist\minecraft-loader-alpha.exe" del /f "dist\minecraft-loader-alpha.exe"

:: Создание исполняемого файла
echo Сборка исполняемого файла...
pyinstaller --onefile --noconsole --icon=assets\icon.ico src\main.py --name minecraft-loader-alpha

:: Копирование файла конфигурации в директорию с исполняемым файлом
echo Копирование файла конфигурации...
copy /y config.json dist\config.json

:: Создание директории assets в dist, если её нет
if not exist "dist\assets" mkdir dist\assets

:: Копирование иконки
if exist "assets\icon.ico" copy /y assets\icon.ico dist\assets\icon.ico

echo Сборка завершена успешно! Исполняемый файл находится в директории dist\.
echo.
echo Нажмите любую клавишу, чтобы закрыть это окно.
pause > nul 