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

# === ОБЯЗАТЕЛЬНО: определяем состояния ДО их использования ===
START, QUERY, CITY, EXCHANGE, PAYMENT = range(5)

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

# === ФУНКЦИИ ОБРАБОТЧИКОВ ===

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
    context.user_data["with_payment
