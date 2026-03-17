from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database.db import SessionLocal
from utils.database_service import DatabaseService
from utils.message_cleaner import mark_last_bot_message, send_clean_reply


async def open_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Открыть чат"""
    query = update.callback_query
    user = query.from_user
    
    if query.message:
        mark_last_bot_message(context, query.message.message_id)
    
    chat_id = int(query.data.split('_')[2])
    
    db = SessionLocal()
    service = DatabaseService(db)
    chat = service.get_chat(chat_id)
    
    if not chat:
        await query.answer("Чат не найден")
        return
    
    # Проверить, что пользователь участник чата
    if user.id not in [chat.customer_id, chat.performer_id]:
        await query.answer("❌ У вас нет доступа к этому чату")
        return
    
    messages = service.get_chat_messages(chat_id)
    listing = service.get_listing(chat.listing_id)
    
    chat_text = f"💬 *Чат* (ID: {chat_id})\n"
    chat_text += f"📌 *{listing.title}*\n\n"
    
    # Показать статус подтверждения
    confirmations = int(chat.performer_confirmed_completion) + int(chat.customer_confirmed_completion)
    if confirmations > 0:
        chat_text += f"_Статус выполнения:_ выполнено ({confirmations}/2)\n\n"
    
    if messages:
        chat_text += "*Сообщения:*\n"
        for msg in messages[-10:]:  # Последние 10 сообщений
            sender_type = "Заказчик" if msg.sender_id == chat.customer_id else "Исполнитель"
            chat_text += f"*{sender_type}:* {msg.text}\n"
    else:
        chat_text += "_(нет сообщений)_\n"
    
    context.user_data['current_chat_id'] = chat_id
    
    keyboard = [
        [InlineKeyboardButton("📤 Написать сообщение", callback_data=f"send_message_{chat_id}")],
    ]
    
    # Кнопки подтверждения выполнения
    if listing.status == 'in_progress':
        if user.id == chat.performer_id and not chat.performer_confirmed_completion:
            keyboard.append([InlineKeyboardButton("✅ Подтвердить выполнение", callback_data=f"confirm_completion_performer_{chat_id}")])
        if user.id == chat.customer_id and not chat.customer_confirmed_completion:
            keyboard.append([InlineKeyboardButton("✅ Подтвердить выполнение", callback_data=f"confirm_completion_{chat_id}")])
            keyboard.append([InlineKeyboardButton("❌ Отклонить", callback_data=f"dispute_task_{chat_id}")])
        if confirmations == 1:
            keyboard.append([InlineKeyboardButton("⏳ Ожидание второй стороны (1/2)", callback_data="noop")])
    
    if not (chat.performer_confirmed_completion and chat.customer_confirmed_completion):
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="my_chats")])
    else:
        keyboard.append([InlineKeyboardButton("⭐ Оценить", callback_data=f"rate_user_{chat.performer_id if user.id == chat.customer_id else chat.customer_id}")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="my_chats")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        chat_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    db.close()


async def send_message_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пригласить написать сообщение"""
    chat_id = context.user_data.get('current_chat_id')
    query = update.callback_query
    if query and query.message:
        mark_last_bot_message(context, query.message.message_id)
    keyboard = [
        [InlineKeyboardButton("🔙 Отменить", callback_data=f"open_chat_{chat_id}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        "📝 Введите ваше сообщение:",
        reply_markup=reply_markup
    )


async def send_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить сообщение в чат"""
    user = update.effective_user
    chat_id = context.user_data.get('current_chat_id')
    
    if not chat_id:
        keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")]]
        await send_clean_reply(
            update,
            context,
            "❌ Ошибка: чат не найден",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    db = SessionLocal()
    service = DatabaseService(db)
    chat = service.get_chat(chat_id)
    
    if not chat or user.id not in [chat.customer_id, chat.performer_id]:
        keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")]]
        await send_clean_reply(
            update,
            context,
            "❌ Ошибка: нет доступа к чату",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        db.close()
        return
    
    service.add_message(chat_id, user.id, update.message.text)
    
    recipient_id = chat.customer_id if user.id == chat.performer_id else chat.performer_id
    listing = service.get_listing(chat.listing_id)
    sender_role = "Исполнитель" if user.id == chat.performer_id else "Заказчик"
    title = listing.title if listing else "(без названия)"
    preview = update.message.text.strip()
    if len(preview) > 200:
        preview = preview[:200] + "…"
    
    try:
        await context.bot.send_message(
            chat_id=recipient_id,
            text=f"📩 Новое сообщение от {sender_role}\n\n📌 *{title}*\n\n{preview}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Открыть чат", callback_data=f"open_chat_{chat_id}")]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        print(f"Ошибка при отправке уведомления: {e}")
    
    db.close()


async def my_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать мои чаты"""
    query = update.callback_query
    user = query.from_user
    
    if query.message:
        mark_last_bot_message(context, query.message.message_id)
    
    db = SessionLocal()
    service = DatabaseService(db)
    
    # Получить чаты пользователя (как заказчик и исполнитель)
    from database.models import Chat
    chats = db.query(Chat).filter(
        (Chat.customer_id == user.id) | (Chat.performer_id == user.id)
    ).all()
    
    if not chats:
        keyboard = [
            [InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "💬 У вас нет чатов",
            reply_markup=reply_markup
        )
        return
    
    chat_text = "💬 *Мои чаты*\n\n"
    
    keyboard = []
    for chat in chats:
        listing = service.get_listing(chat.listing_id)
        role = "Заказчик" if chat.customer_id == user.id else "Исполнитель"
        
        chat_text += f"▫️ *{listing.title}* ({role})\n"
        keyboard.append([
            InlineKeyboardButton(
                f"{listing.title[:30]}...",
                callback_data=f"open_chat_{chat.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        chat_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    db.close()


async def confirm_completion_performer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Исполнитель подтверждает выполнение задания"""
    query = update.callback_query
    user = query.from_user
    
    if query.message:
        mark_last_bot_message(context, query.message.message_id)
    chat_id = int(query.data.split('_')[3])
    
    db = SessionLocal()
    service = DatabaseService(db)
    chat = service.get_chat(chat_id)
    listing = service.get_listing(chat.listing_id)
    
    # Проверка - только исполнитель может подтвердить
    if chat.performer_id != user.id:
        await query.answer("❌ Только исполнитель может подтвердить выполнение")
        db.close()
        return
    
    # Отметить что исполнитель подтвердил
    chat.performer_confirmed_completion = True
    db.commit()
    
    confirmations = int(chat.performer_confirmed_completion) + int(chat.customer_confirmed_completion)
    keyboard = [
        [InlineKeyboardButton("🔙 К чатам", callback_data="my_chats")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ Вы подтвердили выполнение задания!\n\n"
        f"Статус: выполнено ({confirmations}/2)",
        reply_markup=reply_markup
    )
    
    # Уведомить заказчика
    try:
        await context.bot.send_message(
            chat_id=chat.customer_id,
            text=f"📌 *{listing.title}*\n\n"
                 f"✅ Исполнитель подтвердил выполнение.\n\n"
                 f"Статус: выполнено ({confirmations}/2)\n\n"
                 "Подтвердите выполнение, чтобы завершить задачу.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Подтвердить выполнение", callback_data=f"confirm_completion_{chat_id}")],
                [InlineKeyboardButton("❌ Отклонить", callback_data=f"dispute_task_{chat_id}")],
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        print(f"Ошибка при отправке уведомления: {e}")
    
    db.close()


async def confirm_completion_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Заказчик подтверждает выполнение задания"""
    query = update.callback_query
    user = query.from_user
    
    if query.message:
        mark_last_bot_message(context, query.message.message_id)
    chat_id = int(query.data.split('_')[2])
    
    db = SessionLocal()
    service = DatabaseService(db)
    chat = service.get_chat(chat_id)
    listing = service.get_listing(chat.listing_id)
    
    # Проверка - только заказчик может подтвердить
    if chat.customer_id != user.id:
        await query.answer("❌ Только заказчик может подтвердить выполнение")
        db.close()
        return
    
    # Отметить что заказчик подтвердил
    chat.customer_confirmed_completion = True
    db.commit()
    
    keyboard = [
        [InlineKeyboardButton("⭐ Оценить исполнителя", callback_data=f"rate_user_{chat.performer_id}")],
        [InlineKeyboardButton("🔙 К чатам", callback_data="my_chats")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    confirmations = int(chat.performer_confirmed_completion) + int(chat.customer_confirmed_completion)
    await query.edit_message_text(
        "✅ Спасибо за подтверждение!\n\n"
        f"Статус: выполнено ({confirmations}/2)",
        reply_markup=reply_markup
    )
    
    # Завершить задание после подтверждения обеих сторон
    if chat.performer_confirmed_completion and chat.customer_confirmed_completion:
        service.complete_listing(chat.listing_id)
        
        # Уведомить исполнителя
        try:
            await context.bot.send_message(
                chat_id=chat.performer_id,
                text=f"📌 *{listing.title}*\n\n"
                     "✅ Заказчик подтвердил выполнение задания!\n\n"
                     "Задача завершена.",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            print(f"Ошибка при отправке уведомления: {e}")
    else:
        # Уведомить исполнителя, что подтверждено 1/2
        try:
            await context.bot.send_message(
                chat_id=chat.performer_id,
                text=f"📌 *{listing.title}*\n\n"
                     "✅ Заказчик подтвердил выполнение.\n\n"
                     f"Статус: выполнено ({confirmations}/2)\n\n"
                     "Подтвердите выполнение, чтобы завершить задачу.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Подтвердить выполнение", callback_data=f"confirm_completion_performer_{chat_id}")]
                ]),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            print(f"Ошибка при отправке уведомления: {e}")
    
    db.close()


async def dispute_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отклонить выполнение задания (заказчик не согласен)"""
    query = update.callback_query
    user = query.from_user
    
    if query.message:
        mark_last_bot_message(context, query.message.message_id)
    chat_id = int(query.data.split('_')[2])
    
    db = SessionLocal()
    service = DatabaseService(db)
    chat = service.get_chat(chat_id)
    listing = service.get_listing(chat.listing_id)
    
    # Проверка - только заказчик может отклонить
    if chat.customer_id != user.id:
        await query.answer("❌ Только заказчик может отклонить выполнение")
        db.close()
        return
    
    # Сбросить статус исполнителя - вернуться к работе
    chat.performer_confirmed_completion = False
    db.commit()
    
    keyboard = [
        [InlineKeyboardButton("💬 Написать причину", callback_data=f"send_message_{chat_id}")],
        [InlineKeyboardButton("🔙 К чатам", callback_data="my_chats")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚠️ Вы отклонили выполнение задания.\n\n"
        "Пожалуйста, объясните причину в чате.",
        reply_markup=reply_markup
    )
    
    # Уведомить исполнителя
    try:
        await context.bot.send_message(
            chat_id=chat.performer_id,
            text=f"📌 *{listing.title}*\n\n"
                 "⚠️ Заказчик отклонил выполнение задания.\n\n"
                 "Пожалуйста, проверьте сообщения в чате и внесите необходимые доработки.",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        print(f"Ошибка при отправке уведомления: {e}")
    
    db.close()


async def rate_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Оценить пользователя"""
    query = update.callback_query
    
    if query.message:
        mark_last_bot_message(context, query.message.message_id)
    
    rated_user_id = int(query.data.split('_')[2])
    context.user_data['rated_user_id'] = rated_user_id
    
    keyboard = [
        [InlineKeyboardButton("⭐", callback_data=f"rate_score_1_{rated_user_id}"),
         InlineKeyboardButton("⭐⭐", callback_data=f"rate_score_2_{rated_user_id}")],
        [InlineKeyboardButton("⭐⭐⭐", callback_data=f"rate_score_3_{rated_user_id}"),
         InlineKeyboardButton("⭐⭐⭐⭐", callback_data=f"rate_score_4_{rated_user_id}")],
        [InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data=f"rate_score_5_{rated_user_id}")],
        [InlineKeyboardButton("🔙 Пропустить оценку", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⭐ Оцените пользователя:",
        reply_markup=reply_markup
    )


async def rate_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить оценку"""
    query = update.callback_query
    
    if query.message:
        mark_last_bot_message(context, query.message.message_id)
    
    score = int(query.data.split('_')[2])
    context.user_data['rate_score'] = score
    
    keyboard = [
        [InlineKeyboardButton("⏭️ Готово", callback_data=f"skip_comment_{score}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📝 Напишите комментарий (опционально) или нажмите 'Готово':",
        reply_markup=reply_markup
    )


async def rate_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получить комментарий рейтинга"""
    user = update.effective_user
    
    comment = update.message.text
    score = context.user_data.get('rate_score', 5)
    rated_user_id = context.user_data.get('rated_user_id')
    
    db = SessionLocal()
    service = DatabaseService(db)
    
    service.add_rating(
        listing_id=0,  # TODO: получить из контекста
        rater_id=user.id,
        rated_user_id=rated_user_id,
        score=score,
        comment=comment,
        rating_type='performer'
    )
    
    await update.message.reply_text(
        "✅ Спасибо за оценку!"
    )
    db.close()


async def skip_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропустить комментарий при оценке"""
    query = update.callback_query
    user = query.from_user
    
    if query.message:
        mark_last_bot_message(context, query.message.message_id)
    
    score = context.user_data.get('rate_score', 5)
    rated_user_id = context.user_data.get('rated_user_id')
    
    db = SessionLocal()
    service = DatabaseService(db)
    
    # Сохранить оценку без комментария
    service.add_rating(
        listing_id=0,
        rater_id=user.id,
        rated_user_id=rated_user_id,
        score=score,
        comment="",
        rating_type='performer'
    )
    
    keyboard = [
        [InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "✅ Спасибо за оценку!",
        reply_markup=reply_markup
    )
    db.close()


async def report_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пожаловаться на пользователя"""
    query = update.callback_query
    
    if query.message:
        mark_last_bot_message(context, query.message.message_id)
    
    complained_user_id = int(query.data.split('_')[2])
    context.user_data['complained_user_id'] = complained_user_id
    
    keyboard = [
        [InlineKeyboardButton("🔙 Отменить", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📝 Напишите причину жалобы:",
        reply_markup=reply_markup
    )


async def submit_complaint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить жалобу"""
    user = update.effective_user
    reason = update.message.text
    complained_user_id = context.user_data.get('complained_user_id')
    
    db = SessionLocal()
    service = DatabaseService(db)
    
    service.create_complaint(
        listing_id=0,  # TODO: получить из контекста
        complainant_id=user.id,
        complained_user_id=complained_user_id,
        reason=reason
    )
    
    await update.message.reply_text(
        "✅ Жалоба отправлена. Спасибо!"
    )
    db.close()



