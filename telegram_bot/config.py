import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Database
DATABASE_URL = 'sqlite:///bot_database.db'

# Payment
STAR_PRICES = {
    'post_listing': 10,  # Звёзд за публикацию объявления
}

# Reporting system
MAX_COMPLAINTS = 3  # Максимум жалоб перед блокировкой

# Rating system
MIN_RATING = 0.0
MAX_RATING = 5.0

# Admin system
ADMIN_IDS = [int(admin_id) for admin_id in os.getenv('ADMIN_IDS', '').split(',') if admin_id]
SUPER_ADMIN_ID = int(os.getenv('SUPER_ADMIN_ID', '0'))
