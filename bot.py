import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)

# Включи логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Состояния диалога
GIVE, WANT = range(2)

# Токен бота (обязательно замени!)
BOT_TOKEN = "8341008966:AAHxnL0qaKoyfQSve6lRoopxnjFAS7u8mUg"

# Хранилище заявок (в реальности — Google Sheets или БД)
users_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я — Swaply, бот для честного обмена вещами без денег.\n\n"
        "Готов начать? Напиши, что ты хочешь ОТДАТЬ."
    )
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

    # Отправить админу (замени YOUR_ADMIN_ID на свой ID)
    admin_message = (
        f"🆕 Новый обмен!\n"
        f"Пользователь: @{update.message.from_user.username or 'нет username'} (ID: {user_id})\n"
        f"Отдаёт: {users_data[user_id]['give']}\n"
        f"Хочет: {users_data[user_id]['want']}"
    )

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
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
