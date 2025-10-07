import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
    CallbackQueryHandler,
)

# Включи логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Состояния диалога
GIVE, WANT = range(2)
SEARCH_QUERY, SEARCH_REGION = range(2, 4)

# Токен бота
BOT_TOKEN = "8341008966:AAHxnL0qaKoyfQSve6lRoopxnjFAS7u8mUg"

# Поддерживаемые регионы Авито (английские URL)
AVITO_REGIONS = {
    "москва": "moskva",
    "санкт-петербург": "sankt-peterburg",
    "новосибирск": "novosibirsk",
    "екатеринбург": "ekaterinburg",
    "казань": "kazan",
    "нижний новгород": "nizhniy_novgorod",
    "самара": "samara",
    "омск": "omsk",
    "ростов-на-дону": "rostov-na-donu",
    "уфа": "ufa",
}

# Хранилище заявок (в реальности — Google Sheets или БД)
users_data = {}

# === СТАРЫЙ ФУНКЦИОНАЛ: ОБМЕН ===
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

# === НОВЫЙ ФУНКЦИОНАЛ: ПОИСК НА АВИТО ===
async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 Давай найдём объявления об обмене на Авито!\n\n"
        "Что ты хочешь найти? (например: *велосипед*, *iPhone*, *коляска*)"
    )
    return SEARCH_QUERY

async def get_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if not query:
        await update.message.reply_text("Пожалуйста, введи, что ты ищешь.")
        return SEARCH_QUERY

    context.user_data["search_query"] = query

    # Кнопки выбора региона
    buttons = []
    row = []
    for region in AVITO_REGIONS.keys():
        row.append(InlineKeyboardButton(region.title(), callback_data=f"region_{region}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Выбери регион:", reply_markup=reply_markup)
    return SEARCH_REGION

async def region_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    region_key = query.data.replace("region_", "")
    if region_key not in AVITO_REGIONS:
        await query.edit_message_text("❌ Регион не поддерживается.")
        return ConversationHandler.END

    search_query = context.user_data.get("search_query", "")
    avito_region = AVITO_REGIONS[region_key]

    # Формируем запрос: "[то, что ищешь] обмен"
    full_query = f"{search_query} обмен"
    safe_query = full_query.replace(" ", "+")

    rss_url = f"https://www.avito.ru/{avito_region}?q={safe_query}&rss=1"
    search_url = f"https://www.avito.ru/{avito_region}?q={safe_query}&s=104"

    message = (
        f"✅ Готово! Вот твоя RSS-ссылка для отслеживания объявлений со словом «обмен»:\n\n"
        f"📎 <a href='{rss_url}'>RSS-лента на Авито</a>\n\n"
        f"🔍 <a href='{search_url}'>Открыть поиск в браузере</a>\n\n"
        f"💡 Совет: перейди по ссылке и нажми «🔔 Подписаться на поиск», "
        f"чтобы получать уведомления о новых объявлениях."
    )

    await query.edit_message_text(message, parse_mode="HTML", disable_web_page_preview=True)
    return ConversationHandler.END

# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Действие отменено. Напиши /start или /search.")
    return ConversationHandler.END

# Запуск
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Обработчик обмена
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GIVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_give)],
            WANT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_want)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Обработчик поиска
    search_handler = ConversationHandler(
        entry_points=[CommandHandler("search", search_start)],
        states={
            SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_search_query)],
            SEARCH_REGION: [CallbackQueryHandler(region_selected)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(search_handler)
    application.add_handler(CommandHandler("cancel", cancel))

    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
