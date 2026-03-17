from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from enum import Enum

Base = declarative_base()


class User(Base):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    
    # Рейтинг и статистика
    rating_as_customer = Column(Float, default=0.0)  # Рейтинг как заказчик
    rating_as_performer = Column(Float, default=0.0)  # Рейтинг как исполнитель
    
    reviews_as_customer = Column(Integer, default=0)  # Количество отзывов как заказчик
    reviews_as_performer = Column(Integer, default=0)  # Количество отзывов как исполнитель
    
    # Система жалоб
    complaints_count = Column(Integer, default=0)  # Количество жалоб
    is_blocked = Column(Boolean, default=False)  # Заблокирован ли
    
    # Кошелёк
    stars_balance = Column(Integer, default=0)  # Баланс звёзд
    
    # Объявления
    listings_count = Column(Integer, default=0)  # Количество созданных объявлений
    free_listings_remaining = Column(Integer, default=3)  # Осталось бесплатных публикаций
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaymentMethod(str, Enum):
    """Способы оплаты"""
    PREPAYMENT = "prepayment"  # Предоплата
    IMMEDIATE = "immediate"  # Сразу
    AFTER_COMPLETION = "after_completion"  # После выполнения


class Listing(Base):
    """Модель объявления"""
    __tablename__ = 'listings'
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer)  # ID заказчика
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    # Анонимность
    is_anonymous = Column(Boolean, default=False)
    
    # Статус
    status = Column(String(50), default='active')  # active, in_progress, completed, cancelled
    
    # Исполнитель
    performer_id = Column(Integer, nullable=True)
    
    # Времени
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deadline = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Платёж
    payment_made = Column(Boolean, default=False)  # Произведена ли оплата


class Chat(Base):
    """Модель чата между заказчиком и исполнителем"""
    __tablename__ = 'chats'
    
    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer)
    customer_id = Column(Integer)
    performer_id = Column(Integer)
    
    # Подтверждение выполнения
    performer_confirmed_completion = Column(Boolean, default=False)  # Исполнитель подтвердил
    customer_confirmed_completion = Column(Boolean, default=False)   # Заказчик подтвердил
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Message(Base):
    """Модель сообщения в чате"""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer)
    sender_id = Column(Integer)
    text = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class Rating(Base):
    """Модель рейтинга"""
    __tablename__ = 'ratings'
    
    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer)
    
    rater_id = Column(Integer)  # Кто оставляет рейтинг
    rated_user_id = Column(Integer)  # Кому оставляют рейтинг
    
    score = Column(Float)  # Оценка от 1 до 5
    comment = Column(Text)
    
    # Тип рейтинга (customer = оценка от заказчика, performer = оценка от исполнителя)
    rating_type = Column(String(50))  # 'customer' или 'performer'
    
    created_at = Column(DateTime, default=datetime.utcnow)


class Complaint(Base):
    """Модель жалобы"""
    __tablename__ = 'complaints'
    
    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer)
    
    complainant_id = Column(Integer)  # Кто подал жалобу
    complained_user_id = Column(Integer)  # На кого жалоба
    
    reason = Column(Text)  # Причина жалобы
    status = Column(String(50), default='open')  # open, resolved, dismissed
    
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)


class Transaction(Base):
    """Модель финансовой транзакции"""
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    listing_id = Column(Integer, nullable=True)
    
    amount = Column(Float)  # Сумма в звёздах
    transaction_type = Column(String(50))  # 'payment', 'refund', 'payout'
    status = Column(String(50), default='pending')  # pending, completed, failed
    
    payment_charge_id = Column(String(255), nullable=True)  # ID платежа от Telegram
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
