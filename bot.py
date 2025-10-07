import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

# Включи логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Состояния диалога
GIVE, WANT = range(2)

# Твой токен от BotFather (лучше брать из переменных окружения!)
BOT_TOKEN = "8341008966:AAHxnL0qaKoyfQSve6lRoopxnjFAS7u8mUg"

# Простое хранилище (в реальности — Google Таблица или БД)
users_data = {}  # {user_id: {"give": "...", "want": "..."}}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 Привет! Я — Swaply, бот для честного обмена вещами.\n\n"
        "Готов начать? Напиши, что ты хочешь ОТДАТЬ."
    )
    await update.message.reply_text(welcome_text)
    return GIVE

async def get_give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    give_text = update.message.text
    users_data[user_id] = {"give": give_text}
    await update.message.reply_text(
        "🔄 Отлично! А что ты хочешь ПОЛУЧИТЬ взамен?\n\n"
        "Пример: «Детский велосипед, доплачу 1000 ₽»"
    )
    return WANT

async def get_want(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    want_text = update.message.text
    users_data[user_id]["want"] = want_text

    # Здесь можно отправить данные тебе (админу)
    admin_message = (
        f"🆕 Новый обмен!\n"
        f"Пользователь: @{update.message.from_user.username or 'нет username'} (ID: {user_id})\n"
        f"Отдаёт: {users_data[user_id]['give']}\n"
        f"Хочет: {users_data[user_id]['want']}"
    )

    # Отправить себе (админу) — замени на свой Telegram ID
    YOUR_ADMIN_ID = 364191893  # ← ЗАМЕНИ НА СВОЙ ID!
    await context.bot.send_message(chat_id=YOUR_ADMIN_ID, text=admin_message)

    await update.message.reply_text(
        "🎉 Спасибо! Я передал твой запрос.\n"
        "Как только найду подходящий обмен — напишу!\n\n"
        "P.S. Хочешь добавить ещё один обмен? Напиши /start"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Обмен отменён. Напиши /start, чтобы начать заново.")
    return ConversationHandler.END

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GIVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_give)],
            WANT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_want)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
