import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import httpx

# === Настройки ===
BOT_TOKEN = "8341008966:AAHxnL0qaKoyfQSve6lRoopxnjFAS7u8mUg"
OPENROUTER_API_KEY = "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"
MODEL = "qwen/qwen-2.5-7b-instruct"  # Лучший баланс: качество + скорость + бесплатно

# === Логирование ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# === Приветствие ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👷‍♂️ **Я — профессиональный строитель с 10-летним опытом.**\n\n"
        "Специализируюсь на:\n"
        "• Ремонте квартир и домов\n"
        "• Отделке (штукатурка, покраска, плитка)\n"
        "• Электромонтаже и сантехнике\n"
        "• Выборе материалов и инструментов\n"
        "• Расчёте смет и сроков\n\n"
        "⚠️ **Важно**: я отвечаю **только по теме строительства и ремонта**. "
        "На другие вопросы — вежливо откажусь.\n\n"
        "Готов помочь вам с реальной задачей — просто опишите её."
    )
    keyboard = [[InlineKeyboardButton("💬 Задать вопрос или получить консультацию", callback_data="ask")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)

# === Обработка нажатия кнопки ===
async def ask_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📝 Напишите ваш вопрос по строительству или ремонту. Например:\n\n"
        "• Как выровнять стены гипсокартоном?\n"
        "• Нужна ли гидроизоляция в ванной под плитку?\n"
        "• Какой краской покрасить деревянный пол?\n\n"
        "Я дам развернутый, профессиональный ответ."
    )
    # Сохраняем состояние: пользователь в режиме консультации
    context.user_data["in_consultation"] = True

# === Обработка текстовых сообщений ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Если пользователь не в режиме консультации — игнорируем (или можно отправить /start)
    if not context.user_data.get("in_consultation", False):
        await start(update, context)
        return

    user_text = update.message.text.strip()
    
    # Системный промпт — строго по теме
    system_prompt = (
    "Ты — профессиональный строитель с 10-летним опытом. "
    "Ты отвечаешь ТОЛЬКО на вопросы по строительству и ремонту. "
    "ВСЕГДА отвечай ТОЛЬКО на русском языке, даже если вопрос задан на другом языке. "
    "Если вопрос не по теме — вежливо скажи, что ты специалист только в строительстве. "
    "Отвечай чётко, по делу, без воды. Используй профессиональную терминологию, но объясняй, если нужно. "
    "Максимальная длина ответа — 500 слов."
)

    full_prompt = f"{system_prompt}\n\nВопрос клиента: {user_text}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": full_prompt}],
                    "max_tokens": 800
                }
            )
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")

            data = response.json()
            answer = data["choices"][0]["message"]["content"].strip()

            # Добавим кнопку "Задать ещё вопрос"
            keyboard = [[InlineKeyboardButton("🔄 Задать уточняющий или новый вопрос", callback_data="ask")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                answer,
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )

    except Exception as e:
        logging.error(f"Ошибка ИИ: {e}")
        await update.message.reply_text(
            "⚠️ Не удалось получить ответ. Возможно, временные проблемы с сервисом. "
            "Попробуйте через минуту или переформулируйте вопрос."
        )

# === Flask + Webhook ===
app = Flask(__name__)

# Инициализация Telegram-бота
application = Application.builder().token(BOT_TOKEN).build()

# Регистрация обработчиков
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(ask_callback, pattern="^ask$"))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Event loop для асинхронных вызовов
_loop = asyncio.new_event_loop()
asyncio.set_event_loop(_loop)
_loop.run_until_complete(application.initialize())

@app.route("/<path:token>", methods=["POST"])
def telegram_webhook(token):
    if token != BOT_TOKEN:
        return "Forbidden", 403
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    _loop.run_until_complete(application.process_update(update))
    return "OK"

@app.route("/health")
def health():
    return "OK"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
