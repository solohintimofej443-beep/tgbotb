#!/usr/bin/env python3
"""
🚀 Быстрый запуск бота
"""

import os
import sys
import subprocess

def main():
    print("=" * 60)
    print("🤖 Telegram Tasks Bot - Быстрый запуск")
    print("=" * 60)
    
    # Получить путь к скрипту
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_file = os.path.join(script_dir, '.env')
    
    # Проверить .env
    if not os.path.exists(env_file):
        print("\n❌ Файл .env не найден!")
        print("Запуск setup...")
        subprocess.call([sys.executable, 'install.py'])
        return
    
    # Проверить BOT_TOKEN
    with open(env_file, 'r') as f:
        content = f.read()
        if 'BOT_TOKEN=your_token_here' in content or 'BOT_TOKEN=' not in content:
            print("\n⚠️  BOT_TOKEN не настроен!")
            print("\n📝 Пожалуйста:")
            print("   1. Откройте файл .env")
            print("   2. Замените 'your_token_here' на ваш токен:")
            print("      BOT_TOKEN=123456789:ABCDEFGhijklmnopqrstuvwxyz")
            print("\n💡 Как получить токен:")
            print("   - Откройте Telegram")
            print("   - Найдите @BotFather")
            print("   - Отправьте /newbot")
            return
    
    print("\n✅ Проверка конфигурации пройдена!")
    print("\n🚀 Запуск бота...")
    print("-" * 60)
    
    # Запустить основной бот из правильной директории
    main_file = os.path.join(script_dir, 'main.py')
    subprocess.call([sys.executable, main_file], cwd=script_dir)


if __name__ == '__main__':
    main()
