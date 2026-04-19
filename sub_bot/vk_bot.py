"""
VK-бот: выдача ссылки на Яндекс.Диск за подписку на Telegram-канал + секретное слово.
Kwork #61562376

Логика:
  /start или любое сообщение →
    Шаг 1: Кнопка «Подписаться на @dnorca» + «Я подписался»
    Шаг 2: Ввод секретного слова «хочу»
    → Ссылка на Яндекс.Диск
"""

import os
import logging
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Конфигурация ─────────────────────────────────────────────────────────────
VK_TOKEN    = os.environ["VK_TOKEN"]
VK_GROUP_ID = int(os.environ["VK_GROUP_ID"])
TG_CHANNEL  = os.getenv("TG_CHANNEL",  "dnorca")          # без @
SECRET_WORD = os.getenv("SECRET_WORD", "хочу").strip().lower()
DISK_LINK   = os.getenv("DISK_LINK",   "https://disk.yandex.ru/d/c6M_CbirwiK2vQ")
PORT        = int(os.getenv("PORT",    "10000"))
DB_PATH     = os.getenv("DB_PATH",     "/tmp/vk_users.db")
# ─────────────────────────────────────────────────────────────────────────────

# ─── Health-check для хостинга ────────────────────────────────────────────────

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *a): pass

def start_health_server():
    HTTPServer(("0.0.0.0", PORT), HealthHandler).serve_forever()

# ─── База данных ─────────────────────────────────────────────────────────────

def db_init():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id  INTEGER PRIMARY KEY,
                step     INTEGER DEFAULT 0,
                got_link INTEGER DEFAULT 0
            )
        """)
        c.commit()

def db_get_step(user_id: int) -> int:
    with sqlite3.connect(DB_PATH) as c:
        row = c.execute("SELECT step FROM users WHERE user_id=?", (user_id,)).fetchone()
    return row[0] if row else 0

def db_set_step(user_id: int, step: int):
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            INSERT INTO users(user_id, step) VALUES(?,?)
            ON CONFLICT(user_id) DO UPDATE SET step=excluded.step
        """, (user_id, step))
        c.commit()

def db_mark_done(user_id: int):
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            INSERT INTO users(user_id, step, got_link) VALUES(?,3,1)
            ON CONFLICT(user_id) DO UPDATE SET step=3, got_link=1
        """, (user_id,))
        c.commit()

# ─── Клавиатуры ──────────────────────────────────────────────────────────────

def keyboard_subscribe():
    """Шаг 1: кнопка подписки + кнопка проверки."""
    kb = VkKeyboard(one_time=False, inline=False)
    kb.add_openlink_button(f"📢 Подписаться на канал", f"https://t.me/{TG_CHANNEL}")
    kb.add_line()
    kb.add_button("✅ Я подписался", VkKeyboardColor.POSITIVE)
    return kb.get_keyboard()

def keyboard_retry():
    """Кнопка 'начать заново'."""
    kb = VkKeyboard(one_time=True)
    kb.add_button("🔄 Начать заново", VkKeyboardColor.SECONDARY)
    return kb.get_keyboard()

def keyboard_empty():
    """Убрать клавиатуру."""
    return VkKeyboard.get_empty_keyboard()

# ─── Отправка сообщений ───────────────────────────────────────────────────────

def send(vk, user_id: int, text: str, keyboard: str = None):
    params = dict(user_id=user_id, message=text, random_id=0)
    if keyboard is not None:
        params["keyboard"] = keyboard
    try:
        vk.messages.send(**params)
    except Exception as e:
        logger.error(f"send error user={user_id}: {e}")

# ─── Обработка сообщений ─────────────────────────────────────────────────────

def handle(vk, user_id: int, text: str):
    text_l = text.strip().lower()
    step = db_get_step(user_id)

    # ── Старт / перезапуск ──
    if text_l in ("начать", "старт", "start", "/start", "привет", "хай", "помощь") or step == 0:
        db_set_step(user_id, 1)
        send(vk, user_id,
             "👋 Привет!\n\n"
             "Чтобы получить ссылку на материалы, нужно выполнить 2 шага:\n\n"
             "1️⃣ Подписаться на Telegram-канал\n"
             "2️⃣ Ввести секретное слово\n\n"
             "Нажми кнопку ниже 👇",
             keyboard_subscribe())
        return

    # ── Шаг 1: пользователь нажал «Я подписался» ──
    if text_l in ("✅ я подписался", "я подписался", "подписался") or (step == 1 and text_l == "✅ я подписался"):
        db_set_step(user_id, 2)
        send(vk, user_id,
             "✅ Отлично!\n\n"
             "2️⃣ Теперь введи секретное слово в этот чат:",
             keyboard_empty())
        return

    # ── Шаг 2: проверяем секретное слово ──
    if step == 2:
        if SECRET_WORD in text_l:
            db_mark_done(user_id)
            logger.info(f"User {user_id} got the link ✅")
            send(vk, user_id,
                 f"🎉 Верно!\n\n"
                 f"Держи ссылку на материалы:\n{DISK_LINK}\n\n"
                 f"Приятного использования!",
                 keyboard_empty())
        else:
            send(vk, user_id,
                 "🤔 Неверное слово. Попробуй ещё раз.\n\n"
                 "Или нажми кнопку чтобы начать заново:",
                 keyboard_retry())
        return

    # ── Уже получил ссылку ──
    if step == 3:
        send(vk, user_id,
             f"Ты уже получил ссылку 😊\n\n{DISK_LINK}",
             keyboard_empty())
        return

    # ── Шаг 1, ждём нажатия кнопки ──
    if step == 1:
        send(vk, user_id,
             "Сначала подпишись на канал и нажми «✅ Я подписался» 👇",
             keyboard_subscribe())

    # ── Кнопка перезапуска ──
    if text_l in ("🔄 начать заново", "начать заново", "заново"):
        db_set_step(user_id, 1)
        send(vk, user_id,
             "🔄 Начнём сначала!\n\n"
             "1️⃣ Подпишись на канал и нажми кнопку 👇",
             keyboard_subscribe())

# ─── Главный цикл ────────────────────────────────────────────────────────────

def main():
    db_init()

    # Health-check в фоне
    threading.Thread(target=start_health_server, daemon=True).start()

    session = vk_api.VkApi(token=VK_TOKEN)
    vk = session.get_api()
    longpoll = VkBotLongPoll(session, VK_GROUP_ID)

    logger.info(f"VK-бот запущен (group_id={VK_GROUP_ID})")

    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW and event.from_user:
            try:
                uid = event.object.message["from_id"]
                txt = event.object.message.get("text", "")
                logger.info(f"Msg from {uid}: {txt!r}")
                threading.Thread(
                    target=handle,
                    args=(vk, uid, txt),
                    daemon=True,
                ).start()
            except Exception as e:
                logger.error(f"Event error: {e}")


if __name__ == "__main__":
    main()
