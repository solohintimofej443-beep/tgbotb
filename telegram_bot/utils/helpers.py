"""Утилиты для работы с ботом"""

from datetime import datetime, timedelta


def format_date(date: datetime) -> str:
    """Форматировать дату"""
    return date.strftime('%d.%m.%Y %H:%M')


def get_time_until(date: datetime) -> str:
    """Получить время до определённой даты"""
    now = datetime.utcnow()
    delta = date - now
    
    if delta.days > 0:
        return f"{delta.days}d {delta.seconds // 3600}h"
    else:
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def format_price(price: float, currency: str = "⭐") -> str:
    """Форматировать цену"""
    if price == int(price):
        return f"{int(price)}{currency}"
    return f"{price:.2f}{currency}"


def get_rating_stars(rating: float) -> str:
    """Получить звёзды рейтинга"""
    full_stars = int(rating)
    has_half = (rating - full_stars) >= 0.5
    
    stars = "⭐" * full_stars
    if has_half:
        stars += "✨"
    
    return stars


def validate_price(price: str) -> bool:
    """Проверить корректность цены"""
    try:
        float_price = float(price)
        return float_price > 0
    except ValueError:
        return False


def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезать текст"""
    if len(text) > max_length:
        return text[:max_length - 3] + "..."
    return text
