#!/usr/bin/env python3
"""
🚀 Главный скрипт установки - запустите это из корневой папки
"""

import subprocess
import sys
import os

def main():
    print("=" * 70)
    print("🚀 Telegram Bot - Главный скрипт установки")
    print("=" * 70)
    
    # Путь к папке telegram_bot
    telegram_bot_dir = os.path.join(os.path.dirname(__file__), 'telegram_bot')
    install_script = os.path.join(telegram_bot_dir, 'install.py')
    
    if not os.path.exists(install_script):
        print(f"\n❌ Ошибка: не найден {install_script}")
        print("Проверьте что вы находитесь в корректной директории")
        sys.exit(1)
    
    print(f"\n📦 Запуск установки из: {telegram_bot_dir}")
    print("-" * 70)
    
    # Запустить install.py из папки telegram_bot
    result = subprocess.call([sys.executable, install_script])
    
    if result == 0:
        print("\n" + "=" * 70)
        print("✅ УСТАНОВКА ЗАВЕРШЕНА!")
        print("=" * 70)
        print("\n🚀 Для запуска бота выполните:")
        print(f"   cd telegram_bot")
        print(f"   python run.py")
        print("\n   или")
        print(f"   python telegram_bot/run.py")
    else:
        print("\n❌ Ошибка при установке!")
        sys.exit(1)

if __name__ == '__main__':
    main()
