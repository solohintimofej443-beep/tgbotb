import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Proxy list (used to access Telegram)
PROXY_LIST = [
    "socks5://5.255.117.127:1080",
    "http://45.131.6.46:80",
    "http://45.131.7.234:80",
    "http://45.131.4.75:80",
    "http://45.131.210.64:80",
    "http://45.131.6.176:80",
    "http://45.131.7.90:80",
]

# Set PROXY_URL in .env to force a specific proxy
PROXY_URL = os.getenv("PROXY_URL")
PROXY_JSON_URL = os.getenv("PROXY_JSON_URL")

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
