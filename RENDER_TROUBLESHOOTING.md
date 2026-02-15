# 🔧 Диагностика проблем Render

Быстрая диагностика и решение проблем с ботом на Render.

## 🚨 Быстрая проверка

### 1. Проверьте статус сервиса

1. Откройте [Render Dashboard](https://dashboard.render.com)
2. Найдите сервис `telegram-translator-bot`
3. Проверьте статус:
   - ✅ **"Live"** - работает нормально
   - ⚠️ **"Sleeping"** - заснул, но это нормально (проснется при запросе)
   - ❌ **"Failed"** - есть проблема, нужно исправить
   - 🔄 **"Building"** - идет деплой, подождите

### 2. Проверьте логи

1. Render Dashboard → ваш сервис → вкладка **"Logs"**
2. Ищите ошибки (красные строки):
   - `ERROR` - критические ошибки
   - `WARNING` - предупреждения
3. Проверьте последние строки:
   - Должно быть: `"Bot started: @your_bot_username"`
   - Должно быть: `"Health check server started on http://0.0.0.0:XXXX"`

### 3. Проверьте health check

Откройте в браузере:
```
https://telegram-translator-bot-ew8k.onrender.com/health
```

**Ожидаемый результат:**
```json
{
  "status": "healthy",
  "database": "ok",
  "bot": "ok"
}
```

**Если не работает:**
- ❌ Страница не открывается → Render заснул или упал
- ❌ `{"status": "unhealthy"}` → проблема с ботом или базой данных
- ❌ `{"status": "error"}` → ошибка в коде

## 🔍 Частые проблемы и решения

### Проблема 1: "Service is sleeping"

**Симптомы:**
- Health check не отвечает
- Бот не отвечает в Telegram
- Первый запрос занимает 30-50 секунд

**Причина:**
Render заснул из-за неактивности (бесплатный план).

**Решение:**
1. **Быстрое пробуждение:**
   - Откройте health check URL в браузере
   - Или отправьте команду боту в Telegram
   - Подождите 30-50 секунд

2. **Постоянное решение:**
   - Настройте UptimeRobot (см. `RENDER_RESTART.md`)
   - Или перейдите на платный план

### Проблема 2: "Deploy failed" или "Build failed"

**Симптомы:**
- В логах ошибки при установке зависимостей
- Статус "Failed" в Dashboard

**Причины:**
- Ошибка в коде
- Проблемы с зависимостями
- Неправильные переменные окружения

**Решение:**
1. Проверьте логи на наличие ошибок
2. Проверьте переменные окружения:
   - `BOT_TOKEN` - должен быть установлен
   - `DATABASE_URL` - должен быть из PostgreSQL сервиса
3. Попробуйте пересобрать:
   - Render Dashboard → "Manual Deploy" → "Deploy latest commit"

### Проблема 3: "Bot not responding"

**Симптомы:**
- Health check работает
- Но бот не отвечает в Telegram

**Причины:**
- Неправильный `BOT_TOKEN`
- Проблемы с подключением к Telegram API
- Ошибки в обработчиках

**Решение:**
1. Проверьте `BOT_TOKEN`:
   - Render Dashboard → Environment → `BOT_TOKEN`
   - Убедитесь, что токен правильный (от @BotFather)
2. Проверьте логи на ошибки:
   - Ищите `ERROR` или `Exception`
3. Перезапустите сервис:
   - Render Dashboard → "Restart"

### Проблема 4: "Database connection error"

**Симптомы:**
- В логах: `"Database connection failed"`
- Health check возвращает: `"database": "error"`

**Причины:**
- Неправильный `DATABASE_URL`
- PostgreSQL сервис не запущен
- Проблемы с сетью

**Решение:**
1. Проверьте PostgreSQL сервис:
   - Render Dashboard → `telegram-translator-db`
   - Должен быть "Available"
2. Проверьте `DATABASE_URL`:
   - Render Dashboard → ваш сервис → Environment
   - Должен быть из PostgreSQL сервиса
3. Перезапустите оба сервиса:
   - PostgreSQL → "Restart"
   - Web Service → "Restart"

### Проблема 5: "Port scan timeout"

**Симптомы:**
- Деплой не завершается
- Ошибка: "Port scan timeout reached, no open ports detected"

**Причина:**
- Health check сервер не запускается
- Неправильный порт

**Решение:**
✅ **Эта проблема уже исправлена!** Health check сервер теперь запускается автоматически.

Если проблема повторяется:
1. Проверьте логи - должно быть: `"Health check server started"`
2. Проверьте переменную `PORT` (Render устанавливает автоматически)
3. Пересоберите сервис

## 🛠️ Пошаговая диагностика

### Шаг 1: Проверка статуса
```
Render Dashboard → ваш сервис → статус
```

### Шаг 2: Проверка логов
```
Render Dashboard → ваш сервис → Logs
```
Ищите:
- ✅ `"Bot started"`
- ✅ `"Health check server started"`
- ❌ `ERROR`
- ❌ `Exception`

### Шаг 3: Проверка переменных окружения
```
Render Dashboard → ваш сервис → Environment
```
Обязательные:
- `BOT_TOKEN` ✅
- `DATABASE_URL` ✅
- `MODE=polling` ✅
- `TRANSLATOR_PROVIDER=ARGOS` ✅

### Шаг 4: Проверка health check
```
https://telegram-translator-bot-ew8k.onrender.com/health
```

### Шаг 5: Тест бота
Отправьте `/start` боту в Telegram

## 🔄 Быстрое исправление

Если ничего не помогает:

1. **Перезапустите сервис:**
   - Render Dashboard → ваш сервис → "Restart"

2. **Пересоберите:**
   - Render Dashboard → "Manual Deploy" → "Deploy latest commit"

3. **Проверьте последний коммит:**
   - Убедитесь, что код в GitHub актуальный

4. **Откатитесь к предыдущей версии:**
   - Render Dashboard → Events → "Rollback"

## 📞 Получение помощи

Если проблема не решается:

1. **Скопируйте логи:**
   - Render Dashboard → Logs → скопируйте последние 50 строк

2. **Проверьте статус Render:**
   - [status.render.com](https://status.render.com)

3. **Создайте issue:**
   - GitHub репозиторий → Issues → New Issue

## ✅ Чек-лист диагностики

- [ ] Проверил статус сервиса в Render Dashboard
- [ ] Проверил логи на наличие ошибок
- [ ] Проверил health check endpoint
- [ ] Проверил переменные окружения
- [ ] Проверил PostgreSQL сервис
- [ ] Попробовал перезапустить сервис
- [ ] Попробовал пересобрать сервис
- [ ] Протестировал бота в Telegram

---

💡 **Совет:** Большинство проблем решается перезапуском сервиса или проверкой переменных окружения.

