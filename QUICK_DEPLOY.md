# ⚡ Быстрый деплой на Render

## 🚀 За 5 минут

### 1. Подготовка (1 мин)
```bash
# Загрузите код в GitHub репозиторий
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

### 2. Render Setup (3 мин)

**База данных:**
1. [Render Dashboard](https://dashboard.render.com) → **New +** → **PostgreSQL**
2. Name: `telegram-translator-db`, Plan: **Free** → **Create**
3. Скопируйте `DATABASE_URL` из "Connections"

**Web Service:**
1. **New +** → **Web Service** → Connect GitHub
2. Settings:
   - Name: `telegram-translator-bot`
   - Build: `pip install -r requirements.txt`
   - Start: `python start.py`
   - Plan: **Free**

### 3. Environment Variables (1 мин)
```bash
BOT_TOKEN=your_bot_token_from_botfather
DATABASE_URL=postgresql://user:pass@host:port/db
MODE=polling
LOG_LEVEL=INFO
TRANSLATOR_PROVIDER=MYMEMORY
```

### 4. Deploy & Test
- Нажмите **Create Web Service**
- Дождитесь деплоя (2-3 мин)
- Проверьте: `https://your-service.onrender.com/health`
- Тестируйте бота: `/start` в Telegram

## ✅ Готово!

Ваш бот работает 24/7 на `https://your-service.onrender.com`

---

📖 **Подробная инструкция:** [RENDER_DEPLOY.md](./RENDER_DEPLOY.md)

