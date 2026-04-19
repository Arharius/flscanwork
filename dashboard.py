"""
FreelanceBot v15.0 — Admin Web Dashboard
Full admin interface: monitor + control + edit.
Runs in a background thread from main.py.
"""
import os
import sqlite3
import json
import threading
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template_string, request


def _to_msk(ts: str) -> str:
    """Convert UTC timestamp string to Moscow time (UTC+3) for display."""
    if not ts:
        return ""
    s = str(ts).replace("T", " ")[:19]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(s, fmt) + timedelta(hours=3)
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            continue
    return s[:16]

app = Flask(__name__)
app.secret_key = os.urandom(24)

DB_PATH = os.getenv("SQLITE_DB", "jobs.db")
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_config.json")
DASHBOARD_PORT = int(os.getenv("PORT", 5000))

DEFAULT_CONFIG = {
    "min_budget": 50.0,
    "search_interval_minutes": 20,
    "log_level": "INFO",
    "keywords": [
        "Telegram бот", "Python бот", "парсер", "автоматизация",
        "Flask", "FastAPI", "веб-скрапинг", "API интеграция"
    ],
    "disabled_platforms": [],
    "notes": ""
}


def load_config() -> dict:
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg = {**DEFAULT_CONFIG, **data}
            return cfg
    except Exception:
        pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_bot_state():
    try:
        import bot_state as _bs
        return _bs.is_paused()
    except Exception:
        return False


# ── HTML Template ────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FreelanceBot Control Panel</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0f1117;--surface:#1a202c;--surface2:#1e2533;--border:#2d3748;
  --text:#e2e8f0;--muted:#718096;--blue:#63b3ed;--green:#68d391;
  --red:#fc8181;--yellow:#f6e05e;--purple:#b794f4;--orange:#f6ad55;
}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}

/* ── Header ── */
header{background:linear-gradient(135deg,#1a1f2e,#16213e);padding:14px 28px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100}
header h1{font-size:1.25rem;font-weight:700;color:var(--blue);display:flex;align-items:center;gap:10px}
.status-pill{padding:4px 14px;border-radius:999px;font-size:0.8rem;font-weight:700;cursor:pointer;border:none;transition:.2s}
.status-running{background:#22543d;color:var(--green)}
.status-paused{background:#742a2a;color:var(--red)}
#header-time{font-size:0.8rem;color:var(--muted)}

/* ── Tabs ── */
.tabs{display:flex;gap:0;border-bottom:1px solid var(--border);padding:0 28px;background:var(--surface)}
.tab{padding:12px 22px;cursor:pointer;font-size:0.88rem;font-weight:500;color:var(--muted);border-bottom:2px solid transparent;transition:.15s;user-select:none}
.tab:hover{color:var(--text)}
.tab.active{color:var(--blue);border-bottom-color:var(--blue)}

/* ── Main ── */
main{padding:24px 28px;max-width:1400px;margin:0 auto}
.hidden{display:none!important}

/* ── Cards ── */
.stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:24px}
.stat-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:18px;text-align:center}
.stat-num{font-size:2rem;font-weight:800;color:var(--blue);line-height:1}
.stat-label{font-size:0.73rem;color:var(--muted);margin-top:5px;text-transform:uppercase;letter-spacing:.5px}

/* ── Section ── */
.section{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:18px;margin-bottom:18px}
.section-title{font-size:.95rem;font-weight:600;color:var(--muted);margin-bottom:14px;display:flex;align-items:center;gap:8px}

/* ── Table ── */
table{width:100%;border-collapse:collapse;font-size:.84rem}
th{text-align:left;padding:8px 10px;color:var(--muted);font-weight:500;border-bottom:1px solid var(--border);white-space:nowrap}
td{padding:9px 10px;border-bottom:1px solid var(--surface2);vertical-align:middle}
tr:last-child td{border-bottom:none}
tr:hover td{background:var(--surface2)}

/* ── Badges ── */
.badge{display:inline-block;padding:2px 9px;border-radius:4px;font-size:.72rem;font-weight:600}
.bg-green{background:#22543d;color:var(--green)}
.bg-red{background:#742a2a;color:var(--red)}
.bg-yellow{background:#744210;color:var(--yellow)}
.bg-blue{background:#2a4365;color:var(--blue)}
.bg-purple{background:#44337a;color:var(--purple)}
.bg-gray{background:#2d3748;color:#a0aec0}
.platform-badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.72rem;font-weight:600;background:#2d3748;color:var(--blue)}

/* ── Cookie Warning Banner ── */
.cookie-banner{display:none;padding:10px 28px;font-size:.85rem;font-weight:600;align-items:center;gap:10px;border-bottom:1px solid var(--border)}
.cookie-banner.warn{background:#744210;color:var(--yellow);display:flex}
.cookie-banner.error{background:#742a2a;color:var(--red);display:flex}
.cookie-banner a{color:inherit;text-decoration:underline;cursor:pointer}

/* ── Buttons ── */
.btn{display:inline-flex;align-items:center;gap:6px;padding:7px 16px;border-radius:7px;font-size:.84rem;font-weight:600;cursor:pointer;border:none;transition:.15s}
.btn-primary{background:var(--blue);color:#0f1117}
.btn-primary:hover{background:#4299e1}
.btn-danger{background:#742a2a;color:var(--red)}
.btn-danger:hover{background:#9b2c2c}
.btn-success{background:#22543d;color:var(--green)}
.btn-success:hover{background:#276749}
.btn-ghost{background:transparent;color:var(--muted);border:1px solid var(--border)}
.btn-ghost:hover{color:var(--text);border-color:var(--text)}
.btn-sm{padding:4px 10px;font-size:.78rem}
.btn-icon{padding:5px 8px;font-size:.8rem}

/* ── Forms ── */
.form-group{margin-bottom:14px}
label{display:block;font-size:.82rem;color:var(--muted);margin-bottom:5px}
input[type=text],input[type=number],textarea,select{
  width:100%;background:var(--surface2);border:1px solid var(--border);
  color:var(--text);border-radius:7px;padding:8px 12px;font-size:.88rem;outline:none;
  transition:.15s
}
input:focus,textarea:focus,select:focus{border-color:var(--blue)}
textarea{resize:vertical;min-height:80px;font-family:inherit}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.form-actions{display:flex;gap:10px;margin-top:16px}
.checkbox-group{display:flex;flex-wrap:wrap;gap:10px;margin-top:6px}
.checkbox-item{display:flex;align-items:center;gap:6px;font-size:.85rem;cursor:pointer}
.checkbox-item input{width:auto}

/* ── Tags ── */
.tags{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px}
.tag{background:var(--surface2);border:1px solid var(--border);border-radius:5px;padding:3px 10px;font-size:.8rem;display:inline-flex;align-items:center;gap:6px}
.tag-del{color:var(--red);cursor:pointer;font-size:.9rem;line-height:1}
.tag-del:hover{color:#fff}
.tag-add{display:flex;gap:8px;margin-top:10px}
.tag-add input{flex:1}

/* ── Control panel ── */
.control-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-bottom:18px}
.control-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:18px}
.control-card h3{font-size:.88rem;color:var(--muted);margin-bottom:12px}
.control-card p{font-size:.82rem;color:var(--muted);margin-bottom:12px;line-height:1.5}

/* ── Toast ── */
#toast{position:fixed;bottom:24px;right:24px;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px 20px;font-size:.88rem;z-index:999;opacity:0;transition:opacity .3s;pointer-events:none;max-width:320px}
#toast.show{opacity:1}
#toast.ok{border-color:var(--green);color:var(--green)}
#toast.err{border-color:var(--red);color:var(--red)}

/* ── Modal ── */
.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:200;display:flex;align-items:center;justify-content:center;padding:20px}
.modal{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:24px;max-width:640px;width:100%;max-height:80vh;overflow-y:auto}
.modal h2{font-size:1rem;margin-bottom:16px;color:var(--blue)}
.modal pre{background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:12px;font-size:.78rem;white-space:pre-wrap;word-break:break-word;color:#cbd5e0;max-height:300px;overflow-y:auto}
.modal-actions{display:flex;gap:10px;margin-top:16px;justify-content:flex-end}

/* ── Log ── */
#activity-log{background:var(--surface2);border-radius:6px;padding:12px;font-size:.78rem;font-family:monospace;height:180px;overflow-y:auto;line-height:1.6;color:#cbd5e0}

/* ── Misc ── */
.empty{color:var(--muted);font-style:italic;text-align:center;padding:24px}
.text-green{color:var(--green)}
.text-red{color:var(--red)}
.text-yellow{color:var(--yellow)}
.text-blue{color:var(--blue)}
.text-muted{color:var(--muted)}
.flex{display:flex;align-items:center;gap:8px}
.ml-auto{margin-left:auto}
.nowrap{white-space:nowrap}
/* ── Inbox/Messages ── */
.msg-card{background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:12px;transition:.15s}
.msg-card:hover{border-color:var(--blue)}
.msg-card.unread{border-color:var(--red);background:rgba(252,129,129,.07)}
.msg-header{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px;flex-wrap:wrap}
.msg-sender{font-weight:700;font-size:.9rem}
.msg-date{font-size:.75rem;color:var(--muted);white-space:nowrap}
.msg-preview{font-size:.84rem;color:var(--text);line-height:1.5;margin-bottom:10px}
.msg-actions{display:flex;gap:8px;flex-wrap:wrap}

/* ── Tablet/Mobile ── */
@media(max-width:900px){
  header{padding:10px 14px}
  header h1{font-size:1rem}
  .tabs{padding:0 8px;overflow-x:auto;flex-wrap:nowrap}
  .tab{padding:10px 14px;font-size:.82rem;white-space:nowrap}
  main{padding:10px 12px}
  .stat-grid{grid-template-columns:repeat(2,1fr);gap:10px}
  .stat-num{font-size:1.7rem}
  .stat-label{font-size:.65rem}
  .section{padding:14px;margin-bottom:12px}
  table{font-size:.78rem}
  th,td{padding:7px 6px}
  .btn-sm{padding:3px 8px;font-size:.74rem}
  .control-grid{grid-template-columns:1fr}
  .form-row{grid-template-columns:1fr}
  .modal{padding:16px;margin:10px}
}
@media(max-width:480px){
  .stat-grid{grid-template-columns:1fr 1fr}
  .stat-num{font-size:1.4rem}
  header h1 .subtitle{display:none}
}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.55}}
</style>
</head>
<body>

<!-- ── Toast ── -->
<div id="toast"></div>

<!-- ── Proposal Modal ── -->
<div id="modal" class="modal-backdrop hidden">
  <div class="modal">
    <h2 id="modal-title">Текст отклика</h2>
    <pre id="modal-body"></pre>
    <div class="modal-actions">
      <button class="btn btn-ghost btn-sm" onclick="closeModal()">Закрыть</button>
    </div>
  </div>
</div>

<!-- ── Header ── -->
<header>
  <h1>🤖 FreelanceBot <span style="font-size:.85rem;color:var(--muted)">Control Panel</span></h1>
  <div class="flex">
    <a href="/knowledge" style="color:var(--accent,#58a6ff);text-decoration:none;margin-right:16px;font-size:14px">📚 База знаний</a>
    <button id="pause-btn" class="status-pill" onclick="togglePause()">…</button>
    <span id="header-time" style="margin-left:16px"></span>
  </div>
</header>

<!-- ── Tabs ── -->
<div class="tabs">
  <div class="tab active" onclick="switchTab('overview')">📊 Обзор</div>
  <div class="tab" onclick="switchTab('messages')">💬 Переписка <span id="msg-badge" style="background:#fc8181;color:#fff;border-radius:999px;padding:1px 7px;font-size:.7rem;margin-left:4px;display:none"></span></div>
  <div class="tab" onclick="switchTab('jobs')">📋 Заказы</div>
  <div class="tab" onclick="switchTab('projects')">⚙️ Проекты</div>
  <div class="tab" onclick="switchTab('finance')">💰 Финансы</div>
  <div class="tab" onclick="switchTab('settings')">🔧 Настройки</div>
  <div class="tab" onclick="switchTab('control')">🎛️ Управление</div>
  <div class="tab" onclick="switchTab('profile')">👤 Профиль</div>
</div>

<!-- ── Cookie Warning Banner ── -->
<div id="cookie-banner" class="cookie-banner"></div>

<main>

<!-- ══════════════════ TAB: ОБЗОР ══════════════════ -->
<div id="tab-overview">
  <!-- KPI строка -->
  <div class="stat-grid" id="stat-cards" style="grid-template-columns:repeat(4,1fr)">
    <div class="stat-card" style="border-color:var(--yellow)">
      <div class="stat-num text-yellow" id="s-prop">…</div>
      <div class="stat-label">📤 Откликов отправлено</div>
    </div>
    <div class="stat-card" id="sc-replied" style="border-color:var(--red)">
      <div class="stat-num text-red" id="s-replied">…</div>
      <div class="stat-label">💬 Клиент ответил</div>
    </div>
    <div class="stat-card" style="border-color:var(--green)">
      <div class="stat-num text-green" id="s-wins">…</div>
      <div class="stat-label">✅ Заказов взято</div>
    </div>
    <div class="stat-card" style="border-color:var(--muted)">
      <div class="stat-num text-muted" id="s-rej">…</div>
      <div class="stat-label">❌ Отклонено</div>
    </div>
  </div>

  <!-- АКТИВНЫЙ ЗАКАЗ (показывается только когда есть won) -->
  <div id="active-order-block" style="display:none;margin-bottom:16px">
    <div class="section" style="border-color:var(--green);background:rgba(72,187,120,.07)">
      <div class="section-title" style="color:var(--green);margin-bottom:14px">🏆 Активный заказ — бот работает автоматически</div>
      <div id="active-order-content"></div>
    </div>
  </div>

  <!-- ГЛАВНАЯ ТАБЛИЦА ОТКЛИКОВ -->
  <div class="section" id="proposals-section">
    <div class="flex" style="margin-bottom:14px;align-items:center">
      <div class="section-title" style="margin:0">📬 Мои отклики</div>
      <span style="color:var(--muted);font-size:.8rem;margin-left:12px">Статус обновляется автоматически</span>
      <button class="btn btn-ghost btn-sm ml-auto" onclick="loadOverview()">🔄 Обновить</button>
    </div>
    <div id="my-proposals-table"><div class="empty">Загрузка…</div></div>
  </div>

  <!-- Платформы -->
  <div class="section">
    <div class="section-title">🌐 Платформы (Kwork + FL.ru)</div>
    <div id="platforms-table"><div class="empty">Загрузка…</div></div>
  </div>

  <!-- Последние заказы (вторичная инфо) -->
  <div class="section" id="recent-jobs-section">
    <div class="flex" style="margin-bottom:10px">
      <div class="section-title" style="margin:0;font-size:.9rem;color:var(--muted)">Последние найденные заказы</div>
    </div>
    <div id="recent-jobs-table"><div class="empty">Загрузка…</div></div>
  </div>
</div>

<!-- ══════════════════ TAB: ПЕРЕПИСКА ══════════════════ -->
<div id="tab-messages" class="hidden">

  <div class="section" style="border-color:var(--blue);margin-bottom:14px">
    <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px">
      <div>
        <div class="section-title" style="margin:0;color:var(--blue)">💬 Входящие сообщения — Kwork</div>
        <div style="font-size:.78rem;color:var(--muted);margin-top:4px">Реальные сообщения от клиентов. Обновляется каждые 5 мин автоматически.</div>
      </div>
      <button class="btn btn-ghost btn-sm" onclick="loadMessages()">🔄 Обновить</button>
    </div>
  </div>

  <div id="messages-kwork"><div class="empty">Загрузка переписки…</div></div>

  <div class="section" style="margin-top:14px">
    <div class="section-title">💬 FL.ru — Входящие</div>
    <div id="messages-flru"><div class="empty">Загрузка…</div></div>
  </div>

</div>

<!-- ══════════════════ TAB: ФИНАНСЫ ══════════════════ -->
<div id="tab-finance" class="hidden">

  <!-- Доходы -->
  <div class="section">
    <div class="flex" style="margin-bottom:14px">
      <div class="section-title" style="margin:0">💰 Финансовая статистика</div>
      <button class="btn btn-ghost btn-sm ml-auto" onclick="loadFinance()">🔄 Обновить</button>
    </div>
    <div id="finance-stats"><div class="empty">Загрузка…</div></div>
  </div>

  <!-- Kwork — вывод -->
  <div class="section" style="border-color:#68d391">
    <div class="section-title" style="color:#68d391">🏦 Kwork — получение оплаты</div>
    <div style="font-size:.88rem;line-height:1.9;color:var(--text)">
      <b>Kwork платит через платёжную систему платформы:</b><br>
      Клиент платит Kwork → Kwork удерживает комиссию 20% → остаток можно вывести<br><br>
      <b>Шаги для добавления карты:</b><br>
      1. Зайдите на <a href="https://kwork.ru/expense" target="_blank" style="color:var(--blue)">kwork.ru/expense</a><br>
      2. Нажмите <b>«Добавить способ вывода»</b><br>
      3. Выберите <b>«Банковская карта»</b> (Visa/Mastercard/МИР)<br>
      4. Введите номер карты — Kwork пришлёт 2 рубля для верификации<br>
      5. После подтверждения — запрашивайте вывод от <b>500 ₽</b><br><br>
      <b>Также доступно:</b> ЮMoney, Qiwi, WebMoney, USDT (крипто)<br>
      <b>Срок вывода:</b> 1-3 рабочих дня<br>
      <div style="background:var(--surface2);border-radius:8px;padding:12px;margin-top:12px;font-size:.82rem;color:var(--muted)">
        ℹ️ Бот зарабатывает автоматически — деньги копятся на балансе Kwork.
        Вывести можно вручную или через API. Комиссия Kwork: 20% от заказа.
      </div>
    </div>
  </div>

  <!-- FL.ru — авторизация через cookie -->
  <div class="section" style="border-color:#f6ad55">
    <div class="section-title" style="color:#f6ad55">🔑 FL.ru — авторизация (FL_SESSION_COOKIE)</div>
    <div style="font-size:.88rem;line-height:1.9;color:var(--text)">
      FL.ru блокирует автоматический вход с серверных IP (DDoS Guard). Решение — извлечь куки из браузера, как для Kwork.<br><br>
      <b>Как получить FL_SESSION_COOKIE:</b><br>
      1. Зайдите на <a href="https://www.fl.ru" target="_blank" style="color:var(--blue)">fl.ru</a> в браузере и войдите в свой аккаунт<br>
      2. Нажмите <b>F12</b> → вкладка <b>«Application»</b> (Chrome) или <b>«Storage»</b> (Firefox)<br>
      3. Слева выберите <b>Cookies → https://www.fl.ru</b><br>
      4. Найдите куки: <b>PHPSESSID</b>, <b>remember_web_*</b>, <b>XSRF-TOKEN</b><br>
      5. Скопируйте строку вида: <code style="background:var(--surface2);padding:2px 6px;border-radius:4px">PHPSESSID=abc123; remember_web_xyz=def456; XSRF-TOKEN=ghi789</code><br>
      6. В Replit → вкладка <b>«Secrets»</b> → добавьте переменную <b>FL_SESSION_COOKIE</b> с этим значением<br>
      7. Перезапустите бота — и он начнёт отправлять отклики на FL.ru<br>
      <div style="background:var(--surface2);border-radius:8px;padding:10px;margin-top:10px;font-size:.82rem;color:var(--muted)">
        ⏱ Куки действуют 30-90 дней. После истечения повторите процедуру.
      </div>
    </div>
  </div>

  <!-- FL.ru — вывод -->
  <div class="section" style="border-color:#63b3ed">
    <div class="section-title" style="color:#63b3ed">🏦 FL.ru — получение оплаты</div>
    <div style="font-size:.88rem;line-height:1.9;color:var(--text)">
      <b>FL.ru использует внутренний Сейф для хранения и вывода средств:</b><br>
      Клиент пополняет Сейф → Вы принимаете работу → Деньги разблокируются<br><br>
      <b>Шаги для добавления карты:</b><br>
      1. Зайдите на <a href="https://www.fl.ru/payout/" target="_blank" style="color:var(--blue)">fl.ru/payout/</a><br>
      2. Раздел <b>«Вывод средств»</b> → <b>«Добавить реквизиты»</b><br>
      3. Выберите <b>«Банковская карта»</b> или <b>«Расчётный счёт»</b><br>
      4. Минимальный вывод: <b>500 ₽</b><br>
      5. Срок зачисления: до <b>5 рабочих дней</b><br><br>
      <b>Комиссия FL.ru:</b> 15% (при PRO-аккаунте — 10%)<br>
      <div style="background:var(--surface2);border-radius:8px;padding:12px;margin-top:12px;font-size:.82rem;color:var(--muted)">
        ℹ️ Бот принимает заказы и сдаёт работу автоматически.
        После одобрения клиентом деньги поступают на ваш баланс FL.ru.
      </div>
    </div>
  </div>

  <!-- LLM роутинг -->
  <div class="section" style="border-color:#b794f4">
    <div class="section-title" style="color:#b794f4">🤖 Умный выбор AI-модели</div>
    <div id="llm-router-status"><div class="empty">Загрузка…</div></div>
    <div style="font-size:.84rem;line-height:1.8;color:var(--text);margin-top:14px">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:8px">
        <div style="background:var(--surface2);padding:12px;border-radius:8px">
          <div style="font-weight:700;color:#68d391;margin-bottom:6px">🟢 DeepSeek — простые задачи</div>
          <div style="font-size:.78rem;color:var(--muted)">
            • Скрипты и боты (Telegram, Viber)<br>
            • Парсеры и автоматизация<br>
            • Google Sheets, Excel, Airtable<br>
            • Webhook-интеграции<br>
            • Бюджет до 3000 ₽<br>
            <b>Скорость:</b> быстро | <b>Цена:</b> дёшево
          </div>
        </div>
        <div style="background:var(--surface2);padding:12px;border-radius:8px">
          <div style="font-weight:700;color:#b794f4;margin-bottom:6px">🟣 Claude 3.5 — сложные задачи</div>
          <div style="font-size:.78rem;color:var(--muted)">
            • Архитектура и микросервисы<br>
            • Безопасность и OAuth/JWT<br>
            • Machine Learning, AI<br>
            • CRM/ERP системы<br>
            • Бюджет от 15 000 ₽<br>
            <b>Скорость:</b> медленнее | <b>Качество:</b> максимум
          </div>
        </div>
      </div>
      <div style="margin-top:12px;font-size:.78rem;color:var(--muted)">
        Чтобы включить Claude 3.5 через OpenRouter — добавьте ключ <code>OPENROUTER_API_KEY</code>
        (получить на <a href="https://openrouter.ai" target="_blank" style="color:var(--blue)">openrouter.ai</a>)
      </div>
    </div>
  </div>

  <!-- Минимальная ставка -->
  <div class="section">
    <div class="section-title">⚙️ Настройки рентабельности</div>
    <div style="font-size:.85rem;color:var(--muted);margin-bottom:14px">
      Бот автоматически пропускает заказы, где ставка ниже минимальной.
      Расчёт: бюджет ÷ оценочные часы = ₽/час.
    </div>
    <div id="finance-settings"><div class="empty">Загрузка…</div></div>
  </div>

</div>

<!-- ══════════════════ TAB: ПРОЕКТЫ ══════════════════ -->
<div id="tab-projects" class="hidden">

  <div class="section" style="border-color:#f6ad55">
    <div class="section-title" style="color:#f6ad55">📌 Как работает выполнение заказов</div>
    <div style="font-size:.85rem;color:var(--muted);line-height:1.8">
      <b style="color:var(--text)">1. Бот нашёл заказ →</b> написал отклик → отправил вам в Telegram для проверки<br>
      <b style="color:var(--text)">2. Вы пишете боту в Telegram:</b> <code style="background:var(--surface2);padding:2px 8px;border-radius:4px">OK 123</code> — одобрить, или <code style="background:var(--surface2);padding:2px 8px;border-radius:4px">FIX 123: поправь тон</code> — переделать<br>
      <b style="color:var(--text)">3. После одобрения →</b> бот автоматически выполняет: анализ → разработка → тесты → проверка → упаковка → доставка<br>
      <b style="color:var(--text)">4. Готово →</b> файлы сохраняются в папку <code style="background:var(--surface2);padding:2px 8px;border-radius:4px">deliverables/</code>, вы получаете уведомление в Telegram
    </div>
  </div>

  <div class="section">
    <div class="flex" style="margin-bottom:14px">
      <div class="section-title" style="margin:0">🔄 Текущие проекты</div>
      <button class="btn btn-ghost btn-sm ml-auto" onclick="loadProjects()">🔄 Обновить</button>
    </div>
    <div id="projects-running"><div class="empty">Загрузка…</div></div>
  </div>

  <div class="section">
    <div class="section-title">✅ Завершённые проекты</div>
    <div id="projects-done"><div class="empty">Загрузка…</div></div>
  </div>
</div>

<!-- ══════════════════ TAB: ЗАКАЗЫ ══════════════════ -->
<div id="tab-jobs" class="hidden">
  <div class="section">
    <div class="flex" style="margin-bottom:14px">
      <div class="section-title" style="margin:0">Все заказы</div>
      <div class="flex ml-auto" style="gap:8px">
        <select id="jobs-filter-platform" onchange="loadJobs()" style="width:140px">
          <option value="">Все платформы</option>
        </select>
        <select id="jobs-filter-status" onchange="loadJobs()" style="width:150px">
          <option value="">Все статусы</option>
          <option value="sent">Откликнулись</option>
          <option value="won">Приняты</option>
          <option value="rejected">Отклонены</option>
          <option value="pending">Ожидание</option>
        </select>
        <input type="text" id="jobs-search" placeholder="Поиск…" oninput="loadJobs()" style="width:180px">
      </div>
    </div>
    <div id="jobs-table"><div class="empty">Загрузка…</div></div>
  </div>
</div>

<!-- ══════════════════ TAB: НАСТРОЙКИ ══════════════════ -->
<div id="tab-settings" class="hidden">
  <div class="section">
    <div class="section-title">⚙️ Параметры поиска</div>
    <form onsubmit="saveSettings(event)">
      <div class="form-row">
        <div class="form-group">
          <label>Минимальный бюджет (USD)</label>
          <input type="number" id="cfg-min-budget" min="0" step="5">
        </div>
        <div class="form-group">
          <label>Интервал поиска (минуты)</label>
          <input type="number" id="cfg-interval" min="5" step="5">
        </div>
      </div>
      <div class="form-group">
        <label>Заметки / дополнительные инструкции для бота</label>
        <textarea id="cfg-notes" rows="3" placeholder="Например: не откликаться на задачи дешевле $100, приоритет Telegram-ботам…"></textarea>
      </div>
      <div class="form-actions">
        <button type="submit" class="btn btn-primary">💾 Сохранить</button>
      </div>
    </form>
  </div>

  <div class="section">
    <div class="section-title">🔍 Ключевые слова поиска</div>
    <p style="font-size:.82rem;color:var(--muted);margin-bottom:10px">Слова по которым бот ищет заказы. Можно добавлять и удалять.</p>
    <div class="tags" id="keywords-list"></div>
    <div class="tag-add">
      <input type="text" id="kw-input" placeholder="Новое ключевое слово…" onkeydown="if(event.key==='Enter'){event.preventDefault();addKeyword()}">
      <button class="btn btn-primary btn-sm" onclick="addKeyword()">+ Добавить</button>
    </div>
  </div>

  <div class="section">
    <div class="section-title">🌐 Активные платформы</div>
    <p style="font-size:.82rem;color:var(--muted);margin-bottom:10px">Снимите галочку чтобы исключить платформу из поиска.</p>
    <div class="checkbox-group" id="platforms-checkboxes"></div>
    <div class="form-actions">
      <button class="btn btn-primary" onclick="savePlatforms()">💾 Сохранить платформы</button>
    </div>
  </div>
</div>

<!-- ══════════════════ TAB: УПРАВЛЕНИЕ ══════════════════ -->
<div id="tab-control" class="hidden">
  <div class="control-grid">
    <div class="control-card">
      <h3>🤖 Статус бота</h3>
      <p>Пауза останавливает поиск заказов. Управление доступно и через Telegram.</p>
      <div class="flex">
        <button class="btn btn-success" onclick="resumeBot()">▶ Запустить</button>
        <button class="btn btn-danger" onclick="pauseBot()" style="margin-left:8px">⏸ Пауза</button>
      </div>
    </div>
    <div class="control-card">
      <h3>🔍 Немедленный поиск</h3>
      <p>Запустить цикл поиска прямо сейчас, не дожидаясь расписания.</p>
      <button class="btn btn-primary" onclick="searchNow()">⚡ Искать сейчас</button>
    </div>
    <div class="control-card">
      <h3>📊 Статистика базы</h3>
      <p>Общая информация о данных накопленных ботом.</p>
      <button class="btn btn-ghost" onclick="loadDbStats()">🔄 Обновить</button>
      <div id="db-stats" style="margin-top:10px;font-size:.82rem;line-height:1.8;color:var(--muted)"></div>
    </div>
    <div class="control-card">
      <h3>🧠 Лучшие инсайты</h3>
      <p>Что бот узнал из опыта работы.</p>
      <button class="btn btn-ghost" onclick="loadInsights()">🔄 Обновить</button>
      <div id="insights-list" style="margin-top:10px;font-size:.8rem;color:var(--muted)"></div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">📝 Лог активности</div>
    <div id="activity-log">Нажмите «Обновить» чтобы увидеть последние события…</div>
    <div style="margin-top:10px">
      <button class="btn btn-ghost btn-sm" onclick="loadLog()">🔄 Обновить лог</button>
    </div>
  </div>

  <div class="section">
    <div class="section-title">✉️ Лучшие отклики (топ по оценке)</div>
    <div id="top-proposals"><div class="empty">Загрузка…</div></div>
  </div>
</div>

<!-- ══════════════════ TAB: ПРОФИЛЬ ══════════════════ -->
<div id="tab-profile" class="hidden">
  <div class="section-title" style="font-size:1.1rem;margin-bottom:16px">👤 Настройка профилей — Kwork и FL.ru</div>
  <p style="color:var(--muted);margin-bottom:20px;font-size:.88rem">
    Бот сгенерировал готовый контент для ваших профилей. Скопируйте и вставьте вручную на платформах.
  </p>

  <div id="profile-loading" style="text-align:center;padding:40px;color:var(--muted)">⏳ Загрузка…</div>
  <div id="profile-content" class="hidden">

    <!-- Инструкции -->
    <div class="section" style="margin-bottom:16px">
      <div class="section-title">📋 Инструкции</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div>
          <div style="font-weight:600;margin-bottom:8px;color:var(--yellow)">🟡 Kwork.ru</div>
          <ol id="kwork-instructions" style="color:var(--muted);font-size:.83rem;padding-left:18px;line-height:2"></ol>
        </div>
        <div>
          <div style="font-weight:600;margin-bottom:8px;color:var(--blue)">🔵 FL.ru</div>
          <ol id="flru-instructions" style="color:var(--muted);font-size:.83rem;padding-left:18px;line-height:2"></ol>
        </div>
      </div>
    </div>

    <!-- О себе: Kwork -->
    <div class="section" style="margin-bottom:16px">
      <div class="section-title" style="display:flex;justify-content:space-between;align-items:center">
        <span>🟡 Kwork — текст «О себе»</span>
        <button class="btn btn-ghost btn-sm" onclick="copyText('kwork-bio-text')">📋 Копировать</button>
      </div>
      <textarea id="kwork-bio-text" readonly style="width:100%;min-height:90px;background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:10px;font-size:.85rem;resize:vertical;font-family:inherit"></textarea>
    </div>

    <!-- О себе: FL.ru -->
    <div class="section" style="margin-bottom:16px">
      <div class="section-title" style="display:flex;justify-content:space-between;align-items:center">
        <span>🔵 FL.ru — текст «О себе»</span>
        <button class="btn btn-ghost btn-sm" onclick="copyText('flru-bio-text')">📋 Копировать</button>
      </div>
      <textarea id="flru-bio-text" readonly style="width:100%;min-height:90px;background:var(--surface2);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:10px;font-size:.85rem;resize:vertical;font-family:inherit"></textarea>
    </div>

    <!-- Кворки -->
    <div class="section" style="margin-bottom:16px">
      <div class="section-title">🟡 Kwork — Кворки (готовы к созданию)</div>
      <div id="kwork-gigs-list"></div>
    </div>

    <!-- Портфолио -->
    <div class="section">
      <div class="section-title">🖼 Примеры работ (портфолио)</div>
      <div id="portfolio-list"></div>
    </div>

  </div>
</div>

</main>

<script>
// ── State ──────────────────────────────────────────────
let currentTab = 'overview';
let botPaused = false;
let config = {};
let allPlatforms = ["Kwork","FL.ru"];

// ── Tabs ──────────────────────────────────────────────
function switchTab(name) {
  const tabs = ['overview','messages','jobs','projects','finance','settings','control','profile'];
  document.querySelectorAll('.tab').forEach((t,i) => {
    t.classList.toggle('active', tabs[i] === name);
  });
  tabs.forEach(t => {
    document.getElementById('tab-'+t).classList.toggle('hidden', t !== name);
  });
  currentTab = name;
  if (name === 'overview') loadOverview();
  if (name === 'messages') loadMessages();
  if (name === 'jobs') loadJobs();
  if (name === 'projects') loadProjects();
  if (name === 'finance') loadFinance();
  if (name === 'settings') loadSettings();
  if (name === 'control') { loadDbStats(); loadInsights(); loadTopProposals(); }
  if (name === 'profile') loadProfile();
}

// ── Профиль — копировать текст ──────────────────────────────
function copyText(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.select();
  try {
    document.execCommand('copy');
    toast('Скопировано ✓', 'ok');
  } catch (e) {
    navigator.clipboard.writeText(el.value).then(() => toast('Скопировано ✓', 'ok'));
  }
}

// ── Профиль — загрузка данных ───────────────────────────────
async function loadProfile() {
  try {
    const r = await fetch('/api/profile-setup');
    const d = await r.json();
    document.getElementById('profile-loading').classList.add('hidden');
    document.getElementById('profile-content').classList.remove('hidden');

    // Bios
    document.getElementById('kwork-bio-text').value = d.kwork_bio || '';
    document.getElementById('flru-bio-text').value = d.flru_bio || '';

    // Instructions
    document.getElementById('kwork-instructions').innerHTML =
      (d.kwork_instructions || []).map(s => `<li>${s}</li>`).join('');
    document.getElementById('flru-instructions').innerHTML =
      (d.flru_instructions || []).map(s => `<li>${s}</li>`).join('');

    // Gigs
    const gigsList = document.getElementById('kwork-gigs-list');
    gigsList.innerHTML = (d.kwork_gigs || []).map((g, i) => `
      <div style="border:1px solid var(--border);border-radius:8px;padding:14px;margin-bottom:12px;background:var(--surface2)">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">
          <div style="font-weight:600;color:var(--text)">${i+1}. ${g.title}</div>
          <div style="display:flex;gap:8px;flex-shrink:0;margin-left:12px">
            <span style="background:#2d3748;padding:2px 8px;border-radius:4px;font-size:.78rem;color:#fbbf24">${g.price}</span>
            <span style="background:#2d3748;padding:2px 8px;border-radius:4px;font-size:.78rem;color:#68d391">${g.delivery}</span>
          </div>
        </div>
        <div style="font-size:.8rem;color:var(--muted);margin-bottom:6px">📂 ${g.category}</div>
        <div style="font-size:.82rem;color:#a0aec0;line-height:1.6;margin-bottom:8px">${g.description}</div>
        <div style="font-size:.78rem;color:var(--muted)">🏷️ ${g.tags}</div>
        <button class="btn btn-ghost btn-sm" style="margin-top:8px" onclick="copyGig(${i})">📋 Копировать описание</button>
      </div>
    `).join('');

    // Store gigs for copying
    window._GIGS = d.kwork_gigs || [];

    // Portfolio
    const portList = document.getElementById('portfolio-list');
    portList.innerHTML = (d.portfolio_samples || []).map((p, i) => `
      <div style="border:1px solid var(--border);border-radius:8px;padding:14px;margin-bottom:10px;background:var(--surface2)">
        <div style="font-weight:600;margin-bottom:6px">${p.title}</div>
        <div style="font-size:.83rem;color:var(--muted);line-height:1.6">${p.description}</div>
      </div>
    `).join('');

  } catch(e) {
    document.getElementById('profile-loading').innerHTML = `<div class="empty">Ошибка загрузки: ${e.message}</div>`;
  }
}

function copyGig(i) {
  const g = (window._GIGS || [])[i];
  if (!g) return;
  const text = `${g.title}\n\n${g.description}\n\nЦена: ${g.price} | Срок: ${g.delivery}\nТеги: ${g.tags}`;
  navigator.clipboard.writeText(text).then(() => toast('Кворк скопирован ✓', 'ok')).catch(() => {
    const tmp = document.createElement('textarea');
    tmp.value = text;
    document.body.appendChild(tmp);
    tmp.select();
    document.execCommand('copy');
    document.body.removeChild(tmp);
    toast('Кворк скопирован ✓', 'ok');
  });
}

// ── Финансы ────────────────────────────────────────────────
async function loadFinance() {
  try {
    const r = await fetch('/api/finance');
    const d = await r.json();

    // Stats
    const s = d.stats || {};
    document.getElementById('finance-stats').innerHTML = `
      <div class="stat-grid" style="grid-template-columns:repeat(3,1fr)">
        <div class="stat-card" style="border-color:#68d391">
          <div class="stat-num" style="color:#68d391">${s.total_won || 0}</div>
          <div class="stat-label">✅ Заказов взято</div>
        </div>
        <div class="stat-card" style="border-color:#f6ad55">
          <div class="stat-num" style="color:#f6ad55">${(s.total_budget_rub||0).toLocaleString('ru')} ₽</div>
          <div class="stat-label">💰 Потенциальный доход</div>
        </div>
        <div class="stat-card" style="border-color:#63b3ed">
          <div class="stat-num" style="color:#63b3ed">${s.proposals_sent || 0}</div>
          <div class="stat-label">📤 Откликов отправлено</div>
        </div>
      </div>
      <div style="margin-top:14px;padding:12px;background:var(--surface2);border-radius:8px;font-size:.84rem">
        <div style="display:flex;gap:24px;flex-wrap:wrap">
          <div>📊 Конверсия: <b>${s.win_rate||'0%'}</b></div>
          <div>⏱ Пропущено (невыгодные): <b>${s.skipped_unprofitable||0}</b></div>
          <div>🤖 Модель: <b>${s.llm_provider||'DeepSeek'}</b></div>
          <div>🟣 OpenRouter: <b>${s.openrouter_ready ? '✅ Активен' : '❌ Нет ключа'}</b></div>
        </div>
      </div>
    `;

    // LLM Router status
    const router = d.router || {};
    document.getElementById('llm-router-status').innerHTML = `
      <div style="display:flex;gap:12px;flex-wrap:wrap">
        <div style="flex:1;min-width:200px;background:var(--surface2);padding:12px;border-radius:8px">
          <div style="font-size:.78rem;color:var(--muted);margin-bottom:4px">Текущий провайдер (основной)</div>
          <div style="font-weight:700;color:${router.deepseek_ready?'#68d391':'#fc8181'}">
            ${router.deepseek_ready?'✅':'❌'} DeepSeek
          </div>
          <div style="font-size:.75rem;color:var(--muted);margin-top:4px">
            Модель: ${router.deepseek_model||'deepseek-chat'} | Быстро, дёшево
          </div>
        </div>
        <div style="flex:1;min-width:200px;background:var(--surface2);padding:12px;border-radius:8px">
          <div style="font-size:.78rem;color:var(--muted);margin-bottom:4px">Провайдер для сложных задач</div>
          <div style="font-weight:700;color:${router.openrouter_ready?'#b794f4':'#fc8181'}">
            ${router.openrouter_ready?'✅':'❌'} OpenRouter
          </div>
          <div style="font-size:.75rem;color:var(--muted);margin-top:4px">
            ${router.openrouter_ready
              ? 'Модель: claude-3.5-sonnet | Максимальное качество'
              : 'Добавьте OPENROUTER_API_KEY → openrouter.ai'}
          </div>
        </div>
      </div>
    `;

    // Effort settings
    const cfg = d.config || {};
    document.getElementById('finance-settings').innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-bottom:14px">
        <div>
          <label style="font-size:.78rem;color:var(--muted);display:block;margin-bottom:4px">
            Минимальная ставка (₽/час)
          </label>
          <div style="display:flex;gap:8px">
            <input id="min-hourly" type="number" value="${cfg.min_hourly_rate||400}"
              style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:6px 10px;color:var(--text);width:100%;font-size:.9rem">
            <button class="btn btn-primary btn-sm" onclick="saveFinanceConfig()">Сохранить</button>
          </div>
          <div style="font-size:.74rem;color:var(--muted);margin-top:4px">
            Заказы где ставка ниже — автоматически пропускаются
          </div>
        </div>
        <div>
          <label style="font-size:.78rem;color:var(--muted);display:block;margin-bottom:4px">
            Мин. бюджет заказа ($)
          </label>
          <div style="display:flex;gap:8px">
            <input id="min-budget" type="number" value="${cfg.min_budget||50}"
              style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:6px 10px;color:var(--text);width:100%;font-size:.9rem">
            <button class="btn btn-primary btn-sm" onclick="saveFinanceConfig()">Сохранить</button>
          </div>
          <div style="font-size:.74rem;color:var(--muted);margin-top:4px">
            Заказы ниже минимума не обрабатываются
          </div>
        </div>
      </div>
      <div style="background:var(--surface2);padding:12px;border-radius:8px;font-size:.82rem">
        <b>Оценка трудозатрат:</b><br>
        🟢 Простой заказ (~2 ч): скрипты, боты, парсеры<br>
        🟡 Средний (~6 ч): интеграции API, автоматизация<br>
        🔴 Сложный (~20 ч): архитектура, ML, безопасность, CRM
      </div>
    `;
  } catch(e) {
    document.getElementById('finance-stats').innerHTML = `<div class="empty">Ошибка: ${e.message}</div>`;
  }
}

async function saveFinanceConfig() {
  const rate = document.getElementById('min-hourly')?.value;
  const budget = document.getElementById('min-budget')?.value;
  const r = await fetch('/api/finance/config', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({min_hourly_rate: parseFloat(rate), min_budget: parseFloat(budget)})
  });
  const d = await r.json();
  if (d.ok) toast('Настройки сохранены ✓');
  else toast('Ошибка: ' + (d.error||'?'), 'err');
}

// ── Переписка ──────────────────────────────────────────
async function loadMessages() {
  const kwEl = document.getElementById('messages-kwork');
  const flEl = document.getElementById('messages-flru');
  kwEl.innerHTML = '<div class="empty">Загрузка сообщений Kwork…</div>';
  flEl.innerHTML = '<div class="empty">Загрузка сообщений FL.ru…</div>';
  try {
    const r = await fetch('/api/messages');
    const d = await r.json();

    // Kwork messages
    const kwMsgs = d.kwork || [];
    const badge = document.getElementById('msg-badge');
    const unread = kwMsgs.filter(m => m.unread).length;
    if (unread > 0) { badge.textContent = unread; badge.style.display = ''; }
    else { badge.style.display = 'none'; }

    if (!kwMsgs.length) {
      kwEl.innerHTML = `<div class="empty">${esc(d.kwork_status || 'Нет сообщений')}</div>`;
    } else {
      kwEl.innerHTML = kwMsgs.map((m,i) => `
        <div class="msg-card ${m.unread ? 'unread' : ''}">
          <div class="msg-header">
            <div>
              <div class="msg-sender">${m.unread ? '🔴 ' : ''}${esc(m.sender || 'Клиент')}</div>
              ${m.order_title ? `<div style="font-size:.78rem;color:var(--blue);margin-top:2px">📋 ${esc(m.order_title)}</div>` : ''}
            </div>
            <div class="msg-date">${esc(m.date || '')}</div>
          </div>
          <div class="msg-preview">${esc(m.text || '')}</div>
          <div class="msg-actions">
            ${m.url ? `<a href="${m.url}" target="_blank" class="btn btn-primary btn-sm">Открыть на Kwork ↗</a>` : ''}
            ${m.unread ? `<button class="btn btn-ghost btn-sm" onclick="replyMsg('kwork',${m.id||i},'${esc(m.sender||'')}','${encodeURIComponent(m.text||'')}')">💬 Ответить</button>` : ''}
          </div>
        </div>
      `).join('');
    }

    // FL.ru messages
    const flMsgs = d.flru || [];
    if (!flMsgs.length) {
      flEl.innerHTML = `<div class="empty">${esc(d.flru_status || 'Нет сообщений')}</div>`;
    } else {
      flEl.innerHTML = flMsgs.map((m,i) => `
        <div class="msg-card ${m.unread ? 'unread' : ''}">
          <div class="msg-header">
            <div>
              <div class="msg-sender">${m.unread ? '🔴 ' : ''}${esc(m.sender || 'Клиент')}</div>
            </div>
            <div class="msg-date">${esc(m.date || '')}</div>
          </div>
          <div class="msg-preview">${esc(m.text || '')}</div>
          <div class="msg-actions">
            ${m.url ? `<a href="${m.url}" target="_blank" class="btn btn-primary btn-sm">Открыть на FL.ru ↗</a>` : ''}
          </div>
        </div>
      `).join('');
    }
  } catch(e) {
    kwEl.innerHTML = `<div class="empty">Ошибка загрузки: ${e.message}</div>`;
    flEl.innerHTML = `<div class="empty">—</div>`;
  }
}

async function replyMsg(platform, msgId, sender, encodedText) {
  const text = decodeURIComponent(encodedText);
  const reply = prompt(`Ответить клиенту ${sender}:\n\n"${text.substring(0,100)}…"\n\nВаш ответ:`);
  if (!reply) return;
  const r = await fetch('/api/reply-message', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({platform, msg_id: msgId, text: reply, sender})
  });
  const d = await r.json();
  if (d.ok) { toast('Ответ отправлен ✓'); loadMessages(); }
  else toast('Ошибка отправки: ' + (d.error || '?'), 'err');
}

// ── Toast ──────────────────────────────────────────────
function toast(msg, type='ok') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'show ' + type;
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.className = '', 2800);
}

// ── Modal ──────────────────────────────────────────────
window._PMAP = {};
function showModal(title, body) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').textContent = body;
  document.getElementById('modal').classList.remove('hidden');
}
function showProposal(key) {
  showModal('Отклик', window._PMAP[key] || '—');
}
async function viewProposalText(proposalId) {
  const r = await fetch(`/api/proposal-text/${proposalId}`);
  const d = await r.json();
  showModal('Текст отклика', d.text || '—');
}
function closeModal() {
  document.getElementById('modal').classList.add('hidden');
}
document.getElementById('modal').addEventListener('click', e => {
  if (e.target.id === 'modal') closeModal();
});

// ── Pause / Resume ─────────────────────────────────────
async function togglePause() {
  if (botPaused) await resumeBot(); else await pauseBot();
}
async function pauseBot() {
  await fetch('/api/pause', {method:'POST'});
  toast('Бот поставлен на паузу ⏸');
  updatePauseBtn(true);
}
async function resumeBot() {
  await fetch('/api/resume', {method:'POST'});
  toast('Бот запущен ▶');
  updatePauseBtn(false);
}
function updatePauseBtn(paused) {
  botPaused = paused;
  const btn = document.getElementById('pause-btn');
  btn.textContent = paused ? '⏸ Пауза' : '▶ Активен';
  btn.className = 'status-pill ' + (paused ? 'status-paused' : 'status-running');
}

async function searchNow() {
  const r = await fetch('/api/search-now', {method:'POST'});
  const j = await r.json();
  toast(j.message || 'Поиск запущен ⚡');
}

// ── Clock ──────────────────────────────────────────────
function tick() {
  document.getElementById('header-time').textContent = new Date().toLocaleString('ru-RU',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
}
setInterval(tick, 1000); tick();

// ── Статус отклика ─────────────────────────────────────
function proposalStatusHtml(status) {
  const map = {
    'sent':     ['#f6e05e','#744210','⏳ Ожидает ответа'],
    'pending':  ['#f6e05e','#744210','⏳ Ожидает ответа'],
    'viewed':   ['#63b3ed','#1a365d','👁 Просмотрен'],
    'replied':  ['#fc8181','#742a2a','💬 Клиент написал!'],
    'won':      ['#68d391','#1c4532','✅ Взят'],
    'rejected': ['#4a5568','#e2e8f0','❌ Отклонён'],
  };
  const [bg, col, label] = map[status] || ['#4a5568','#e2e8f0', status || '—'];
  return `<span style="background:${bg};color:${col};border-radius:6px;padding:3px 10px;font-size:.78rem;font-weight:600;white-space:nowrap">${label}</span>`;
}

// ── Загрузка обзора ────────────────────────────────────
async function loadOverview() {
  // Параллельно загружаем данные
  const [r1, r2, r3] = await Promise.all([
    fetch('/api/my-proposals'), fetch('/api/data'), fetch('/api/active-orders')
  ]);
  const [mp, d, ao] = await Promise.all([r1.json(), r2.json(), r3.json()]);

  updatePauseBtn(d.paused);

  // KPI счётчики
  document.getElementById('s-prop').textContent   = mp.counts.sent;
  document.getElementById('s-replied').textContent = mp.counts.replied;
  document.getElementById('s-wins').textContent    = mp.counts.won;
  document.getElementById('s-rej').textContent     = mp.counts.rejected;

  // Мигание карточки "Клиент ответил" если есть
  const sc = document.getElementById('sc-replied');
  sc.style.animation = mp.counts.replied > 0 ? 'pulse 1.5s infinite' : '';

  // === АКТИВНЫЕ ЗАКАЗЫ ===
  const aob = document.getElementById('active-order-block');
  const aoc = document.getElementById('active-order-content');
  if (ao.orders && ao.orders.length > 0) {
    aob.style.display = '';
    aoc.innerHTML = ao.orders.map(o => `
      <div style="display:flex;align-items:flex-start;gap:20px;flex-wrap:wrap">
        <div style="flex:1;min-width:220px">
          <div style="font-size:1rem;font-weight:700;margin-bottom:6px">
            <span class="platform-badge">${esc(o.platform)}</span>
            ${o.url ? `<a href="${o.url}" target="_blank" style="color:var(--blue);text-decoration:none;margin-left:8px">${esc(o.title)} ↗</a>`
                    : `<span style="margin-left:8px">${esc(o.title)}</span>`}
          </div>
          <div style="color:var(--muted);font-size:.82rem;margin-bottom:10px">
            Взят: ${o.won_at ? o.won_at.replace('T',' ').substring(0,16) : '—'}
            ${o.budget ? ' · Бюджет: <b>' + o.budget + ' ' + (o.currency||'') + '</b>' : ''}
          </div>
          <div style="color:var(--text);font-size:.88rem;margin-bottom:12px">
            🤖 <b>Бот работает автоматически:</b> отслеживает переписку, отвечает клиенту, выполняет работу и сдаёт результат. Ваше участие не требуется.
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            ${o.url ? `<a href="${o.url}" target="_blank" class="btn" style="background:var(--green);color:#fff;text-decoration:none;padding:6px 14px;border-radius:6px;font-size:.83rem;font-weight:600">Открыть на ${esc(o.platform)} ↗</a>` : ''}
            <button class="btn btn-ghost btn-sm" onclick='viewProposalText(${o.proposal_id})'>📄 Посмотреть отклик</button>
          </div>
        </div>
        <div style="font-size:.8rem;color:var(--muted);min-width:160px">
          <div style="margin-bottom:4px">📊 Статус: <b style="color:var(--green)">Взят ✓</b></div>
          <div>🤖 Выполнение: <b>${o.execution_status || 'Ожидает запуска'}</b></div>
        </div>
      </div>
    `).join('<hr style="border:0;border-top:1px solid var(--border);margin:14px 0">');
  } else {
    aob.style.display = 'none';
  }

  // === ГЛАВНАЯ ТАБЛИЦА ОТКЛИКОВ ===
  const proposals = mp.proposals;  // sorted: replied → sent → won → rejected
  const mt = document.getElementById('my-proposals-table');
  if (!proposals.length) {
    mt.innerHTML = '<div class="empty">Откликов пока нет. Бот ищет заказы…</div>';
  } else {
    proposals.forEach((p,i) => { if(p.proposal_text) window._PMAP['mp'+i] = p.proposal_text; });
    let lastSection = null;
    const rows = proposals.map((p,i) => {
      let sectionHeader = '';
      const section = p.status === 'replied' ? 'replied'
                    : (p.status === 'sent' || p.status === 'pending' || p.status === 'viewed') ? 'waiting'
                    : p.status === 'won' ? 'won' : 'rejected';
      if (section !== lastSection) {
        lastSection = section;
        const labels = {
          replied:  '💬 Клиент написал — бот отвечает автоматически',
          waiting:  '⏳ Ожидают ответа от клиента (бот следит)',
          won:      '✅ Взятые заказы',
          rejected: '❌ Отклонённые',
        };
        sectionHeader = `<tr><td colspan="6" style="background:var(--surface2);color:var(--muted);font-size:.75rem;font-weight:700;text-transform:uppercase;padding:8px 12px;letter-spacing:.05em">${labels[section]}</td></tr>`;
      }
      const rowBg = p.status === 'replied' ? 'background:rgba(252,129,129,.08)' : '';
      const titleHtml = p.url
        ? `<a href="${p.url}" target="_blank" style="color:var(--blue);text-decoration:none;font-weight:500">${esc((p.title||'').substring(0,60))}${(p.title||'').length>60?'…':''}</a>`
        : `<span style="font-weight:500">${esc((p.title||'').substring(0,60))}</span>`;
      const actionBtns = '';
      return sectionHeader + `<tr style="${rowBg}">
        <td><span class="platform-badge">${p.platform}</span></td>
        <td style="max-width:340px">${titleHtml}</td>
        <td class="nowrap text-muted">${p.budget ? p.budget+' '+p.currency : '—'}</td>
        <td>${proposalStatusHtml(p.status)}</td>
        <td class="nowrap text-muted" style="font-size:.78rem">${p.sent_at}</td>
        <td class="nowrap flex" style="gap:4px">
          ${p.proposal_text ? `<button class="btn btn-ghost btn-sm btn-icon" title="Посмотреть текст отклика" onclick="showProposal('mp${i}')">📄</button>` : ''}
          ${actionBtns}
        </td>
      </tr>`;
    }).join('');
    mt.innerHTML = `<table style="width:100%">
      <tr><th>Платформа</th><th>Заказ</th><th>Бюджет</th><th>Статус</th><th>Отправлен</th><th>Действие</th></tr>
      ${rows}
    </table>`;
  }

  // === Платформы ===
  const pt = document.getElementById('platforms-table');
  if (!d.platforms.length) { pt.innerHTML = '<div class="empty">Нет данных</div>'; }
  else {
    pt.innerHTML = `<table>
      <tr><th>Платформа</th><th>Статус</th><th>Заказов</th><th>Откликов</th><th>Побед</th><th>Конверсия</th><th>Проверено</th></tr>
      ${d.platforms.map(p => `<tr>
        <td><span class="platform-badge">${p.platform}</span></td>
        <td>${statusBadge(p.status)}</td>
        <td>${p.jobs}</td><td>${p.proposals}</td><td>${p.wins}</td>
        <td>${p.wr}%</td><td class="text-muted nowrap">${p.checked}</td>
      </tr>`).join('')}
    </table>`;
  }

  // === Последние найденные заказы (сокращённо) ===
  const jt = document.getElementById('recent-jobs-table');
  if (!d.jobs.length) { jt.innerHTML = '<div class="empty">Заказов пока нет</div>'; }
  else {
    d.jobs.slice(0,8).forEach((j,i) => { if(j.proposal_text) window._PMAP['ov'+i] = j.proposal_text; });
    jt.innerHTML = `<table>
      <tr><th>Платформа</th><th>Заказ</th><th>Бюджет</th><th>Оценка ИИ</th><th>Найден</th></tr>
      ${d.jobs.slice(0,8).map((j,i) => `<tr>
        <td><span class="platform-badge">${j.platform}</span></td>
        <td style="max-width:400px">${j.url ? `<a href="${j.url}" target="_blank" style="color:var(--blue);text-decoration:none">${esc(j.title.substring(0,65))}${j.title.length>65?'…':''}</a>` : esc(j.title.substring(0,65))}</td>
        <td class="nowrap">${j.budget ? j.budget+' '+j.currency : '—'}</td>
        <td>${j.score ? `<span style="color:${j.score>=7?'var(--green)':j.score>=5?'var(--yellow)':'var(--red)'}">${j.score}/10</span>` : '—'}</td>
        <td class="text-muted nowrap">${j.first_seen}</td>
      </tr>`).join('')}
    </table><div class="text-muted" style="font-size:.75rem;margin-top:6px;text-align:right">Все заказы → вкладка "Заказы"</div>`;
  }
}

// ── Jobs Tab ────────────────────────────────────────────
async function loadJobs() {
  const platform = document.getElementById('jobs-filter-platform').value;
  const status = document.getElementById('jobs-filter-status').value;
  const q = document.getElementById('jobs-search').value;
  const r = await fetch(`/api/jobs?platform=${encodeURIComponent(platform)}&status=${encodeURIComponent(status)}&q=${encodeURIComponent(q)}`);
  const d = await r.json();

  // Fill platform filter
  const sel = document.getElementById('jobs-filter-platform');
  if (sel.options.length <= 1) {
    allPlatforms.forEach(p => { const o = document.createElement('option'); o.value=p; o.text=p; sel.appendChild(o); });
  }

  const jt = document.getElementById('jobs-table');
  if (!d.jobs.length) { jt.innerHTML = '<div class="empty">Заказов не найдено</div>'; return; }

  d.jobs.forEach((j,i) => { if(j.proposal_text) window._PMAP['jb'+i] = j.proposal_text; });
  jt.innerHTML = `<table>
    <tr><th>Платформа</th><th>Заказ</th><th>Бюджет</th><th>Отклик</th><th>Оценка</th><th>Дата</th><th>Действия</th></tr>
    ${d.jobs.map((j,i) => `<tr>
      <td><span class="platform-badge">${j.platform}</span></td>
      <td>${j.url ? `<a href="${j.url}" target="_blank" style="color:var(--blue);text-decoration:none">${esc(j.title.substring(0,55))}${j.title.length>55?'…':''}</a>` : esc(j.title.substring(0,55))}</td>
      <td class="nowrap">${j.budget ? j.budget+' '+j.currency : '—'}</td>
      <td>${proposalBadge(j.proposal_status, j.is_relevant)}</td>
      <td>${j.score ? j.score+'/10' : '—'}</td>
      <td class="text-muted nowrap">${j.first_seen}</td>
      <td class="nowrap flex">
        ${j.proposal_text ? `<button class="btn btn-ghost btn-sm btn-icon" title="Просмотр отклика" onclick="showProposal('jb${i}')">📄</button>` : ''}
        
      </td>
    </tr>`).join('')}
  </table>
  <div class="text-muted" style="font-size:.78rem;margin-top:8px;text-align:right">Показано ${d.jobs.length} заказов</div>`;
}

async function markOutcome(proposalId, outcome) {
  const r = await fetch('/api/mark-outcome', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({proposal_id: proposalId, outcome})
  });
  const j = await r.json();
  toast(j.ok ? (outcome==='won'?'🏆 Победа записана!':'✗ Отклонение записано') : '❌ Ошибка', j.ok?'ok':'err');
  loadJobs();
}

// ── Settings Tab ────────────────────────────────────────
async function loadSettings() {
  const r = await fetch('/api/config');
  config = await r.json();

  document.getElementById('cfg-min-budget').value = config.min_budget || 50;
  document.getElementById('cfg-interval').value = config.search_interval_minutes || 20;
  document.getElementById('cfg-notes').value = config.notes || '';

  renderKeywords();
  renderPlatformCheckboxes();
}

function renderKeywords() {
  const list = document.getElementById('keywords-list');
  list.innerHTML = (config.keywords || []).map((kw,i) =>
    `<span class="tag">${esc(kw)}<span class="tag-del" onclick="removeKeyword(${i})">×</span></span>`
  ).join('');
}

function removeKeyword(i) {
  config.keywords.splice(i, 1);
  renderKeywords();
  saveKeywords();
}

function addKeyword() {
  const inp = document.getElementById('kw-input');
  const val = inp.value.trim();
  if (!val) return;
  if (!config.keywords) config.keywords = [];
  config.keywords.push(val);
  inp.value = '';
  renderKeywords();
  saveKeywords();
}

async function saveKeywords() {
  await fetch('/api/config', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({keywords: config.keywords})
  });
  toast('Ключевые слова сохранены');
}

function renderPlatformCheckboxes() {
  const c = document.getElementById('platforms-checkboxes');
  const disabled = config.disabled_platforms || [];
  c.innerHTML = allPlatforms.map(p =>
    `<label class="checkbox-item"><input type="checkbox" value="${p}" ${disabled.includes(p)?'':'checked'}> ${p}</label>`
  ).join('');
}

async function savePlatforms() {
  const disabled = [];
  document.querySelectorAll('#platforms-checkboxes input').forEach(cb => {
    if (!cb.checked) disabled.push(cb.value);
  });
  await fetch('/api/config', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({disabled_platforms: disabled})
  });
  toast('Платформы сохранены');
}

async function saveSettings(e) {
  e.preventDefault();
  const data = {
    min_budget: parseFloat(document.getElementById('cfg-min-budget').value),
    search_interval_minutes: parseInt(document.getElementById('cfg-interval').value),
    notes: document.getElementById('cfg-notes').value,
  };
  const r = await fetch('/api/config', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(data)
  });
  const j = await r.json();
  toast(j.ok ? '✅ Настройки сохранены' : '❌ Ошибка', j.ok?'ok':'err');
}

// ── Control Tab ─────────────────────────────────────────
async function loadDbStats() {
  const r = await fetch('/api/db-stats');
  const d = await r.json();
  document.getElementById('db-stats').innerHTML = Object.entries(d.tables).map(([k,v])=>
    `<div><span style="color:var(--text)">${k}</span>: <b>${v}</b> записей</div>`
  ).join('');
}

async function loadInsights() {
  const r = await fetch('/api/insights');
  const d = await r.json();
  const el = document.getElementById('insights-list');
  if (!d.insights.length) { el.innerHTML = '<i>Инсайтов пока нет</i>'; return; }
  el.innerHTML = d.insights.slice(0,5).map(i =>
    `<div style="margin-bottom:6px;padding:6px 8px;background:var(--surface2);border-radius:5px">
      <span style="color:var(--blue)">[${i.platform}]</span> ${esc(i.content.substring(0,120))}
    </div>`
  ).join('');
}

async function loadTopProposals() {
  const r = await fetch('/api/top-proposals');
  const d = await r.json();
  const el = document.getElementById('top-proposals');
  if (!d.proposals.length) { el.innerHTML = '<div class="empty">Нет данных</div>'; return; }
  d.proposals.forEach((p,i) => { if(p.text) window._PMAP['tp'+i] = p.text; });
  el.innerHTML = `<table>
    <tr><th>Платформа</th><th>Заказ</th><th>Оценка</th><th>Отклик</th><th></th></tr>
    ${d.proposals.map((p,i) => `<tr>
      <td><span class="platform-badge">${p.platform}</span></td>
      <td>${esc((p.job_title||'').substring(0,50))}</td>
      <td class="text-green">${p.score ? '⭐ '+p.score+'/10' : '—'}</td>
      <td class="text-muted">${esc((p.text||'').substring(0,80))}…</td>
      <td><button class="btn btn-ghost btn-sm btn-icon" onclick="showProposal('tp${i}')">📄</button></td>
    </tr>`).join('')}
  </table>`;
}

// ── Projects Tab ────────────────────────────────────────
const STAGES = ['Анализ','Разработка','Тесты','Проверка','Упаковка','Доставка'];

function stageBar(iterations, status) {
  if (status === 'completed') {
    return `<div style="display:flex;gap:4px">${STAGES.map(s=>`<div style="flex:1;height:6px;background:var(--green);border-radius:3px" title="${s}"></div>`).join('')}</div>`;
  }
  const done = Math.min(iterations || 1, STAGES.length);
  return `<div style="display:flex;gap:4px">${STAGES.map((s,i)=>`<div style="flex:1;height:6px;background:${i<done?'var(--blue)':'var(--border)'};border-radius:3px" title="${s}"></div>`).join('')}</div><div style="font-size:.72rem;color:var(--muted);margin-top:3px">${STAGES[Math.min(done,STAGES.length-1)]}</div>`;
}

async function loadProjects() {
  const r = await fetch('/api/projects');
  const d = await r.json();

  const badge = document.getElementById('projects-badge');
  if (badge) {
    if (d.running.length > 0) {
      badge.textContent = d.running.length;
      badge.style.display = '';
    } else {
      badge.style.display = 'none';
    }
  }

  const runEl = document.getElementById('projects-running');
  if (!d.running.length) {
    runEl.innerHTML = '<div class="empty">Нет активных проектов. Ожидаем заказов на Kwork / FL.ru</div>';
  } else {
    runEl.innerHTML = `<table>
      <tr><th>Платформа</th><th>Заказ</th><th>Статус</th><th>Прогресс</th><th>Итераций</th><th>Начат</th></tr>
      ${d.running.map(p => `<tr>
        <td><span class="platform-badge">${p.platform}</span></td>
        <td style="max-width:260px">${esc(p.title)}</td>
        <td>
          ${p.status==='running'?'<span class="badge bg-yellow">▶ Выполняется</span>':
            p.status==='queued'?'<span class="badge bg-blue">⏳ В очереди</span>':
            `<span class="badge bg-gray">${esc(p.status)}</span>`}
        </td>
        <td style="min-width:160px">${stageBar(p.iterations, p.status)}</td>
        <td>${p.iterations || 0}</td>
        <td class="text-muted nowrap">${p.started}</td>
      </tr>`).join('')}
    </table>`;
  }

  const doneEl = document.getElementById('projects-done');
  if (!d.done.length) {
    doneEl.innerHTML = '<div class="empty">Завершённых проектов пока нет</div>';
  } else {
    doneEl.innerHTML = `<table>
      <tr><th>Платформа</th><th>Заказ</th><th>Оценка</th><th>Тесты</th><th>Файлы</th><th>Завершён</th></tr>
      ${d.done.map(p => `<tr>
        <td><span class="platform-badge">${p.platform}</span></td>
        <td>${esc(p.title.substring(0,55))}</td>
        <td>${p.score ? `<span class="text-green">⭐ ${p.score}/10</span>` : '—'}</td>
        <td>${p.test_passed ? '<span class="badge bg-green">✓ Прошли</span>' : '<span class="badge bg-red">✗ Не прошли</span>'}</td>
        <td>${p.deliverable ? `<span class="badge bg-blue">📦 Готово</span>` : '—'}</td>
        <td class="text-muted nowrap">${p.completed}</td>
      </tr>`).join('')}
    </table>`;
  }
}

async function loadLog() {
  const r = await fetch('/api/log');
  const d = await r.json();
  const el = document.getElementById('activity-log');
  el.textContent = d.lines.join('\n') || 'Лог пуст';
  el.scrollTop = el.scrollHeight;
}

// ── Helpers ─────────────────────────────────────────────
function esc(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function statusBadge(status) {
  if (!status || status === 'ok') return '<span class="badge bg-green">✓ Активна</span>';
  if (status === 'error') return '<span class="badge bg-red">✗ Ошибка</span>';
  if (status === 'degraded') return '<span class="badge bg-yellow" title="Были ошибки в последнем цикле, бот продолжает работу">⚠️ Были ошибки</span>';
  return `<span class="badge bg-yellow">⚠️ ${esc(status)}</span>`;
}

function proposalBadge(status, isRelevant) {
  if (status === 'won') return '<span class="badge bg-green">🏆 Принят</span>';
  if (status === 'sent') return '<span class="badge bg-blue">✓ Отправлен</span>';
  if (status === 'rejected') return '<span class="badge bg-red">✗ Отклонён</span>';
  if (status === 'viewed') return '<span class="badge bg-yellow">👁 Просмотрен</span>';
  if (isRelevant === 0) return '<span class="badge bg-gray">Нерелевантный</span>';
  return '<span class="badge bg-gray">Ожидание</span>';
}

// ── Cookie Status Banner ─────────────────────────────────
async function checkCookieStatus() {
  try {
    const r = await fetch('/api/cookie-status');
    const d = await r.json();
    const banner = document.getElementById('cookie-banner');
    const kw = d.kwork;

    // Always reset inline styles before applying new state
    banner.style.cssText = '';
    if (!kw.configured) {
      banner.className = 'cookie-banner error';
      banner.innerHTML = '🔴 KWORK_SESSION_COOKIE не задан — бот не может отправлять отклики. Добавьте куки Kwork в Secrets.';
    } else if (kw.valid === false) {
      banner.className = 'cookie-banner error';
      banner.innerHTML = `🔴 Сессия Kwork истекла! ${esc(kw.error)} Откройте kwork.ru в браузере → DevTools → Storage → Cookies и обновите секрет KWORK_SESSION_COOKIE.`;
    } else if (kw.valid === true && kw.days_remaining !== null && kw.days_remaining < 7) {
      banner.className = 'cookie-banner warn';
      const daysStr = kw.days_remaining <= 0 ? 'истёк!' : `осталось ${kw.days_remaining} дн.`;
      const expStr = kw.expires_at ? ` (${esc(kw.expires_at)})` : '';
      banner.innerHTML = `⚠️ Сессия Kwork истекает скоро${expStr} — ${daysStr}. Обновите KWORK_SESSION_COOKIE в Secrets заблаговременно!`;
    } else if (kw.valid === true) {
      const expInfo = kw.expires_at ? ` — активна до ${esc(kw.expires_at)}` : '';
      banner.className = 'cookie-banner';
      banner.style.cssText = 'display:flex;background:#1a3a1a;color:#68d391;border-bottom:1px solid var(--border)';
      banner.innerHTML = `✅ Kwork сессия активна${expInfo}`;
      // Hide after 10s to avoid clutter when all is fine
      setTimeout(() => { banner.style.display = 'none'; }, 10000);
    } else {
      banner.className = 'cookie-banner';
      banner.style.display = 'none';
    }
  } catch(e) {}
}

// ── Init ────────────────────────────────────────────────
async function init() {
  const r = await fetch('/api/data');
  const d = await r.json();
  updatePauseBtn(d.paused);
  loadOverview();
  checkCookieStatus();
}

// Auto-refresh every 30s on overview, 5min on messages tab
setInterval(() => { if(currentTab==='overview') loadOverview(); }, 30000);
setInterval(() => { if(currentTab==='messages') loadMessages(); }, 300000);
// Re-check cookie status every 5 min
setInterval(checkCookieStatus, 300000);

// Check unread messages badge every 3 minutes in background
async function checkMsgBadge() {
  try {
    const r = await fetch('/api/messages');
    const d = await r.json();
    const unread = (d.kwork || []).filter(m => m.unread).length;
    const badge = document.getElementById('msg-badge');
    if (unread > 0) { badge.textContent = unread; badge.style.display = ''; }
    else { badge.style.display = 'none'; }
  } catch(e) {}
}
setInterval(checkMsgBadge, 180000);

init();
</script>
</body>
</html>"""


# ── API endpoints ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML)


# /health route is defined later (extended in v15.5)


# ============================================================
# v15.7: Knowledge Base — two tabs (Bot guide + Python lessons)
# ============================================================
KNOWLEDGE_HTML = r"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>База знаний — FreelanceBot</title>
<style>
:root { --bg:#0d1117; --panel:#161b22; --border:#30363d; --text:#c9d1d9;
        --accent:#58a6ff; --green:#3fb950; --yellow:#d29922; --code:#1f2428; }
* { box-sizing:border-box; }
body { margin:0; font-family:-apple-system,Segoe UI,Roboto,sans-serif;
       background:var(--bg); color:var(--text); line-height:1.6; }
header { background:var(--panel); padding:16px 24px; border-bottom:1px solid var(--border);
         display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; }
header h1 { margin:0; font-size:20px; }
header a { color:var(--accent); text-decoration:none; font-size:14px; }
.tabs { display:flex; gap:4px; background:var(--panel); padding:0 24px;
        border-bottom:1px solid var(--border); overflow-x:auto; }
.tab { padding:14px 20px; cursor:pointer; border:none; background:none; color:var(--text);
       font-size:15px; border-bottom:2px solid transparent; white-space:nowrap; }
.tab.active { border-bottom-color:var(--accent); color:var(--accent); font-weight:600; }
main { max-width:900px; margin:0 auto; padding:24px; }
.panel { display:none; }
.panel.active { display:block; }
h2 { color:var(--accent); margin-top:32px; padding-bottom:8px; border-bottom:1px solid var(--border); }
h3 { color:var(--text); margin-top:24px; }
code { background:var(--code); padding:2px 6px; border-radius:4px; font-size:13px;
       color:#79c0ff; }
pre { background:var(--code); padding:14px; border-radius:6px; overflow-x:auto;
      border:1px solid var(--border); }
pre code { background:none; padding:0; color:var(--text); }
.tip { background:rgba(63,185,80,0.1); border-left:3px solid var(--green);
       padding:12px 16px; margin:16px 0; border-radius:4px; }
.warn { background:rgba(210,153,34,0.1); border-left:3px solid var(--yellow);
        padding:12px 16px; margin:16px 0; border-radius:4px; }
ul, ol { padding-left:24px; }
li { margin:6px 0; }
kbd { background:var(--code); border:1px solid var(--border); border-radius:3px;
      padding:1px 6px; font-size:12px; }
</style></head>
<body>
<header>
  <h1>📚 База знаний FreelanceBot</h1>
  <a href="/">← На дашборд</a>
</header>
<div class="tabs">
  <button class="tab active" data-target="howto">🤖 Как пользоваться ботом</button>
  <button class="tab" data-target="python">🐍 Уроки Python</button>
</div>
<main>

<section id="howto" class="panel active">
  <h2>1. Что делает бот</h2>
  <p>Бот каждые 20 минут проверяет Kwork и FL.ru, ищет подходящие заказы по Python/автоматизации,
  пишет персональные отклики через ИИ (DeepSeek) и отправляет их с вашего аккаунта.
  Когда клиент отвечает — бот общается, выполняет заказ (генерирует код, тесты, README в ZIP)
  и отправляет результат в личку.</p>

  <h2>2. Главный экран (дашборд)</h2>
  <ul>
    <li><b>Pipeline</b> — сколько откликов отправлено, сколько ответили, сколько в работе</li>
    <li><b>Revenue</b> — сумма по активным проектам и месячный прогноз</li>
    <li><b>Hot Skills</b> — какие навыки сейчас платят больше</li>
    <li><b>Optimal Times</b> — лучшее время отправки откликов на каждой бирже (UTC)</li>
  </ul>
  <div class="tip">💡 <b>Все цифры — реальные.</b> Бот не использует заглушки.
  Если видите $0 — значит реально 0 (например, ещё нет завершённых сделок).</div>

  <h2>3. Управление ботом</h2>
  <h3>Поставить на паузу</h3>
  <p>В Telegram-боте: команда <code>/pause</code>. Бот перестанет искать новые заказы
  и отправлять отклики (текущие проекты доделает). Возобновить: <code>/resume</code>.</p>
  <div class="warn">⚠️ Сейчас Telegram отключён — нужны секреты <code>TELEGRAM_BOT_TOKEN</code>
  и <code>TELEGRAM_CHAT_ID</code>. Скажите когда добавить — подключу.</div>

  <h3>Проверить здоровье системы</h3>
  <p>Откройте <code>/health</code> — увидите JSON со статусом БД, числом заказов и активных задач.
  Полезно подключить к UptimeRobot для уведомлений если бот упал.</p>

  <h2>4. Обновление сессионных куков (раз в 1–3 месяца)</h2>
  <p>Куки Kwork и FL.ru со временем устаревают. Когда это случится, в логах появится
  <code>⛔ KWORK_SESSION_COOKIE истёк</code> или <code>FL_SESSION_COOKIE невалиден</code>.</p>
  <h3>Как обновить куку Kwork:</h3>
  <ol>
    <li>Зайдите на <code>kwork.ru</code> с компьютера в обычном браузере (Chrome/Edge)</li>
    <li>Войдите в свой аккаунт</li>
    <li>Нажмите <kbd>F12</kbd> → вкладка <b>Application</b> → раздел <b>Cookies</b> → <code>https://kwork.ru</code></li>
    <li>Найдите строку <code>track</code> (или <code>session</code>) — скопируйте её <b>Value</b></li>
    <li>В Replit: вкладка <b>Secrets</b> (🔒 в левой панели) → найдите <code>KWORK_SESSION_COOKIE</code> → вставьте новое значение → Save</li>
    <li>Перезапустите проект кнопкой Run</li>
  </ol>
  <h3>Куку FL.ru обновляют так же</h3>
  <p>Только секрет называется <code>FL_SESSION_COOKIE</code>, а зайти надо на <code>fl.ru</code>.
  Имя куки чаще всего <code>id</code> или <code>PHPSESSID</code>.</p>

  <h2>5. Когда приходят деньги</h2>
  <ol>
    <li>Бот находит заказ → отправляет отклик</li>
    <li>Клиент пишет в личку → бот отвечает, согласовывает детали</li>
    <li>Клиент создаёт «Безопасную сделку» (Kwork) или «Договор» (FL.ru) и кладёт деньги в эскроу</li>
    <li>Бот выполняет заказ, отдаёт ZIP с кодом и README</li>
    <li>Клиент проверяет → подтверждает приёмку → деньги падают на ваш баланс на бирже</li>
    <li>Вывод денег: вручную с биржи на карту/кошелёк (минимум обычно 500 ₽)</li>
  </ol>
  <div class="tip">💰 <b>Реалистичный прогноз:</b> первый месяц — отзывы накапливаются,
  выйти можно на 30–80 тыс. ₽. Через 3–6 месяцев при стабильной работе и хороших отзывах —
  150–300 тыс. ₽/мес. Это требует времени и качества.</div>

  <h2>6. Что делать если что-то сломалось</h2>
  <ul>
    <li><b>Не приходят отклики</b> — проверьте куку Kwork (см. п.4)</li>
    <li><b>FL.ru = 403</b> — Replit IP в чёрном списке у FL.ru, нужен резидентный прокси (~$10/мес)</li>
    <li><b>Бот завис</b> — нажмите Stop → Run в Replit, или перезапустите workflow</li>
    <li><b>Клиент жалуется на качество</b> — проверьте папку <code>deliverables/</code>, при необходимости доработайте вручную и повторно отправьте</li>
  </ul>
</section>

<section id="python" class="panel">
  <h2>Урок 1. С чего начать Python</h2>
  <p>Python — это язык программирования. Мы пишем команды текстом, компьютер их выполняет.</p>
  <pre><code>print("Привет, мир!")</code></pre>
  <p>Это самая простая программа. <code>print</code> — функция, которая выводит текст на экран.
  Запустите её — увидите «Привет, мир!».</p>

  <h2>Урок 2. Переменные и типы данных</h2>
  <p>Переменная — это «коробка» с именем, в которую можно положить значение:</p>
  <pre><code>name = "Аркадий"          # строка (текст)
age = 30                  # целое число
balance = 1500.50         # дробное число
is_active = True          # булево (True/False)

print(f"Привет, {name}! Тебе {age} лет.")</code></pre>
  <p>Знак <code>=</code> — присвоение. Префикс <code>f</code> у строки позволяет вставлять
  переменные через <code>{ }</code>.</p>

  <h2>Урок 3. Условия (if/else)</h2>
  <pre><code>balance = 5000

if balance &gt; 10000:
    print("Можно купить квадрокоптер")
elif balance &gt; 1000:
    print("Можно купить книгу")
else:
    print("Только хлеб")</code></pre>
  <p>Отступы (4 пробела) важны — Python ими определяет, что относится к блоку.</p>

  <h2>Урок 4. Списки и циклы</h2>
  <pre><code>orders = ["Бот", "Сайт", "Парсер", "API"]

for order in orders:
    print(f"Делаю заказ: {order}")

print(f"Всего заказов: {len(orders)}")</code></pre>
  <p><code>for ... in</code> — перебирает элементы по одному. <code>len()</code> — длина списка.</p>

  <h2>Урок 5. Функции</h2>
  <p>Функция — это блок кода с именем, который можно переиспользовать:</p>
  <pre><code>def calculate_commission(price, rate=0.1):
    "Считает комиссию биржи."
    return price * rate

fee = calculate_commission(10000)        # 1000.0
fee2 = calculate_commission(10000, 0.15) # 1500.0 (Kwork)</code></pre>
  <p><code>def</code> объявляет функцию. <code>return</code> возвращает результат.
  <code>rate=0.1</code> — значение по умолчанию.</p>

  <h2>Урок 6. Словари (как у нас в боте)</h2>
  <pre><code>job = {
    "title": "Telegram бот для магазина",
    "budget": 25000,
    "platform": "Kwork",
}

print(job["title"])              # доступ по ключу
job["status"] = "in_progress"    # добавить новое поле
print(len(job))                  # 4 ключа</code></pre>

  <h2>Урок 7. Работа с файлами</h2>
  <pre><code># Запись
with open("notes.txt", "w", encoding="utf-8") as f:
    f.write("Первая заметка\n")
    f.write("Вторая заметка\n")

# Чтение
with open("notes.txt", "r", encoding="utf-8") as f:
    text = f.read()
    print(text)</code></pre>
  <p>Конструкция <code>with ... as</code> автоматически закроет файл.</p>

  <h2>Урок 8. Обработка ошибок</h2>
  <pre><code>try:
    result = 100 / 0
except ZeroDivisionError as e:
    print(f"Ошибка: {e}")
    result = 0
finally:
    print("Это выполнится всегда")</code></pre>
  <div class="warn">⚠️ Никогда не пишите <code>except:</code> без указания типа —
  это поглощает <kbd>Ctrl+C</kbd> и системные сигналы. Всегда <code>except Exception:</code> минимум.
  Наш бот это проверяет автоматически.</div>

  <h2>Урок 9. Классы (объекты)</h2>
  <pre><code>class Order:
    def __init__(self, title, budget):
        self.title = title
        self.budget = budget
        self.status = "new"

    def commission(self, rate=0.15):
        return self.budget * rate

order = Order("Парсер", 8000)
print(order.commission())   # 1200.0
print(order.title)          # Парсер</code></pre>

  <h2>Урок 10. Внешние библиотеки</h2>
  <p>Python мощен благодаря тысячам готовых библиотек. Установка:</p>
  <pre><code>pip install requests</code></pre>
  <p>Использование (запрос к сайту):</p>
  <pre><code>import requests

r = requests.get("https://api.github.com")
print(r.status_code)        # 200
print(r.json()["current_user_url"])</code></pre>

  <h2>Что дальше</h2>
  <ul>
    <li><b>asyncio</b> — асинхронность, наш бот её активно использует</li>
    <li><b>FastAPI / Flask</b> — веб-серверы (наш дашборд на Flask)</li>
    <li><b>SQLAlchemy / sqlite3</b> — работа с базами данных</li>
    <li><b>aiogram</b> — Telegram-боты на Python</li>
    <li><b>BeautifulSoup / lxml</b> — парсинг HTML (Kwork-парсер у нас на этом)</li>
  </ul>
  <div class="tip">📖 Бесплатные ресурсы на русском: <b>stepik.org</b> (курс «Поколение Python»),
  <b>pythontutor.ru</b>, документация на <b>docs.python.org/ru/3</b>.</div>
</section>

</main>
<script>
document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.target).classList.add('active');
    window.scrollTo(0, 0);
  });
});
</script>
</body></html>
"""


@app.route("/knowledge")
def knowledge_base():
    return KNOWLEDGE_HTML


@app.route("/api/my-proposals")
def api_my_proposals():
    """Все мои отклики, отсортированные по статусу для главного экрана."""
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT pr.id as proposal_id, pr.status, pr.sent_at,
                      pr.generated_text as proposal_text,
                      j.platform, j.title, j.url, j.budget, j.currency
               FROM proposals pr
               JOIN jobs j ON j.id = pr.job_id
               ORDER BY
                 CASE pr.status
                   WHEN 'replied'  THEN 1
                   WHEN 'viewed'   THEN 2
                   WHEN 'sent'     THEN 3
                   WHEN 'pending'  THEN 3
                   WHEN 'won'      THEN 4
                   WHEN 'rejected' THEN 5
                   ELSE 6
                 END,
                 pr.sent_at DESC
               LIMIT 100"""
        ).fetchall()

        proposals = []
        for r in rows:
            sent = _to_msk(r["sent_at"] or "")
            proposals.append(dict(
                proposal_id=r["proposal_id"],
                status=r["status"] or "sent",
                sent_at=sent,
                proposal_text=r["proposal_text"] or "",
                platform=r["platform"] or "—",
                title=r["title"] or "—",
                url=r["url"],
                budget=round(r["budget"]) if r["budget"] else None,
                currency=r["currency"] or "",
            ))

        counts = {
            "sent":     sum(1 for p in proposals if p["status"] in ("sent","pending","viewed")),
            "replied":  sum(1 for p in proposals if p["status"] == "replied"),
            "won":      sum(1 for p in proposals if p["status"] == "won"),
            "rejected": sum(1 for p in proposals if p["status"] == "rejected"),
        }

        return jsonify({"proposals": proposals, "counts": counts})
    finally:
        conn.close()


@app.route("/api/data")
def api_data():
    conn = get_db()
    try:
        stats = _fetch_stats(conn)
        platforms = _fetch_platforms(conn)
        jobs = _fetch_jobs(conn, limit=15)
        pipeline = _fetch_pipeline(conn)
        paused = get_bot_state()
        return jsonify(dict(stats=stats, platforms=platforms, jobs=jobs, pipeline=pipeline, paused=paused))
    finally:
        conn.close()


@app.route("/api/jobs")
def api_jobs():
    platform = request.args.get("platform", "")
    status = request.args.get("status", "")
    q = request.args.get("q", "")
    conn = get_db()
    try:
        jobs = _fetch_jobs(conn, limit=200, platform=platform, status_filter=status, search=q)
        return jsonify(dict(jobs=jobs))
    finally:
        conn.close()


@app.route("/api/mark-outcome", methods=["POST"])
def api_mark_outcome():
    data = request.get_json() or {}
    proposal_id = data.get("proposal_id")
    outcome = data.get("outcome", "")
    if not proposal_id or outcome not in ("rejected", "viewed", "replied"):
        return jsonify({"ok": False, "error": "Invalid params — статус 'won' выставляется только ботом автоматически"}), 400
    conn = get_db()
    try:
        conn.execute(
            "UPDATE proposals SET status=? WHERE id=?", (outcome, proposal_id)
        )
        conn.execute(
            "INSERT INTO proposal_outcomes (proposal_id, outcome, recorded_at, notes) VALUES (?,?,?,?)",
            (proposal_id, outcome, datetime.utcnow().isoformat(), "Отмечено вручную через дашборд")
        )
        conn.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "GET":
        return jsonify(load_config())
    data = request.get_json() or {}
    cfg = load_config()
    cfg.update({k: v for k, v in data.items() if k in DEFAULT_CONFIG or k in cfg})
    save_config(cfg)
    return jsonify({"ok": True})


@app.route("/api/pause", methods=["POST"])
def api_pause():
    try:
        import bot_state as _bs
        _bs.set_paused(True)
    except Exception:
        pass
    return jsonify({"ok": True, "paused": True})


@app.route("/api/resume", methods=["POST"])
def api_resume():
    try:
        import bot_state as _bs
        _bs.set_paused(False)
    except Exception:
        pass
    return jsonify({"ok": True, "paused": False})


@app.route("/api/search-now", methods=["POST"])
def api_search_now():
    try:
        import bot_state as _bs
        _bs.trigger_search()
        return jsonify({"ok": True, "message": "⚡ Поиск будет запущен в следующем цикле"})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)})


@app.route("/api/enqueue-order", methods=["POST", "GET"])
def api_enqueue_order():
    """v15.9.3: Ручной запуск работы по принятому заказу.
    Принимает либо ?url=https://kwork.ru/orders/12345  либо ?id=12345
    Создаёт job + proposal(won) + кладёт в job_execution_queue.
    """
    import re as _re
    raw = (request.args.get("url") or request.args.get("id")
           or request.form.get("url") or request.form.get("id") or "").strip()
    if not raw:
        return jsonify({"ok": False, "error": "send ?url=... or ?id=..."}), 400
    m = _re.search(r'/orders?/(\d+)', raw)
    order_id = m.group(1) if m else _re.sub(r'\D', '', raw)
    if not order_id:
        return jsonify({"ok": False, "error": "не удалось извлечь id"}), 400

    title = (request.args.get("title") or request.form.get("title") or f"Kwork order {order_id}").strip()
    try:
        budget = float(request.args.get("budget") or request.form.get("budget") or 0)
    except Exception:
        budget = 0.0

    ext_id = f"Kwork_{order_id}"
    conn = get_db()
    try:
        # job
        row = conn.execute("SELECT id FROM jobs WHERE external_id=?", (ext_id,)).fetchone()
        if row:
            job_id = row["id"]
        else:
            cur = conn.execute(
                "INSERT INTO jobs (platform, external_id, title, description, budget, currency, url, category) "
                "VALUES (?,?,?,?,?,?,?,?)",
                ("Kwork", ext_id, title, title, budget, "RUB",
                 f"https://kwork.ru/orders/{order_id}", "automation")
            )
            job_id = cur.lastrowid
        # proposal
        prow = conn.execute("SELECT id FROM proposals WHERE job_id=? LIMIT 1", (job_id,)).fetchone()
        if prow:
            proposal_id = prow["id"]
        else:
            cur = conn.execute(
                "INSERT INTO proposals (job_id, generated_text, status, prompt_version) VALUES (?,?,?,?)",
                (job_id, "[Manually enqueued]", "won", "manual")
            )
            proposal_id = cur.lastrowid
        conn.execute("UPDATE proposals SET status='won' WHERE id=?", (proposal_id,))
        conn.execute(
            "INSERT INTO proposal_outcomes (proposal_id, outcome, notes) VALUES (?,?,?)",
            (proposal_id, "won", f"Manual enqueue via dashboard for order {order_id}")
        )
        conn.execute(
            "INSERT OR IGNORE INTO job_execution_queue (external_id, notes) VALUES (?,?)",
            (ext_id, f"Manual enqueue from dashboard for Kwork order {order_id}")
        )
        conn.commit()
        return jsonify({
            "ok": True, "message": f"✅ Заказ {order_id} в очереди — будет запущен в течение 5 минут",
            "ext_id": ext_id, "job_id": job_id, "proposal_id": proposal_id,
            "url": f"https://kwork.ru/orders/{order_id}"
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        conn.close()


@app.route("/api/db-stats")
def api_db_stats():
    conn = get_db()
    try:
        tables = ["jobs", "proposals", "proposal_outcomes", "order_executions",
                  "knowledge_base", "learning_insights", "revenue_pipeline",
                  "market_intelligence", "portfolio_entries"]
        counts = {}
        for t in tables:
            try:
                counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except Exception:
                pass
        return jsonify({"tables": counts})
    finally:
        conn.close()


@app.route("/api/insights")
def api_insights():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT platform, insight_type, content, effectiveness FROM learning_insights "
            "ORDER BY created_at DESC LIMIT 10"
        ).fetchall()
        return jsonify({"insights": [dict(r) for r in rows]})
    finally:
        conn.close()


@app.route("/api/top-proposals")
def api_top_proposals():
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT j.platform, j.title as job_title, pr.generated_text as text,
                      ps.self_score as score
               FROM proposals pr
               JOIN jobs j ON j.id = pr.job_id
               LEFT JOIN proposal_scores ps ON ps.proposal_id = pr.id
               ORDER BY ps.self_score DESC, pr.sent_at DESC LIMIT 10"""
        ).fetchall()
        return jsonify({"proposals": [dict(r) for r in rows]})
    finally:
        conn.close()


@app.route("/api/projects")
def api_projects():
    conn = get_db()
    try:
        running_rows = conn.execute(
            """SELECT oe.id, oe.status, oe.iterations, oe.started_at,
                      j.title, j.platform, j.url
               FROM order_executions oe
               LEFT JOIN jobs j ON j.id = oe.job_id
               WHERE oe.status NOT IN ('completed','failed')
               ORDER BY oe.started_at DESC"""
        ).fetchall()
        running = []
        for r in running_rows:
            running.append(dict(
                id=r["id"], status=r["status"],
                iterations=r["iterations"] or 0,
                title=r["title"] or "—",
                platform=r["platform"] or "—",
                url=r["url"],
                started=(r["started_at"] or "")[:16]
            ))

        # Also include queued jobs
        queued_rows = conn.execute(
            """SELECT q.id, q.external_id, q.queued_at, j.title, j.platform, j.url
               FROM job_execution_queue q
               LEFT JOIN jobs j ON j.external_id = q.external_id
               ORDER BY q.priority DESC, q.queued_at"""
        ).fetchall()
        for r in queued_rows:
            running.append(dict(
                id=r["id"], status="queued",
                iterations=0,
                title=r["title"] or r["external_id"] or "—",
                platform=r["platform"] or "—",
                url=r["url"],
                started=(r["queued_at"] or "")[:16]
            ))

        done_rows = conn.execute(
            """SELECT oe.id, oe.status, oe.review_score, oe.iterations,
                      oe.test_passed, oe.deliverable_path, oe.completed_at,
                      j.title, j.platform, j.url
               FROM order_executions oe
               LEFT JOIN jobs j ON j.id = oe.job_id
               WHERE oe.status IN ('completed','failed')
               ORDER BY oe.completed_at DESC LIMIT 20"""
        ).fetchall()
        done = []
        for r in done_rows:
            done.append(dict(
                id=r["id"], status=r["status"],
                score=r["review_score"],
                iterations=r["iterations"] or 0,
                test_passed=bool(r["test_passed"]),
                deliverable=bool(r["deliverable_path"]),
                title=r["title"] or "—",
                platform=r["platform"] or "—",
                url=r["url"],
                completed=(r["completed_at"] or "")[:16]
            ))
        return jsonify({"running": running, "done": done})
    finally:
        conn.close()


@app.route("/api/inbox")
def api_inbox():
    conn = get_db()
    try:
        items = []
        # Won proposals
        rows = conn.execute(
            """SELECT po.outcome, po.recorded_at, j.platform, j.title, j.url
               FROM proposal_outcomes po
               JOIN proposals pr ON pr.id = po.proposal_id
               JOIN jobs j ON j.id = pr.job_id
               WHERE po.outcome IN ('won','accepted','hired')
               ORDER BY po.recorded_at DESC LIMIT 10"""
        ).fetchall()
        for r in rows:
            items.append(dict(
                type="won", platform=r["platform"],
                description=f"Заказ принят: {r['title'][:80]}",
                date=(r["recorded_at"] or "")[:16], url=r["url"]
            ))
        # Replied proposals (client answered)
        rows2 = conn.execute(
            """SELECT pr.status, pr.sent_at, j.platform, j.title, j.url
               FROM proposals pr
               JOIN jobs j ON j.id = pr.job_id
               WHERE pr.status IN ('replied','viewed')
               ORDER BY pr.sent_at DESC LIMIT 10"""
        ).fetchall()
        for r in rows2:
            items.append(dict(
                type=r["status"], platform=r["platform"],
                description=f"Клиент {'ответил' if r['status']=='replied' else 'просмотрел'}: {r['title'][:70]}",
                date=_to_msk(r["sent_at"] or ""), url=r["url"]
            ))
        # Active executions
        rows3 = conn.execute(
            """SELECT oe.status, oe.started_at, j.platform, j.title, j.url
               FROM order_executions oe
               JOIN jobs j ON j.id = oe.job_id
               WHERE oe.status NOT IN ('completed','failed')
               ORDER BY oe.started_at DESC LIMIT 5"""
        ).fetchall()
        for r in rows3:
            items.append(dict(
                type="executing", platform=r["platform"],
                description=f"Выполняется: {r['title'][:70]}",
                date=(r["started_at"] or "")[:16], url=r["url"]
            ))
        items.sort(key=lambda x: x["date"], reverse=True)
        return jsonify({"items": items})
    finally:
        conn.close()


@app.route("/api/active-orders")
def api_active_orders():
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT pr.id as proposal_id, pr.generated_text, po.recorded_at as won_at,
                      j.title, j.url, j.platform, j.budget, j.currency,
                      oe.status as execution_status
               FROM proposal_outcomes po
               JOIN proposals pr ON pr.id = po.proposal_id
               JOIN jobs j ON j.id = pr.job_id
               LEFT JOIN order_executions oe ON oe.job_id = j.id
               WHERE po.outcome IN ('won','accepted','hired')
                 AND pr.status NOT IN ('failed', 'rejected')
               ORDER BY po.recorded_at DESC LIMIT 10"""
        ).fetchall()
        orders = []
        for r in rows:
            budget = r["budget"]
            try:
                budget = int(float(budget)) if budget else None
            except Exception:
                budget = None
            orders.append(dict(
                proposal_id=r["proposal_id"],
                title=r["title"],
                url=r["url"],
                platform=r["platform"],
                budget=budget,
                currency=r["currency"] or "",
                won_at=(r["won_at"] or "")[:19],
                execution_status=r["execution_status"],
                proposal_text=r["generated_text"] or "",
            ))
        return jsonify({"orders": orders})
    finally:
        conn.close()


@app.route("/api/proposal-text/<int:proposal_id>")
def api_proposal_text(proposal_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT generated_text FROM proposals WHERE id=?", (proposal_id,)
        ).fetchone()
        return jsonify({"text": row["generated_text"] if row else ""})
    finally:
        conn.close()


@app.route("/api/finance")
def api_finance():
    """Finance stats + LLM router status + config."""
    import os
    conn = get_db()
    try:
        # Won orders count
        won = conn.execute(
            "SELECT COUNT(*) FROM proposal_outcomes WHERE outcome IN ('won','accepted','hired')"
        ).fetchone()[0]

        # Total budget of won jobs
        total_budget = conn.execute(
            """SELECT COALESCE(SUM(j.budget),0) FROM proposal_outcomes po
               JOIN proposals pr ON pr.id = po.proposal_id
               JOIN jobs j ON j.id = pr.job_id
               WHERE po.outcome IN ('won','accepted','hired')"""
        ).fetchone()[0]

        # Proposals sent
        sent = conn.execute(
            "SELECT COUNT(*) FROM proposals WHERE status IN ('sent','won')"
        ).fetchone()[0]

        win_rate = f"{(won/sent*100):.1f}%" if sent > 0 else "0%"

        deepseek_key   = bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())
        openrouter_key = bool(os.environ.get("OPENROUTER_API_KEY", "").strip())

        # Read saved config from JSON file (falls back to env vars)
        cfg_data = _load_finance_cfg()

        # Determine display label: both can be active simultaneously (smart routing)
        if deepseek_key and openrouter_key:
            llm_label = "DeepSeek + Claude 3.5"
        elif deepseek_key:
            llm_label = "DeepSeek"
        elif openrouter_key:
            llm_label = "OpenRouter (Claude 3.5)"
        else:
            llm_label = "Нет ключа"

        return jsonify({
            "stats": {
                "total_won":            won,
                "total_budget_rub":     int(total_budget or 0),
                "proposals_sent":       sent,
                "win_rate":             win_rate,
                "skipped_unprofitable": cfg_data.get("skipped_unprofitable", 0),
                "llm_provider":         llm_label,
                "openrouter_ready":     openrouter_key,
            },
            "router": {
                "deepseek_ready":   deepseek_key,
                "deepseek_model":   "deepseek-chat",
                "openrouter_ready": openrouter_key,
                "openrouter_model": "claude-3.5-sonnet",
            },
            "config": {
                "min_hourly_rate": cfg_data.get("min_hourly_rate", 400),
                "min_budget":      cfg_data.get("min_budget", 50),
            }
        })
    finally:
        conn.close()


# ── Finance config helpers ────────────────────────────────────────────
_FINANCE_CFG_PATH = os.path.join(os.path.dirname(__file__), "finance_config.json")

def _load_finance_cfg() -> dict:
    try:
        with open(_FINANCE_CFG_PATH) as f:
            return json.load(f)
    except Exception:
        return {
            "min_hourly_rate": float(os.environ.get("MIN_HOURLY_RATE", "400")),
            "min_budget":      float(os.environ.get("MIN_BUDGET", "50")),
        }

def _save_finance_cfg(cfg: dict):
    with open(_FINANCE_CFG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


@app.route("/api/finance/config", methods=["POST"])
def api_finance_config():
    """Save financial config: min_hourly_rate, min_budget."""
    data = request.get_json(force=True) or {}
    try:
        cfg = _load_finance_cfg()
        if "min_hourly_rate" in data:
            v = float(data["min_hourly_rate"])
            cfg["min_hourly_rate"] = v
            os.environ["MIN_HOURLY_RATE"] = str(v)
        if "min_budget" in data:
            v = float(data["min_budget"])
            cfg["min_budget"] = v
            os.environ["MIN_BUDGET"] = str(v)
        _save_finance_cfg(cfg)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/messages")
def api_messages():
    """Fetch real inbox messages from Kwork (web scrape) and FL.ru."""
    import os
    import re as _re

    kwork_msgs = []
    kwork_status = "Сессионная кука не задана"
    flru_msgs = []
    flru_status = "Учётные данные FL.ru не заданы"

    # ── Kwork ──────────────────────────────────────────────
    cookie = os.environ.get("KWORK_SESSION_COOKIE", "").strip()
    if cookie:
        try:
            import requests as _req
            sess = _req.Session()
            sess.headers.update({
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "ru-RU,ru;q=0.9",
            })
            # Inject session cookie
            cookie_name = "PHPSESSID"
            if "=" in cookie and not cookie.startswith("PHPSESSID"):
                # possibly "name=value" format
                parts = cookie.split("=", 1)
                cookie_name, cookie_val = parts[0].strip(), parts[1].strip()
            else:
                cookie_val = cookie
            sess.cookies.set(cookie_name, cookie_val, domain="kwork.ru")

            resp = sess.get("https://kwork.ru/inbox", timeout=15,
                            allow_redirects=True)
            html = resp.text

            if "signin" in resp.url or "login" in resp.url:
                kwork_status = "Сессия устарела — нужно обновить KWORK_SESSION_COOKIE"
            else:
                # Parse message threads from page HTML
                # Each thread: <a class="inbox-thread-item" href="/inbox/12345">
                threads = _re.findall(
                    r'<a[^>]+class="[^"]*inbox-thread-item[^"]*"[^>]+href="(/inbox/(\d+))"[^>]*>(.*?)</a>',
                    html, _re.S
                )
                if not threads:
                    # Try alternate structure
                    threads = _re.findall(
                        r'href="(/inbox/(\d+))"[^>]*>',
                        html, _re.S
                    )
                    threads = [(p, i, '') for p, i in threads]

                for thread_path, thread_id, thread_html in threads[:20]:
                    # Fetch individual thread for real messages
                    t_resp = sess.get(f"https://kwork.ru{thread_path}", timeout=10)
                    t_html = t_resp.text

                    # Extract sender name
                    sender_m = _re.search(r'<span[^>]+class="[^"]*inbox-username[^"]*"[^>]*>([^<]+)</span>', t_html)
                    sender = sender_m.group(1).strip() if sender_m else f"Клиент #{thread_id}"

                    # Extract order title if any
                    order_m = _re.search(r'<div[^>]+class="[^"]*inbox-order-title[^"]*"[^>]*>([^<]+)<', t_html)
                    order_title = order_m.group(1).strip() if order_m else None

                    # Extract last message text
                    msg_blocks = _re.findall(
                        r'<div[^>]+class="[^"]*message-text[^"]*"[^>]*>(.*?)</div>',
                        t_html, _re.S
                    )
                    if not msg_blocks:
                        msg_blocks = _re.findall(
                            r'<p[^>]+class="[^"]*msg-text[^"]*"[^>]*>(.*?)</p>',
                            t_html, _re.S
                        )
                    last_text = ""
                    if msg_blocks:
                        last_text = _re.sub(r'<[^>]+>', '', msg_blocks[-1]).strip()[:400]

                    # Date
                    date_m = _re.search(r'<time[^>]+datetime="([^"]+)"', t_html)
                    msg_date = date_m.group(1)[:16].replace("T", " ") if date_m else ""

                    # Unread indicator
                    unread = 'unread' in t_html.lower() and 'inbox-thread-item--unread' in html

                    kwork_msgs.append({
                        "id": int(thread_id),
                        "sender": sender,
                        "order_title": order_title,
                        "text": last_text or "(сообщение не удалось извлечь — откройте на Kwork)",
                        "date": msg_date,
                        "unread": unread,
                        "url": f"https://kwork.ru/inbox/{thread_id}"
                    })

                kwork_status = f"Загружено {len(kwork_msgs)} диалогов" if kwork_msgs else "Нет диалогов в ящике"

        except Exception as e:
            kwork_status = f"Ошибка при получении: {str(e)[:120]}"

    # ── FL.ru ──────────────────────────────────────────────
    fl_user = os.environ.get("FL_USERNAME", "").strip()
    fl_pass = os.environ.get("FL_PASSWORD", "").strip()
    if fl_user and fl_pass:
        try:
            import requests as _req
            fl_sess = _req.Session()
            fl_sess.headers.update({
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "ru-RU,ru;q=0.9",
            })
            # Login
            login_r = fl_sess.post("https://www.fl.ru/login/",
                data={"login": fl_user, "password": fl_pass, "remember": "1"},
                timeout=15, allow_redirects=True)
            if "logout" in login_r.text.lower() or fl_sess.cookies.get("fl_user_id"):
                # Fetch messages page
                msg_r = fl_sess.get("https://www.fl.ru/msg/", timeout=10)
                msg_html = msg_r.text
                # Parse threads
                import re as re2
                threads = re2.findall(
                    r'<a[^>]+href="(https://www\.fl\.ru/msg/\?[^"]+)"[^>]*>(.*?)</a>',
                    msg_html, re2.S
                )
                for t_url, t_html_inner in threads[:15]:
                    sender_m = re2.search(r'<span[^>]+class="[^"]*username[^"]*"[^>]*>([^<]+)</span>', t_html_inner)
                    text_m = re2.search(r'<span[^>]+class="[^"]*msg-preview[^"]*"[^>]*>([^<]+)</span>', t_html_inner)
                    sender = sender_m.group(1).strip() if sender_m else "Клиент FL.ru"
                    text = text_m.group(1).strip() if text_m else re2.sub(r'<[^>]+>', '', t_html_inner).strip()[:200]
                    flru_msgs.append({"sender": sender, "text": text, "url": t_url,
                                       "unread": "unread" in t_html_inner.lower(), "date": ""})
                flru_status = f"Загружено {len(flru_msgs)} диалогов" if flru_msgs else "Нет диалогов"
            else:
                flru_status = "Не удалось войти на FL.ru — проверьте FL_USERNAME/FL_PASSWORD"
        except Exception as e:
            flru_status = f"Ошибка FL.ru: {str(e)[:100]}"

    return jsonify({
        "kwork": kwork_msgs,
        "kwork_status": kwork_status,
        "flru": flru_msgs,
        "flru_status": flru_status,
    })


@app.route("/api/reply-message", methods=["POST"])
def api_reply_message():
    """Send a reply to a message on Kwork."""
    import os, re as _re
    data = request.get_json(force=True) or {}
    platform = data.get("platform", "kwork")
    msg_id = data.get("msg_id")
    text = data.get("text", "").strip()
    if not text or not msg_id:
        return jsonify({"ok": False, "error": "Не указан текст или ID"})

    if platform == "kwork":
        cookie = os.environ.get("KWORK_SESSION_COOKIE", "").strip()
        if not cookie:
            return jsonify({"ok": False, "error": "KWORK_SESSION_COOKIE не задан"})
        try:
            import requests as _req
            sess = _req.Session()
            sess.headers.update({
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            })
            cookie_name = "PHPSESSID"
            if "=" in cookie and not cookie.startswith("PHPSESSID"):
                parts = cookie.split("=", 1)
                cookie_name, cookie_val = parts[0].strip(), parts[1].strip()
            else:
                cookie_val = cookie
            sess.cookies.set(cookie_name, cookie_val, domain="kwork.ru")

            # Fetch inbox page to get CSRF token
            page = sess.get(f"https://kwork.ru/inbox/{msg_id}", timeout=10)
            csrf_m = _re.search(r'"csrf"\s*:\s*"([a-zA-Z0-9_\-]+)"', page.text)
            csrf = csrf_m.group(1) if csrf_m else ""

            resp = sess.post(f"https://kwork.ru/inbox/{msg_id}/send",
                data={"message": text, "csrf": csrf},
                headers={"X-Requested-With": "XMLHttpRequest",
                         "Referer": f"https://kwork.ru/inbox/{msg_id}"},
                timeout=10)
            if resp.status_code == 200:
                return jsonify({"ok": True})
            else:
                return jsonify({"ok": False, "error": f"HTTP {resp.status_code}"})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)[:120]})

    return jsonify({"ok": False, "error": "Платформа не поддерживается"})


@app.route("/api/log")
def api_log():
    lines = []
    try:
        log_files = sorted([
            f for f in os.listdir("/tmp/logs")
            if f.startswith("Start_application") and f.endswith(".log")
        ], reverse=True)
        if log_files:
            with open(f"/tmp/logs/{log_files[0]}", "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
            lines = [l.rstrip() for l in all_lines[-80:]]
    except Exception as e:
        lines = [f"Лог недоступен: {e}"]
    return jsonify({"lines": lines})


@app.route("/api/profile-setup")
def api_profile_setup():
    """Returns ready-to-copy profile content for Kwork and FL.ru."""
    kwork_bio = (
        "Python-разработчик с 5+ годами опыта. Специализация: Telegram-боты (aiogram 3), "
        "FastAPI/Django REST API, веб-парсинг (httpx, Playwright), автоматизация бизнес-процессов, "
        "интеграции с CRM, Google Sheets, платёжными системами (ЮKassa, Tinkoff). "
        "Пишу чистый, документированный код с тестами. Работаю быстро и по ТЗ. "
        "Всегда на связи, сдаю в срок. Портфолио — более 50 проектов на Python."
    )
    flru_bio = (
        "Профессиональный Python-разработчик. Создаю Telegram-ботов, REST API на FastAPI/Django, "
        "парсеры сайтов, системы автоматизации. Опыт: CRM-интеграции (amoCRM, Битрикс24), "
        "платёжные шлюзы (ЮKassa, Robokassa, Tinkoff), работа с PostgreSQL/Redis/Docker. "
        "Принимаю заказы от 2000 ₽. Чёткие сроки, исходники, документация."
    )
    kwork_gigs = [
        {
            "title": "Разработаю Telegram-бота на Python (aiogram 3) под ваш бизнес",
            "price": "от 3 000 ₽",
            "delivery": "5 дней",
            "description": (
                "Профессиональный Telegram-бот на aiogram 3.x: FSM сценарии, inline-кнопки, "
                "Reply-клавиатуры, работа с PostgreSQL/SQLite, webhook или polling, "
                "админ-панель, оплата через ЮKassa/Stripe, Docker-compose. "
                "Любая сложность: от простого чат-бота до полноценного магазина."
            ),
            "category": "Чат-боты и автоматизация мессенджеров (38)",
            "tags": "telegram, бот, aiogram, python, чат-бот",
        },
        {
            "title": "Создам REST API на FastAPI + PostgreSQL с документацией",
            "price": "от 5 000 ₽",
            "delivery": "7 дней",
            "description": (
                "Backend API на FastAPI: JWT авторизация, Pydantic v2 схемы, "
                "SQLAlchemy 2.0 (async), Alembic миграции, Redis кэш, "
                "автогенерация Swagger docs, Docker Compose, pytest тесты. "
                "Production-ready с логированием, rate limiting, CORS."
            ),
            "category": "Веб-программирование и CMS (11)",
            "tags": "fastapi, python, api, postgresql, rest",
        },
        {
            "title": "Напишу парсер сайта (scraper) на Python — любой сложности",
            "price": "от 2 500 ₽",
            "delivery": "3 дня",
            "description": (
                "Web-scraping на Python: httpx/aiohttp для простых сайтов, "
                "Playwright/Selenium для JS-рендеринга, обход Cloudflare/reCAPTCHA, "
                "сохранение в Excel/CSV/PostgreSQL, прокси-ротация, "
                "расписание (APScheduler/cron), уведомления в Telegram."
            ),
            "category": "Веб-программирование и CMS (11)",
            "tags": "парсинг, scraping, python, playwright, автоматизация",
        },
        {
            "title": "Автоматизирую бизнес-процессы на Python: Excel, Google Sheets, API",
            "price": "от 2 000 ₽",
            "delivery": "4 дня",
            "description": (
                "Автоматизация на Python: выгрузка/обработка Excel (openpyxl, pandas), "
                "синхронизация с Google Sheets (gspread), интеграция с CRM/1С/amoCRM, "
                "автоматические email/Telegram уведомления, планировщик задач, "
                "обработка PDF. Любые рутинные процессы — под ключ."
            ),
            "category": "Веб-программирование и CMS (11)",
            "tags": "автоматизация, python, excel, google-sheets, crm",
        },
        {
            "title": "Разработаю Django-сайт или веб-приложение с админкой",
            "price": "от 8 000 ₽",
            "delivery": "10 дней",
            "description": (
                "Веб-приложение на Django 5.x: модели/миграции, DRF API, "
                "кастомная Django Admin, шаблоны Bootstrap/Tailwind, "
                "аутентификация (JWT/сессии), Celery очереди, Redis, "
                "деплой на VPS/Railway/Render, SSL, nginx."
            ),
            "category": "Веб-программирование и CMS (11)",
            "tags": "django, python, web, drf, backend",
        },
        {
            "title": "Интегрирую платёжные системы: ЮKassa, QIWI, Тinkoff в ваш проект",
            "price": "от 3 500 ₽",
            "delivery": "4 дня",
            "description": (
                "Интеграция платёжного шлюза в Python-проект: ЮKassa SDK, "
                "Tinkoff Acquiring API, QIWI P2P, webhooks подтверждения оплаты, "
                "автоматические чеки (ФЗ-54), refund логика, тесты, документация."
            ),
            "category": "Веб-программирование и CMS (11)",
            "tags": "юkassa, оплата, python, webhook, интеграция",
        },
        {
            "title": "Настрою мониторинг и алерты для вашего сервера или сайта",
            "price": "от 1 500 ₽",
            "delivery": "2 дня",
            "description": (
                "Мониторинг сервиса на Python: проверка доступности URL (httpx), "
                "мониторинг CPU/RAM/диска (psutil), Telegram-алерты при падении, "
                "сбор метрик в SQLite, дашборд на Flask/FastAPI, "
                "cron/systemd запуск, логирование в файл и Telegram."
            ),
            "category": "Веб-программирование и CMS (11)",
            "tags": "мониторинг, python, telegram, devops, алерты",
        },
    ]
    portfolio_samples = [
        {
            "title": "Telegram-бот для интернет-магазина с оплатой ЮKassa",
            "description": (
                "Production-ready Telegram-бот на aiogram 3.x: каталог товаров, "
                "корзина, оформление заказа, оплата через ЮKassa, "
                "уведомления администратору, PostgreSQL. "
                "Стек: Python 3.12, aiogram 3, SQLAlchemy, Docker."
            ),
        },
        {
            "title": "FastAPI REST API с JWT авторизацией и документацией",
            "description": (
                "Полноценный REST API: регистрация/логин (JWT), роли пользователей, "
                "CRUD операции, асинхронный SQLAlchemy + PostgreSQL, "
                "Swagger UI, pytest покрытие 85%+. Docker Compose."
            ),
        },
        {
            "title": "Парсер маркетплейса с сохранением в Excel и Telegram-уведомлениями",
            "description": (
                "Автоматический сборщик данных с крупного маркетплейса: "
                "обход пагинации, извлечение цен/описаний/остатков, "
                "ежедневный Excel-отчёт, Telegram-уведомление при изменении цен. "
                "Playwright + httpx, APScheduler."
            ),
        },
    ]
    kwork_instructions = [
        "1. Войдите на kwork.ru → Личный кабинет → Настройки профиля",
        "2. Вставьте текст «О себе» из блока «Kwork — О себе» ниже",
        "3. Перейдите в раздел «Мои кворки» → «Создать кворк»",
        "4. Для каждого кворка из списка ниже: скопируйте название, описание, укажите цену и категорию",
        "5. Загрузите примеры работ в раздел «Портфолио»",
    ]
    flru_instructions = [
        "1. Войдите на fl.ru → Профиль → Редактировать",
        "2. Вставьте текст «О себе» из блока «FL.ru — О себе»",
        "3. Укажите навыки: Python, Django, FastAPI, Telegram Bot, aiogram, Парсинг, Автоматизация",
        "4. Установите минимальную ставку: 500 ₽/час или 2000 ₽ за проект",
        "5. Добавьте примеры работ в портфолио",
    ]
    return jsonify({
        "kwork_bio": kwork_bio,
        "flru_bio": flru_bio,
        "kwork_gigs": kwork_gigs,
        "portfolio_samples": portfolio_samples,
        "kwork_instructions": kwork_instructions,
        "flru_instructions": flru_instructions,
    })


@app.route("/health")
def health():
    """v15.5: Extended health check for uptime monitoring (UptimeRobot, etc.)."""
    import time, sqlite3
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs.db")
    out = {"status": "ok", "bot": "FreelanceBot v15.5", "timestamp": int(time.time())}
    try:
        conn = sqlite3.connect(db_path, timeout=2.0)
        c = conn.execute("SELECT COUNT(*) FROM jobs")
        out["jobs_total"] = c.fetchone()[0]
        c = conn.execute("SELECT COUNT(*) FROM proposals WHERE status='sent'")
        out["proposals_sent"] = c.fetchone()[0]
        try:
            c = conn.execute("SELECT COUNT(*) FROM client_followups WHERE sent_at IS NULL")
            out["followups_pending"] = c.fetchone()[0]
        except Exception:
            out["followups_pending"] = 0
        conn.close()
    except Exception as e:
        out["status"] = "degraded"
        out["error"] = str(e)[:100]
        return jsonify(out), 503
    return jsonify(out)


@app.route("/download/<safe_id>")
def download_deliverable(safe_id):
    """Serve the ZIP archive of a completed order's deliverable."""
    from flask import send_file, abort
    # Basic safety: only alphanumerics, dash, underscore
    import re as _re
    if not _re.fullmatch(r"[A-Za-z0-9_\-]+", safe_id or ""):
        return abort(400, "Invalid id")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    zip_path = os.path.join(base_dir, "deliverables", f"{safe_id}.zip")
    if not os.path.isfile(zip_path):
        return abort(404, "Deliverable not found")
    return send_file(zip_path, as_attachment=True,
                     download_name=f"{safe_id}.zip",
                     mimetype="application/zip")


@app.route("/api/deliverables")
def api_deliverables():
    """List all packaged deliverables (ZIPs) ready for download."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    deliv_dir = os.path.join(base_dir, "deliverables")
    items = []
    if os.path.isdir(deliv_dir):
        for fn in sorted(os.listdir(deliv_dir), reverse=True):
            if not fn.endswith(".zip"):
                continue
            full = os.path.join(deliv_dir, fn)
            try:
                size_kb = os.path.getsize(full) // 1024
                mtime = datetime.utcfromtimestamp(os.path.getmtime(full)).strftime("%Y-%m-%d %H:%M:%S")
                items.append({
                    "id": fn[:-4],
                    "size_kb": size_kb,
                    "created_at": _to_msk(mtime),
                    "url": f"/download/{fn[:-4]}",
                })
            except Exception:
                continue
    return jsonify({"deliverables": items, "count": len(items)})


@app.route("/api/cookie-status")
def api_cookie_status():
    """Returns Kwork session cookie health status."""
    try:
        import bot_state as _bs
        kwork = _bs.get_kwork_cookie_status()
        flru = _bs.get_flru_cookie_status()
    except Exception:
        kwork = {"valid": None, "checked_at": "", "error": "", "set_at": ""}
        flru = {"valid": None, "checked_at": "", "error": "", "set_at": ""}

    has_kwork = bool(os.environ.get("KWORK_SESSION_COOKIE", "").strip())
    has_flru = bool(os.environ.get("FL_SESSION_COOKIE", "").strip())

    return jsonify({
        "kwork": {
            **kwork,
            "configured": has_kwork,
        },
        "flru": {
            **flru,
            "configured": has_flru,
        },
    })


# ── DB helpers ────────────────────────────────────────────────────────────────

def _fetch_stats(conn):
    total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    relevant = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_relevant=1").fetchone()[0]
    proposals = conn.execute("SELECT COUNT(*) FROM proposals").fetchone()[0]
    wins = conn.execute(
        "SELECT COUNT(*) FROM proposal_outcomes WHERE outcome IN ('won','accepted','hired')"
    ).fetchone()[0]
    win_rate = round(wins / proposals * 100, 1) if proposals > 0 else 0
    pipeline_total = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM revenue_pipeline WHERE stage NOT IN ('lost','rejected')"
    ).fetchone()[0]
    executions = conn.execute(
        "SELECT COUNT(*) FROM order_executions WHERE status NOT IN ('completed','failed')"
    ).fetchone()[0]
    knowledge = conn.execute("SELECT COUNT(*) FROM knowledge_base").fetchone()[0]
    return dict(
        total_jobs=total_jobs, relevant_jobs=relevant,
        proposals_sent=proposals, wins=wins, win_rate=win_rate,
        pipeline_total=int(pipeline_total or 0), executions=executions, knowledge=knowledge
    )


def _fetch_platforms(conn):
    raw = conn.execute(
        """SELECT platform, status, error_message, checked_at FROM platform_status
           WHERE id IN (SELECT MAX(id) FROM platform_status GROUP BY platform)
           ORDER BY platform"""
    ).fetchall()
    result = []
    for r in raw:
        p = r["platform"]
        jobs_cnt = conn.execute("SELECT COUNT(*) FROM jobs WHERE platform=?", (p,)).fetchone()[0]
        prop_cnt = conn.execute(
            "SELECT COUNT(*) FROM proposals pr JOIN jobs j ON j.id=pr.job_id WHERE j.platform=?", (p,)
        ).fetchone()[0]
        wins_cnt = conn.execute(
            "SELECT COUNT(*) FROM proposal_outcomes po JOIN proposals pr ON pr.id=po.proposal_id "
            "JOIN jobs j ON j.id=pr.job_id WHERE j.platform=? AND po.outcome IN ('won','accepted','hired')", (p,)
        ).fetchone()[0]
        wr = round(wins_cnt / prop_cnt * 100, 1) if prop_cnt > 0 else 0
        checked = _to_msk(r["checked_at"] or "")
        result.append(dict(platform=p, status=r["status"] or "ok", jobs=jobs_cnt,
                           proposals=prop_cnt, wins=wins_cnt, wr=wr, checked=checked or "—"))
    return result


def _fetch_jobs(conn, limit=30, platform="", status_filter="", search=""):
    where = []
    params = []
    if platform:
        where.append("j.platform=?")
        params.append(platform)
    if search:
        where.append("(j.title LIKE ? OR j.description LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if status_filter == "sent":
        where.append("pr.status='sent'")
    elif status_filter == "won":
        where.append("pr.status='won'")
    elif status_filter == "rejected":
        where.append("pr.status='rejected'")
    elif status_filter == "pending":
        where.append("pr.id IS NULL AND j.is_relevant=1")

    wc = ("WHERE " + " AND ".join(where)) if where else ""
    rows = conn.execute(
        f"""SELECT j.id, j.platform, j.title, j.budget, j.currency, j.url,
                   j.is_relevant, j.first_seen_at,
                   pr.id as proposal_id, pr.status as proposal_status,
                   pr.generated_text as proposal_text,
                   js.score
            FROM jobs j
            LEFT JOIN proposals pr ON pr.job_id = j.id
            LEFT JOIN job_scores js ON js.job_id = j.id
            {wc}
            ORDER BY j.first_seen_at DESC LIMIT ?""",
        params + [limit]
    ).fetchall()
    result = []
    for r in rows:
        seen = (r["first_seen_at"] or "")[:16]
        result.append(dict(
            id=r["id"], platform=r["platform"], title=r["title"] or "(без названия)",
            budget=round(r["budget"], 0) if r["budget"] else None,
            currency=r["currency"] or "USD", url=r["url"],
            is_relevant=r["is_relevant"],
            proposal_id=r["proposal_id"],
            proposal_status=r["proposal_status"],
            proposal_text=r["proposal_text"] or "",
            score=round(r["score"], 1) if r["score"] else None,
            first_seen=seen or "—"
        ))
    return result


def _fetch_pipeline(conn):
    rows = conn.execute(
        "SELECT job_title, platform, stage, amount, probability FROM revenue_pipeline "
        "WHERE stage NOT IN ('lost','rejected') ORDER BY amount DESC LIMIT 15"
    ).fetchall()
    result = []
    for r in rows:
        prob = r["probability"] or 0
        amount = r["amount"] or 0
        result.append(dict(
            job_title=r["job_title"] or "—", platform=r["platform"],
            stage=r["stage"], amount=int(amount), probability=int(prob),
            expected=int(amount * prob / 100)
        ))
    return result


# ── Server ────────────────────────────────────────────────────────────────────

def run_dashboard():
    import logging as _log
    _log.getLogger("werkzeug").setLevel(_log.WARNING)
    app.run(host="0.0.0.0", port=DASHBOARD_PORT, debug=False, use_reloader=False)


def start_dashboard_thread():
    t = threading.Thread(target=run_dashboard, daemon=True, name="DashboardThread")
    t.start()
    return t


if __name__ == "__main__":
    print(f"FreelanceBot Dashboard on http://localhost:{DASHBOARD_PORT}")
    run_dashboard()
