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
MODEL = "meta-llama/llama-3.1-70b-instruct"

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
    context.user_data["in_consultation"] = True

# === Обработка текстовых сообщений ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("in_consultation", False):
        await start(update, context)
        return

    user_text = update.message.text.strip()

    system_prompt = (
    "Ты — профессиональный строитель с 10-летним опытом. "
    "Ты отвечаешь ТОЛЬКО на вопросы по строительству и ремонту. "
    "Если вопрос не по теме — вежливо откажись и напомни, что ты специалист только в строительстве. "
    "ОТВЕЧАЙ ТОЛЬКО НА РУССКОМ ЯЗЫКЕ. НИКАКИХ КИТАЙСКИХ ИЕРОГЛИФОВ. НИКАКОГО АНГЛИЙСКОГО, КРОМЕ ОБЩЕПРИНЯТЫХ АББРЕВИАТУР (LED, PVC, ГКЛ). "
    "НЕ ПИШИ РАССУЖДЕНИЯ. НЕ ИСПОЛЬЗУЙ ФРАЗЫ ВРОДЕ «Я думаю», «Мне кажется», «Как строитель, я рекомендую». "
    "ПИШИ КАК ЭКСПЕРТ: КРАТКО, ТОЧНО, ПО ДЕЛУ. "
    "НЕ ОБРЫВАЙ ОТВЕТ НА ПОЛУСЛОВЕ. ЗАВЕРШАЙ МЫСЛЬ. "
    "МАКСИМУМ — 400 слов."
)

    if "chat_history" not in context.user_data:
        context.user_data["chat_history"] = []
    context.user_data["chat_history"].append({"role": "user", "content": user_text})
    if len(context.user_data["chat_history"]) > 5:
        context.user_data["chat_history"] = context.user_data["chat_history"][-5:]

    history_str = "\n".join([
        f"{msg['role'].capitalize()}: {msg['content']}" 
        for msg in context.user_data["chat_history"]
    ])
    full_prompt = f"{system_prompt}\n\nИстория диалога:\n{history_str}\n\nНовый вопрос: {user_text}\n\nОтветь на русском языке, без лишних слов."

    await update.message.reply_text("⏳ Минутку, мне нужно подумать...")

    logging.info(f"Отправляю запрос к OpenRouter: {full_prompt[:200]}...")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",  # ← УБРАНЫ ЛИШНИЕ ПРОБЕЛЫ!
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": full_prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.3         # ← добавлено (0.0–1.0; 0.3 = стабильно)
                }
            )
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")

            data = response.json()
            answer = data["choices"][0]["message"]["content"].strip()

            logging.info(f"Получен ответ от OpenRouter: {answer[:200]}")

            keyboard = [[InlineKeyboardButton("🔄 Задать ещё вопрос", callback_data="ask")]]
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

application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(ask_callback, pattern="^ask$"))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

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
