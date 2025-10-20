### Swaply — экспертный Telegram-бот по строительству

Бот консультирует по вопросам строительства и ремонта, используя локальную базу знаний (`base_knowledge/*.txt`) и онлайн-поиск по нормативам на `docs.cntd.ru`. Для генерации ответов используется OpenRouter.

### Возможности
- Ответы только по теме строительства/ремонта
- Ретрив по локальным текстам с TF‑IDF
- Поиск свежих нормативов на `docs.cntd.ru`
- Вебхук через Flask для Telegram

### Быстрый старт
1) Установите Python 3.11 (см. `runtime.txt`).
2) Установите зависимости:
```bash
pip install -r requirements.txt
```
3) Создайте файл `.env` с переменными окружения:
```env
BOT_TOKEN=ваш_токен_от_botfather
OPENROUTER_API_KEY=ваш_ключ_openrouter
OPENROUTER_MODEL=meta-llama/llama-3.1-70b-instruct
ADMIN_ID=364191893
PORT=10000
```

**Как получить токены:**
- **BOT_TOKEN**: Создайте бота через [@BotFather](https://t.me/BotFather) в Telegram
- **OPENROUTER_API_KEY**: Получите на [OpenRouter.ai](https://openrouter.ai/)
4) Добавьте файлы знаний в `base_knowledge/*.txt` (уже есть примеры).
5) Запустите локально:
```bash
python bot.py
```

### Деплой на Render.com
1. **Создайте Web Service** на [Render.com](https://render.com/)
2. **Подключите GitHub репозиторий**
3. **Настройте переменные окружения** в панели Render:
   - `BOT_TOKEN` - токен от BotFather
   - `OPENROUTER_API_KEY` - ключ от OpenRouter
   - `ADMIN_ID` - 364191893
   - `PORT` - 10000
4. **Настройте вебхук Telegram**:
   - URL: `https://<ваш-домен>.onrender.com/<BOT_TOKEN>`
   - Метод: POST
5. **Приложение стартует Flask-сервером** (`/health`, и `/<BOT_TOKEN>` как endpoint для вебхука Telegram).

### Настройка вебхука Telegram
После деплоя настройте вебхук через BotFather:
```
/setwebhook
URL: https://ваш-домен.onrender.com/ваш-BOT-TOKEN
```

### Дополнительно
- Подготовка знаний из PDF: `prepare_knowledge.py` создаёт `knowledge_chunks.json` (пример обработки, не используется напрямую ботом).
- Зависимости: см. `requirements.txt` (в т.ч. `python-dotenv`, `PyPDF2`).
- База знаний: автоматически загружаются все `.txt` файлы из папки `base_knowledge/`

### Безопасность
- Секреты не хардкожены — используйте `.env`.
- Не коммитьте `.env` в репозиторий.
- Админские функции доступны только пользователю с `ADMIN_ID`.






