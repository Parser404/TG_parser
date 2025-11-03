 # bot.py
from telethon import TelegramClient, events, functions, types
import markovify
import os
import random
import asyncio
from datetime import datetime, time as dt_time, timedelta
import pytz

import telegram_config as cfg

# === НАСТРОЙКИ ===
# Укажи ID чатов: группы (отрицательные), личные чаты (положительные)
CHAT_IDS = [
    -1************,   # ← замени на свой ID чата 1
    -1************,   # ← замени на свой ID чата 2
    # 123456789       # ← пример личного чата (раскомментируй при необходимости)
]

BASE_CORPUS_PATH = "base_corpus.txt"
MODELS_DIR = "models"
os.makedirs(MODELS_DIR, exist_ok=True)

# Пользователи с персональными словарями
PERSONAL_USERS = {
    6*********,
    4********,
    7********,
    5********,
    1********,
    3********,
    7********,
    3********,
    1********,
    9********,
    6********,
    1********,
    8********,
}

# Временная зона — ОБЯЗАТЕЛЬНО замени на свою!
LOCAL_TZ = pytz.timezone("Europe/Moscow")  # ← например: "Asia/Novosibirsk", "America/New_York"
INITIATIVE_TIMES = [dt_time(9, 0), dt_time(21, 0)]

# Используем существующую сессию
client = TelegramClient('session_name', cfg.api_id, cfg.api_hash)

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def load_base_corpus():
    if os.path.exists(BASE_CORPUS_PATH):
        with open(BASE_CORPUS_PATH, encoding="utf-8") as f:
            return f.read()
    return "Привет! Как твои дела? Расскажи что-нибудь интересное."

def get_user_model_key(user_id):
    return str(user_id) if user_id in PERSONAL_USERS else "default"

def load_user_text(user_key):
    path = f"{MODELS_DIR}/user_{user_key}.txt"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return load_base_corpus()

# === ИНИЦИАТИВА: отправка во все чаты ===

async def send_initiative_message():
    full_text = load_user_text("default")
    model = markovify.Text(full_text, state_size=2)
    sentence = model.make_sentence(tries=50, max_words=18)
    if not sentence:
        sentence = random.choice([
            "Доброе утро! О чём поговорим?",
            "Вечер в хату! Как прошёл день?",
            "Привет! Есть минутка поболтать?",
            "Иногда так хочется просто поговорить…"
        ])
    for chat_id in CHAT_IDS:
        try:
            await client.send_message(chat_id, f"🌅 {sentence}")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Отправлено в чат {chat_id}")
        except Exception as e:
            print(f"❌ Ошибка отправки в чат {chat_id}: {e}")

async def initiative_scheduler():
    while True:
        now = datetime.now(LOCAL_TZ)
        today = now.date()
        next_times = []
        for t in INITIATIVE_TIMES:
            candidate = LOCAL_TZ.localize(datetime.combine(today, t))
            if candidate > now:
                next_times.append(candidate)
        if not next_times:
            next_fire = LOCAL_TZ.localize(
                datetime.combine(today, INITIATIVE_TIMES[0]) + timedelta(days=1)
            )
        else:
            next_fire = min(next_times)
        sleep_sec = (next_fire - now).total_seconds()
        print(f"⏳ Следующая инициатива: {next_fire.strftime('%Y-%m-%d %H:%M')}")
        await asyncio.sleep(sleep_sec)
        await send_initiative_message()

# === ОСНОВНОЙ ОБРАБОТЧИК ДЛЯ ВСЕХ ЧАТОВ ===

@client.on(events.NewMessage(chats=CHAT_IDS))
async def message_handler(event):
    sender = await event.get_sender()
    if not sender or sender.bot:
        return

    user_id = sender.id
    text = (event.message.text or "").strip()
    if not text:
        return

    me = await client.get_me()
    if user_id == me.id:
        return  # игнорируем свои сообщения

    # Упоминание бота
    is_mentioned = False
    if event.message.entities:
        for ent in event.message.entities:
            if getattr(ent, 'user_id', None) == me.id:
                is_mentioned = True
                break

    # Ответ на сообщение бота
    is_reply_to_bot = False
    if event.message.reply_to:
        try:
            replied = await event.get_reply_message()
            if replied and replied.sender_id == me.id:
                is_reply_to_bot = True
        except:
            pass

    if is_mentioned or is_reply_to_bot:
        delay = random.uniform(5, 10)
        print(f"🕒 Задержка перед ответом: {delay:.1f} сек")
        await asyncio.sleep(delay)

        # Обновляем текст пользователя
        model_key = get_user_model_key(user_id)
        full_text = load_user_text(model_key) + "\n" + text
        text_path = f"{MODELS_DIR}/user_{model_key}.txt"
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(full_text)

        # Генерация ответа
        model = markovify.Text(full_text, state_size=2)
        reply = model.make_sentence(tries=50, max_words=20)
        if not reply:
            reply = random.choice([
                "Интересно...", "Продолжай!", "А ты сам как думаешь?",
                "Расскажи подробнее.", "Хм... не уверен, но звучит любопытно!"
            ])

        # Вывод времени и текста ответа в терминал
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Ответ пользователю {user_id}: {reply}")

        await event.reply(reply)

        # Ставим реакцию
        try:
            await client(functions.messages.SendReactionRequest(
                peer=event.chat_id,
                msg_id=event.message.id,
                reaction=[types.ReactionEmoji(emoticon="👍")]
            ))
        except:
            pass

# === ЗАПУСК ===

print("🤖 Марков-бот запущен!")
print(f"Чаты: {CHAT_IDS}")
print(f"Инициатива: {', '.join(t.strftime('%H:%M') for t in INITIATIVE_TIMES)} по времени {LOCAL_TZ}")

with client:
    client.loop.create_task(initiative_scheduler())
    client.run_until_disconnected()
