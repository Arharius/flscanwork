#!/usr/bin/env python3
"""
Автономный сервис для поиска и автоматического отклика на заказы по Viber-ботам.
Версия для Replit: все модули в одном файле.
"""

import os
import asyncio
import logging
import sqlite3
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

# Загрузка переменных из .env (если файл есть)
load_dotenv()

# --- Конфигурация ---
@dataclass
class Config:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "jobs.db")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    SEARCH_INTERVAL_MINUTES: int = int(os.getenv("SEARCH_INTERVAL_MINUTES", "20"))
    MIN_BUDGET: float = float(os.getenv("MIN_BUDGET", "50.0"))
    KEYWORDS: List[str] = [
        "viber", "bot", "чат-бот", "webhook", "python", "node.js",
        "автоматизация", "интеграция", "api"
    ]

config = Config()

# --- Настройка логирования ---
logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("service.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("FreelanceBot")

# --- База данных (SQLite) ---
class Database:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                external_id TEXT UNIQUE NOT NULL,
                title TEXT,
                description TEXT,
                budget REAL,
                currency TEXT,
                url TEXT,
                posted_at TIMESTAMP,
                first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_relevant INTEGER DEFAULT 0,
                is_processed INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                generated_text TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (job_id) REFERENCES jobs (id)
            )
        ''')
        self.conn.commit()

    def job_exists(self, external_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM jobs WHERE external_id = ?", (external_id,))
        return cursor.fetchone() is not None

    def create_job(self, job_data: Dict[str, Any]) -> int:
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO jobs (
                platform, external_id, title, description, budget, currency,
                url, posted_at, is_relevant
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job_data['platform'],
            job_data['external_id'],
            job_data.get('title'),
            job_data.get('description'),
            job_data.get('budget'),
            job_data.get('currency'),
            job_data.get('url'),
            job_data.get('posted_at'),
            1 if job_data.get('is_relevant', False) else 0
        ))
        self.conn.commit()
        return cursor.lastrowid

    def create_proposal(self, job_id: int, text: str, status: str = 'sent'):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO proposals (job_id, generated_text, status) VALUES (?, ?, ?)",
            (job_id, text, status)
        )
        self.conn.commit()

    def mark_job_processed(self, external_id: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE jobs SET is_processed = 1 WHERE external_id = ?",
            (external_id,)
        )
        self.conn.commit()

db = Database(config.DATABASE_URL)

# --- LLM Сервис (заглушка или реальный API) ---
class LLMService:
    def __init__(self):
        self.api_key = config.OPENAI_API_KEY
        self.model = config.LLM_MODEL

    async def generate_proposal(self, job_description: str) -> str:
        """Генерирует текст отклика. Использует OpenAI, если есть ключ, иначе заглушку."""
        if not self.api_key:
            logger.warning("OPENAI_API_KEY не задан, используется заглушка ответа.")
            return self._mock_proposal(job_description)

        prompt = self._create_prompt(job_description)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 500
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"Ошибка OpenAI API: {e}")
            return self._mock_proposal(job_description)

    def _create_prompt(self, job_description: str) -> str:
        return f"""
Ты — опытный разработчик Viber-ботов. Напиши профессиональный, дружелюбный отклик на этот заказ.
Покажи понимание задачи и предложи конкретные технологии.
Длина: 3-5 коротких абзацев.
Описание заказа:
{job_description}
"""

    def _mock_proposal(self, job_description: str) -> str:
        return (
            "Здравствуйте! Внимательно изучил Ваше описание. У меня большой опыт в разработке "
            "Viber-ботов на Python (библиотека viber-bot) и Node.js. Готов реализовать проект "
            "в кратчайшие сроки с интеграцией webhook и необходимым функционалом. "
            "Буду рад обсудить детали в личных сообщениях."
        )

llm = LLMService()

# --- Заглушка для платформы (демонстрация) ---
class BasePlatform:
    def __init__(self, name: str, config_dict: Dict[str, Any] = None):
        self.name = name
        self.config = config_dict or {}

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """Возвращает список словарей с данными заказов."""
        # В реальном проекте здесь будет парсинг или API-запрос
        logger.info(f"[{self.name}] Поиск заказов...")
        await asyncio.sleep(1)  # Имитация задержки
        return self._mock_jobs()

    def _mock_jobs(self) -> List[Dict[str, Any]]:
        # Генерируем случайные тестовые заказы для демонстрации
        jobs = []
        for i in range(random.randint(0, 3)):
            job = {
                "platform": self.name,
                "external_id": f"{self.name}_{datetime.now().timestamp()}_{i}",
                "title": f"Разработка Viber-бота #{i+1}",
                "description": f"Требуется создать чат-бота для Viber с интеграцией CRM. Бюджет: ${50 + i*30}.",
                "budget": 50.0 + i * 30,
                "currency": "USD",
                "url": f"https://{self.name.lower()}.com/job/{i}",
                "posted_at": datetime.now().isoformat(),
                "is_relevant": True
            }
            jobs.append(job)
        return jobs

    async def send_proposal(self, job_external_id: str, proposal_text: str) -> bool:
        """Отправляет отклик на платформу. Возвращает True в случае успеха."""
        logger.info(f"[{self.name}] Отправка отклика на заказ {job_external_id}...")
        await asyncio.sleep(1)  # Имитация отправки
        # В реальном коде здесь будет POST-запрос или взаимодействие через Selenium
        return True

# Список платформ для мониторинга (заглушки)
PLATFORMS = [
    BasePlatform("Upwork"),
    BasePlatform("Fiverr"),
    BasePlatform("Freelancer"),
    BasePlatform("Kwork"),
    BasePlatform("Weblancer"),
]

# --- Утилита проверки релевантности (простой фильтр по ключевым словам и бюджету) ---
def is_relevant(job: Dict[str, Any]) -> bool:
    text = (job.get("title", "") + " " + job.get("description", "")).lower()
    if not any(kw.lower() in text for kw in config.KEYWORDS):
        return False
    if job.get("budget") and job["budget"] < config.MIN_BUDGET:
        return False
    return True

# --- Основной рабочий цикл ---
async def process_platform(platform: BasePlatform):
    try:
        jobs = await platform.fetch_jobs()
        for job_data in jobs:
            if db.job_exists(job_data["external_id"]):
                continue

            job_data["is_relevant"] = is_relevant(job_data)
            if not job_data["is_relevant"]:
                logger.debug(f"Пропущен нерелевантный заказ: {job_data['title']}")
                continue

            # Сохраняем в БД
            job_id = db.create_job(job_data)
            logger.info(f"Найден новый заказ: {job_data['title']} (ID: {job_data['external_id']})")

            # Генерируем отклик
            proposal_text = await llm.generate_proposal(job_data["description"])
            logger.debug(f"Сгенерирован отклик:\n{proposal_text}")

            # Отправляем отклик
            success = await platform.send_proposal(job_data["external_id"], proposal_text)
            status = "sent" if success else "failed"
            db.create_proposal(job_id, proposal_text, status)
            if success:
                db.mark_job_processed(job_data["external_id"])
                logger.info(f"Отклик успешно отправлен на заказ {job_data['external_id']}")
            else:
                logger.error(f"Не удалось отправить отклик на заказ {job_data['external_id']}")

            # Уведомление в Telegram (если настроено)
            await send_telegram_notification(
                f"✅ Отправлен отклик на {platform.name}\n"
                f"Заказ: {job_data['title']}\n"
                f"Бюджет: {job_data['budget']} {job_data['currency']}"
            )

    except Exception as e:
        logger.error(f"Ошибка при обработке платформы {platform.name}: {e}", exc_info=True)

async def main_cycle():
    """Главный цикл, вызываемый планировщиком."""
    logger.info("=== Запуск цикла поиска заказов ===")
    tasks = [process_platform(p) for p in PLATFORMS]
    await asyncio.gather(*tasks)
    logger.info("=== Цикл завершён ===\n")

async def send_telegram_notification(message: str):
    """Отправка уведомления в Telegram (если указаны токен и chat_id)."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            })
    except Exception as e:
        logger.error(f"Ошибка отправки в Telegram: {e}")

# --- Точка входа ---
async def main():
    logger.info("Запуск FreelanceBot v1.0")
    logger.info(f"База данных: {config.DATABASE_URL}")
    logger.info(f"Интервал проверки: {config.SEARCH_INTERVAL_MINUTES} мин")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        main_cycle,
        trigger=IntervalTrigger(minutes=config.SEARCH_INTERVAL_MINUTES),
        id="job_search",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Планировщик запущен. Нажмите Ctrl+C для остановки.")

    # Первый запуск сразу (без ожидания интервала)
    await main_cycle()

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Остановка сервиса...")
        scheduler.shutdown()

if __name__ == "__main__":
    asyncio.run(main())