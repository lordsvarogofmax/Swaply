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
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
from selectolax.parser import HTMLParser

# === Настройки ===
BOT_TOKEN = "8379969489:AAGQNjLanMwL5vyKfsSfLc5kK5UObZnCQ5E"
OPENROUTER_API_KEY = "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"
MODEL = "meta-llama/llama-3.1-70b-instruct"

# === Логирование ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# === Загрузка базы знаний из base_knowledge/*.txt ===
_knowledge_chunks = []
knowledge_dir = "base_knowledge"

if os.path.exists(knowledge_dir):
    for filename in ["kniga-1.txt", "kniga-2.txt", "kniga-3.txt"]:
        path = os.path.join(knowledge_dir, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                text = f.read().strip()
                # Разбиваем на чанки по ~500 слов
                sentences = text.split(". ")
                current_chunk = ""
                for sent in sentences:
                    if len(current_chunk.split()) + len(sent.split()) > 500:
                        if len(current_chunk) > 50:
                            _knowledge_chunks.append(current_chunk.strip())
                        current_chunk = sent + ". "
                    else:
                        current_chunk += sent + ". "
                if current_chunk and len(current_chunk) > 50:
                    _knowledge_chunks.append(current_chunk.strip())
        else:
            print(f"⚠️ Файл не найден: {path}")

    print(f"✅ Загружено {_knowledge_chunks.__len__()} фрагментов из base_knowledge/")
else:
    print("❌ Папка base_knowledge не найдена!")

# Подготавливаем TF-IDF векторизатор
if _knowledge_chunks:
    _vectorizer = TfidfVectorizer(stop_words=None)
    _vectorizer.fit(_knowledge_chunks)
    _knowledge_ready = True
else:
    _knowledge_ready = False

# === Приветствие ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👷‍♂️ **Я — профессиональный консультант в сфере строительства и ремонта.**\n\n"
        "Специализируюсь на:\n"
        "• Ремонте квартир и домов\n"
        "• Отделке (штукатурка, покраска, плитка)\n"
        "• Электромонтаже и сантехнике\n"
        "• Выборе материалов и инструментов\n"
        "• Расчёте смет и сроков\n\n"
        "• Отвечу на вопросы по СНиПам и ГОСТам\n\n"
        "⚠️ **Примечание**: я отвечаю **только по теме строительства и ремонта**. "
        "Я поддерживаю ветку диалога до 10 сообщений\n\n"
        "Готов помочь вам с реальной задачей — просто опишите её."
    )
    keyboard = [[InlineKeyboardButton("💬 Получить новую консультацию", callback_data="ask")]]
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

# === Поиск релевантных фрагментов ===
def retrieve_relevant_chunks(query, top_k=3):
    if not _knowledge_ready:
        return []
    query_vec = _vectorizer.transform([query])
    knowledge_vecs = _vectorizer.transform(_knowledge_chunks)
    similarities = cosine_similarity(query_vec, knowledge_vecs).flatten()
    top_indices = similarities.argsort()[-top_k:][::-1]
    return [_knowledge_chunks[i] for i in top_indices if similarities[i] > 0.1]

# === Ищет актуальные нормативные документы на docs.cntd.ru ===

async def search_cntd(query: str, max_chars=1500) -> str:
    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            }
        ) as client:
            search_url = f"https://docs.cntd.ru/search?text={query}"
            response = await client.get(search_url)
            response.raise_for_status()

            # Парсинг без изменений
            tree = HTMLParser(response.text)
            results = []
            for item in tree.css("div.search-results__item"):
                title_node = item.css_first("a")
                if not title_node:
                    continue
                title = title_node.text().strip()
                href = title_node.attributes.get("href")
                if not href or not href.startswith("/document/"):
                    continue
                status_node = item.css_first("span.document-info__status")
                status = status_node.text().strip().lower() if status_node else ""
                if "отмен" in status or "не действует" in status:
                    continue
                results.append({"title": title, "url": "https://docs.cntd.ru" + href})

            if not results:
                return ""

            doc_url = results[0]["url"]
            doc_resp = await client.get(doc_url)
            doc_tree = HTMLParser(doc_resp.text)
            content = ""
            for p in doc_tree.css("div.document-content p"):
                text = p.text().strip()
                if text and len(text) > 20:
                    content += text + "\n"
                    if len(content) > max_chars:
                        break

            return f"[Источник: {results[0]['title']}]\n{content[:max_chars]}..." if content else ""

    except Exception as e:
        logging.error(f"Ошибка поиска на cntd.ru: {e}")
        return ""

# === Обработка текстовых сообщений ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("in_consultation", False):
        await start(update, context)
        return

    user_text = update.message.text.strip()

    # Проверка: запрос про нормативы?
    is_normative = any(word in user_text.lower() for word in [
        "снип", "гост", "сп ", "свод правил", "актуальн", "действует",
        "новый", "нормы", "требован", "стандарт", "2025", "2024", "обновл"
    ])

    relevant_chunks = []
    online_context = ""

    if is_normative:
        online_context = await search_cntd(user_text)
        if not online_context:
            # Fallback на локальную базу
            relevant_chunks = retrieve_relevant_chunks(user_text)
    else:
        relevant_chunks = retrieve_relevant_chunks(user_text)

    # Формируем контекст
    if online_context:
        knowledge_context = online_context
    elif relevant_chunks:
        knowledge_context = "\n\n".join(relevant_chunks)
    else:
        knowledge_context = "Нет релевантной информации в базе знаний."

    # Системный промпт с указанием года
    current_year = datetime.now().year
    system_prompt = (
        f"Сегодня {current_year} год. Ты — профессиональный строитель с 10-летним опытом. "
        "Ты отвечаешь ТОЛЬКО на вопросы по строительству и ремонту. "
        "Если вопрос не по теме — вежливо откажись. "
        "ОТВЕЧАЙ ТОЛЬКО НА РУССКОМ ЯЗЫКЕ. "
        "НЕ ПИШИ РАССУЖДЕНИЯ. НЕ ИСПОЛЬЗУЙ ФРАЗЫ ВРОДЕ «Я думаю». "
        "ПИШИ КАК ЭКСПЕРТ: КРАТКО, ТОЧНО, ПО ДЕЛУ. "
        "МАКСИМУМ — 400 слов."
    )

    if online_context or relevant_chunks:
        full_prompt = (
            f"{system_prompt}\n\n"
            f"Информация из строительных нормативов:\n{knowledge_context}\n\n"
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
                "https://openrouter.ai/api/v1/chat/completions",  # ← УБРАНЫ ЛИШНИЕ ПРОБЕЛЫ!
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

            keyboard = [[InlineKeyboardButton("🔄 Задать новый вопрос", callback_data="ask")]]
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
