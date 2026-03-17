from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import ADMIN_IDS, SUPER_ADMIN_ID
from database.db import SessionLocal
from utils.database_service import DatabaseService
from utils.message_cleaner import send_clean_reply, mark_last_bot_message
from database.models import User, Complaint


def is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь администратором"""
    return user_id in ADMIN_IDS or user_id == SUPER_ADMIN_ID


def is_super_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь суперадминистратором"""
    return user_id == SUPER_ADMIN_ID


async def admin_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Проверить права администратора"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        if update.callback_query:
            await update.callback_query.answer("❌ Доступ запрещён. Вы не администратор.", show_alert=True)
        elif update.effective_message:
            await update.effective_message.reply_text("❌ Доступ запрещён. Вы не администратор.")
        return False
    return True


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать панель администратора"""
    user_id = update.effective_user.id
    
    if not await admin_check(update, context):
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("⚠️ Жалобы", callback_data="admin_complaints")],
        [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("🚫 Блокировки", callback_data="admin_blocks")],
        [InlineKeyboardButton("💼 Задания", callback_data="admin_listings")],
        [InlineKeyboardButton("💳 Бесплатные публикации", callback_data="admin_free_listings")],
    ]
    
    if is_super_admin(user_id):
        keyboard.append([InlineKeyboardButton("⚙️ Супер-настройки", callback_data="admin_super")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        f"🔐 *Панель администратора*\n\n"
        f"Пользователь: {update.effective_user.first_name}\n"
        f"ID: `{user_id}`"
    )
    if update.callback_query:
        if update.callback_query.message:
            mark_last_bot_message(context, update.callback_query.message.message_id)
        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await send_clean_reply(
            update,
            context,
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ Доступ запрещён")
        return
    
    db = SessionLocal()
    service = DatabaseService(db)
    
    # Получить статистику
    total_users = db.query(User).count()
    blocked_users = db.query(User).filter(User.is_blocked == True).count()
    
    from database.models import Listing, Chat, Rating, Complaint
    total_listings = db.query(Listing).count()
    active_listings = db.query(Listing).filter(Listing.status == 'active').count()
    total_chats = db.query(Chat).count()
    total_ratings = db.query(Rating).count()
    total_complaints = db.query(Complaint).count()
    
    stats_text = f"""
📊 *Статистика системы*

👥 *Пользователи:*
   Всего: {total_users}
   Заблокировано: {blocked_users}

📋 *Задания:*
   Всего: {total_listings}
   Активные: {active_listings}

💬 *Чаты:* {total_chats}
⭐ *Отзывы:* {total_ratings}
⚠️ *Жалобы:* {total_complaints}
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 Вернуться", callback_data="admin_panel_back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        stats_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    db.close()


async def admin_complaints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр жалоб"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ Доступ запрещён")
        return
    
    db = SessionLocal()
    service = DatabaseService(db)
    
    from database.models import Complaint
    complaints = db.query(Complaint).filter(Complaint.status == 'open').all()
    
    if not complaints:
        await query.edit_message_text("✅ Открытых жалоб нет")
        return
    
    complaints_text = f"⚠️ *Жалобы ({len(complaints)})*\n\n"
    
    keyboard = []
    for complaint in complaints[:10]:
        user_complained = service.get_user(complaint.complained_user_id)
        complaints_text += f"▫️ ID: {complaint.id}\n"
        complaints_text += f"   На пользователя: {user_complained.first_name if user_complained else 'Unknown'}\n"
        complaints_text += f"   Причина: {complaint.reason[:50]}...\n\n"
        
        keyboard.append([
            InlineKeyboardButton(
                f"📋 Жалоба #{complaint.id}",
                callback_data=f"admin_complaint_detail_{complaint.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Вернуться", callback_data="admin_panel_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        complaints_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    db.close()


async def admin_complaint_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Детали жалобы"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ Доступ запрещён")
        return
    
    complaint_id = int(query.data.split('_')[3])
    
    db = SessionLocal()
    service = DatabaseService(db)
    
    from database.models import Complaint
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    
    if not complaint:
        await query.answer("Жалоба не найдена")
        return
    
    complainant = service.get_user(complaint.complainant_id)
    complained = service.get_user(complaint.complained_user_id)
    
    detail_text = f"""
⚠️ *Деталь жалобы #{complaint.id}*

👤 *От:* {complainant.first_name if complainant else 'Unknown'} (ID: {complaint.complainant_id})
👤 *На:* {complained.first_name if complained else 'Unknown'} (ID: {complaint.complained_user_id})

📝 *Причина:*
{complaint.reason}

📅 *Дата:* {complaint.created_at.strftime('%d.%m.%Y %H:%M')}
📊 *Статус:* {complaint.status}
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_resolve_complaint_{complaint_id}_resolved")],
        [InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_resolve_complaint_{complaint_id}_dismissed")],
        [InlineKeyboardButton("🔙 Вернуться", callback_data="admin_complaints")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        detail_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    db.close()


async def admin_resolve_complaint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Разрешить жалобу"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ Доступ запрещён")
        return
    
    parts = query.data.split('_')
    complaint_id = int(parts[3])
    status = parts[4]
    
    db = SessionLocal()
    service = DatabaseService(db)
    
    service.resolve_complaint(complaint_id, status)
    
    await query.answer(f"✅ Жалоба {status.title()}")
    await admin_complaints(update, context)
    db.close()


async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр пользователей"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ Доступ запрещён")
        return
    
    db = SessionLocal()
    service = DatabaseService(db)
    
    users = db.query(User).order_by(User.created_at.desc()).limit(20).all()
    
    users_text = f"👥 *Пользователи ({len(users)})*\n\n"
    
    keyboard = []
    for user in users:
        status = "🚫 Заблокирован" if user.is_blocked else "✅ Активен"
        users_text += f"▫️ {user.first_name} (ID: {user.user_id})\n"
        users_text += f"   {status}\n"
        users_text += f"   ⭐ К: {user.rating_as_customer:.1f}★ И: {user.rating_as_performer:.1f}★\n\n"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{user.first_name}",
                callback_data=f"admin_user_detail_{user.user_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Вернуться", callback_data="admin_panel_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        users_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    db.close()


async def admin_user_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Детали пользователя"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ Доступ запрещён")
        return
    
    user_id_to_check = int(query.data.split('_')[3])
    
    db = SessionLocal()
    service = DatabaseService(db)
    
    user = service.get_user(user_id_to_check)
    
    if not user:
        await query.answer("Пользователь не найден")
        return
    
    detail_text = f"""
👤 *Пользователь: {user.first_name} {user.last_name or ''}*

📊 *Информация:*
   ID: `{user.user_id}`
   Создан: {user.created_at.strftime('%d.%m.%Y %H:%M')}
   
⭐ *Рейтинг:*
   Как заказчик: {user.rating_as_customer:.1f}★ ({user.reviews_as_customer})
   Как исполнитель: {user.rating_as_performer:.1f}★ ({user.reviews_as_performer})
   
⚠️ *Жалоб:* {user.complaints_count}/3
💳 *Баланс:* {user.stars_balance}★
🚫 *Статус:* {'Заблокирован' if user.is_blocked else 'Активен'}
"""
    
    keyboard = []
    if not user.is_blocked:
        keyboard.append([InlineKeyboardButton("🚫 Заблокировать", callback_data=f"admin_block_user_{user_id_to_check}")])
    else:
        keyboard.append([InlineKeyboardButton("✅ Разблокировать", callback_data=f"admin_unblock_user_{user_id_to_check}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Вернуться", callback_data="admin_users")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        detail_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    db.close()


async def admin_block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Заблокировать пользователя"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ Доступ запрещён")
        return
    
    user_id_to_block = int(query.data.split('_')[3])
    
    db = SessionLocal()
    service = DatabaseService(db)
    service.block_user(user_id_to_block)
    
    await query.answer("✅ Пользователь заблокирован")
    
    # Обновить информацию
    user = service.get_user(user_id_to_block)
    context.user_data['selected_user_id'] = user_id_to_block
    await admin_user_detail(update, context)
    db.close()


async def admin_unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Разблокировать пользователя"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ Доступ запрещён")
        return
    
    user_id_to_unblock = int(query.data.split('_')[3])
    
    db = SessionLocal()
    service = DatabaseService(db)
    
    user = service.get_user(user_id_to_unblock)
    if user:
        user.is_blocked = False
        db.commit()
    
    await query.answer("✅ Пользователь разблокирован")
    
    # Обновить информацию
    context.user_data['selected_user_id'] = user_id_to_unblock
    await admin_user_detail(update, context)
    db.close()


async def admin_blocks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать заблокированных пользователей"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ Доступ запрещён")
        return
    
    db = SessionLocal()
    service = DatabaseService(db)
    
    blocked = db.query(User).filter(User.is_blocked == True).all()
    
    if not blocked:
        await query.edit_message_text("✅ Нет заблокированных пользователей")
        return
    
    blocks_text = f"🚫 *Заблокированные пользователи ({len(blocked)})*\n\n"
    
    keyboard = []
    for user in blocked:
        blocks_text += f"▫️ {user.first_name} (ID: {user.user_id})\n"
        blocks_text += f"   Жалоб: {user.complaints_count}/3\n\n"
        keyboard.append([
            InlineKeyboardButton(
                f"{user.first_name}",
                callback_data=f"admin_user_detail_{user.user_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Вернуться", callback_data="admin_panel_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        blocks_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    db.close()


async def admin_listings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр заданий"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ Доступ запрещён")
        return
    
    db = SessionLocal()
    service = DatabaseService(db)
    
    from database.models import Listing
    listings = db.query(Listing).order_by(Listing.created_at.desc()).limit(20).all()
    
    listings_text = f"📋 *Задания ({len(listings)})*\n\n"
    
    keyboard = []
    for listing in listings:
        listings_text += f"▫️ {listing.title} (ID: {listing.id})\n"
        listings_text += f"   Статус: {listing.status}\n"
        listings_text += "   Цена: не указана\n\n"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{listing.title[:20]}...",
                callback_data=f"admin_listing_detail_{listing.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Вернуться", callback_data="admin_panel_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        listings_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    db.close()


async def admin_listing_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Детали Задания"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ Доступ запрещён")
        return
    
    listing_id = int(query.data.split('_')[3])
    
    db = SessionLocal()
    from database.models import Listing
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    
    if not listing:
        await query.answer("Задание не найдено")
        db.close()
        return
    
    detail_text = f"""
📌 *{listing.title}* (ID: {listing.id})

📝 *Описание:*
{listing.description}

👤 *Заказчик ID:* {listing.customer_id}
👤 *Исполнитель ID:* {listing.performer_id or '—'}

📊 *Статус:* {listing.status}
📅 *Создано:* {listing.created_at.strftime('%d.%m.%Y %H:%M')}
"""
    
    keyboard = [
        [InlineKeyboardButton("🗑 Удалить Задание", callback_data=f"admin_delete_listing_{listing.id}")],
        [InlineKeyboardButton("🔙 Вернуться", callback_data="admin_listings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        detail_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    db.close()


async def admin_delete_listing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить Задание"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ Доступ запрещён")
        return
    
    listing_id = int(query.data.split('_')[3])
    
    db = SessionLocal()
    from database.models import Listing, Chat, Message, Rating, Complaint, Transaction
    
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        await query.answer("Задание не найдено")
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
    await admin_listings(update, context)
    db.close()


async def admin_panel_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуть в админ-панель"""
    await admin_panel(update, context)


async def admin_free_listings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление бесплатными публикациями"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ Доступ запрещён")
        return
    
    db = SessionLocal()
        
    # Получить список пользователей с их счётчиками  
    from database.models import User
    users = db.query(User).order_by(User.listings_count.desc()).limit(20).all()
    
    text = "💳 *Управление бесплатными публикациями*\n\n"
    text += "Топ пользователей по Заданиям:\n\n"
    
    keyboard = []
    for u in users:
        text += f"▫️ {u.first_name} (ID: {u.user_id})\n"
        text += f"   заданий: {u.listings_count}\n"
        text += f"   Бесплатных осталось: {u.free_listings_remaining}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(
                f"➕ {u.first_name[:15]}...",
                callback_data=f"grant_free_{u.user_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_panel_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    db.close()


async def grant_free_listing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Дать бесплатную публикацию пользователю"""
    query = update.callback_query
    target_user_id = int(query.data.split('_')[2])
    
    from handlers.admin import is_admin
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ Доступ запрещён")
        return
    
    db = SessionLocal()
    service = DatabaseService(db)
    
    user = service.get_user(target_user_id)
    
    if not user:
        await query.answer(f"❌ Пользователь с ID {target_user_id} не найден!", show_alert=True)
        db.close()
        return
    
    # Дать 1 бесплатное Задание
    user.free_listings_remaining += 1
    db.commit()
    
    await query.answer(f"✅ Дана 1 бесплатная публикация пользователю {user.first_name}", show_alert=True)
    
    # Вернуться к списку
    await admin_free_listings(update, context)
    db.close()


