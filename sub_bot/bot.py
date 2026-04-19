"""
Telegram-бот: выдача ссылки на Яндекс.Диск за подписку на канал + секретное слово.
Kwork #61562376

Режим работы: polling (polling активен) + aiohttp health-check сервер на PORT.
Render.com free tier: health check на / держит сервис живым.
"""
import asyncio
import logging
import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes,
)

# ─── Конфигурация ─────────────────────────────────────────────────────────────
BOT_TOKEN   = os.environ["BOT_TOKEN"]
CHANNEL_ID  = os.getenv("CHANNEL_ID",  "@dnorca")
SECRET_WORD = os.getenv("SECRET_WORD", "хочу").strip().lower()
DISK_LINK   = os.getenv("DISK_LINK",   "https://disk.yandex.ru/d/c6M_CbirwiK2vQ")
PORT        = int(os.getenv("PORT",    "10000"))
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "/tmp/users.db")

# ─── Health-check HTTP-сервер (держит Render free alive) ─────────────────────

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, *args):
        pass  # заглушаем логи health-check

def start_health_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    logger.info(f"Health-check server running on port {PORT}")
    server.serve_forever()

# ─── База данных ─────────────────────────────────────────────────────────────

def db_init():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id  INTEGER PRIMARY KEY,
                step     INTEGER DEFAULT 0,
                got_link INTEGER DEFAULT 0,
                ts       INTEGER DEFAULT (strftime('%s','now'))
            )
        """)
        conn.commit()

def db_get_step(user_id: int) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT step FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
    return row[0] if row else 0

def db_set_step(user_id: int, step: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO users(user_id, step) VALUES(?,?)
            ON CONFLICT(user_id) DO UPDATE SET step=excluded.step
        """, (user_id, step))
        conn.commit()

def db_mark_done(user_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO users(user_id, step, got_link) VALUES(?,3,1)
            ON CONFLICT(user_id) DO UPDATE SET step=3, got_link=1
        """, (user_id,))
        conn.commit()

# ─── Клавиатуры ──────────────────────────────────────────────────────────────

def subscribe_keyboard():
    channel = CHANNEL_ID.lstrip("@")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Подписаться на канал", url=f"https://t.me/{channel}")],
        [InlineKeyboardButton("✅ Я подписался — проверить", callback_data="check_sub")],
    ])

def retry_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Начать заново", callback_data="restart")],
    ])

# ─── Проверка подписки ────────────────────────────────────────────────────────

async def is_subscribed(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )
    except Exception as e:
        logger.warning(f"is_subscribed error for {user_id}: {e}")
        return False

# ─── Обработчики ─────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_set_step(user.id, 1)
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Чтобы получить ссылку на материалы, нужно выполнить *2 шага*:\n\n"
        "1️⃣ Подписаться на наш Telegram-канал\n"
        "2️⃣ Ввести секретное слово\n\n"
        "Нажми кнопку ниже 👇",
        parse_mode="Markdown",
        reply_markup=subscribe_keyboard(),
    )

async def on_check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if await is_subscribed(context.bot, user.id):
        db_set_step(user.id, 2)
        await query.edit_message_text(
            "✅ Подписка подтверждена!\n\n"
            "2️⃣ Теперь напиши *секретное слово* в этот чат:",
            parse_mode="Markdown",
        )
    else:
        await query.edit_message_text(
            "❌ Ты ещё не подписан на канал.\n\n"
            "Подпишись и нажми кнопку ещё раз 👇",
            reply_markup=subscribe_keyboard(),
        )

async def on_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db_set_step(query.from_user.id, 1)
    await query.edit_message_text(
        "🔄 Начнём сначала!\n\n"
        "1️⃣ Подпишись на канал и нажми кнопку ниже 👇",
        reply_markup=subscribe_keyboard(),
    )

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (update.message.text or "").strip().lower()
    step = db_get_step(user.id)

    if step == 0:
        await update.message.reply_text(
            "Нажми /start чтобы начать 🚀"
        )
        return

    if step == 1:
        await update.message.reply_text(
            "Сначала подпишись на канал и нажми «✅ Я подписался» 👇",
            reply_markup=subscribe_keyboard(),
        )
        return

    if step == 2:
        if SECRET_WORD in text:
            db_mark_done(user.id)
            await update.message.reply_text(
                "🎉 *Верно!*\n\n"
                f"Держи ссылку на материалы:\n{DISK_LINK}\n\n"
                "_Приятного использования!_",
                parse_mode="Markdown",
            )
            logger.info(f"User {user.id} (@{user.username}) got the link ✅")
        else:
            await update.message.reply_text(
                "🤔 Неверное слово. Попробуй ещё раз.",
                reply_markup=retry_keyboard(),
            )
        return

    if step == 3:
        await update.message.reply_text(
            f"Ты уже получил ссылку 😊\n\n{DISK_LINK}\n\n"
            "Напиши /start если хочешь пройти снова."
        )

# ─── Запуск ───────────────────────────────────────────────────────────────────

def main():
    db_init()

    # Health-check сервер в отдельном потоке
    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_check_sub, pattern="^check_sub$"))
    app.add_handler(CallbackQueryHandler(on_restart,   pattern="^restart$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    logger.info("Bot started (polling mode)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
