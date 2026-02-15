# 🔍 Диагностика: Бот не отвечает 5+ минут

## ❌ Проблема

Бот не отвечает на команды 5+ минут (даже после пробуждения Render).

## 🔍 Возможные причины

### 1. Render сервис упал или завис
**Проверка:**
- Render Dashboard → ваш сервис → статус
- Должен быть "Live" или "Sleeping" (не "Failed")
- Проверьте логи на ошибки

**Решение:**
- Если "Failed" → перезапустите сервис
- Если есть ошибки в логах → исправьте их

### 2. Проблема с polling (бот не получает обновления)
**Проверка:**
- Render Dashboard → Logs
- Ищите: `"Bot started: @username"`
- Ищите ошибки: `"Error in polling"` или `"Failed to get updates"`

**Возможные причины:**
- Бот не запустился
- Ошибка при инициализации
- Проблема с подключением к Telegram API

**Решение:**
- Перезапустите сервис в Render Dashboard
- Проверьте `BOT_TOKEN` в переменных окружения

### 3. Блокирующая операция в обработчике
**Проверка:**
- Render Dashboard → Logs
- Ищите, где застрял обработчик
- Ищите долгие операции (база данных, переводы)

**Возможные причины:**
- Долгий запрос к базе данных
- Таймаут при переводе (ARGOS недоступен)
- Бесконечный цикл или deadlock

**Решение:**
- Проверьте логи на последнюю операцию перед зависанием
- Убедитесь, что нет блокирующих операций

### 4. Проблема с базой данных
**Проверка:**
- Render Dashboard → Logs
- Ищите: `"Database connection failed"` или `"Database health check failed"`

**Возможные причины:**
- PostgreSQL сервис недоступен
- Неправильный `DATABASE_URL`
- Блокировка базы данных

**Решение:**
- Проверьте PostgreSQL сервис (должен быть "Available")
- Проверьте `DATABASE_URL` в переменных окружения
- Перезапустите PostgreSQL сервис

### 5. Rate limiting или throttling
**Проверка:**
- Render Dashboard → Logs
- Ищите: `"Rate limit exceeded"`

**Решение:**
- Подождите и попробуйте снова
- Или увеличьте лимиты в настройках

## 🛠️ Пошаговая диагностика

### Шаг 1: Проверка статуса Render
```
1. Откройте Render Dashboard
2. Найдите сервис telegram-translator-bot
3. Проверьте статус:
   - ✅ "Live" - работает
   - ⚠️ "Sleeping" - заснул (нормально)
   - ❌ "Failed" - упал (нужно исправить)
```

### Шаг 2: Проверка логов
```
1. Render Dashboard → ваш сервис → Logs
2. Прокрутите до последних записей
3. Ищите:
   - ✅ "Bot started: @username" - бот запущен
   - ✅ "Health check server started" - сервер работает
   - ❌ ERROR - ошибки
   - ❌ Exception - исключения
```

### Шаг 3: Проверка health check
```
Откройте в браузере:
https://telegram-translator-bot-ew8k.onrender.com/health

Ожидаемый результат:
{"status": "healthy", "database": "ok", "bot": "ok"}

Если не работает:
- ❌ Страница не открывается → Render упал
- ❌ {"status": "unhealthy"} → проблема с ботом/БД
- ❌ {"status": "error"} → ошибка в коде
```

### Шаг 4: Проверка переменных окружения
```
Render Dashboard → ваш сервис → Environment

Обязательные:
- ✅ BOT_TOKEN - должен быть установлен
- ✅ DATABASE_URL - должен быть из PostgreSQL
- ✅ MODE=polling
```

### Шаг 5: Тест бота
```
1. Отправьте /start боту
2. Подождите 30-60 секунд (максимум)
3. Если не отвечает → проблема подтверждена
```

## 🔧 Быстрое исправление

### Если Render упал:
1. Render Dashboard → ваш сервис → "Restart"
2. Дождитесь перезапуска (2-3 минуты)
3. Проверьте логи

### Если бот не запускается:
1. Проверьте `BOT_TOKEN` в переменных окружения
2. Проверьте логи на ошибки инициализации
3. Пересоберите сервис: "Manual Deploy" → "Deploy latest commit"

### Если база данных недоступна:
1. Проверьте PostgreSQL сервис (должен быть "Available")
2. Проверьте `DATABASE_URL`
3. Перезапустите PostgreSQL сервис

## 📊 Что проверить в логах

### ✅ Нормальные записи:
```
INFO - Bot started: @your_bot_username
INFO - Health check server started on http://0.0.0.0:XXXX
INFO - Database (sqlite) initialized successfully
```

### ❌ Проблемные записи:
```
ERROR - Failed to initialize database
ERROR - Bot token invalid
ERROR - Database connection failed
ERROR - Error in polling
Exception - ...
```

## 🆘 Если ничего не помогает

1. **Скопируйте логи:**
   - Render Dashboard → Logs → последние 100 строк
   
2. **Проверьте статус Render:**
   - [status.render.com](https://status.render.com)

3. **Пересоберите сервис:**
   - Render Dashboard → "Manual Deploy" → "Deploy latest commit"

4. **Откатитесь к предыдущей версии:**
   - Render Dashboard → Events → "Rollback"

---

💡 **Совет:** После настройки UptimeRobot (см. UPGRADE_RENDER.md) Render не будет засыпать, и эта проблема должна исчезнуть.

