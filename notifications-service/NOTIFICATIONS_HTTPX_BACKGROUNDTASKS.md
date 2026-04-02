## notifications-service: httpx + BackgroundTasks (что сделано и как работает)

В этом сервисе `notifications-service` (FastAPI + PostgreSQL) реализованы две доработки:
1) асинхронный эндпоинт, который получает данные из публичного API через `httpx`;
2) фоновое логирование действий пользователя через `BackgroundTasks` в одном из POST-эндпоинтов.

Ниже подробно описано, что именно было изменено, какие эндпоинты появились и как проверить работу.

---

## 1) Изменения зависимостей

В файл `requirements.txt` добавлена зависимость `httpx`, потому что внешний HTTP-запрос выполняется из обработчика FastAPI:

- `Library_Django/notifications-service/requirements.txt`

После этого в коде можно использовать `httpx.AsyncClient(...)` внутри `async def` endpoint.

---

## 2) Асинхронный endpoint через httpx (GET)

### Эндпоинт

- `GET /notifications/from-external`

Этот endpoint делает HTTP-запрос к JSONPlaceholder и на основе ответа создаёт уведомление в таблице `notifications`.

### Какой API используется

По параметру `external_post_id` формируется URL:

- `https://jsonplaceholder.typicode.com/posts/{external_post_id}`

Из JSON ответа берутся поля:
- `title` -> поле `title` уведомления
- `body`  -> поле `message` уведомления

### Параметры запроса (Query)

`user_id` (int) — пользователь, которому создаётся уведомление  
`external_post_id` (int) — id поста в JSONPlaceholder  
`type` (NotificationType) — тип уведомления  
`priority` (NotificationPriority, по умолчанию `medium`)  
`channel` (NotificationChannel, по умолчанию `in_app`)

### Пример запроса (curl)

```bash
curl -X GET "http://localhost:8000/notifications/from-external?user_id=789&external_post_id=1&type=system&priority=medium&channel=in_app"
```

### Что происходит внутри

1. FastAPI вызывает обработчик `async def` для `GET /notifications/from-external`.
2. Внутри создаётся `httpx.AsyncClient(timeout=10.0)`.
3. Выполняется `await client.get(url)`.
4. Если внешний сервис вернул ошибку статуса — обрабатывается как ошибка внешнего API.
5. Если внешний элемент не найден/пустой или в ответе нет `body` — возвращается ошибка 404.
6. Извлечённые `title/body` формируют поля уведомления.
7. В БД создаётся запись `models.Notification` с `read_at=None`.
8. Запись возвращается клиенту в формате `schemas.NotificationResponse`.

### Обработка ошибок (важно про 502)

Раньше в реализации ошибка 502 могла возникать из-за ситуации, когда в ответе внешнего API отсутствовал ожидаемый контент.
Сейчас:

- `502` используется только для проблем запроса к внешнему API (таймаут, сеть, внешний HTTP-статус не 2xx, невалидный JSON);
- `404` возвращается если внешний элемент не найден (пустой/неподходящий ответ) или если в ответе нет `body`.

Формально:
- `httpx.HTTPStatusError` -> `502`
- `httpx.RequestError` / `ValueError` -> `502`
- пустой ответ / отсутствует `body` -> `404`

### Примечание про схему

В `app/schemas.py` изначально была добавлена схема `NotificationFromExternalCreate` под POST-версию.
Поскольку эндпоинт был переведён на `GET`, текущая версия использует query-параметры и напрямую не использует `NotificationFromExternalCreate` (схема остаётся в коде на будущее).

Файл:
- `Library_Django/notifications-service/app/schemas.py`

---

## 3) BackgroundTasks для логирования в POST /notifications

### Эндпоинт

- `POST /notifications`

### Что добавлено

В `POST /notifications` добавлен параметр `background_tasks: BackgroundTasks`.
После успешного коммита в БД в фоне ставится задача логирования.

Файлы:
- `Library_Django/notifications-service/app/main.py`

### Что логируется

Логгер-функция `log_notification_created(...)` пишет сообщение в стандартный логгер сервиса (`logger.info(...)`).

Формат сообщения:

- `user_action=create_notification user_id=... notification_id=... type=... channel=...`

### Когда выполняется фон

Порядок работы:

1. В синхронном обработчике создаётся объект `Notification`.
2. Делается `db.commit()` и `db.refresh()`.
3. Сразу после коммита планируется фоновая задача через `background_tasks.add_task(...)`.
4. Response клиенту отправляется обычным образом.
5. После отправки ответа задача логирования выполняется в фоне.

### Где смотреть логи

Логи будут видны в stdout процесса `uvicorn`, например в том терминале, где запущен:

- `uvicorn app.main:app --reload`

---

## 4) Как проверить вручную (минимальный чеклист)

1. Убедиться, что сервис поднят (`/docs` в браузере открывается).
2. Выполнить `GET /notifications/from-external` примером выше.
3. Убедиться, что в ответе пришло созданное уведомление.
4. Выполнить `POST /notifications` (как раньше) и проверить, что после ответа в логах появилась строка `user_action=create_notification ...`.

