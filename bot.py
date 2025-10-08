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
import gdown
from PyPDF2 import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# === Настройки ===
BOT_TOKEN = "8341008966:AAHxnL0qaKoyfQSve6lRoopxnjFAS7u8mUg"
OPENROUTER_API_KEY = "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"
MODEL = "meta-llama/llama-3.1-70b-instruct"

# === Логирование ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# === Глобальные переменные для RAG ===
_knowledge_chunks = []
_vectorizer = None
_knowledge_ready = False

# === Функция: скачать PDF из Google Drive ===
def download_knowledge_base():
    knowledge_dir = "knowledge_base"
    os.makedirs(knowledge_dir, exist_ok=True)

    files = {
        "kniga-1.pdf": "1nKeMBQjnYJk-t7uzWoR6fuOWrRu9ojtZ",
        "kniga-2.pdf": "1QK1iTldWZpwblR2S8u85bMCfR0ras2zm",
        "kniga-3.pdf": "1x8hTrTn3Ad4eW05aclC7l85Upa6Tn2UL",
        "kniga-4.pdf": "17LRntDOBzlk408p1GK1M7q2kVcs0wfvD",
        "kniga-5.pdf": "1GNg4TM7v5cBpx4NaDfGfmKVgVYBn6i84",
    }

    for filename, file_id in files.items():
        path = os.path.join(knowledge_dir, filename)
        if not os.path.exists(path):
            print(f"Скачиваю {filename}...")
            url = f"https://drive.google.com/uc?id={file_id}"
            gdown.download(url, path, quiet=False)
            print(f"✅ {filename} загружен.")

# === Функция: извлечь текст из PDF ===
def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

# === Функция: подготовить базу знаний для поиска ===
def prepare_knowledge_base():
    global _knowledge_chunks, _vectorizer, _knowledge_ready
    knowledge_dir = "knowledge_base"
    all_text = ""

    # Собираем текст из всех PDF
    for filename in os.listdir(knowledge_dir):
        if filename.endswith(".pdf"):
            path = os.path.join(knowledge_dir, filename)
            print(f"Извлекаю текст из {filename}...")
            all_text += extract_text_from_pdf(path) + "\n"

    # Разбиваем на чанки по 500 слов
    sentences = all_text.split(". ")
    chunks = []
    current_chunk = ""
    for sent in sentences:
        if len(current_chunk.split()) + len(sent.split()) > 500:
            chunks.append(current_chunk.strip())
            current_chunk = sent + ". "
        else:
            current_chunk += sent + ". "
    if current_chunk:
        chunks.append(current_chunk.strip())

    _knowledge_chunks = [chunk for chunk in chunks if len(chunk) > 50]  # убираем мусор
    print(f"Подготовлено {_knowledge_chunks.__len__()} фрагментов.")

    # Создаём TF-IDF векторизатор
    _vectorizer = TfidfVectorizer(stop_words="english")
    _vectorizer.fit(_knowledge_chunks)
    _knowledge_ready = True
    print("✅ База знаний готова к использованию.")

# === Функция: найти релевантные фрагменты ===
def retrieve_relevant_chunks(query, top_k=3):
    if not _knowledge_ready:
        return []
    query_vec = _vectorizer.transform([query])
    knowledge_vecs = _vectorizer.transform(_knowledge_chunks)
    similarities = cosine_similarity(query_vec, knowledge_vecs).flatten()
    top_indices = similarities.argsort()[-top_k:][::-1]
    return [_knowledge_chunks[i] for i in top_indices if similarities[i] > 0.1]

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
        "Я дам развернутый, профессиональный ответ на основе строительных норм и справочников."
    )
    context.user_data["in_consultation"] = True

# === Обработка текстовых сообщений ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("in_consultation", False):
        await start(update, context)
        return

    user_text = update.message.text.strip()

    # Ищем релевантные фрагменты в базе знаний
    relevant_chunks = retrieve_relevant_chunks(user_text)
    knowledge_context = "\n\n".join(relevant_chunks) if relevant_chunks else "Нет релевантной информации в базе знаний."

    system_prompt = (
        "Ты — профессиональный строитель с 10-летним опытом. "
        "Ты отвечаешь ТОЛЬКО на вопросы по строительству и ремонту. "
        "Если вопрос не по теме — вежливо откажись и напомни, что ты специалист только в строительстве. "
        "ОТВЕЧАЙ ТОЛЬКО НА РУССКОМ ЯЗЫКЕ. НИКАКИХ КИТАЙСКИХ ИЕРОГЛИФОВ. НИКАКОГО АНГЛИЙСКОГО, КРОМЕ ОБЩЕПРИНЯТЫХ АББРЕВИАТУР (LED, PVC, ГКЛ). "
        "НЕ ПИШИ РАССУЖДЕНИЯ. НЕ ИСПОЛЬЗУЙ ФРАЗЫ ВРОДЕ «Я думаю», «Мне кажется». "
        "ПИШИ КАК ЭКСПЕРТ: КРАТКО, ТОЧНО, ПО ДЕЛУ. "
        "МАКСИМУМ — 400 слов."
    )

    if relevant_chunks:
        full_prompt = (
            f"{system_prompt}\n\n"
            f"Информация из строительных справочников и нормативов:\n{knowledge_context}\n\n"
            f"Вопрос клиента: {user_text}\n\n"
            f"Ответь на русском языке, без лишних слов."
        )
    else:
        full_prompt = f"{system_prompt}\n\nВопрос клиента: {user_text}\n\nОтветь на русском языке, без лишних слов."

    await update.message.reply_text("⏳ Минутку, мне нужно подумать...")

    logging.info(f"Отправляю запрос к OpenRouter: {full_prompt[:200]}...")

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
                    "max_tokens": 1000,
                    "temperature": 0.3
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
    download_knowledge_base()
    prepare_knowledge_base()  # ← инициализация RAG
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
