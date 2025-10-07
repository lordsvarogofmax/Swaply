import os
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8341008966:AAHxnL0qaKoyfQSve6lRoopxnjFAS7u8mUg"
CITIES = {
    "Москва": "moskva",
    "Санкт-Петербург": "sankt-peterburg",
    "Новосибирск": "novosibirsk",
    "Екатеринбург": "ekaterinburg",
    "Казань": "kazan",
    "Нижний Новгород": "nizhniy_novgorod",
    "Самара": "samara",
    "Омск": "omsk",
    "Ростов-на-Дону": "rostov-na-donu",
    "Уфа": "ufa",
}

# === ВСЕ ФУНКЦИИ ОБРАБОТЧИКОВ (start, get_query и т.д.) ===
# (вставь сюда все функции из предыдущего кода — они не меняются)

# Создаём Flask-приложение
app = Flask(__name__)

# Инициализируем Telegram-бота
application = Application.builder().token(BOT_TOKEN).build()

# Добавляем обработчики (как раньше)
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        START: [CallbackQueryHandler(start_search_callback, pattern="^start_search$")],
        QUERY: [MessageHandler(~filters.COMMAND, get_query)],
        CITY: [CallbackQueryHandler(city_selected, pattern="^city_")],
        EXCHANGE: [CallbackQueryHandler(exchange_selected, pattern="^exchange_(yes|no)$")],
        PAYMENT: [CallbackQueryHandler(payment_selected, pattern="^payment_(yes|no)$")],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
application.add_handler(conv_handler)

# Устанавливаем webhook при запуске
@app.before_first_request
def setup_webhook():
    webhook_url = f"{os.environ.get('RENDER_EXTERNAL_URL')}/{BOT_TOKEN}"
    application.bot.set_webhook(url=webhook_url)
    logging.info(f"Webhook установлен: {webhook_url}")

# Обработчик входящих обновлений
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "OK"

# Health-check для Render
@app.route("/health")
def health():
    return "OK"

if __name__ == "__main__":
    # Локально — polling
    if os.environ.get("RENDER_EXTERNAL_URL"):
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
    else:
        application.run_polling()
