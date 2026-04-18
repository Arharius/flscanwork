#!/bin/bash
# FreelanceBot v14.0 — Запуск на Mac Mini
# Использование: bash start_mac.sh

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "=== FreelanceBot v14.0 ==="

# Проверяем Python
if ! command -v python3 &>/dev/null; then
  echo "❌ Python3 не найден. Установите: brew install python@3.11"
  exit 1
fi
echo "✓ Python: $(python3 --version)"

# Устанавливаем зависимости
echo "→ Устанавливаем зависимости..."
pip3 install -r requirements.txt -q

# Проверяем .env
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    echo "⚠️  Создан .env из .env.example — заполните своими ключами!"
    echo "   nano .env"
    exit 1
  else
    echo "❌ Файл .env не найден. Создайте его с вашими ключами."
    exit 1
  fi
fi
echo "✓ .env найден"

# Запускаем бота
echo ""
echo "🚀 Запускаем FreelanceBot..."
echo "   Веб-дашборд: http://localhost:8080"
echo "   Остановить: Ctrl+C"
echo ""

python3 main.py
