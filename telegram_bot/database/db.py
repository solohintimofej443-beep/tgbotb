from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from config import DATABASE_URL
from .models import Base
import os

# Создание движка БД
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

# Создание фабрики сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Инициализация базы данных"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Получить сессию БД"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


def get_db_session():
    """Context manager для работы с БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
