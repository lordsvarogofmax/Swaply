import os
import logging
import asyncio
import threading  # добавь в импорты, если ещё не там
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

# === Состояния диалога (обязательно до использования) ===
START, QUERY, CITY, EXCHANGE, PAYMENT = range(5)

# === Логирование ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# === Настройки ===
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

# === Обработчики ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🚀 Поехали", callback_data="start_search")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Привет! Я — твой помощник в мире Avito.\n\n"
        "Я помогу быстро найти свежие объявления по твоему запросу — "
        "с учётом города, обмена и доплаты.\n\n"
        "Готов начать?",
        reply_markup=reply_markup
    )
    return START

async def start_search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔍 Что нужно найти? (например: *велосипед*, *iPhone 13*, *коляска*)")
    return QUERY

async def get_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Пожалуйста, введи, что нужно найти.")
        return QUERY
    context.user_data["query"] = text
    buttons = [[InlineKeyboardButton(city, callback_data=f"city_{city}")] for city in CITIES.keys()]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("🏙 В каком городе искать?", reply_markup=reply_markup)
    return CITY

async def city_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    city_name = query.data.replace("city_", "")
    if city_name not in CITIES:
        await query.edit_message_text("❌ Город не поддерживается.")
        return ConversationHandler.END
    context.user_data["city"] = city_name
    keyboard = [
        [InlineKeyboardButton("Да", callback_data="exchange_yes")],
        [InlineKeyboardButton("Нет", callback_data="exchange_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("🔄 Хочешь обмен?", reply_markup=reply_markup)
    return EXCHANGE

async def exchange_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    if choice == "exchange_no":
        context.user_data["exchange"] = False
        await generate_avito_link(update, context)
        return ConversationHandler.END
    else:
        context.user_data["exchange"] = True
        keyboard = [
            [InlineKeyboardButton("С доплатой", callback_data="payment_yes")],
            [InlineKeyboardButton("Без доплаты", callback_data="payment_no")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("💰 С доплатой или без?", reply_markup=reply_markup)
        return PAYMENT

async def payment_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    context.user_data["with_payment"] = (choice == "payment_yes")
    await generate_avito_link(update, context)
    return ConversationHandler.END

async def generate_avito_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = context.user_data["query"]
    city_name = context.user_data["city"]
    city_code = CITIES[city_name]
    exchange = context.user_data.get("exchange", False)
    with_payment = context.user_data.get("with_payment", False)

    search_terms = [query]
    if exchange:
        search_terms.append("обмен")
        if with_payment:
            search_terms.append("доплата")
        else:
            search_terms.append("без доплаты")

    full_query = " ".join(search_terms)
    safe_query = full_query.replace(" ", "+")
    avito_url = f"https://www.avito.ru/{city_code}?q={safe_query}&s=104"

    message = (
        "✅ Готово! Вот твоя персональная ссылка на свежие объявления:\n\n"
        f"🔗 <a href='{avito_url}'>Открыть на Avito</a>\n\n"
        "💡 Совет: нажми «🔔 Подписаться на поиск» внизу страницы, "
        "чтобы получать уведомления о новых объявлениях."
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            message, parse_mode="HTML", disable_web_page_preview=True
        )
    else:
        await update.message.reply_text(
            message, parse_mode="HTML", disable_web_page_preview=True
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Поиск отменён. Напиши /start, чтобы начать заново.")
    return ConversationHandler.END

# === Flask + Webhook ===

app = Flask(__name__)

# Инициализация Telegram-бота
application = Application.builder().token(BOT_TOKEN).build()

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

_webhook_set = threading.Event()

@app.before_request
def setup_webhook_once():
    if not _webhook_set.is_set():
        with app.app_context():
            render_url = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
            webhook_url = f"{render_url}/{BOT_TOKEN}"
            asyncio.run(application.bot.set_webhook(url=webhook_url))
            logging.info(f"Webhook установлен: {webhook_url}")
            _webhook_set.set()

@app.route("/<path:token>", methods=["POST"])
def telegram_webhook(token):
    if token != BOT_TOKEN:
        return "Forbidden", 403
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "OK"

@app.route("/health")
def health():
    return "OK"

# === Запуск ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
