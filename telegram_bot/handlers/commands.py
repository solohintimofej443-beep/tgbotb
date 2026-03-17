from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User as TelegramUser
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from utils.database_service import DatabaseService
from utils.navigation import NavigationHistory
from utils.message_cleaner import send_clean_reply, mark_last_bot_message, edit_message_text_safe
from database.db import SessionLocal

# Состояния для ConversationHandler
CREATE_LISTING_TITLE = 1
CREATE_LISTING_DESC = 2
CREATE_LISTING_ANONYMOUS = 3

REPLY_TO_LISTING_TITLE = 10
REPLY_TO_LISTING_MESSAGE = 11

RATE_USER_SCORE = 20
RATE_USER_COMMENT = 21

COMPLAINT_REASON = 30


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    db = SessionLocal()
    service = DatabaseService(db)
    
    db_user = service.get_or_create_user(
        user.id,
        user.username or "Аноним",
        user.first_name,
        user.last_name
    )
    
    if service.is_user_blocked(user.id):
        await update.message.reply_text(
            "❌ Вы заблокированы в системе. Слишком много жалоб."
        )
        db.close()
        return
    
    # Очистить историю при начале
    NavigationHistory.clear_history(context)
    NavigationHistory.add_state(context, 'main_menu')
    
    keyboard = [
        [InlineKeyboardButton("📝 Создать Задание", callback_data="create_listing")],
        [InlineKeyboardButton("📋 Список заданий", callback_data="view_listings")],
        [InlineKeyboardButton("💬 Мои чаты", callback_data="my_chats")],
        [InlineKeyboardButton("⭐ Мой профиль", callback_data="my_profile")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await send_clean_reply(
        update,
        context,
        f"👋 Привет, {user.first_name}!\n\n"
        "Добро пожаловать на платформу анонимных заданий!",
        reply_markup=reply_markup
    )
    db.close()


async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать профиль пользователя"""
    query = update.callback_query
    user = query.from_user
    
    if query.message:
        mark_last_bot_message(context, query.message.message_id)
    
    # Добавить в историю
    NavigationHistory.add_state(context, 'my_profile')
    
    db = SessionLocal()
    service = DatabaseService(db)
    db_user = service.get_user(user.id)
    
    if not db_user:
        await query.answer("Ошибка: пользователь не найден")
        db.close()
        return
    
    profile_text = f"""
👤 *Профиль пользователя*

*Имя:* {db_user.first_name} {db_user.last_name or ''}
*ID:* `{db_user.user_id}`

⭐ *Как заказчик:* {db_user.rating_as_customer:.1f}★ ({db_user.reviews_as_customer} отзывов)
⭐ *Как исполнитель:* {db_user.rating_as_performer:.1f}★ ({db_user.reviews_as_performer} отзывов)

⚠️ *Жалоб:* {db_user.complaints_count}/3
💳 *Баланс звёзд:* {db_user.stars_balance}
"""
    
    keyboard = [
        [InlineKeyboardButton("📊 История транзакций", callback_data="transactions_history")],
        [InlineKeyboardButton("⭐ Мои отзывы", callback_data="my_reviews")],
    ]
    
    # Добавить кнопку "Назад" если есть история
    if NavigationHistory.has_previous(context):
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="go_back")])
    else:
        keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await edit_message_text_safe(
        query,
        profile_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    db.close()


async def view_listings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список заданий"""
    query = update.callback_query
    user = query.from_user
    
    if query.message:
        mark_last_bot_message(context, query.message.message_id)
    
    # Добавить в историю
    NavigationHistory.add_state(context, 'view_listings')
    
    # Страница
    page = 1
    if query.data.startswith("view_listings_page_"):
        try:
            page = max(1, int(query.data.split('_')[3]))
        except Exception:
            page = 1
    
    db = SessionLocal()
    service = DatabaseService(db)
    listings = service.get_active_listings()
    
    if not listings:
        keyboard = []
        if NavigationHistory.has_previous(context):
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="go_back")])
        else:
            keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")])
        
        await edit_message_text_safe(
            query,
            "📋 заданий нет",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        db.close()
        return
    
    per_page = 5
    total_pages = max(1, (len(listings) + per_page - 1) // per_page)
    page = min(page, total_pages)
    start = (page - 1) * per_page
    end = start + per_page
    page_listings = listings[start:end]
    
    text = f"📋 *Активные Задания* (стр. {page}/{total_pages})\n\n"
    
    for listing in page_listings:
        if listing.is_anonymous:
            customer_display = "Аноним"
        else:
            customer = service.get_user(listing.customer_id)
            if customer and customer.username:
                customer_display = f"@{customer.username}"
            elif customer and customer.first_name:
                customer_display = customer.first_name
            else:
                customer_display = f"ID: {listing.customer_id}"
        text += f"▫️ *{listing.title}*\n"
        text += f"  От: {customer_display}\n\n"
    
    keyboard = []
    for listing in page_listings:
        keyboard.append([
            InlineKeyboardButton(
                f"📌 {listing.title[:20]}...",
                callback_data=f"listing_detail_{listing.id}"
            )
        ])
    
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"view_listings_page_{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("➡️ Вперёд", callback_data=f"view_listings_page_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)
    
    if NavigationHistory.has_previous(context):
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="go_back")])
    else:
        keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await edit_message_text_safe(
        query,
        text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    db.close()


async def my_reviews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать отзывы пользователя"""
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    if query.message:
        mark_last_bot_message(context, query.message.message_id)
    
    db = SessionLocal()
    service = DatabaseService(db)
    
    ratings = service.get_user_ratings(user.id)
    if not ratings:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="my_profile")]]
        await edit_message_text_safe(
            query,
            "⭐ У вас пока нет отзывов",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        db.close()
        return
    
    text = "⭐ *Мои отзывы*\n\n"
    for r in ratings[-10:]:
        role = "Заказчик" if r.rating_type == 'customer' else "Исполнитель"
        comment = r.comment.strip() if r.comment else "Без комментария"
        text += f"▫️ {role}: {r.score:.1f}★\n"
        text += f"   {comment}\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="my_profile")]]
    await edit_message_text_safe(
        query,
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    db.close()


async def delete_listing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить своё Задание"""
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    if query.message:
        mark_last_bot_message(context, query.message.message_id)
    
    listing_id = int(query.data.split('_')[2])
    
    db = SessionLocal()
    from database.models import Listing, Chat, Message, Rating, Complaint, Transaction
    
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        await query.answer("Задание не найдено")
        db.close()
        return
    
    if listing.customer_id != user.id:
        await query.answer("❌ Нельзя удалить чужое Задание")
        db.close()
        return
    
    chats = db.query(Chat).filter(Chat.listing_id == listing_id).all()
    for chat in chats:
        db.query(Message).filter(Message.chat_id == chat.id).delete()
    db.query(Chat).filter(Chat.listing_id == listing_id).delete()
    db.query(Rating).filter(Rating.listing_id == listing_id).delete()
    db.query(Complaint).filter(Complaint.listing_id == listing_id).delete()
    db.query(Transaction).filter(Transaction.listing_id == listing_id).delete()
    
    db.delete(listing)
    db.commit()
    
    await query.answer("✅ Задание удалено")
    await view_listings(update, context)
    db.close()


async def my_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать чаты пользователя"""
    query = update.callback_query
    user = query.from_user
    
    if query.message:
        mark_last_bot_message(context, query.message.message_id)
    
    # Добавить в историю
    NavigationHistory.add_state(context, 'my_chats')
    
    db = SessionLocal()
    service = DatabaseService(db)
    chats = service.get_user_chats(user.id)
    
    if not chats:
        keyboard = []
        if NavigationHistory.has_previous(context):
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="go_back")])
        else:
            keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")])
        
        await query.edit_message_text(
            "💬 У вас нет активных чатов",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        db.close()
        return
    
    text = "💬 *Мои чаты*\n\n"
    
    keyboard = []
    for chat in chats:
        listing = service.get_listing(chat.listing_id)
        if listing:
            text += f"▫️ *{listing.title}*\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"💬 {listing.title[:20]}...",
                    callback_data=f"open_chat_{chat.id}"
                )
            ])
    
    if NavigationHistory.has_previous(context):
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="go_back")])
    else:
        keyboard.append([InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    db.close()


async def listing_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать детали Задания"""
    query = update.callback_query
    user = query.from_user
    
    if query.message:
        mark_last_bot_message(context, query.message.message_id)
    
    listing_id = int(query.data.split('_')[2])
    
    db = SessionLocal()
    service = DatabaseService(db)
    listing = service.get_listing(listing_id)
    
    if not listing:
        await query.answer("Задание не найдено")
        db.close()
        return
    
    if listing.is_anonymous:
        customer_display = "Аноним"
    else:
        customer = service.get_user(listing.customer_id)
        if customer and customer.username:
            customer_display = f"@{customer.username}"
        elif customer and customer.first_name:
            customer_display = customer.first_name
        else:
            customer_display = f"ID: {listing.customer_id}"
    
    detail_text = f"""
📌 *{listing.title}*

📰 *Описание:*
{listing.description}

� *Тип:* {'Анонимное' if listing.is_anonymous else 'Публичное'}
📊 *Статус:* {listing.status.title()}
👤 *От:* {customer_display}

📅 Создано: {listing.created_at.strftime('%d.%m.%Y %H:%M')}
"""
    
    keyboard = []
    
    if listing.customer_id != user.id and listing.status == 'active':
        keyboard.append([
            InlineKeyboardButton("✅ Откликнуться", callback_data=f"respond_listing_{listing_id}")
        ])
    
    if listing.customer_id == user.id:
        keyboard.append([
            InlineKeyboardButton("❌ Удалить", callback_data=f"delete_listing_{listing_id}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 К Заданиям", callback_data="view_listings")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await edit_message_text_safe(
        query,
        detail_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    db.close()


async def respond_listing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Откликнуться на Задание"""
    query = update.callback_query
    user = query.from_user
    
    if query.message:
        mark_last_bot_message(context, query.message.message_id)
    listing_id = int(query.data.split('_')[2])
    
    db = SessionLocal()
    service = DatabaseService(db)
    listing = service.get_listing(listing_id)
    
    if not listing:
        await query.answer("Задание не найдено")
        db.close()
        return
    
    # Создать чат
    chat = service.create_or_get_chat(listing_id, listing.customer_id, user.id)
    
    # Сразу перейти к написанию сообщения
    context.user_data['current_chat_id'] = chat.id
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить выполнение", callback_data=f"confirm_completion_performer_{chat.id}")],
        [InlineKeyboardButton("🔙 Отменить", callback_data=f"open_chat_{chat.id}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ Вы откликнулись на Задание!\n\n"
        f"📌 *{listing.title}*\n\n"
        "📝 Введите ваше сообщение:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    db.close()


async def create_listing_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать создание Задания"""
    query = update.callback_query
    user = query.from_user
    
    if query.message:
        mark_last_bot_message(context, query.message.message_id)
    db = SessionLocal()
    service = DatabaseService(db)
    
    if service.is_user_blocked(user.id):
        await query.answer("❌ Вы заблокированы!")
        db.close()
        return ConversationHandler.END
    
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_clean_reply(
        update,
        context,
        "📝 *Создание Задания*\n\n"
        "Введите название задания:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    db.close()
    return CREATE_LISTING_TITLE


async def create_listing_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить название Задания"""
    if context.user_data.get('current_chat_id'):
        # Если пользователь в чате, перенаправить сообщение туда и завершить создание
        from handlers.chat import send_message
        await send_message(update, context)
        context.user_data.pop('listing_title', None)
        context.user_data.pop('listing_desc', None)
        context.user_data.pop('listing_anonymous', None)
        return ConversationHandler.END

    context.user_data['listing_title'] = update.message.text
    
    keyboard = [
        [InlineKeyboardButton("🔙 Отменить создание", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await send_clean_reply(
        update,
        context,
        "Описание задания (подробнее о том, что нужно сделать):",
        reply_markup=reply_markup
    )
    return CREATE_LISTING_DESC


async def create_listing_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить описание Задания"""
    if context.user_data.get('current_chat_id'):
        # Если пользователь в чате, перенаправить сообщение туда и завершить создание
        from handlers.chat import send_message
        await send_message(update, context)
        context.user_data.pop('listing_title', None)
        context.user_data.pop('listing_desc', None)
        context.user_data.pop('listing_anonymous', None)
        return ConversationHandler.END

    context.user_data['listing_desc'] = update.message.text
    
    keyboard = [
        [InlineKeyboardButton("Публичное Задание", callback_data="anonymous_false")],
        [InlineKeyboardButton("Анонимное Задание", callback_data="anonymous_true")],
        [InlineKeyboardButton("🔙 Отменить создание", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await send_clean_reply(
        update,
        context,
        "Публичность Задания:",
        reply_markup=reply_markup
    )
    return CREATE_LISTING_ANONYMOUS


async def create_listing_anonymous(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить тип анонимности и создать Задание"""
    query = update.callback_query
    user = query.from_user
    
    if query.message:
        mark_last_bot_message(context, query.message.message_id)
    
    # Проверить, не это ли отмена
    if query.data == "back_to_menu":
        context.user_data.clear()
        await back_to_menu(update, context)
        return ConversationHandler.END
    
    is_anonymous = query.data == 'anonymous_true'
    context.user_data['listing_anonymous'] = is_anonymous
    
    db = SessionLocal()
    service = DatabaseService(db)
    
    # Получить или создать пользователя
    user_db = service.get_user(user.id)
    if not user_db:
        user_db = service.get_or_create_user(user.id, user.username or "Аноним", user.first_name, user.last_name)
    
    # Проверить, админ ли пользователь
    from handlers.admin import is_admin
    is_user_admin = is_admin(user.id)
    
    # НОВАЯ ЛОГИКА: Стоимость публикации 1 звезда, первые 3 бесплатно
    cost_of_listing = 1  # 1 звезда за публикацию
    
    if not is_user_admin:
        # НЕ-АДМИН: проверяем свободные публикации и баланс
        if user_db.free_listings_remaining > 0:
            # Используем бесплатную публикацию
            user_db.free_listings_remaining -= 1
            cost_paid = 0
        else:
            # Проверяем баланс звёзд
            if user_db.stars_balance < cost_of_listing:
                await query.edit_message_text(
                    f"⭐ *Недостаточно звёзд!*\n\n"
                    f"Текущий баланс: {user_db.stars_balance}★\n"
                    f"Требуется: {cost_of_listing}★\n"
                    f"Осталось бесплатных публикаций: {user_db.free_listings_remaining}\n\n"
                    f"Пополните баланс или используйте бесплатные публикации.",
                    parse_mode=ParseMode.MARKDOWN
                )
                db.close()
                context.user_data.clear()
                return ConversationHandler.END
            
            # Списываем стоимость
            user_db.stars_balance -= cost_of_listing
            cost_paid = cost_of_listing
    else:
        # АДМИН: публикует бесплатно
        cost_paid = 0
    
    # Увеличить счётчик заданий
    user_db.listings_count += 1
    
    # Создать Задание БЕЗ цены (цена больше не указывается)
    listing = service.create_listing(
        customer_id=user.id,
        title=context.user_data['listing_title'],
        description=context.user_data['listing_desc'],
        is_anonymous=is_anonymous
    )
    
    db.commit()
    
    # Текст подтверждения
    free_status = "бесплатно" if cost_paid == 0 else f"-{cost_paid}★"
    confirmation_text = f"""
✅ *Задание создано!*

📝 *{listing.title}*
📰 {listing.description}
🔒 {'Анонимное' if is_anonymous else 'Публичное'}

ID Задания: `{listing.id}`
💳 Стоимость: {free_status}
"""
    
    if not is_user_admin and user_db.free_listings_remaining > 0:
        confirmation_text += f"\n📌 Осталось бесплатных публикаций: {user_db.free_listings_remaining}"
    
    keyboard = [
        [InlineKeyboardButton("📋 К Заданиям", callback_data="view_listings")],
        [InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        confirmation_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Очистить данные
    context.user_data.clear()
    db.close()
    return ConversationHandler.END


async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться на шаг назад"""
    query = update.callback_query
    
    # Ответить на callback сразу
    await query.answer()
    
    # Получить предыдущее состояние
    previous_state = NavigationHistory.go_back(context)
    
    if not previous_state:
        # Если нет предыдущего, вернуться в главное меню
        await back_to_menu(update, context)
        return
    
    state = previous_state.get('state')
    
    # Переехать на нужный экран в зависимости от состояния
    if state == 'main_menu':
        await back_to_menu(update, context)
    elif state == 'my_profile':
        await my_profile(update, context)
    elif state == 'view_listings':
        await view_listings(update, context)
    elif state == 'my_chats':
        await my_chats(update, context)
    else:
        await back_to_menu(update, context)


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться в главное меню"""
    query = update.callback_query
    user = query.from_user
    
    if query.message:
        mark_last_bot_message(context, query.message.message_id)
    
    # Очистить и установить главное меню в историю
    NavigationHistory.clear_history(context)
    NavigationHistory.add_state(context, 'main_menu')
    
    keyboard = [
        [InlineKeyboardButton("📝 Создать Задание", callback_data="create_listing")],
        [InlineKeyboardButton("📋 Список заданий", callback_data="view_listings")],
        [InlineKeyboardButton("💬 Мои чаты", callback_data="my_chats")],
        [InlineKeyboardButton("⭐ Мой профиль", callback_data="my_profile")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"👋 Привет, {user.first_name}!",
        reply_markup=reply_markup
    )



