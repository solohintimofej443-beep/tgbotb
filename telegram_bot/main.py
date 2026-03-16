import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, PreCheckoutQueryHandler
from telegram import Update
from config import BOT_TOKEN
from database.db import init_db
from handlers.commands import (
    start, my_profile, create_listing_start, create_listing_title, create_listing_desc,
    create_listing_anonymous, view_listings,
    listing_detail, respond_listing, delete_listing, back_to_menu, go_back, my_reviews, CREATE_LISTING_TITLE, CREATE_LISTING_DESC,
    CREATE_LISTING_ANONYMOUS
)
from handlers.chat import (
    open_chat, send_message_prompt, send_message, my_chats, confirm_completion_performer,
    confirm_completion_customer, dispute_task, rate_user, rate_score, skip_comment, rate_comment, report_user, submit_complaint
)
from handlers.payment import pre_checkout_query, successful_payment, buy_stars
from handlers.admin import (
    admin_panel, admin_stats, admin_complaints, admin_complaint_detail,
    admin_resolve_complaint, admin_users, admin_user_detail, admin_block_user,
    admin_unblock_user, admin_blocks, admin_listings, admin_panel_back, is_admin,
    admin_free_listings, grant_free_listing, admin_listing_detail, admin_delete_listing
)
from utils.message_cleaner import cleanup_user_message

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Запустить бота"""
    # Инициализировать БД
    init_db()
    
    # Создать приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # ConversationHandler для создания объявления
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(create_listing_start, pattern='^create_listing$')],
        states={
            CREATE_LISTING_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_listing_title),
                CallbackQueryHandler(back_to_menu, pattern='^back_to_menu$')
            ],
            CREATE_LISTING_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_listing_desc),
                CallbackQueryHandler(back_to_menu, pattern='^back_to_menu$')
            ],
            CREATE_LISTING_ANONYMOUS: [
                CallbackQueryHandler(create_listing_anonymous, pattern='^anonymous_|^back_to_menu$')
            ],
        },
        fallbacks=[CommandHandler('start', start)]
    )
    
    # Добавить обработчики
    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_handler)
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(my_profile, pattern='^my_profile$'))
    application.add_handler(CallbackQueryHandler(my_reviews, pattern='^my_reviews$'))
    application.add_handler(CallbackQueryHandler(view_listings, pattern='^view_listings($|_page_)'))
    application.add_handler(CallbackQueryHandler(listing_detail, pattern='^listing_detail_'))
    application.add_handler(CallbackQueryHandler(delete_listing, pattern='^delete_listing_'))
    application.add_handler(CallbackQueryHandler(respond_listing, pattern='^respond_listing_'))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern='^back_to_menu$'))
    application.add_handler(CallbackQueryHandler(go_back, pattern='^go_back$'))
    application.add_handler(CallbackQueryHandler(my_chats, pattern='^my_chats$'))
    application.add_handler(CallbackQueryHandler(open_chat, pattern='^open_chat_'))
    application.add_handler(CallbackQueryHandler(send_message_prompt, pattern='^send_message_'))
    application.add_handler(CallbackQueryHandler(confirm_completion_performer, pattern='^confirm_completion_performer_'))
    application.add_handler(CallbackQueryHandler(confirm_completion_customer, pattern='^confirm_completion_'))
    application.add_handler(CallbackQueryHandler(dispute_task, pattern='^dispute_task_'))
    application.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer("⏳ Ожидание подтверждения...", show_alert=False), pattern='^noop$'))
    application.add_handler(CallbackQueryHandler(rate_user, pattern='^rate_user_'))
    application.add_handler(CallbackQueryHandler(rate_score, pattern='^rate_score_'))
    application.add_handler(CallbackQueryHandler(skip_comment, pattern='^skip_comment_'))
    application.add_handler(CallbackQueryHandler(report_user, pattern='^report_user_'))
    application.add_handler(CallbackQueryHandler(buy_stars, pattern='^buy_stars$'))
    
    # Admin handlers
    application.add_handler(CommandHandler('admin', admin_panel))
    application.add_handler(CallbackQueryHandler(admin_panel, pattern='^admin_panel$'))
    application.add_handler(CallbackQueryHandler(admin_stats, pattern='^admin_stats$'))
    application.add_handler(CallbackQueryHandler(admin_complaints, pattern='^admin_complaints$'))
    application.add_handler(CallbackQueryHandler(admin_complaint_detail, pattern='^admin_complaint_detail_'))
    application.add_handler(CallbackQueryHandler(admin_resolve_complaint, pattern='^admin_resolve_complaint_'))
    application.add_handler(CallbackQueryHandler(admin_users, pattern='^admin_users$'))
    application.add_handler(CallbackQueryHandler(admin_user_detail, pattern='^admin_user_detail_'))
    application.add_handler(CallbackQueryHandler(admin_block_user, pattern='^admin_block_user_'))
    application.add_handler(CallbackQueryHandler(admin_unblock_user, pattern='^admin_unblock_user_'))
    application.add_handler(CallbackQueryHandler(admin_blocks, pattern='^admin_blocks$'))
    application.add_handler(CallbackQueryHandler(admin_listings, pattern='^admin_listings$'))
    application.add_handler(CallbackQueryHandler(admin_listing_detail, pattern='^admin_listing_detail_'))
    application.add_handler(CallbackQueryHandler(admin_delete_listing, pattern='^admin_delete_listing_'))
    application.add_handler(CallbackQueryHandler(admin_free_listings, pattern='^admin_free_listings$'))
    application.add_handler(CallbackQueryHandler(grant_free_listing, pattern='^grant_free_'))
    application.add_handler(CallbackQueryHandler(admin_panel_back, pattern='^admin_panel_back$'))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_message))
    application.add_handler(MessageHandler(filters.ALL, cleanup_user_message, block=False), group=99)
    
    # Payment handlers
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_query))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    
    # Запустить бота
    logger.info("Бот запущен!")
    application.run_polling(allowed_updates=['message', 'callback_query', 'pre_checkout_query', 'successful_payment'])


if __name__ == '__main__':
    main()
