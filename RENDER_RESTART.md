# 🔄 Возобновление работы на Render

Инструкция по возобновлению работы бота на Render после отключения.

## ⚠️ ВАЖНО: Бот не отвечает после засыпания?

**Проблема:** Render засыпает после 15 минут неактивности, первый запрос занимает 30-50 секунд.

**Решение:** Настройте UptimeRobot за 5 минут - см. [UPGRADE_RENDER.md](./UPGRADE_RENDER.md) для подробной инструкции!

## 🔍 Почему Render отключился?

**Бесплатный план Render:**
- ⚠️ Засыпает после 15 минут неактивности (нет HTTP-запросов)
- ⚠️ Холодный старт ~30 секунд при пробуждении
- ✅ Автоматически просыпается при запросах
- ✅ 750 часов в месяц бесплатно (достаточно для 24/7)

**Это нормально!** Render не "отключился" навсегда, он просто заснул.

## 🚀 Быстрое возобновление

### 🌐 Новый режим: Webhook вместо polling

Чтобы бот просыпался автоматически, мы перевели его на webhook. Теперь Telegram сам стучится в Render при каждом сообщении и будит сервис.

Что нужно сделать один раз:
1. Откройте Render Dashboard → Environment
2. Проверьте переменные:
   - `MODE=webhook`
   - `WEBHOOK_URL=https://telegram-translator-bot-ew8k.onrender.com`
3. Нажмите **Manual Deploy → Deploy latest commit**
4. В логах появится строка `Webhook set to: https://.../webhook`

После этого Render просыпается автоматически, и бот отвечает без задержек.

### Вариант 1: Через Render Dashboard (самый простой)

1. **Войдите в [Render Dashboard](https://dashboard.render.com)**
2. Найдите ваш сервис `telegram-translator-bot`
3. Нажмите кнопку **"Manual Deploy"** → **"Deploy latest commit"**
4. Или просто откройте health check URL: `https://your-service.onrender.com/health`
5. Render автоматически проснется и запустит бота

### Вариант 2: Обновление через GitHub

1. Сделайте любой небольшой коммит:
```bash
git add .
git commit -m "Update: restart bot"
git push origin main
```

2. Render автоматически:
   - Обнаружит изменения
   - Пересоберет сервис
   - Запустит бота

### Вариант 3: Проверка и исправление

1. **Проверьте статус сервиса:**
   - Render Dashboard → ваш сервис → вкладка "Logs"
   - Проверьте, есть ли ошибки

2. **Проверьте переменные окружения:**
   - Render Dashboard → ваш сервис → вкладка "Environment"
   - Убедитесь, что `BOT_TOKEN` установлен
   - Проверьте `TRANSLATOR_PROVIDER=ARGOS` (обновлено)

3. **Перезапустите сервис:**
   - Render Dashboard → ваш сервис → кнопка "Restart"

## 🔧 Обновление конфигурации

### Обновленные настройки:

1. **TRANSLATOR_PROVIDER** изменен с `MYMEMORY` на `ARGOS` (лучшее качество)

2. **Проверьте переменные окружения в Render Dashboard:**

```bash
# Обязательные
BOT_TOKEN=your_bot_token_here

# Переводчик (обновлено)
TRANSLATOR_PROVIDER=ARGOS  # было MYMEMORY

# База данных
DATABASE_URL=postgresql://...  # из PostgreSQL сервиса

# Остальные настройки
MODE=webhook
WEBHOOK_URL=https://telegram-translator-bot-ew8k.onrender.com
LOG_LEVEL=INFO
DEFAULT_CHANNEL_LANGS=en
DEFAULT_USER_LANG=en
```

## 🛠️ Пошаговая инструкция

### Шаг 1: Проверка сервисов

1. Откройте [Render Dashboard](https://dashboard.render.com)
2. Проверьте статус:
   - ✅ **Web Service** `telegram-translator-bot` - должен быть "Live" или "Sleeping"
   - ✅ **PostgreSQL** `telegram-translator-db` - должен быть "Available"

### Шаг 2: Обновление переменных окружения

1. Откройте Web Service → вкладка **"Environment"**
2. Проверьте/обновите:
   - `TRANSLATOR_PROVIDER=ARGOS` (если было `MYMEMORY`)
   - `BOT_TOKEN` - убедитесь, что правильный
   - `DATABASE_URL` - должен быть из PostgreSQL сервиса

### Шаг 3: Перезапуск

1. Нажмите **"Manual Deploy"** → **"Deploy latest commit"**
2. Или нажмите **"Restart"** (если сервис уже запущен)
3. Дождитесь завершения деплоя (2-3 минуты)

### Шаг 4: Проверка работы

1. **Health Check:**
   ```
   https://your-service-name.onrender.com/health
   ```
   Должен вернуть статус 200

2. **Проверка логов:**
   - Render Dashboard → ваш сервис → вкладка "Logs"
   - Ищите: `"Bot started: @your_bot_username"`

3. **Тест бота:**
   - Отправьте `/start` вашему боту в Telegram
   - Бот должен ответить (может быть задержка ~30 сек при пробуждении)

## ⚡ Предотвращение засыпания (ВАЖНО!)

### ❓ Часто задаваемые вопросы:

**Q: Если я закрою макбук, бот будет отвечать с задержкой 30 секунд?**
**A:** Нет! Закрытие вашего компьютера **НЕ влияет** на бота на Render. Бот работает на удаленном сервере Render, а не на вашем компьютере.

**Q: Когда возникает задержка 30 секунд?**
**A:** Задержка возникает **только при первом запросе** после того, как Render заснул (после 15 минут неактивности). Все последующие запросы обрабатываются **мгновенно** без задержки.

**Q: Как избежать задержки вообще?**
**A:** Настройте автоматический ping health check endpoint каждые 10-14 минут. Render не будет засыпать, и задержек не будет.

### Вариант 1: Health Check Ping (рекомендуется, БЕСПЛАТНО)

Настройте внешний сервис для периодического ping:

1. **UptimeRobot** (бесплатно, до 50 мониторов):
   - Зарегистрируйтесь на [uptimerobot.com](https://uptimerobot.com)
   - Добавьте монитор типа "HTTP(s)":
     - URL: `https://your-service.onrender.com/health`
     - Интервал: **10 минут** (чтобы не дать Render заснуть)
     - Метод: GET
   - Render будет получать ping каждые 10 минут и **не будет засыпать**
   - ✅ **Результат: бот всегда отвечает мгновенно, без задержек!**

2. **Cron-job.org** (бесплатно):
   - Зарегистрируйтесь на [cron-job.org](https://cron-job.org)
   - Создайте задачу:
     - URL: `https://your-service.onrender.com/health`
     - Метод: GET
     - Запуск: **каждые 10 минут** (cron: `*/10 * * * *`)
   - ✅ **Результат: бот всегда отвечает мгновенно, без задержек!**

### Вариант 2: Платный план Render

- **Starter Plan** ($7/месяц):
  - ✅ Не засыпает
  - ✅ Нет холодного старта
  - ✅ Больше ресурсов

## 🔍 Диагностика проблем

### Бот не отвечает:

1. **Проверьте логи:**
   ```
   Render Dashboard → ваш сервис → Logs
   ```
   Ищите ошибки (красные строки)

2. **Проверьте BOT_TOKEN:**
   - Убедитесь, что токен правильный
   - Проверьте в логах: `"Bot started: @username"`

3. **Проверьте health check:**
   ```
   curl https://your-service.onrender.com/health
   ```

### Webhook не приходит (бот молчит):

1. Проверьте `WEBHOOK_URL` в переменных окружения (должен совпадать с Render URL)
2. Убедитесь, что `MODE=webhook`
3. В логах должно быть: `"Webhook set to: https://.../webhook"`
4. Если меняли домен Render — обновите `WEBHOOK_URL` и перезапустите сервис

### Ошибки базы данных:

1. **Проверьте PostgreSQL сервис:**
   - Должен быть "Available"
   - Проверьте `DATABASE_URL` в переменных окружения

2. **Проверьте подключение:**
   - В логах должно быть: `"Database (sqlite) initialized successfully"` или `"Database (postgresql) initialized successfully"`

### Сервис постоянно засыпает:

1. **Настройте UptimeRobot** (см. выше)
2. **Или переключитесь на Fly.io** (не засыпает бесплатно)

## 📊 Мониторинг

### Полезные ссылки:

- **Render Dashboard**: [dashboard.render.com](https://dashboard.render.com)
- **Логи**: Dashboard → ваш сервис → вкладка "Logs"
- **Метрики**: Dashboard → ваш сервис → вкладка "Metrics"
- **Health Check**: `https://your-service.onrender.com/health`

## ✅ Чек-лист возобновления

- [ ] Войти в Render Dashboard
- [ ] Проверить статус Web Service
- [ ] Проверить статус PostgreSQL
- [ ] Обновить `TRANSLATOR_PROVIDER=ARGOS` (если нужно)
- [ ] Проверить `BOT_TOKEN` в переменных окружения
- [ ] Нажать "Manual Deploy" или "Restart"
- [ ] Дождаться завершения деплоя
- [ ] Проверить health check
- [ ] Проверить логи на наличие ошибок
- [ ] Протестировать бота в Telegram
- [ ] (Опционально) Настроить UptimeRobot для предотвращения засыпания

## 🎯 После возобновления

1. **Обновите код:**
   ```bash
   git add .
   git commit -m "Update: restart on Render"
   git push origin main
   ```

2. **Render автоматически задеплоит** (если подключен GitHub)

3. **Настройте мониторинг** (UptimeRobot) чтобы предотвратить засыпание

---

🎉 **Готово!** Бот снова работает на Render!

💡 **Совет:** Для постоянной работы без засыпания рассмотрите Fly.io (см. `FLY_DEPLOY.md`)

