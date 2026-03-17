from telegram import Update, LabeledPrice
from telegram.ext import ContextTypes
from database.db import SessionLocal
from utils.database_service import DatabaseService


async def pre_checkout_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка запроса перед оплатой"""
    query = update.pre_checkout_query
    
    if query.invoice_payload == "listing_creation":
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Что-то пошло не так. Попробуйте позже.")


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка успешной оплаты"""
    user = update.effective_user
    payment = update.message.successful_payment
    
    db = SessionLocal()
    service = DatabaseService(db)
    
    # Создать транзакцию
    transaction = service.create_transaction(
        user_id=user.id,
        amount=payment.total_amount / 100,  # Конвертировать в звёзды
        transaction_type='top_up'
    )
    
    # Обновить баланс пользователя
    db_user = service.get_user(user.id)
    if db_user:
        db_user.stars_balance += int(payment.total_amount / 100)
        db.commit()
    
    service.update_transaction_status(
        transaction.id,
        'completed',
        payment.telegram_payment_charge_id
    )
    
    await update.message.reply_text(
        f"✅ Платёж успешно принят!\n\n"
        f"Вы получили {int(payment.total_amount / 100)} звёзд"
    )
    db.close()


async def buy_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Купить звёзды"""
    query = update.callback_query
    user = query.from_user
    
    # Варианты покупки
    stars_options = {
        10: 1,    # 10 звёзд = 1 RUB (для тестирования)
        50: 5,
        100: 10,
        500: 50,
    }
    
    prices = [
        LabeledPrice(label=f"{stars} ⭐", amount=amount * 100)
        for stars, amount in stars_options.items()
    ]
    
    await context.bot.send_invoice(
        chat_id=user.id,
        title="Звёзды для платформы",
        description="Купи звёзды для создания объявлений",
        payload="listing_creation",
        provider_token="",  # Здесь должен быть реальный токен платежного провайдера
        currency="RUB",
        prices=prices,
    )
