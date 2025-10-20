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
3) Создайте файл `.env` по образцу ниже и заполните токены:
```env
BOT_TOKEN=123456:telegram-bot-token
OPENROUTER_API_KEY=sk-or-xxxx
OPENROUTER_MODEL=meta-llama/llama-3.1-70b-instruct
PORT=10000
```
4) Добавьте файлы знаний в `base_knowledge/*.txt` (уже есть примеры).
5) Запустите локально:
```bash
python bot.py
```

### Деплой
- Приложение стартует Flask-сервером (`/health`, и `/<BOT_TOKEN>` как endpoint для вебхука Telegram).
- Настройте у Telegram вебхук на `https://<ваш-домен>/<BOT_TOKEN>`.

### Дополнительно
- Подготовка знаний из PDF: `prepare_knowledge.py` создаёт `knowledge_chunks.json` (пример обработки, не используется напрямую ботом).
- Зависимости: см. `requirements.txt` (в т.ч. `python-dotenv`, `PyPDF2`).

### Безопасность
- Секреты не хардкожены — используйте `.env`.
- Не коммитьте `.env` в репозиторий.






