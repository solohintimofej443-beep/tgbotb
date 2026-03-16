from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest


async def delete_message_safe(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


async def delete_last_bot_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not chat:
        return
    last_id = context.user_data.get("last_bot_message_id")
    if last_id:
        await delete_message_safe(context, chat.id, last_id)
        context.user_data.pop("last_bot_message_id", None)


def mark_last_bot_message(context: ContextTypes.DEFAULT_TYPE, message_id: int):
    if message_id:
        context.user_data["last_bot_message_id"] = message_id


async def send_clean_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None, parse_mode=None):
    await delete_last_bot_message(update, context)
    msg = await update.effective_chat.send_message(
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode
    )
    mark_last_bot_message(context, msg.message_id)
    return msg


async def cleanup_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await delete_message_safe(context, update.message.chat_id, update.message.message_id)


async def edit_message_text_safe(query, text, reply_markup=None, parse_mode=None):
    try:
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    except BadRequest as e:
        if "message is not modified" in str(e).lower():
            return
        raise
