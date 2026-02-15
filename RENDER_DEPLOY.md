# 🚀 Деплой на Render

Пошаговая инструкция по развертыванию Telegram Translation Bot на Render.

## 📋 Предварительные требования

1. **GitHub репозиторий** - загрузите код в GitHub
2. **Аккаунт Render** - зарегистрируйтесь на [render.com](https://render.com)
3. **Токен бота** - получите от [@BotFather](https://t.me/BotFather)

## 🗄️ Шаг 1: Создание базы данных PostgreSQL

1. Войдите в [Render Dashboard](https://dashboard.render.com)
2. Нажмите **"New +"** → **"PostgreSQL"**
3. Заполните:
   - **Name**: `telegram-translator-db`
   - **Database**: `telegram_translator`
   - **User**: `telegram_user`
   - **Region**: выберите ближайший
   - **Plan**: **Free**
4. Нажмите **"Create Database"**
5. **Сохраните** `DATABASE_URL` из раздела "Connections" (понадобится позже)

## 🤖 Шаг 2: Создание Web Service

1. Нажмите **"New +"** → **"Web Service"**
2. Подключите ваш GitHub репозиторий
3. Заполните настройки:
   - **Name**: `telegram-translator-bot`
   - **Region**: тот же, что и для базы данных
   - **Branch**: `main` (или ваша основная ветка)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python start.py`
   - **Plan**: **Free**

## 🔧 Шаг 3: Настройка переменных окружения

В разделе **"Environment"** добавьте переменные:

### Обязательные переменные:
```bash
BOT_TOKEN=ваш_токен_от_botfather
DATABASE_URL=postgresql://user:password@host:port/database
```

### Дополнительные переменные:
```bash
MODE=webhook
WEBHOOK_URL=https://your-service-name.onrender.com
LOG_LEVEL=INFO
TRANSLATOR_PROVIDER=ARGOS
DEFAULT_CHANNEL_LANGS=en
DEFAULT_USER_LANG=en
RATE_LIMIT_REQUESTS=5
RATE_LIMIT_WINDOW=15
MAX_TEXT_LENGTH=4096
MAX_COMMENT_LENGTH=3500
USE_SENTRY=false
PYTHON_VERSION=3.11.0
```

## 🔗 Шаг 4: Связывание базы данных

1. В настройках Web Service найдите раздел **"Environment"**
2. Добавьте переменную `DATABASE_URL` со значением из PostgreSQL сервиса
3. Или используйте автоматическое связывание в разделе **"Connect"**

## 🚀 Шаг 5: Деплой

1. Нажмите **"Create Web Service"**
2. Render автоматически:
   - Склонирует репозиторий
   - Установит зависимости
   - Запустит бота
3. Следите за логами в разделе **"Logs"**

## ✅ Шаг 6: Проверка работы

1. **Health Check**: откройте `https://your-service-name.onrender.com/health`
2. **Статус бота**: проверьте логи на наличие "Bot started: @your_bot_username"
3. **Тест бота**: отправьте `/start` вашему боту в Telegram

## 📊 Мониторинг

### Логи
- **Render Dashboard** → ваш сервис → **"Logs"**
- Фильтруйте по уровням: `INFO`, `ERROR`, `WARNING`

### Метрики
- **Render Dashboard** → ваш сервис → **"Metrics"**
- Отслеживайте CPU, память, HTTP запросы

### Health Check
- URL: `https://your-service-name.onrender.com/health`
- Проверяет состояние бота и базы данных

## 🔄 Обновление

1. **Push в GitHub** - Render автоматически пересоберет сервис
2. **Ручной деплой** - нажмите "Manual Deploy" в Dashboard
3. **Откат** - используйте "Rollback" к предыдущей версии

## ⚠️ Важные моменты

### Бесплатный план Render:
- ✅ 750 часов в месяц (достаточно для 24/7)
- ⚠️ Засыпает после 15 минут неактивности
- ⚠️ Холодный старт ~30 секунд
- ✅ Автоматическое пробуждение при запросах

### Рекомендации:
1. **Мониторинг**: настройте уведомления о падении сервиса
2. **Backup**: регулярно экспортируйте данные PostgreSQL
3. **Логи**: следите за ошибками в логах
4. **Обновления**: регулярно обновляйте зависимости

## 🆘 Решение проблем

### Бот не отвечает:
1. Проверьте логи на ошибки
2. Убедитесь, что `BOT_TOKEN` правильный
3. Проверьте health check endpoint

### Ошибки базы данных:
1. Проверьте `DATABASE_URL`
2. Убедитесь, что PostgreSQL сервис запущен
3. Проверьте подключение в логах

### Превышение лимитов:
1. Оптимизируйте частоту запросов
2. Рассмотрите платный план
3. Используйте кэширование

## 📞 Поддержка

- **Render Docs**: [render.com/docs](https://render.com/docs)
- **Render Community**: [community.render.com](https://community.render.com)
- **GitHub Issues**: создайте issue в репозитории проекта

---

🎉 **Готово!** Ваш бот теперь работает 24/7 на Render!

