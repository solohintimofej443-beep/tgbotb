#!/usr/bin/env python3
"""
Скрипт для автоматической установки всех необходимых зависимостей
"""

import subprocess
import sys
import os


def install_requirements():
    """Установить зависимости из requirements.txt"""
    # Получить путь к текущему скрипту
    script_dir = os.path.dirname(os.path.abspath(__file__))
    requirements_file = os.path.join(script_dir, 'requirements.txt')
    
    if not os.path.exists(requirements_file):
        print(f"❌ Файл requirements.txt не найден!")
        print(f"   Искали в: {requirements_file}")
        return False
    
    print("📦 Установка зависимостей...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', requirements_file])
        print("✅ Зависимости успешно установлены!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Ошибка при установке зависимостей!")
        return False


def check_python_version():
    """Проверить версию Python"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print(f"❌ Требуется Python 3.9+ (у вас {version.major}.{version.minor})")
        return False
    print(f"✅ Python {version.major}.{version.minor} OK")
    return True


def check_env_file():
    """Проверить наличие файла .env"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_file = os.path.join(script_dir, '.env')
    
    if not os.path.exists(env_file):
        print("⚠️  Файл .env не найден!")
        print("\n📝 Создание файла .env...")
        
        env_content = """# Telegram Bot Configuration
BOT_TOKEN=your_token_here

# Admin settings
SUPER_ADMIN_ID=your_user_id
ADMIN_IDS=admin_id_1,admin_id_2

# Database (optional)
# DATABASE_URL=sqlite:///bot_database.db

# Payment (optional)
# PAYMENT_PROVIDER_TOKEN=your_payment_token
"""
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print("✅ Файл .env создан!")
        print("\n⚠️  ВАЖНО: Отредактируйте файл .env и добавьте:")
        print("   - BOT_TOKEN: ваш токен бота (от @BotFather)")
        print("   - SUPER_ADMIN_ID: ваш ID пользователя (для админских прав)")
        print("   - ADMIN_IDS:  ID администраторов (через запятую)")
        return False
    
    print("✅ Файл .env найден")
    return True


def test_imports():
    """Проверить импорты"""
    print("\n🔍 Проверка импортов...")
    
    try:
        import telegram
        print("✅ python-telegram-bot OK")
    except ImportError:
        print("❌ python-telegram-bot не установлен")
        return False
    
    try:
        import sqlalchemy
        print("✅ sqlalchemy OK")
    except ImportError:
        print("❌ sqlalchemy не установлен")
        return False
    
    try:
        import dotenv
        print("✅ python-dotenv OK")
    except ImportError:
        print("❌ python-dotenv не установлен")
        return False
    
    print("✅ Все импорты в порядке!")
    return True


def main():
    """Главная функция"""
    print("🤖 Инициализация Telegram Bot\n")
    
    # Получить директорию скрипта
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)  # Перейти в директорию скрипта
    
    # Проверить версию Python
    if not check_python_version():
        sys.exit(1)
    
    # Проверить .env файл
    env_ok = check_env_file()
    
    # Установить зависимости
    if not install_requirements():
        sys.exit(1)
    
    # Проверить импорты
    if not test_imports():
        sys.exit(1)
    
    print("\n" + "="*50)
    print("✅ Инициализация завершена успешно!")
    print("="*50)
    
    if not env_ok:
        print("\n⚠️  Перед запуском бота:")
        print("   1. Отредактируйте файл .env")
        print("   2. Добавьте BOT_TOKEN")
        print("   3. Добавьте SUPER_ADMIN_ID и ADMIN_IDS")
        print("\n📖 Инструкции в SETUP.md")
    
    print("\n🚀 Для запуска бота выполните: python run.py")


if __name__ == '__main__':
    main()
