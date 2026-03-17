from sqlalchemy.orm import Session
from database.models import User, Listing, Chat, Message, Rating, Complaint, Transaction, PaymentMethod
from datetime import datetime


class DatabaseService:
    """Сервис для работы с базой данных"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ===== ПОЛЬЗОВАТЕЛИ =====
    
    def get_or_create_user(self, user_id: int, username: str, first_name: str, last_name: str = None) -> User:
        """Получить или создать пользователя"""
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            user = User(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            self.db.add(user)
            self.db.commit()
        return user
    
    def get_user(self, user_id: int) -> User:
        """Получить пользователя по ID"""
        return self.db.query(User).filter(User.user_id == user_id).first()
    
    def is_user_blocked(self, user_id: int) -> bool:
        """Проверить, заблокирован ли пользователь"""
        user = self.get_user(user_id)
        return user and user.is_blocked
    
    def block_user(self, user_id: int):
        """Заблокировать пользователя"""
        user = self.get_user(user_id)
        if user:
            user.is_blocked = True
            self.db.commit()
    
    # ===== ОБЪЯВЛЕНИЯ =====
    
    def create_listing(self, customer_id: int, title: str, description: str, 
                      is_anonymous: bool) -> Listing:
        """Создать объявление"""
        listing = Listing(
            customer_id=customer_id,
            title=title,
            description=description,
            is_anonymous=is_anonymous
        )
        self.db.add(listing)
        self.db.commit()
        return listing
    
    def get_listing(self, listing_id: int) -> Listing:
        """Получить объявление по ID"""
        return self.db.query(Listing).filter(Listing.id == listing_id).first()
    
    def get_active_listings(self) -> list:
        """Получить активные объявления"""
        return self.db.query(Listing).filter(Listing.status == 'active').all()
    
    def update_listing_status(self, listing_id: int, status: str):
        """Обновить статус объявления"""
        listing = self.get_listing(listing_id)
        if listing:
            listing.status = status
            listing.updated_at = datetime.utcnow()
            self.db.commit()
    
    def set_listing_performer(self, listing_id: int, performer_id: int):
        """Установить исполнителя для объявления"""
        listing = self.get_listing(listing_id)
        if listing:
            listing.performer_id = performer_id
            listing.status = 'in_progress'
            self.db.commit()
    
    def complete_listing(self, listing_id: int):
        """Завершить объявление"""
        listing = self.get_listing(listing_id)
        if listing:
            listing.status = 'completed'
            listing.completed_at = datetime.utcnow()
            self.db.commit()
    
    # ===== ЧАТЫ =====
    
    def create_or_get_chat(self, listing_id: int, customer_id: int, performer_id: int) -> Chat:
        """Создать или получить чат"""
        chat = self.db.query(Chat).filter(
            Chat.listing_id == listing_id,
            Chat.customer_id == customer_id,
            Chat.performer_id == performer_id
        ).first()
        
        if not chat:
            chat = Chat(
                listing_id=listing_id,
                customer_id=customer_id,
                performer_id=performer_id
            )
            self.db.add(chat)
            self.db.commit()
        return chat
    
    def get_chat(self, chat_id: int) -> Chat:
        """Получить чат по ID"""
        return self.db.query(Chat).filter(Chat.id == chat_id).first()
    
    def add_message(self, chat_id: int, sender_id: int, text: str) -> Message:
        """Добавить сообщение в чат"""
        message = Message(
            chat_id=chat_id,
            sender_id=sender_id,
            text=text
        )
        self.db.add(message)
        self.db.commit()
        return message
    
    def get_chat_messages(self, chat_id: int) -> list:
        """Получить сообщения чата"""
        return self.db.query(Message).filter(Message.chat_id == chat_id).all()
    
    # ===== РЕЙТИНГИ И ОТЗЫВЫ =====
    
    def add_rating(self, listing_id: int, rater_id: int, rated_user_id: int, 
                   score: float, comment: str, rating_type: str):
        """Добавить рейтинг"""
        # Проверить, не существует ли уже рейтинг
        existing = self.db.query(Rating).filter(
            Rating.listing_id == listing_id,
            Rating.rater_id == rater_id,
            Rating.rating_type == rating_type
        ).first()
        
        if existing:
            existing.score = score
            existing.comment = comment
            self.db.commit()
            return existing
        
        rating = Rating(
            listing_id=listing_id,
            rater_id=rater_id,
            rated_user_id=rated_user_id,
            score=score,
            comment=comment,
            rating_type=rating_type
        )
        self.db.add(rating)
        
        # Обновить рейтинг пользователя
        self._update_user_rating(rated_user_id, rating_type)
        self.db.commit()
        return rating
    
    def _update_user_rating(self, user_id: int, rating_type: str):
        """Обновить рейтинг пользователя"""
        user = self.get_user(user_id)
        if not user:
            return
        
        if rating_type == 'customer':
            ratings = self.db.query(Rating).filter(
                Rating.rated_user_id == user_id,
                Rating.rating_type == 'customer'
            ).all()
            if ratings:
                avg_score = sum(r.score for r in ratings) / len(ratings)
                user.rating_as_customer = round(avg_score, 2)
                user.reviews_as_customer = len(ratings)
        else:
            ratings = self.db.query(Rating).filter(
                Rating.rated_user_id == user_id,
                Rating.rating_type == 'performer'
            ).all()
            if ratings:
                avg_score = sum(r.score for r in ratings) / len(ratings)
                user.rating_as_performer = round(avg_score, 2)
                user.reviews_as_performer = len(ratings)
        
        self.db.commit()
    
    def get_user_ratings(self, user_id: int, rating_type: str = None) -> list:
        """Получить рейтинги пользователя"""
        query = self.db.query(Rating).filter(Rating.rated_user_id == user_id)
        if rating_type:
            query = query.filter(Rating.rating_type == rating_type)
        return query.all()
    
    # ===== ЖАЛОБЫ =====
    
    def create_complaint(self, listing_id: int, complainant_id: int, 
                        complained_user_id: int, reason: str) -> Complaint:
        """Создать жалобу"""
        complaint = Complaint(
            listing_id=listing_id,
            complainant_id=complainant_id,
            complained_user_id=complained_user_id,
            reason=reason
        )
        self.db.add(complaint)
        
        # Увеличить счётчик жалоб
        user = self.get_user(complained_user_id)
        if user:
            user.complaints_count += 1
            if user.complaints_count >= 3:
                self.block_user(complained_user_id)
        
        self.db.commit()
        return complaint
    
    def get_complaints(self, complained_user_id: int) -> list:
        """Получить жалобы на пользователя"""
        return self.db.query(Complaint).filter(
            Complaint.complained_user_id == complained_user_id
        ).all()
    
    def resolve_complaint(self, complaint_id: int, status: str):
        """Разрешить жалобу"""
        complaint = self.db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if complaint:
            complaint.status = status
            complaint.resolved_at = datetime.utcnow()
            self.db.commit()
    
    # ===== ТРАНЗАКЦИИ =====
    
    def create_transaction(self, user_id: int, amount: float, transaction_type: str, 
                          listing_id: int = None) -> Transaction:
        """Создать транзакцию"""
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            listing_id=listing_id
        )
        self.db.add(transaction)
        self.db.commit()
        return transaction
    
    def get_transactions(self, user_id: int) -> list:
        """Получить транзакции пользователя"""
        return self.db.query(Transaction).filter(
            Transaction.user_id == user_id
        ).order_by(Transaction.created_at.desc()).all()
    
    def update_transaction_status(self, transaction_id: int, status: str, payment_charge_id: str = None):
        """Обновить статус транзакции"""
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if transaction:
            transaction.status = status
            if payment_charge_id:
                transaction.payment_charge_id = payment_charge_id
            if status == 'completed':
                transaction.completed_at = datetime.utcnow()
            self.db.commit()
